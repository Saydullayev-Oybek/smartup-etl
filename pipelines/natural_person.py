import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


# ── Transform funksiyalari ────────────────────────────────────────────────────

def build_natural_persons(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "person_id", "code", "first_name", "last_name", "middle_name",
        "gender", "birthday", "latlng", "main_phone", "web",
        "address", "post_address", "region_code", "region_name",
        "legal_person_code", "telegram", "email",
        "is_budgetarian", "is_client", "is_supplier",
        "tin", "passport_number", "state",
    ]
    df = raw[[c for c in columns if c in raw.columns]].copy()

    df["person_id"] = pd.to_numeric(df["person_id"], errors="coerce").astype("Int64")

    return df.drop_duplicates(subset=["person_id"]).reset_index(drop=True)


def build_natural_person_group(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["person_id", "groups"]].iterrows():
        items = row["groups"]
        if not isinstance(items, list):
            continue
        for g in items:
            rows.append({
                "person_id":  row["person_id"],
                "group_code": g.get("group_code"),
                "type_code":  g.get("type_code"),
            })

    if not rows:
        return pd.DataFrame(columns=["person_id", "group_code", "type_code"])

    df = pd.DataFrame(rows)
    df["person_id"] = pd.to_numeric(df["person_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_id", "group_code"]).reset_index(drop=True)


def build_natural_person_room(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["person_id", "rooms"]].iterrows():
        items = row["rooms"]
        if not isinstance(items, list):
            continue
        for r in items:
            rows.append({
                "person_id":      row["person_id"],
                "room_id":        r.get("room_id"),
                "room_code":      r.get("room_code"),
                "room_type_code": r.get("room_type_code"),
            })

    if not rows:
        return pd.DataFrame(columns=["person_id", "room_id", "room_code", "room_type_code"])

    df = pd.DataFrame(rows)
    df["person_id"] = pd.to_numeric(df["person_id"], errors="coerce").astype("Int64")
    df["room_id"]   = pd.to_numeric(df["room_id"],   errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_id", "room_id"]).reset_index(drop=True)


# ── Run ───────────────────────────────────────────────────────────────────────

def run():
    print("=== Natural Person pipeline ===")

    # 1. Extract
    raw = fetch(ENDPOINTS["natural_person"], get_headers(), key="natural_person")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    # 2. Transform
    dim  = build_natural_persons(raw)
    groups = build_natural_person_group(raw)
    rooms  = build_natural_person_room(raw)

    print(f"[JAMI] {len(dim)} ta shaxs, {len(groups)} ta group, {len(rooms)} ta room")

    # 3. Load — Excel
    dim.to_excel(os.path.join(OUTPUT_DIR, "natural_persons.xlsx"),             index=False)
    groups.to_excel(os.path.join(OUTPUT_DIR, "natural_person_group.xlsx"),     index=False)
    rooms.to_excel(os.path.join(OUTPUT_DIR, "natural_person_room.xlsx"),       index=False)

    # 4. Load — PostgreSQL
    save_to_db(dim,    "natural_persons")
    save_to_db(groups, "natural_person_group")
    save_to_db(rooms,  "natural_person_room")

    print("=== Natural Person pipeline tugadi ===")
