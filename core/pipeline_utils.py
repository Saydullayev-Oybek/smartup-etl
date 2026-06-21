"""Shared output helpers for pipelines.

Centralises the "write Excel (optional) + load to DB" step so every pipeline
emits its tables the same way, honours the ``WRITE_EXCEL`` flag, and routes
through the idempotent loader with a merge key.
"""
from __future__ import annotations

import os

import pandas as pd

from core.config import OUTPUT_DIR, WRITE_EXCEL
from core.loader import save_to_db
from core.logging_config import get_logger
from core.validation import validate_table

log = get_logger(__name__)


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_excel(df: pd.DataFrame, filename: str) -> None:
    """Write ``df`` to ``OUTPUT_DIR/filename`` when Excel output is enabled."""
    if not WRITE_EXCEL:
        return
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_excel(path, index=False)
    log.debug("Wrote %s (%d rows)", path, len(df))


def emit(
    df: pd.DataFrame,
    *,
    excel_name: str,
    table: str,
    key: str | None = None,
    unique: bool = False,
) -> None:
    """Persist a table: validate + optional Excel export + idempotent DB load.

    ``key`` is the parent-entity id used to merge in upsert mode. Set
    ``unique=True`` for dimension tables whose ``key`` is a true primary key.
    """
    validate_table(df, table, key=key, unique=unique)
    write_excel(df, excel_name)
    save_to_db(df, table, key=key)


