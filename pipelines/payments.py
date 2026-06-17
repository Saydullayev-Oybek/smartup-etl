import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import select, to_int64, to_numeric

log = get_logger(__name__)


def build_payments(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "cashin_id", "filial_code", "external_id",
        "cashin_time", "cashin_date", "cashin_number",
        "bill_collector_code", "client_code", "client_id",
        "client_name", "client_tin", "subfilial_code",
        "contract_code", "payment_type_code", "currency_code",
        "cashbox_code", "bank_account_code", "amount", "posted",
        "bank_trans_number", "bank_trans_date", "purpose", "note",
    ]
    df = select(raw, columns)
    to_int64(df, ["cashin_id", "client_id"])
    to_numeric(df, ["amount"])
    return df.drop_duplicates(subset=["cashin_id"]).reset_index(drop=True)


def run():
    log.info("Payments pipeline started")

    raw = fetch(ENDPOINTS["Payments_from_clients"], get_headers(), key="cashin")
    if raw.empty:
        log.info("No payments found.")
        return

    payments = build_payments(raw)
    log.info("Payments: %d rows", len(payments))

    emit(payments, excel_name="payments.xlsx", table="payments", key="cashin_id", unique=True)

    log.info("Payments pipeline finished")
