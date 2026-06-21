import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, nested_columns, to_int64

log = get_logger(__name__)


def _build_main(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop(columns=nested_columns(raw)).copy()
    if "deal_id" in df.columns:
        to_int64(df, ["deal_id"])
        df = df.drop_duplicates(subset=["deal_id"])
    return df.reset_index(drop=True)


def _find_items_col(raw: pd.DataFrame) -> str | None:
    """Locate the line-items column: known names first, then any nested
    list column (preferring product/item-like names)."""
    for name in ("return_products", "return_items", "products", "items"):
        if name in raw.columns:
            return name
    nested = nested_columns(raw)
    preferred = [c for c in nested if "product" in c.lower() or "item" in c.lower()]
    candidates = preferred or nested
    return candidates[0] if candidates else None


def _build_items(raw: pd.DataFrame) -> pd.DataFrame:
    items_col = _find_items_col(raw)
    if not items_col or "deal_id" not in raw.columns:
        return pd.DataFrame()
    df = explode_records(raw, "deal_id", items_col)
    if df.empty:
        return df
    return to_int64(df, ["deal_id"]).reset_index(drop=True)


def run():
    log.info("Returns (mijozlardan) pipeline started")

    raw = fetch(ENDPOINTS["return"], get_headers(), key="return")
    if raw.empty:
        log.info("No returns found.")
        return

    returns = _build_main(raw)
    return_items = _build_items(raw)
    log.info("Returns: %d returns, %d items", len(returns), len(return_items))

    emit(returns, excel_name="returns.xlsx", table="returns", key="deal_id", unique=True)
    emit(return_items, excel_name="return_products.xlsx", table="return_products", key="deal_id")

    log.info("Returns pipeline finished")
