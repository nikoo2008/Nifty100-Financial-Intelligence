"""FastAPI entry point for Nifty 100 Financial Intelligence."""

from __future__ import annotations

import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.common import ROOT
from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    version="1.0.0",
    description="Read-only financial analytics API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Log method, path, and response time for each request."""
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s %.2fms %s",
        request.method,
        request.url.path,
        elapsed,
        response.status_code,
    )
    return response


prefix = "/api/v1"
for module in [
    health,
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
]:
    app.include_router(module.router, prefix=prefix)


@app.on_event("startup")
def export_openapi():
    """Export the OpenAPI document when the application starts."""
    try:
        (ROOT / "docs").mkdir(exist_ok=True)
        (ROOT / "docs" / "openapi.json").write_text(
            json.dumps(app.openapi(), indent=2), encoding="utf-8"
        )
    except OSError:
        logger.exception("Could not write OpenAPI export")
