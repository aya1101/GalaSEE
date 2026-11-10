import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def configured_origins() -> list[str]:
    raw_origins = os.getenv("WEB_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(
    title="TideAware API",
    version="0.1.0",
    description="Evidence-aware coastal intelligence API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tideaware-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/meta")
def metadata() -> dict[str, str]:
    return {
        "name": "TideAware",
        "version": "0.1.0",
        "stage": "initial-scaffold",
        "data_status": "demo-data-not-connected",
    }
