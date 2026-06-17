import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64

log = get_logger(__name__)

_TYPE_COLUMNS = ["person_group_id", "person_type_id", "code", "name", "state", "order_no"]


def build_person_groups(raw: pd.DataFrame) -> pd.DataFrame:
    df = select(raw, ["person_group_id", "code", "name", "person_kind", "state"])
    to_int64(df, ["person_group_id"])
    return df.drop_duplicates(subset=["person_group_id"]).reset_index(drop=True)


def build_person_group_types(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_group_id", "person_group_types")
    if df.empty:
        return pd.DataFrame(columns=_TYPE_COLUMNS)
    df = df.reindex(columns=_TYPE_COLUMNS)
    to_int64(df, ["person_group_id", "person_type_id"])
    return df.drop_duplicates(subset=["person_group_id", "person_type_id"]).reset_index(drop=True)


def run():
    log.info("Person Group pipeline started")

    raw = fetch(ENDPOINTS["Persons_group"], get_headers(), key="person_group")
    if raw.empty:
        log.info("No person groups found.")
        return

    groups = build_person_groups(raw)
    types = build_person_group_types(raw)
    log.info("Person groups: %d groups, %d types", len(groups), len(types))

    emit(groups, excel_name="person_groups.xlsx", table="person_groups",
         key="person_group_id", unique=True)
    emit(types, excel_name="person_group_types.xlsx",
         table="person_group_types", key="person_group_id")

    log.info("Person Group pipeline finished")
