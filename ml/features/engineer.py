"""
Transforms TransactionRecord dataclasses into ML-ready feature matrices.
"""

from __future__ import annotations
import math
import pandas as pd
from ml.features.extractor import TransactionRecord

# ---------------------------------------------------------------------------
# Constants — column name registry so models reference names
# ---------------------------------------------------------------------------

# Numeric features used by all models
NUMERIC_FEATURES = [
    "amount",
    "log_amount",
    "day_of_week",
    "day_of_month",
    "week_of_month",
    "month",
    "days_until_month_end",
    "is_weekend",
    "is_start_of_month",
    "is_end_of_month",
    "z_score_7d",
    "z_score_30d",
    "tx_freq_7d",
    "tx_freq_30d",
    "note_length",
    "note_is_null",
]

# One-hot / label-encoded categoricals
CATEGORICAL_FEATURES = [
    "method",        # upi | cash | internet_banking | cheque | unknown
    "type",          # income | expense | transfer
    "account_type",  # savings | current | credit | …
    "bank_name",     # hdfc | sbi | icici | …
]

# Text feature column (TF-IDF vector — categorizer only)
TEXT_COLUMN = "note_clean"

# Label columns used in training frames
LABEL_COLUMN = "category_id"
LABEL_NAME_COLUMN = "category_name"  # human-readable, kept for debugging only

# Known method values — any unseen value maps to 'unknown'
_KNOWN_METHODS = {"upi", "cash", "internet_banking", "cheque"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _week_of_month(day: int) -> int:
    """Return which week of the month a day falls in (1-indexed)."""
    return math.ceil(day / 7)


def _days_until_month_end(date: pd.Timestamp) -> int:
    """Days remaining in the month (inclusive of the given day)."""
    return date.days_in_month - date.day


def _safe_zscore(
    amount: float,
    mean: float | None,
    std: float | None,
) -> float:
    if mean is None or std is None or std == 0:
        return 0.0
    return (amount - mean) / std


def _normalise_method(method: str | None) -> str:
    if method and method.lower() in _KNOWN_METHODS:
        return method.lower()
    return "unknown"


def _record_to_raw_dict(
    record: TransactionRecord,
    stats: dict,
) -> dict:
    """
    Convert a single TransactionRecord + rolling stats dict into a flat
    dictionary of raw feature values. No encoding or scaling here.
    """
    ts = pd.Timestamp(record.date)
    amount = float(record.amount)

    row: dict = {}

    # amount
    row["amount"] = amount
    row["log_amount"] = math.log1p(abs(amount))  # log1p avoids log(0), abs avoids domain error

    # temporal
    row["day_of_week"] = ts.dayofweek
    row["day_of_month"] = ts.day
    row["week_of_month"] = _week_of_month(ts.day)
    row["month"] = ts.month
    row["days_until_month_end"] = _days_until_month_end(ts)
    row["is_weekend"] = int(ts.dayofweek >= 5)
    row["is_start_of_month"] = int(ts.day <= 5)
    row["is_end_of_month"] = int(ts.day >= 25)

    # rolling stats / anomaly features
    row["z_score_7d"] = _safe_zscore(amount, stats.get("avg_7d"), stats.get("std_7d"))
    row["z_score_30d"] = _safe_zscore(amount, stats.get("avg_30d"), stats.get("std_30d"))
    row["tx_freq_7d"] = stats.get("count_7d", 0)
    row["tx_freq_30d"] = stats.get("count_30d", 0)

    # text proxy features
    row["note_clean"] = record.note or ""
    row["note_length"] = len(record.note) if record.note else 0
    row["note_is_null"] = int(record.note is None)

    # categorical
    row["method"] = _normalise_method(record.method)
    row["type"] = record.type
    row["account_type"] = (record.account_type or "unknown").lower()
    row["bank_name"] = (record.bank_name or "unknown").lower()

    # pass-through identifiers (not used as features, handy for debugging)
    row["transaction_id"] = record.transaction_id
    row["member_id"] = record.member_id
    row["date"] = ts

    return row


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_training_frame(
    records: list[TransactionRecord],
    stats_map: dict[int, dict],
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Build a labelled feature frame suitable for model training/eval.
    """
    if not records:
        columns = (
            NUMERIC_FEATURES + CATEGORICAL_FEATURES
            + [TEXT_COLUMN, "transaction_id", "member_id", "date"]
        )
        empty = pd.DataFrame(columns=columns)
        return empty, pd.Series(dtype=int), pd.Series(dtype=str)

    rows = []
    for rec in records:
        stats = stats_map.get(rec.transaction_id, {})
        row = _record_to_raw_dict(rec, stats)
        row[LABEL_COLUMN] = rec.category_id
        row[LABEL_NAME_COLUMN] = rec.category_name
        rows.append(row)

    df = pd.DataFrame(rows)

    # Drop rows where we somehow ended up without a label
    df = df.dropna(subset=[LABEL_COLUMN])
    df[LABEL_COLUMN] = df[LABEL_COLUMN].astype(int)

    y_id = df.pop(LABEL_COLUMN)
    y_name = df.pop(LABEL_NAME_COLUMN)

    return df, y_id, y_name


def build_inference_row(
    record: TransactionRecord,
    stats: dict,
) -> pd.DataFrame:
    """
    Build a single-row feature DataFrame for a new, unlabelled transaction.
    """
    row = _record_to_raw_dict(record, stats)
    return pd.DataFrame([row])


def get_feature_columns() -> dict[str, list | str]:
    """
    Return the canonical feature column lists.
    Models call this to know exactly which columns to select from the frame.
    """
    return {
        "numeric": NUMERIC_FEATURES,
        "categorical": CATEGORICAL_FEATURES,
        "text": TEXT_COLUMN,
        "all": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        "label": LABEL_COLUMN,
        "label_name": LABEL_NAME_COLUMN,
    }