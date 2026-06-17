"""Lightweight data-quality checks run before loading.

By default failures are logged as warnings (non-blocking) so a single dodgy
record never silently corrupts a load *and* never hard-stops the batch. Set
``VALIDATION_STRICT=true`` to raise :class:`DataValidationError` instead — use
that in CI / staging to catch problems early.
"""
from __future__ import annotations

import os
from collections.abc import Iterable

import pandas as pd

from exceptions import DataValidationError
from logging_config import get_logger

log = get_logger(__name__)


def _strict() -> bool:
    return os.getenv("VALIDATION_STRICT", "false").strip().lower() in {"1", "true", "yes", "on"}


def _fail(message: str) -> None:
    if _strict():
        raise DataValidationError(message)
    log.warning("Validation: %s", message)


def validate_table(
    df: pd.DataFrame,
    table: str,
    *,
    key: str | None = None,
    unique: bool = False,
    non_null: Iterable[str] = (),
) -> pd.DataFrame:
    """Validate ``df`` before loading ``table``. Returns ``df`` unchanged.

    - ``key`` must contain no null values (it drives the merge).
    - ``unique=True`` additionally asserts ``key`` is unique (dimensions).
    - ``non_null`` columns must contain no nulls.
    """
    if df is None or df.empty:
        return df

    if key and key in df.columns:
        n_null = int(df[key].isna().sum())
        if n_null:
            _fail(f"{table}: {n_null} row(s) with null merge key '{key}'")
        if unique:
            n_dup = int(df[key].duplicated().sum())
            if n_dup:
                _fail(f"{table}: {n_dup} duplicate '{key}' value(s)")

    for col in non_null:
        if col in df.columns:
            n_null = int(df[col].isna().sum())
            if n_null:
                _fail(f"{table}: {n_null} null value(s) in required column '{col}'")

    return df
