import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, to_int64, to_numeric

log = get_logger(__name__)

_COLUMNS = [
    "product_id", "inventory_code", "inventory_barcode",
    "price_type_code", "card_code", "price",
]


def build_inventory_prices(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, ["product_id", "inventory_code", "inventory_barcode"], "price_type")
    if df.empty:
        return df
    df = df.reindex(columns=_COLUMNS)
    to_int64(df, ["product_id"])
    to_numeric(df, ["price"])
    return df.reset_index(drop=True)


def run():
    log.info("Inventory Price pipeline started")

    raw = fetch(ENDPOINTS["Inventory_price"], get_headers(), key="inventory")
    if raw.empty:
        log.info("No inventory prices found.")
        return

    prices = build_inventory_prices(raw)
    log.info("Inventory prices: %d rows", len(prices))

    emit(prices, excel_name="inventory_prices.xlsx", table="inventory_prices", key="product_id")

    log.info("Inventory Price pipeline finished")
