import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, select, to_int64

log = get_logger(__name__)

_GROUP_COLUMNS = ["person_id", "group_id", "group_code", "type_id", "type_code"]
_BANK_COLUMNS = [
    "person_id", "bank_account_id", "bank_account_code", "bank_account_name",
    "is_main", "state", "currency_code", "mfo", "bank_name",
]
_ROOM_COLUMNS = ["person_id", "room_id", "room_code", "room_type_code"]


def build_legal_persons(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "person_id", "code", "name", "short_name", "tin", "cea",
        "latlng", "main_phone", "web", "address", "post_address",
        "address_guide", "region_id", "region_code",
        "primary_person_code", "parent_person_code",
        "allow_owner", "vat_code", "barcode", "zip_code", "email",
        "is_budgetarian", "is_client", "is_supplier", "state",
    ]
    df = select(raw, columns)
    to_int64(df, ["person_id", "region_id"])
    return df.drop_duplicates(subset=["person_id"]).reset_index(drop=True)


def build_legal_person_group(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_id", "groups")
    if df.empty:
        return pd.DataFrame(columns=_GROUP_COLUMNS)
    df = df.reindex(columns=_GROUP_COLUMNS)
    to_int64(df, ["person_id", "group_id", "type_id"])
    return df.drop_duplicates(subset=["person_id", "group_id"]).reset_index(drop=True)


def build_legal_person_bank_account(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_id", "bank_accounts")
    if df.empty:
        return pd.DataFrame(columns=_BANK_COLUMNS)
    df = df.reindex(columns=_BANK_COLUMNS)
    to_int64(df, ["person_id", "bank_account_id"])
    return df.drop_duplicates(subset=["person_id", "bank_account_id"]).reset_index(drop=True)


def build_legal_person_room(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, "person_id", "rooms")
    if df.empty:
        return pd.DataFrame(columns=_ROOM_COLUMNS)
    df = df.reindex(columns=_ROOM_COLUMNS)
    to_int64(df, ["person_id", "room_id"])
    return df.drop_duplicates(subset=["person_id", "room_id"]).reset_index(drop=True)


def run():
    log.info("Legal Person pipeline started")

    raw = fetch(ENDPOINTS["legal_person"], get_headers(), key="legal_person")
    if raw.empty:
        log.info("No legal persons found.")
        return

    dim = build_legal_persons(raw)
    groups = build_legal_person_group(raw)
    bank_accounts = build_legal_person_bank_account(raw)
    rooms = build_legal_person_room(raw)
    log.info("Legal persons: %d persons, %d groups, %d bank accounts, %d rooms",
             len(dim), len(groups), len(bank_accounts), len(rooms))

    emit(dim, excel_name="legal_persons.xlsx", table="legal_persons", key="person_id", unique=True)
    emit(groups, excel_name="legal_person_group.xlsx",
         table="legal_person_group", key="person_id")
    emit(bank_accounts, excel_name="legal_person_bank_account.xlsx",
         table="legal_person_bank_account", key="person_id")
    emit(rooms, excel_name="legal_person_room.xlsx",
         table="legal_person_room", key="person_id")

    log.info("Legal Person pipeline finished")
