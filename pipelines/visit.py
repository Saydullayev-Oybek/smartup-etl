import pandas as pd

from core.client import fetch
from core.config import ENDPOINTS, get_headers
from core.logging_config import get_logger
from core.pipeline_utils import emit
from core.transforms import explode_records, nested_columns, to_int64

log = get_logger(__name__)

_PERSON_TYPE_COLUMNS = ["visit_id", "person_type_id", "person_type_name"]
_COMMENT_COLUMNS = ["visit_id", "comment_name", "comment_created_by_name"]


def _first_visit_id(headers) -> object:
    if isinstance(headers, list) and headers:
        return headers[0].get("visit_id")
    return None


def build_visits(raw: pd.DataFrame) -> pd.DataFrame:
    df = explode_records(raw, [], "visit_headers")
    if df.empty:
        return pd.DataFrame()
    df = df.drop(columns=nested_columns(df))  # drop list-valued keys (e.g. person_types)
    to_int64(df, ["visit_id", "person_id", "room_id", "supervisor_id", "sales_manager_id"])
    return df.drop_duplicates(subset=["visit_id"]).reset_index(drop=True)


def build_visit_person_types(raw: pd.DataFrame) -> pd.DataFrame:
    headers = explode_records(raw, [], "visit_headers")
    if headers.empty or "person_types" not in headers.columns or "visit_id" not in headers.columns:
        return pd.DataFrame(columns=_PERSON_TYPE_COLUMNS)
    df = explode_records(headers, "visit_id", "person_types")
    if df.empty:
        return pd.DataFrame(columns=_PERSON_TYPE_COLUMNS)
    df = df.reindex(columns=_PERSON_TYPE_COLUMNS)
    to_int64(df, ["visit_id", "person_type_id"])
    return df.drop_duplicates(subset=["visit_id", "person_type_id"]).reset_index(drop=True)


def build_visit_comments(raw: pd.DataFrame) -> pd.DataFrame:
    if "comments" not in raw.columns:
        return pd.DataFrame(columns=_COMMENT_COLUMNS)
    headers = (raw["visit_headers"] if "visit_headers" in raw.columns
               else pd.Series([None] * len(raw)))
    tmp = pd.DataFrame({
        "visit_id": headers.apply(_first_visit_id).values,
        "comments": raw["comments"].values,
    })
    df = explode_records(tmp, "visit_id", "comments")
    if df.empty:
        return pd.DataFrame(columns=_COMMENT_COLUMNS)
    df = df.reindex(columns=_COMMENT_COLUMNS)
    to_int64(df, ["visit_id"])
    return df.reset_index(drop=True)


def run():
    log.info("Visit pipeline started")

    raw = fetch(ENDPOINTS["visit"], get_headers(), key="visit")
    if raw.empty:
        log.info("No visits found.")
        return

    visits = build_visits(raw)
    person_types = build_visit_person_types(raw)
    comments = build_visit_comments(raw)
    log.info("Visits: %d visits, %d person_types, %d comments",
             len(visits), len(person_types), len(comments))

    emit(visits, excel_name="visits.xlsx", table="visits", key="visit_id", unique=True)
    emit(person_types, excel_name="visit_person_types.xlsx",
         table="visit_person_types", key="visit_id")
    emit(comments, excel_name="visit_comments.xlsx", table="visit_comments", key="visit_id")

    log.info("Visit pipeline finished")
