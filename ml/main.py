from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Response, status
from ml.db.connection import init_pool, close_pool, get_connection

# from ml.routers import categorize, anomaly, forecast

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()

app = FastAPI(
    title="Finance Tracker ML Service",
    description=(
        "Read-only ML layer for the finance-tracker project. "
        "Endpoints for categorisation, anomaly detection, and spending forecast."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/health", tags=["meta"])
async def health(response: Response):

    artifacts_base = os.path.join(os.path.dirname(__file__), "artifacts")
    models = ["categorizer", "anomaly", "forecaster"]

    model_status = {
        m: "ready" if os.path.exists(os.path.join(artifacts_base, m, "metadata.json"))
        else "not_trained"
        for m in models
    }

    db_status = "connected"
    service_status = "ok"

    if all(v == "not_trained" for v in model_status.values()):
        service_status = "not_trained"

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
    except Exception as e:
        db_status = f"disconnected ({e})"
        service_status = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE 

    return {
        "service": "finance-tracker-ml",
        "status": service_status,
        "db": db_status,
        "models": model_status,
    }


# app.include_router(categorize.router, prefix="/categorize", tags=["categorize"])
# app.include_router(anomaly.router,    prefix="/anomaly",    tags=["anomaly"])
# app.include_router(forecast.router,   prefix="/forecast",   tags=["forecast"])