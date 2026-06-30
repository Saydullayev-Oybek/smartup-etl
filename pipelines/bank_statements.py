import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64, to_numeric

log = get_logger(__name__)


def build_bank_statements(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "operation_id", "filial_code", "external_id",
        "operation_date", "operation_number", "subfilial_code",
        "posted", "bank_account_code", "cashflow_reason_code",
        "cashflow_kind", "corr_coa_code", "corr_person_code",
        "currency_code", "amount", "responsible_person_code",
        "bank_trans_number", "bank_trans_date", "note",
    ]
    df = select(raw, columns)
    to_int64(df, ["operation_id"])
    to_numeric(df, ["amount"])
    return df.drop_duplicates(subset=["operation_id"]).reset_index(drop=True)


def build_bank_statement_refs(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "operation_id", "ref_codes")
    if df.empty:
        return df
    return to_int64(df, ["operation_id"]).reset_index(drop=True)


def run():
    log.info("Bank Statements pipeline started")

    raw = fetch(ENDPOINTS["bank_statements"], get_headers(), key="bank_operation")
    if raw.empty:
        log.info("No bank statements found.")
        return

    statements = build_bank_statements(raw)
    refs = build_bank_statement_refs(raw)
    log.info("Bank statements: %d statements, %d refs", len(statements), len(refs))

    emit(statements, excel_name="bank_statements.xlsx", table="bank_statements",
         key="operation_id", unique=True)
    if not refs.empty:
        emit(refs, excel_name="bank_statement_refs.xlsx",
             table="bank_statement_refs", key="operation_id")

    log.info("Bank Statements pipeline finished")
