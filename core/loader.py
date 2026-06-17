"""Load DataFrames into PostgreSQL.

Two strategies are supported (configurable via ``LOAD_STRATEGY``):

``upsert`` (default, recommended)
    Idempotent merge. Within a single transaction the loader deletes the rows
    whose ``key`` value appears in the incoming batch and re-inserts the batch.
    Because every table refreshes by a single parent-entity id (a dimension by
    its own id, a child/bridge table by its parent id), this preserves history
    for entities *not* in the current batch, keeps the table (and its indexes)
    in place, and is safe to re-run.

``replace`` (legacy)
    Drops and recreates the whole table on every run. Kept for backward
    compatibility; not recommended for production.

Both paths run inside a transaction, so a mid-run failure rolls back cleanly
instead of leaving a half-loaded table.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.engine import Engine

from core.config import DB_URL, LOAD_STRATEGY
from core.exceptions import LoadError
from core.logging_config import get_logger

log = get_logger(__name__)

# Keep multi-row INSERTs comfortably under driver parameter limits
# (SQLite caps at 32766; PostgreSQL at 65535). chunksize is derived per table.
_MAX_BIND_PARAMS = 20_000
_DELETE_BATCH = 1_000


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide singleton SQLAlchemy engine."""
    return create_engine(DB_URL, pool_pre_ping=True, future=True)


def dispose_engine() -> None:
    """Dispose the cached engine (mainly for tests/teardown)."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()


def _safe_chunksize(n_cols: int) -> int:
    return max(1, _MAX_BIND_PARAMS // max(1, n_cols))


def _write(df: pd.DataFrame, table: str, conn, if_exists: str) -> None:
    df.to_sql(
        table, conn, if_exists=if_exists, index=False,
        chunksize=_safe_chunksize(len(df.columns)), method="multi",
    )


def _batches(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _delete_existing(conn, table: str, df: pd.DataFrame, key: str) -> int:
    """Delete rows whose ``key`` value is present in the incoming batch."""
    meta = MetaData()
    tbl = Table(table, meta, autoload_with=conn)
    if key not in tbl.c:
        raise LoadError(f"Key column '{key}' not found in table '{table}'.")

    values = pd.unique(df[key].dropna())
    values = [v.item() if hasattr(v, "item") else v for v in values]

    deleted = 0
    col = tbl.c[key]
    for chunk in _batches(values, _DELETE_BATCH):
        result = conn.execute(tbl.delete().where(col.in_(chunk)))
        deleted += result.rowcount or 0
    return deleted


def save_to_db(
    df: pd.DataFrame,
    table: str,
    *,
    key: str | None = None,
    strategy: str | None = None,
    engine: Engine | None = None,
) -> None:
    """Load ``df`` into ``table``.

    Parameters
    ----------
    df : DataFrame to load. Empty frames are skipped (the table is left intact).
    table : target table name.
    key : column used to merge in ``upsert`` mode (the parent-entity id).
    strategy : ``"upsert"`` or ``"replace"``; defaults to ``LOAD_STRATEGY``.
    engine : optional engine override (dependency injection for tests).
    """
    if df is None or df.empty:
        log.info("[SKIP] '%s' is empty - nothing to load.", table)
        return

    strategy = (strategy or LOAD_STRATEGY).lower()
    engine = engine or get_engine()

    if strategy == "upsert" and not key:
        log.warning("[%s] upsert requested without a key — falling back to replace.", table)
        strategy = "replace"

    try:
        with engine.begin() as conn:  # one atomic transaction
            if strategy == "replace":
                _write(df, table, conn, if_exists="replace")
            else:
                _write(df.head(0), table, conn, if_exists="append")  # ensure table exists
                deleted = _delete_existing(conn, table, df, key)
                _write(df, table, conn, if_exists="append")
                log.info("[DB] '%s' merged on '%s' (-%d, +%d rows).",
                         table, key, deleted, len(df))
                return
        log.info("[DB] '%s' replaced — %d rows.", table, len(df))
    except Exception as exc:  # noqa: BLE001 — wrap and re-raise as LoadError
        raise LoadError(f"Failed to load '{table}': {exc}") from exc
