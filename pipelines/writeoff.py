import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64, to_numeric

log = get_logger(__name__)


def build_writeoffs(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "writeoff_id", "filial_code", "external_id", "status",
        "writeoff_number", "writeoff_date", "currency_code",
        "warehouse_code", "reason_code", "barcode",
        "c_amount", "c_amount_base", "note",
    ]
    df = select(raw, columns)
    to_int64(df, ["writeoff_id"])
    to_numeric(df, ["c_amount", "c_amount_base"])
    return df.drop_duplicates(subset=["writeoff_id"]).reset_index(drop=True)


def build_writeoff_items(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "writeoff_id", "writeoff_items")
    if df.empty:
        return df
    to_int64(df, ["writeoff_id", "writeoff_item_id"])
    to_numeric(df, ["quantity"])
    return df.reset_index(drop=True)


def run():
    log.info("Writeoff pipeline started")

    raw = fetch(ENDPOINTS["writeoff"], get_headers(), key="writeoff")
    if raw.empty:
        log.info("No writeoffs found.")
        return

    writeoffs = build_writeoffs(raw)
    items = build_writeoff_items(raw)
    log.info("Writeoffs: %d writeoffs, %d items", len(writeoffs), len(items))

    emit(writeoffs, excel_name="writeoffs.xlsx", table="writeoffs", key="writeoff_id", unique=True)
    emit(items, excel_name="writeoff_items.xlsx", table="writeoff_items", key="writeoff_id")

    log.info("Writeoff pipeline finished")
