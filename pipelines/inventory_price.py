import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_inventory_prices(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, rec in raw.iterrows():
        for pt in (rec.get("price_type") or []):
            rows.append({
                "product_id":        rec.get("product_id"),
                "inventory_code":    rec.get("inventory_code"),
                "inventory_barcode": rec.get("inventory_barcode"),
                "price_type_code":   pt.get("price_type_code"),
                "card_code":         pt.get("card_code"),
                "price":             pt.get("price"),
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["price"]      = pd.to_numeric(df["price"],      errors="coerce")
    return df.reset_index(drop=True)


def run():
    print("=== Inventory Price pipeline ===")

    raw = fetch(ENDPOINTS["Inventory_price"], get_headers(), key="inventory")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    prices = build_inventory_prices(raw)
    print(f"[JAMI] {len(prices)} ta narx yozuvi")

    prices.to_excel(os.path.join(OUTPUT_DIR, "inventory_prices.xlsx"), index=False)
    save_to_db(prices, "inventory_prices")

    print("=== Inventory Price pipeline tugadi ===")
