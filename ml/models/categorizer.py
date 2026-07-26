from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report

from ml.features.engineer import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TEXT_COLUMN,
    build_inference_row,
    build_training_frame,
)
from ml.features.extractor import (
    fetch_for_inference,
    fetch_labeled,
    fetch_member_recent_stats,
    fetch_stats_for_records,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_SAMPLES  = 50    # hard floor — refuse training below this
WARN_SAMPLES = 100   # soft floor — warn about likely low accuracy

_TOP_N = 3           # default number of suggestions returned per inference

_ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts" / "categorizer"

# ---------------------------------------------------------------------------
# In-memory artifact cache
# Populated on first predict call, cleared after each retrain.
# category_names cached here to avoid a disk read on every inference call.
# ---------------------------------------------------------------------------

_pipeline:        Pipeline     | None = None
_label_encoder:   LabelEncoder | None = None
_category_names:  dict         | None = None
_warning:         str          | None = None

def _clear_cache() -> None:
    global _pipeline, _label_encoder, _category_names, _warning
    _pipeline       = None
    _label_encoder  = None
    _category_names = None
    _warning        = None

async def _load_artifacts() -> tuple[Pipeline, LabelEncoder, dict, str | None]:
    global _pipeline, _label_encoder, _category_names, _warning

    if _pipeline is None:
        pipeline_path = _ARTIFACTS_DIR / "pipeline.joblib"
        encoder_path  = _ARTIFACTS_DIR / "label_encoder.joblib"
        metadata_path = _ARTIFACTS_DIR / "metadata.json"

        if not pipeline_path.exists() or not encoder_path.exists():
            raise FileNotFoundError(
                "Categoriser artifacts not found. POST /categorize/retrain to train."
            )

        # Offload blocking disk reads to a thread
        _pipeline      = await asyncio.to_thread(joblib.load, pipeline_path)
        _label_encoder = await asyncio.to_thread(joblib.load, encoder_path)
        metadata       = json.loads(
            await asyncio.to_thread(metadata_path.read_text)
        )
        _category_names = metadata.get("category_names", {})
        _warning        = metadata.get("warning")

    return _pipeline, _label_encoder, _category_names, _warning


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------

def _build_pipeline() -> Pipeline:
    """
    ColumnTransformer handles three feature groups then feeds XGBClassifier.
    remainder='drop' silently discards pass-through columns
    (transaction_id, member_id, date) so they never reach the model.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
                CATEGORICAL_FEATURES,
            ),
            (
                "text",
                TfidfVectorizer(
                    max_features=300,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                ),
                TEXT_COLUMN,
            ),
        ],
        remainder="drop",
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
            tree_method="hist",
        )),
    ])


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

async def train(conn, member_id: int | None = None) -> dict:
    """
    Fetch labelled transactions, fit the pipeline, persist artifacts atomically.
    Returns metadata dict echoed back by the /categorize/retrain endpoint.

    Parameters
    ----------
    conn        : async psycopg3 connection from the read-only pool
    member_id   : None = all members (default)

    Raises
    ------
    ValueError  if fewer than MIN_SAMPLES labelled transactions exist.
    """
    # 1. Fetch all labeled records
    records  = await fetch_labeled(conn, member_id=member_id)
    n_samples = len(records)

    if n_samples < MIN_SAMPLES:
        raise ValueError(
            f"Insufficient data: {n_samples} labelled transactions found, "
            f"minimum required is {MIN_SAMPLES}."
        )

    warning = "low_sample_count" if n_samples < WARN_SAMPLES else None

    # 2. Build feature matrix
    stats_map = await fetch_stats_for_records(conn, records)
    df, y_raw, y_name = build_training_frame(records, stats_map)

    # 3. Encode labels to contiguous integers
    le = LabelEncoder()
    y  = le.fit_transform(y_raw)

    # Capture category_id → name mapping at train time so inference never needs a DB call just to resolve a name.
    category_names: dict[str, str] = {
        str(cat_id): name
        for cat_id, name in zip(y_raw.tolist(), y_name.tolist())
    }

    # 4. Train / val split — stratify where possible, fall back to random
    try:
        X_train, X_val, y_train, y_val = train_test_split(
            df, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_val, y_train, y_val = train_test_split(
            df, y, test_size=0.2, random_state=42
        )

    # 5. Build and fit — offloaded to thread to avoid blocking the event loop
    pipeline = _build_pipeline()
    await asyncio.to_thread(pipeline.fit, X_train, y_train)

    # 6. Evaluate
    y_pred       = await asyncio.to_thread(pipeline.predict, X_val)
    val_accuracy = round(float(accuracy_score(y_val, y_pred)), 4)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, df, y, cv=cv, scoring="f1_macro")
    cv_f1_macro = round(float(cv_scores.mean()), 4)
    cv_f1_std   = round(float(cv_scores.std()), 4)

    # Per-class report for debugging — logged but not exposed in API response
    report = classification_report(y_val, y_pred, 
                                target_names=[str(c) for c in le.classes_])
    print(f"[categorizer] Classification report:\n{report}", flush=True)

    # 7. Persist artifacts atomically
    # Write to .tmp files first, then rename — rename is atomic on POSIX systems.
    # Prevents a concurrent predict call from reading a half-written file.
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_tmp = _ARTIFACTS_DIR / "pipeline.tmp.joblib"
    encoder_tmp  = _ARTIFACTS_DIR / "label_encoder.tmp.joblib"
    metadata_tmp = _ARTIFACTS_DIR / "metadata.tmp.json"

    metadata = {
        "model":          "xgboost",
        "val_accuracy":   val_accuracy,
        "cv_f1_macro":    cv_f1_macro,
        "cv_f1_std":      cv_f1_std,
        "n_samples":      n_samples,
        "n_classes":      int(len(le.classes_)),
        "trained_at":     datetime.now(timezone.utc).isoformat(),
        "warning":        warning,
        "category_names": category_names,
    }

    await asyncio.to_thread(joblib.dump, pipeline, pipeline_tmp)
    await asyncio.to_thread(joblib.dump, le, encoder_tmp)
    await asyncio.to_thread(
        metadata_tmp.write_text, json.dumps(metadata, indent=2)
    )

    # Atomic rename — all three files swap together
    pipeline_tmp.replace(_ARTIFACTS_DIR / "pipeline.joblib")
    encoder_tmp.replace(_ARTIFACTS_DIR / "label_encoder.joblib")
    metadata_tmp.replace(_ARTIFACTS_DIR / "metadata.json")

    # 8. Invalidate cache so next predict loads fresh artifacts
    _clear_cache()

    return {k: v for k, v in metadata.items() if k != "category_names"}


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

async def predict(
    conn,
    member_id: int,
    amount: Decimal,
    type_: str,
    method: str | None,
    date: datetime,
    note: str | None,
    account_id: int,
    top_n: int = _TOP_N,
) -> dict:
    """
    Predict the most likely categories for a new unlabelled transaction.
    Returns top-N suggestions sorted by confidence descending.

    Returns
    -------
    {
        "status":      "ok" | "not_trained",
        "suggestions": [
            {"category_id": 3, "category_name": "Food", "confidence": 0.82},
            ...
        ],
        "warning": null | "low_sample_count"
    }
    """
    # Load artifacts — return early if not yet trained
    try:
        pipeline, le, category_names, warning = await _load_artifacts()
    except FileNotFoundError:
        return {"status": "not_trained", "suggestions": [], "warning": None}


    # Build single inference row
    record = await fetch_for_inference(
        conn,
        member_id=member_id,
        amount=amount,
        type_=type_,
        method=method,
        date=date,
        note=note,
        account_id=account_id,
    )
    stats  = await fetch_member_recent_stats(conn, member_id, date)
    row_df = build_inference_row(record, stats)

    # Offload CPU-bound predict_proba to thread
    proba       = await asyncio.to_thread(pipeline.predict_proba, row_df)
    proba       = proba[0]    # shape: (n_classes,)
    top_indices = np.argsort(proba)[::-1][:top_n]

    suggestions = []
    for idx in top_indices:
        cat_id = int(le.inverse_transform([idx])[0])
        suggestions.append({
            "category_id":   cat_id,
            "category_name": category_names.get(str(cat_id), "Unknown"),
            "confidence":    round(float(proba[idx]), 4),
        })

    return {
        "status":      "ok",
        "suggestions": suggestions,
        "warning":     warning,
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def get_metadata() -> dict | None:
    """Return persisted training metadata, or None if not yet trained."""
    path = _ARTIFACTS_DIR / "metadata.json"
    if not path.exists():
        return None
    metadata = json.loads(path.read_text())
    return {k: v for k, v in metadata.items() if k != "category_names"}
