import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, nested_columns, to_int64

log = get_logger(__name__)


def _build_main(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop(columns=nested_columns(raw)).copy()
    if "return_id" in df.columns:
        to_int64(df, ["return_id"])
        df = df.drop_duplicates(subset=["return_id"])
    return df.reset_index(drop=True)


def _build_items(raw: pd.DataFrame) -> pd.DataFrame:
    items_col = next((c for c in ["return_items", "return_products"] if c in raw.columns), None)
    if not items_col or "return_id" not in raw.columns:
        return pd.DataFrame()
    df = explode_records(raw, "return_id", items_col)
    if df.empty:
        return df
    return to_int64(df, ["return_id"]).reset_index(drop=True)


def run():
    log.info("Returns to Supplier pipeline started")

    raw = fetch(ENDPOINTS["Return_to_suppliers"], get_headers(), key="return")
    if raw.empty:
        log.info("No supplier returns found.")
        return

    returns = _build_main(raw)
    return_items = _build_items(raw)
    log.info("Supplier returns: %d returns, %d items", len(returns), len(return_items))

    emit(returns, excel_name="supplier_returns.xlsx", table="supplier_returns",
         key="return_id", unique=True)
    emit(return_items, excel_name="supplier_return_items.xlsx",
         table="supplier_return_items", key="return_id")

    log.info("Returns to Supplier pipeline finished")
