import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db

INV_KIND_LABELS = {
    "G": "Goods (tovar)",
    "M": "Material (material)",
    "P": "Product (tayyor mahsulot)",
    "E": "Equipment (asbob-uskuna)",
    "S": "Service (xizmat)",
}


# ── Transform funksiyalari ────────────────────────────────────────────────────

def build_products(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["state"] == "A"].copy()

    columns = [
        "product_id", "code", "name", "short_name", "weight_netto",
        "weight_brutto", "litr", "box_type_code", "box_quant", "producer_code",
        "measure_code", "order_no", "article_code", "barcodes", "gtin",
        "ikpu", "tnved", "marking_group_code",
        "groups", "inventory_kinds", "sector_codes",
    ]
    df = df[[c for c in columns if c in df.columns]]

    df["product_id"]   = pd.to_numeric(df["product_id"],   errors="coerce").astype("Int64")
    df["weight_netto"] = pd.to_numeric(df["weight_netto"], errors="coerce")
    df["weight_brutto"]= pd.to_numeric(df["weight_brutto"],errors="coerce")
    df["litr"]         = pd.to_numeric(df["litr"],         errors="coerce")
    df["box_quant"]    = pd.to_numeric(df["box_quant"],    errors="coerce")
    df["order_no"]     = pd.to_numeric(df["order_no"],     errors="coerce")

    return df.drop_duplicates(subset=["product_id"]).reset_index(drop=True)


def build_product_group(dim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in dim[["product_id", "groups"]].iterrows():
        groups = row["groups"]
        if not isinstance(groups, list):
            continue
        for g in groups:
            rows.append({
                "product_id": row["product_id"],
                "group_id":   g.get("group_id"),
                "group_code": g.get("group_code"),
                "type_id":    g.get("type_id"),
                "type_code":  g.get("type_code"),
            })

    if not rows:
        return pd.DataFrame(columns=["product_id", "group_id", "group_code", "type_id", "type_code"])

    df = pd.DataFrame(rows)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["group_id"]   = pd.to_numeric(df["group_id"],   errors="coerce").astype("Int64")
    df["type_id"]    = pd.to_numeric(df["type_id"],    errors="coerce").astype("Int64")
    df = df.dropna(subset=["product_id", "group_id", "type_id"])
    return df.drop_duplicates(subset=["product_id", "group_id", "type_id"]).reset_index(drop=True)


def build_product_inv_kind(dim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in dim[["product_id", "inventory_kinds"]].iterrows():
        kinds = row["inventory_kinds"]
        if not isinstance(kinds, list):
            continue
        for item in kinds:
            ik = item.get("inventory_kind")
            if ik:
                rows.append({
                    "product_id":     row["product_id"],
                    "inventory_kind": ik.strip().upper(),
                })

    if not rows:
        return pd.DataFrame(columns=["product_id", "inventory_kind", "label"])

    df = pd.DataFrame(rows)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df = df.drop_duplicates(subset=["product_id", "inventory_kind"]).reset_index(drop=True)
    df["label"] = df["inventory_kind"].map(INV_KIND_LABELS)
    return df


def build_product_sector(dim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in dim[["product_id", "sector_codes"]].iterrows():
        sectors = row["sector_codes"]
        if not isinstance(sectors, list):
            continue
        for item in sectors:
            sc = item.get("sector_code")
            if sc:
                rows.append({
                    "product_id":  row["product_id"],
                    "sector_code": str(sc).strip(),
                })

    if not rows:
        return pd.DataFrame(columns=["product_id", "sector_code"])

    df = pd.DataFrame(rows)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["product_id", "sector_code"]).reset_index(drop=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def run():
    print("=== Products pipeline ===")

    # 1. Extract
    raw = fetch(ENDPOINTS["inventory"], get_headers(), key="inventory")
    if raw.empty:
        return

    # 2. Transform
    dim            = build_products(raw)           # nested ustunlar saqlanadi
    product_group  = build_product_group(dim)
    product_inv    = build_product_inv_kind(dim)
    product_sector = build_product_sector(dim)

    # nested ustunlarni olib tashlash — faqat DB/Excel uchun
    nested = ["groups", "inventory_kinds", "sector_codes"]
    products = dim.drop(columns=[c for c in nested if c in dim.columns])

    # 3. Load — Excel
    products.to_excel(os.path.join(OUTPUT_DIR, "products.xlsx"),               index=False)
    product_group.to_excel(os.path.join(OUTPUT_DIR, "product_group.xlsx"),     index=False)
    product_inv.to_excel(os.path.join(OUTPUT_DIR, "product_inv_kind.xlsx"),    index=False)
    product_sector.to_excel(os.path.join(OUTPUT_DIR, "product_sector.xlsx"),   index=False)

    # 4. Load — PostgreSQL
    save_to_db(products,       "products")
    save_to_db(product_group,  "product_group")
    save_to_db(product_inv,    "product_inventory_kind")
    save_to_db(product_sector, "product_sector")

    print("=== Products pipeline tugadi ===")
