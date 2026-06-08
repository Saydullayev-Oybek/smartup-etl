import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_writeoffs(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "writeoff_id", "filial_code", "external_id", "status",
        "writeoff_number", "writeoff_date", "currency_code",
        "warehouse_code", "reason_code", "barcode",
        "c_amount", "c_amount_base", "note",
    ]
    df = raw[[c for c in columns if c in raw.columns]].copy()
    df["writeoff_id"] = pd.to_numeric(df["writeoff_id"], errors="coerce").astype("Int64")
    for col in ["c_amount", "c_amount_base"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.drop_duplicates(subset=["writeoff_id"]).reset_index(drop=True)


def build_writeoff_items(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["writeoff_id", "writeoff_items"]].iterrows():
        items = row["writeoff_items"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["writeoff_id"] = row["writeoff_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["writeoff_id"]      = pd.to_numeric(df["writeoff_id"],      errors="coerce").astype("Int64")
    df["writeoff_item_id"] = pd.to_numeric(df["writeoff_item_id"], errors="coerce").astype("Int64")
    for col in ["quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.reset_index(drop=True)


def run():
    print("=== Writeoff pipeline ===")

    raw = fetch(ENDPOINTS["writeoff"], get_headers(), key="writeoff")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    writeoffs = build_writeoffs(raw)
    items     = build_writeoff_items(raw)

    print(f"[JAMI] {len(writeoffs)} ta writeoff, {len(items)} ta item")

    writeoffs.to_excel(os.path.join(OUTPUT_DIR, "writeoffs.xlsx"),       index=False)
    items.to_excel(os.path.join(OUTPUT_DIR, "writeoff_items.xlsx"),      index=False)

    save_to_db(writeoffs, "writeoffs")
    save_to_db(items,     "writeoff_items")

    print("=== Writeoff pipeline tugadi ===")
