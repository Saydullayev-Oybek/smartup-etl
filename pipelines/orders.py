import os
from datetime import datetime, timedelta
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch_post
from loader import save_to_db


def _date_chunks(start: datetime, end: datetime, days: int = 30):
    """start dan end gacha 30 kunlik intervallar qaytaradi."""
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


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

def _fetch_all(begin_date: datetime, end_date: datetime) -> pd.DataFrame:
    """begin_date dan end_date gacha oyma-oy so'rov yuborib birlashtiradi."""
    headers = get_headers()
    frames = []
    for start, end in _date_chunks(begin_date, end_date):
        print(f"  [{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}]")
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


def run(begin_date: str = None, end_date: str = None, body: dict = None):
    """
    begin_date / end_date — "DD.MM.YYYY" formatida (ixtiyoriy).
    Agar ko'rsatilmasa, so'nggi 30 kun olinadi.
    body — to'liq custom request body (qolgan parametrlarni bekor qiladi).
    """
    print("=== Orders pipeline ===")

    if body:
        raw = fetch_post(ENDPOINTS["order"], get_headers(), body, key="order")
    else:
        end   = datetime.strptime(end_date,   "%d.%m.%Y") if end_date   else datetime.today()
        start = datetime.strptime(begin_date, "%d.%m.%Y") if begin_date else end - timedelta(days=30)
        print(f"Davr: {start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}")
        raw = _fetch_all(start, end)

    if raw.empty:
        print("[INFO] Hech qanday order topilmadi.")
        return

    # 2. Transform
    orders             = build_orders(raw)
    order_products     = build_order_products(raw)
    order_gifts        = build_order_gifts(raw)
    order_actions      = build_order_actions(raw)
    order_consignments = build_order_consignments(raw)

    print(f"[JAMI] {len(orders)} ta order, {len(order_products)} ta mahsulot qatori")

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
