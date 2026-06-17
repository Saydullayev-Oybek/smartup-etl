import pandas as pd

from client import fetch
from config import ENDPOINTS, get_headers
from logging_config import get_logger
from pipeline_utils import emit
from transforms import explode_records, select, to_int64, to_numeric

log = get_logger(__name__)


def build_cash_operations(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "operation_id", "filial_code", "external_id",
        "operation_date", "operation_number", "subfilial_code",
        "posted", "cashbox_code", "cashflow_reason_code",
        "cashflow_kind", "corr_coa_code", "corr_person_code",
        "currency_code", "amount", "responsible_person_code",
        "collector_code", "note",
    ]
    df = select(raw, columns)
    to_int64(df, ["operation_id"])
    to_numeric(df, ["amount"])
    return df.drop_duplicates(subset=["operation_id"]).reset_index(drop=True)


def build_cash_operation_refs(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "operation_id", "ref_codes")
    if df.empty:
        return df
    return to_int64(df, ["operation_id"]).reset_index(drop=True)


def run():
    log.info("Cash Operations pipeline started")

    raw = fetch(ENDPOINTS["Cash_Operations"], get_headers(), key="cash_operation")
    if raw.empty:
        log.info("No cash operations found.")
        return

    ops = build_cash_operations(raw)
    refs = build_cash_operation_refs(raw)
    log.info("Cash operations: %d ops, %d refs", len(ops), len(refs))

    emit(ops, excel_name="cash_operations.xlsx", table="cash_operations",
         key="operation_id", unique=True)
    if not refs.empty:
        emit(refs, excel_name="cash_operation_refs.xlsx",
             table="cash_operation_refs", key="operation_id")

    log.info("Cash Operations pipeline finished")
