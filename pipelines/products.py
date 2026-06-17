import pandas as pd

from client import fetch
from config import ENDPOINTS, get_headers
from logging_config import get_logger
from pipeline_utils import emit
from transforms import explode_records, select, to_int64, to_numeric

log = get_logger(__name__)

INV_KIND_LABELS = {
    "G": "Goods (tovar)",
    "M": "Material (material)",
    "P": "Product (tayyor mahsulot)",
    "E": "Equipment (asbob-uskuna)",
    "S": "Service (xizmat)",
}

_GROUP_COLUMNS = ["product_id", "group_id", "group_code", "type_id", "type_code"]
_NESTED = ["groups", "inventory_kinds", "sector_codes"]


# ── Transform functions ───────────────────────────────────────────────────────

def build_products(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["state"] == "A"].copy()

    columns = [
        "product_id", "code", "name", "short_name", "weight_netto",
        "weight_brutto", "litr", "box_type_code", "box_quant", "producer_code",
        "measure_code", "order_no", "article_code", "barcodes", "gtin",
        "ikpu", "tnved", "marking_group_code",
        "groups", "inventory_kinds", "sector_codes",
    ]
    df = select(df, columns)
    to_int64(df, ["product_id"])
    to_numeric(df, ["weight_netto", "weight_brutto", "litr", "box_quant", "order_no"])
    return df.drop_duplicates(subset=["product_id"]).reset_index(drop=True)


def build_product_group(dim: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(dim, "product_id", "groups")
    if df.empty:
        return pd.DataFrame(columns=_GROUP_COLUMNS)
    df = df.reindex(columns=_GROUP_COLUMNS)
    to_int64(df, ["product_id", "group_id", "type_id"])
    df = df.dropna(subset=["product_id", "group_id", "type_id"])
    return df.drop_duplicates(subset=["product_id", "group_id", "type_id"]).reset_index(drop=True)


def build_product_inv_kind(dim: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(dim, "product_id", "inventory_kinds")
    if df.empty or "inventory_kind" not in df.columns:
        return pd.DataFrame(columns=["product_id", "inventory_kind", "label"])
    df = df[df["inventory_kind"].notna()].copy()
    df["inventory_kind"] = df["inventory_kind"].astype(str).str.strip().str.upper()
    df = df[df["inventory_kind"] != ""]
    df = df.reindex(columns=["product_id", "inventory_kind"])
    to_int64(df, ["product_id"])
    df = df.drop_duplicates(subset=["product_id", "inventory_kind"]).reset_index(drop=True)
    df["label"] = df["inventory_kind"].map(INV_KIND_LABELS)
    return df


def build_product_sector(dim: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(dim, "product_id", "sector_codes")
    if df.empty or "sector_code" not in df.columns:
        return pd.DataFrame(columns=["product_id", "sector_code"])
    df = df[df["sector_code"].notna()].copy()
    df["sector_code"] = df["sector_code"].astype(str).str.strip()
    df = df[df["sector_code"] != ""]
    df = df.reindex(columns=["product_id", "sector_code"])
    to_int64(df, ["product_id"])
    return df.drop_duplicates(subset=["product_id", "sector_code"]).reset_index(drop=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def run():
    log.info("Products pipeline started")

    raw = fetch(ENDPOINTS["inventory"], get_headers(), key="inventory")
    if raw.empty:
        log.info("No products found.")
        return

    dim = build_products(raw)                       # keeps nested columns
    product_group = build_product_group(dim)
    product_inv = build_product_inv_kind(dim)
    product_sector = build_product_sector(dim)

    products = dim.drop(columns=[c for c in _NESTED if c in dim.columns])
    log.info("Products: %d products, %d groups, %d inv_kinds, %d sectors",
             len(products), len(product_group), len(product_inv), len(product_sector))

    emit(products, excel_name="products.xlsx", table="products", key="product_id", unique=True)
    emit(product_group, excel_name="product_group.xlsx", table="product_group", key="product_id")
    emit(product_inv, excel_name="product_inv_kind.xlsx",
         table="product_inventory_kind", key="product_id")
    emit(product_sector, excel_name="product_sector.xlsx",
         table="product_sector", key="product_id")

    log.info("Products pipeline finished")
