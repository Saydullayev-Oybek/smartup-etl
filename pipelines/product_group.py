import pandas as pd

from client import fetch
from config import ENDPOINTS, get_headers
from logging_config import get_logger
from pipeline_utils import emit
from transforms import explode_records, select, to_int64

log = get_logger(__name__)

_TYPE_COLUMNS = ["product_group_id", "product_type_id", "code", "name", "state", "order_no"]


def build_product_groups(raw: pd.DataFrame) -> pd.DataFrame:
    df = select(raw, ["product_group_id", "code", "name", "product_kind", "state"])
    to_int64(df, ["product_group_id"])
    return df.drop_duplicates(subset=["product_group_id"]).reset_index(drop=True)


def build_product_group_types(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "product_group_id", "product_group_types")
    if df.empty:
        return pd.DataFrame(columns=_TYPE_COLUMNS)
    df = df.reindex(columns=_TYPE_COLUMNS)
    to_int64(df, ["product_group_id", "product_type_id"])
    return df.drop_duplicates(subset=["product_group_id", "product_type_id"]).reset_index(drop=True)


def run():
    log.info("Product Group pipeline started")

    raw = fetch(ENDPOINTS["Product_group"], get_headers(), key="product_group")
    if raw.empty:
        log.info("No product groups found.")
        return

    groups = build_product_groups(raw)
    types = build_product_group_types(raw)
    log.info("Product groups: %d groups, %d types", len(groups), len(types))

    emit(groups, excel_name="product_groups.xlsx", table="product_groups",
         key="product_group_id", unique=True)
    emit(types, excel_name="product_group_types.xlsx",
         table="product_group_types", key="product_group_id")

    log.info("Product Group pipeline finished")
