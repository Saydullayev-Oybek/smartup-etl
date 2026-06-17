import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64

log = get_logger(__name__)

_GROUP_COLUMNS = ["person_id", "group_code", "type_code"]
_ROOM_COLUMNS = ["person_id", "room_id", "room_code", "room_type_code"]


def build_natural_persons(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "person_id", "code", "first_name", "last_name", "middle_name",
        "gender", "birthday", "latlng", "main_phone", "web",
        "address", "post_address", "region_code", "region_name",
        "legal_person_code", "telegram", "email",
        "is_budgetarian", "is_client", "is_supplier",
        "tin", "passport_number", "state",
    ]
    df = select(raw, columns)
    to_int64(df, ["person_id"])
    return df.drop_duplicates(subset=["person_id"]).reset_index(drop=True)


def build_natural_person_group(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_id", "groups")
    if df.empty:
        return pd.DataFrame(columns=_GROUP_COLUMNS)
    df = df.reindex(columns=_GROUP_COLUMNS)
    to_int64(df, ["person_id"])
    return df.drop_duplicates(subset=["person_id", "group_code"]).reset_index(drop=True)


def build_natural_person_room(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_id", "rooms")
    if df.empty:
        return pd.DataFrame(columns=_ROOM_COLUMNS)
    df = df.reindex(columns=_ROOM_COLUMNS)
    to_int64(df, ["person_id", "room_id"])
    return df.drop_duplicates(subset=["person_id", "room_id"]).reset_index(drop=True)


def run():
    log.info("Natural Person pipeline started")

    raw = fetch(ENDPOINTS["natural_person"], get_headers(), key="natural_person")
    if raw.empty:
        log.info("No natural persons found.")
        return

    dim = build_natural_persons(raw)
    groups = build_natural_person_group(raw)
    rooms = build_natural_person_room(raw)
    log.info("Natural persons: %d persons, %d groups, %d rooms", len(dim), len(groups), len(rooms))

    emit(dim, excel_name="natural_persons.xlsx", table="natural_persons",
         key="person_id", unique=True)
    emit(groups, excel_name="natural_person_group.xlsx",
         table="natural_person_group", key="person_id")
    emit(rooms, excel_name="natural_person_room.xlsx",
         table="natural_person_room", key="person_id")

    log.info("Natural Person pipeline finished")
