"""Reusable, vectorised transform helpers shared by all pipelines.

These replace the per-row ``DataFrame.iterrows()`` loops that previously
appeared in every pipeline. ``explode_records`` in particular turns an
O(rows) Python loop into a vectorised pandas ``explode`` — typically 10-100x
faster on large frames — while preserving the original output semantics
(each nested dict becomes a row with the parent id attached).
"""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def to_int64(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Coerce ``columns`` to pandas nullable ``Int64`` in place; returns df."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def to_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Coerce ``columns`` to float (NaN on failure) in place; returns df."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def select(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Return a copy with only the columns that actually exist (order kept)."""
    cols = [c for c in columns if c in df.columns]
    return df[cols].copy()


def explode_records(raw: pd.DataFrame, parent_key, list_col: str) -> pd.DataFrame:
    """Explode a column of lists-of-dicts into a flat child DataFrame.

    For every row in ``raw`` whose ``list_col`` is a non-empty list, each
    element (a dict) becomes a row in the result with the parent column(s)
    attached. ``parent_key`` may be a single column name or a list of names.
    Equivalent to the old ``iterrows`` + append loop, but vectorised.
    """
    parents = [parent_key] if isinstance(parent_key, str) else list(parent_key)
    if list_col not in raw.columns or not all(p in raw.columns for p in parents):
        return pd.DataFrame()

    sub = raw[parents + [list_col]]
    mask = sub[list_col].apply(lambda v: isinstance(v, list) and len(v) > 0)
    sub = sub[mask]
    if sub.empty:
        return pd.DataFrame()

    exploded = sub.explode(list_col, ignore_index=True)
    items = pd.DataFrame(exploded[list_col].tolist())
    for parent in parents:
        items[parent] = exploded[parent].values
    return items


def nested_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that contain at least one list value."""
    return [c for c in df.columns if df[c].apply(lambda v: isinstance(v, list)).any()]
