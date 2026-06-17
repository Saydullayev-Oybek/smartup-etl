from datetime import datetime, timedelta

import pandas as pd

from core.client import fetch_post
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64, to_numeric

log = get_logger(__name__)


def _date_chunks(start: datetime, end: datetime, days: int = 30):
    """Yield (start, end) intervals of at most ``days`` days covering the range."""
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


# ── Transform functions ───────────────────────────────────────────────────────

def build_orders(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "deal_id", "filial_code", "external_id", "invoice_external_id",
        "subfilial_code", "deal_time", "delivery_date", "delivery_number",
        "booked_date", "total_amount", "status", "currency_code",
        "room_id", "room_code", "room_name", "robot_code", "lap_code",
        "sales_manager_id", "sales_manager_code", "sales_manager_name",
        "expeditor_id", "expeditor_code", "expeditor_name",
        "person_id", "person_code", "person_name", "person_local_code", "person_tin",
        "owner_person_code", "van_code", "contract_code", "contract_number",
        "invoice_number", "payment_type_code",
        "deal_margin_kind", "deal_margin_value",
        "note", "deal_note", "with_marking", "self_shipment",
        "delivery_address_short", "delivery_address_full",
        "visit_id", "total_weight_netto", "total_weight_brutto", "total_litre",
    ]
    df = select(raw, columns)
    to_int64(df, ["deal_id", "room_id", "sales_manager_id", "expeditor_id",
                  "person_id", "visit_id"])
    to_numeric(df, ["total_amount", "deal_margin_value", "total_weight_netto",
                    "total_weight_brutto", "total_litre"])
    return df.drop_duplicates(subset=["deal_id"]).reset_index(drop=True)


def build_order_products(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "deal_id", "order_products")
    if df.empty:
        return df
    to_int64(df, ["deal_id", "product_unit_id", "price_type_id"])
    to_numeric(df, ["order_quant", "sold_quant", "return_quant", "product_price",
                    "margin_amount", "margin_value", "vat_amount", "vat_percent", "sold_amount"])
    nested = ["details", "action_margins"]
    return df.drop(columns=[c for c in nested if c in df.columns]).reset_index(drop=True)


def build_order_gifts(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "deal_id", "order_gifts")
    if df.empty:
        return df
    to_int64(df, ["deal_id"])
    to_numeric(df, ["order_quant", "sold_quant", "return_quant"])
    return df.reset_index(drop=True)


def build_order_actions(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "deal_id", "order_actions")
    if df.empty:
        return df
    to_int64(df, ["deal_id"])
    to_numeric(df, ["order_quant", "sold_quant", "return_quant", "bonus_id"])
    return df.reset_index(drop=True)


def build_order_consignments(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "deal_id", "order_consignments")
    if df.empty:
        return df
    to_int64(df, ["deal_id"])
    to_numeric(df, ["consignment_unit_id", "consignment_amount"])
    return df.reset_index(drop=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def _fetch_all(begin_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetch orders month-by-month between the dates and concatenate."""
    headers = get_headers()
    frames = []
    for start, end in _date_chunks(begin_date, end_date):
        log.info("  [%s - %s]", start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y"))
        body = {
            "begin_modified_on": start.strftime("%d.%m.%Y"),
            "end_modified_on":   end.strftime("%d.%m.%Y"),
        }
        chunk = fetch_post(ENDPOINTS["order"], headers, body, key="order")
        if not chunk.empty:
            frames.append(chunk)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def run(begin_date: str | None = None, end_date: str | None = None, body: dict | None = None):
    """Run the orders pipeline.

    begin_date / end_date — "DD.MM.YYYY" (optional). Default: last 30 days.
    body — full custom request body (overrides the date parameters).
    """
    log.info("Orders pipeline started")

    if body:
        raw = fetch_post(ENDPOINTS["order"], get_headers(), body, key="order")
    else:
        end = datetime.strptime(end_date, "%d.%m.%Y") if end_date else datetime.today()
        start = (datetime.strptime(begin_date, "%d.%m.%Y") if begin_date
                 else end - timedelta(days=30))
        log.info("Period: %s - %s", start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y"))
        raw = _fetch_all(start, end)

    if raw.empty:
        log.info("No orders found.")
        return

    orders = build_orders(raw)
    order_products = build_order_products(raw)
    order_gifts = build_order_gifts(raw)
    order_actions = build_order_actions(raw)
    order_consignments = build_order_consignments(raw)
    log.info("Orders: %d orders, %d product rows", len(orders), len(order_products))

    emit(orders, excel_name="orders.xlsx", table="orders", key="deal_id", unique=True)
    emit(order_products, excel_name="order_products.xlsx", table="order_products", key="deal_id")
    emit(order_gifts, excel_name="order_gifts.xlsx", table="order_gifts", key="deal_id")
    emit(order_actions, excel_name="order_actions.xlsx", table="order_actions", key="deal_id")
    emit(order_consignments, excel_name="order_consignments.xlsx",
         table="order_consignments", key="deal_id")

    log.info("Orders pipeline finished")
