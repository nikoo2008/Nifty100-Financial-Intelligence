"""Health endpoint."""

from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter

from src.api.common import DB_PATH

router = APIRouter(tags=["health"])
START_TIME = time.monotonic()


@router.get("/health")
def health():
    """Return API status and SQLite row counts."""
    with sqlite3.connect(DB_PATH) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }
    return {
        "status": "ok",
        "db_row_counts": counts,
        "uptime_seconds": round(time.monotonic() - START_TIME, 3),
        "version": "1.0.0",
    }
