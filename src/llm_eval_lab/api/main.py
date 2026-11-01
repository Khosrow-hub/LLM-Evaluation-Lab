"""
FastAPI application factory.

Security
--------
* CORS is configured explicitly from settings.cors_origins.
* The server binds to 127.0.0.1 by default.
* Stack traces are never returned to the browser.
* API keys are never returned in any response.
* File uploads are validated for type and size.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_eval_lab.api.routes import comparisons, datasets, experiments, reports
from llm_eval_lab.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if settings.api_host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            "SECURITY WARNING: LLM Evaluation Lab API is binding to non-loopback host '%s'. "
            "The API does not enforce authentication and is intended for trusted local development. "
            "Do not expose this service to untrusted networks without an authenticating reverse proxy.",
            settings.api_host,
        )
    logger.info("LLM Evaluation Lab API starting.")
    yield
    logger.info("LLM Evaluation Lab API shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LLM Evaluation Lab API",
        description="Backend API for LLM Evaluation Lab.",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    # CORS — restrict to configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Accept"],
    )

    # Routers
    app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
    app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
    app.include_router(comparisons.router, prefix="/api/comparisons", tags=["comparisons"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app
