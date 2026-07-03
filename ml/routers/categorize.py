"""
Categorisation router — three endpoints:

  POST /categorize/predict   → top-N category suggestions for a new transaction
  POST /categorize/retrain   → trigger model training (or retraining)
  GET  /categorize/status    → current model metadata without retraining
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ml.db.connection import get_connection
from ml.models import categorizer

router = APIRouter()


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

async def get_db():
    async with get_connection() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    member_id:  int
    amount:     Decimal     = Field(..., gt=0)
    type:       str         = Field(..., pattern="^(income|expense|transfer)$")
    method:     Optional[str] = Field(None, pattern="^(upi|cash|internet_banking|cheque)$")
    date:       datetime
    note:       Optional[str] = None
    account_id: int
    top_n:      int         = Field(default=3, ge=1, le=10)


class CategorySuggestion(BaseModel):
    category_id:   int
    category_name: str
    confidence:    float


class PredictResponse(BaseModel):
    status:      str                        # "ok" | "not_trained"
    suggestions: list[CategorySuggestion]
    warning:     Optional[str] = None       # "low_sample_count" | None


class RetrainRequest(BaseModel):
    member_id: Optional[int] = Field(
        default=None,
        description="Restrict training to one member. Omit to train on all members."
    )


class RetrainResponse(BaseModel):
    model:        str
    val_accuracy: float
    n_samples:    int
    n_classes:    int
    trained_at:   str
    warning:      Optional[str] = None


class StatusResponse(BaseModel):
    status:       str           # "ready" | "not_trained"
    model:        Optional[str]         = None
    val_accuracy: Optional[float]       = None
    n_samples:    Optional[int]         = None
    n_classes:    Optional[int]         = None
    trained_at:   Optional[str]         = None
    warning:      Optional[str]         = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Suggest categories for a new transaction",
)
async def predict(
    body: PredictRequest,
    conn=Depends(get_db),
):
    
    result = await categorizer.predict(
        conn,
        member_id=body.member_id,
        amount=body.amount,
        type_=body.type,
        method=body.method,
        date=body.date,
        note=body.note,
        account_id=body.account_id,
        top_n=body.top_n,
    )
    return PredictResponse(
        status=result["status"],
        suggestions=[CategorySuggestion(**s) for s in result["suggestions"]],
        warning=result.get("warning"),
    )


@router.post(
    "/retrain",
    response_model=RetrainResponse,
    summary="Train or retrain the categorisation model",
    status_code=status.HTTP_200_OK,
)
async def retrain(
    body: RetrainRequest,
    conn=Depends(get_db),
):
    
    try:
        metadata = await categorizer.train(conn, member_id=body.member_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return RetrainResponse(**metadata)


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Check categoriser model status",
)
async def model_status():
    
    metadata = categorizer.get_metadata()
    if metadata is None:
        return StatusResponse(status="not_trained")
    return StatusResponse(status="ready", **metadata)