import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def _build_main(raw: pd.DataFrame) -> pd.DataFrame:
    nested = [c for c in raw.columns if raw[c].apply(lambda v: isinstance(v, list)).any()]
    df = raw.drop(columns=nested).copy()
    if "return_id" in df.columns:
        df["return_id"] = pd.to_numeric(df["return_id"], errors="coerce").astype("Int64")
        df = df.drop_duplicates(subset=["return_id"])
    return df.reset_index(drop=True)


def _build_items(raw: pd.DataFrame) -> pd.DataFrame:
    items_col = next((c for c in ["return_products", "return_items"] if c in raw.columns), None)
    if not items_col:
        return pd.DataFrame()
    rows = []
    for _, row in raw[["return_id", items_col]].iterrows():
        for item in (row[items_col] or []):
            item["return_id"] = row["return_id"]
            rows.append(item)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["return_id"] = pd.to_numeric(df["return_id"], errors="coerce").astype("Int64")
    return df.reset_index(drop=True)


def run():
    print("=== Returns (mijozlardan) pipeline ===")

    raw = fetch(ENDPOINTS["return"], get_headers(), key="return")
    if raw.empty:
        print("[INFO] Qaytarish topilmadi.")
        print("=== Returns pipeline tugadi ===")
        return

    returns      = _build_main(raw)
    return_items = _build_items(raw)
    print(f"[JAMI] {len(returns)} ta qaytarish, {len(return_items)} ta mahsulot")

    returns.to_excel(os.path.join(OUTPUT_DIR, "returns.xlsx"),             index=False)
    return_items.to_excel(os.path.join(OUTPUT_DIR, "return_products.xlsx"), index=False)
    save_to_db(returns,      "returns")
    save_to_db(return_items, "return_products")

    print("=== Returns pipeline tugadi ===")
