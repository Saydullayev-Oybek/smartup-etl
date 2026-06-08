import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_visits(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, rec in raw.iterrows():
        headers = rec.get("visit_headers")
        if not isinstance(headers, list):
            continue
        for h in headers:
            rows.append({k: v for k, v in h.items() if not isinstance(v, list)})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col in ["visit_id", "person_id", "room_id", "supervisor_id",
                "sales_manager_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df.drop_duplicates(subset=["visit_id"]).reset_index(drop=True)


def build_visit_person_types(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, rec in raw.iterrows():
        headers = rec.get("visit_headers")
        if not isinstance(headers, list):
            continue
        for h in headers:
            visit_id = h.get("visit_id")
            for pt in (h.get("person_types") or []):
                rows.append({
                    "visit_id":        visit_id,
                    "person_type_id":  pt.get("person_type_id"),
                    "person_type_name": pt.get("person_type_name"),
                })

    if not rows:
        return pd.DataFrame(columns=["visit_id", "person_type_id", "person_type_name"])

    df = pd.DataFrame(rows)
    df["visit_id"]       = pd.to_numeric(df["visit_id"],       errors="coerce").astype("Int64")
    df["person_type_id"] = pd.to_numeric(df["person_type_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["visit_id", "person_type_id"]).reset_index(drop=True)


def build_visit_comments(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, rec in raw.iterrows():
        headers = rec.get("visit_headers")
        visit_id = headers[0].get("visit_id") if isinstance(headers, list) and headers else None
        for c in (rec.get("comments") or []):
            rows.append({
                "visit_id":                 visit_id,
                "comment_name":             c.get("comment_name"),
                "comment_created_by_name":  c.get("comment_created_by_name"),
            })

    if not rows:
        return pd.DataFrame(columns=["visit_id", "comment_name", "comment_created_by_name"])

    df = pd.DataFrame(rows)
    df["visit_id"] = pd.to_numeric(df["visit_id"], errors="coerce").astype("Int64")
    return df.reset_index(drop=True)


def run():
    print("=== Visit pipeline ===")

    raw = fetch(ENDPOINTS["visit"], get_headers(), key="visit")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    visits       = build_visits(raw)
    person_types = build_visit_person_types(raw)
    comments     = build_visit_comments(raw)

    print(f"[JAMI] {len(visits)} ta visit, {len(person_types)} ta person_type, {len(comments)} ta comment")

    visits.to_excel(os.path.join(OUTPUT_DIR, "visits.xlsx"),                    index=False)
    person_types.to_excel(os.path.join(OUTPUT_DIR, "visit_person_types.xlsx"), index=False)
    comments.to_excel(os.path.join(OUTPUT_DIR, "visit_comments.xlsx"),         index=False)

    save_to_db(visits,       "visits")
    save_to_db(person_types, "visit_person_types")
    save_to_db(comments,     "visit_comments")

    print("=== Visit pipeline tugadi ===")
