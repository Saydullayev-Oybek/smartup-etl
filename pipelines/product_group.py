import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_product_groups(raw: pd.DataFrame) -> pd.DataFrame:
    columns = ["product_group_id", "code", "name", "product_kind", "state"]
    df = raw[[c for c in columns if c in raw.columns]].copy()
    df["product_group_id"] = pd.to_numeric(df["product_group_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["product_group_id"]).reset_index(drop=True)


def build_product_group_types(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["product_group_id", "product_group_types"]].iterrows():
        items = row["product_group_types"]
        if not isinstance(items, list):
            continue
        for t in items:
            rows.append({
                "product_group_id":   row["product_group_id"],
                "product_type_id":    t.get("product_type_id"),
                "code":               t.get("code"),
                "name":               t.get("name"),
                "state":              t.get("state"),
                "order_no":           t.get("order_no"),
            })

    if not rows:
        return pd.DataFrame(columns=["product_group_id", "product_type_id", "code", "name", "state", "order_no"])

    df = pd.DataFrame(rows)
    df["product_group_id"] = pd.to_numeric(df["product_group_id"], errors="coerce").astype("Int64")
    df["product_type_id"]  = pd.to_numeric(df["product_type_id"],  errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["product_group_id", "product_type_id"]).reset_index(drop=True)


def run():
    print("=== Product Group pipeline ===")

    raw = fetch(ENDPOINTS["Product_group"], get_headers(), key="product_group")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    groups = build_product_groups(raw)
    types  = build_product_group_types(raw)

    print(f"[JAMI] {len(groups)} ta group, {len(types)} ta type")

    groups.to_excel(os.path.join(OUTPUT_DIR, "product_groups.xlsx"),      index=False)
    types.to_excel(os.path.join(OUTPUT_DIR, "product_group_types.xlsx"),  index=False)

    save_to_db(groups, "product_groups")
    save_to_db(types,  "product_group_types")

    print("=== Product Group pipeline tugadi ===")
