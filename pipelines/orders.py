import os
from datetime import datetime, timedelta
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch_post
from loader import save_to_db


def _default_body() -> dict:
    """So'nggi 7 kunlik orderlarni olish uchun request body."""
    today = datetime.today()
    week_ago = today - timedelta(days=7)
    return {
        "begin_deal_date": week_ago.strftime("%d.%m.%Y"),
        "end_deal_date":   today.strftime("%d.%m.%Y"),
    }


# ── Transform funksiyalari ────────────────────────────────────────────────────

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
    df = raw[[c for c in columns if c in raw.columns]].copy()

    for col in ["deal_id", "room_id", "sales_manager_id", "expeditor_id", "person_id", "visit_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ["total_amount", "deal_margin_value", "total_weight_netto",
                "total_weight_brutto", "total_litre"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.drop_duplicates(subset=["deal_id"]).reset_index(drop=True)


def build_order_products(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["deal_id", "order_products"]].iterrows():
        items = row["order_products"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["deal_id"] = row["deal_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["deal_id"] = pd.to_numeric(df["deal_id"], errors="coerce").astype("Int64")

    for col in ["product_unit_id", "price_type_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ["order_quant", "sold_quant", "return_quant", "product_price",
                "margin_amount", "margin_value", "vat_amount", "vat_percent", "sold_amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # nested listlarni olib tashlash (details, action_margins)
    nested = ["details", "action_margins"]
    df = df.drop(columns=[c for c in nested if c in df.columns])

    return df.reset_index(drop=True)


def build_order_gifts(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["deal_id", "order_gifts"]].iterrows():
        items = row["order_gifts"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["deal_id"] = row["deal_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["deal_id"] = pd.to_numeric(df["deal_id"], errors="coerce").astype("Int64")

    for col in ["order_quant", "sold_quant", "return_quant"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def build_order_actions(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["deal_id", "order_actions"]].iterrows():
        items = row["order_actions"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["deal_id"] = row["deal_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["deal_id"] = pd.to_numeric(df["deal_id"], errors="coerce").astype("Int64")

    for col in ["order_quant", "sold_quant", "return_quant", "bonus_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def build_order_consignments(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["deal_id", "order_consignments"]].iterrows():
        items = row["order_consignments"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["deal_id"] = row["deal_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["deal_id"] = pd.to_numeric(df["deal_id"], errors="coerce").astype("Int64")

    for col in ["consignment_unit_id", "consignment_amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def run(body: dict = None):
    print("=== Orders pipeline ===")

    # 1. Extract
    raw = fetch_post(
        ENDPOINTS["order"],
        get_headers(),
        body or _default_body(),
        key="order",
    )
    if raw.empty:
        print("[INFO] Hech qanday order topilmadi.")
        return

    # 2. Transform
    orders             = build_orders(raw)
    order_products     = build_order_products(raw)
    order_gifts        = build_order_gifts(raw)
    order_actions      = build_order_actions(raw)
    order_consignments = build_order_consignments(raw)

    # 3. Load — Excel
    orders.to_excel(os.path.join(OUTPUT_DIR, "orders.xlsx"),                         index=False)
    order_products.to_excel(os.path.join(OUTPUT_DIR, "order_products.xlsx"),         index=False)
    order_gifts.to_excel(os.path.join(OUTPUT_DIR, "order_gifts.xlsx"),               index=False)
    order_actions.to_excel(os.path.join(OUTPUT_DIR, "order_actions.xlsx"),           index=False)
    order_consignments.to_excel(os.path.join(OUTPUT_DIR, "order_consignments.xlsx"), index=False)

    # 4. Load — PostgreSQL
    save_to_db(orders,             "orders")
    save_to_db(order_products,     "order_products")
    save_to_db(order_gifts,        "order_gifts")
    save_to_db(order_actions,      "order_actions")
    save_to_db(order_consignments, "order_consignments")

    print("=== Orders pipeline tugadi ===")
