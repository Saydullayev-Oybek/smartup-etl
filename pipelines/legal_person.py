import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


# ── Transform funksiyalari ────────────────────────────────────────────────────

def build_legal_persons(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "person_id", "code", "name", "short_name", "tin", "cea",
        "latlng", "main_phone", "web", "address", "post_address",
        "address_guide", "region_id", "region_code",
        "primary_person_code", "parent_person_code",
        "allow_owner", "vat_code", "barcode", "zip_code", "email",
        "is_budgetarian", "is_client", "is_supplier", "state",
    ]
    df = raw[[c for c in columns if c in raw.columns]].copy()

    df["person_id"]  = pd.to_numeric(df["person_id"],  errors="coerce").astype("Int64")
    df["region_id"]  = pd.to_numeric(df["region_id"],  errors="coerce").astype("Int64")

    return df.drop_duplicates(subset=["person_id"]).reset_index(drop=True)


def build_legal_person_group(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["person_id", "groups"]].iterrows():
        items = row["groups"]
        if not isinstance(items, list):
            continue
        for g in items:
            rows.append({
                "person_id":  row["person_id"],
                "group_id":   g.get("group_id"),
                "group_code": g.get("group_code"),
                "type_id":    g.get("type_id"),
                "type_code":  g.get("type_code"),
            })

    if not rows:
        return pd.DataFrame(columns=["person_id", "group_id", "group_code", "type_id", "type_code"])

    df = pd.DataFrame(rows)
    df["person_id"] = pd.to_numeric(df["person_id"], errors="coerce").astype("Int64")
    df["group_id"]  = pd.to_numeric(df["group_id"],  errors="coerce").astype("Int64")
    df["type_id"]   = pd.to_numeric(df["type_id"],   errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_id", "group_id"]).reset_index(drop=True)


def build_legal_person_bank_account(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["person_id", "bank_accounts"]].iterrows():
        items = row["bank_accounts"]
        if not isinstance(items, list):
            continue
        for b in items:
            rows.append({
                "person_id":           row["person_id"],
                "bank_account_id":     b.get("bank_account_id"),
                "bank_account_code":   b.get("bank_account_code"),
                "bank_account_name":   b.get("bank_account_name"),
                "is_main":             b.get("is_main"),
                "state":               b.get("state"),
                "currency_code":       b.get("currency_code"),
                "mfo":                 b.get("mfo"),
                "bank_name":           b.get("bank_name"),
            })

    if not rows:
        return pd.DataFrame(columns=[
            "person_id", "bank_account_id", "bank_account_code",
            "bank_account_name", "is_main", "state", "currency_code", "mfo", "bank_name",
        ])

    df = pd.DataFrame(rows)
    df["person_id"]       = pd.to_numeric(df["person_id"],       errors="coerce").astype("Int64")
    df["bank_account_id"] = pd.to_numeric(df["bank_account_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_id", "bank_account_id"]).reset_index(drop=True)


def build_legal_person_room(raw: pd.DataFrame) -> pd.DataFrame:
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
    print("=== Legal Person pipeline ===")

    # 1. Extract
    raw = fetch(ENDPOINTS["legal_person"], get_headers(), key="legal_person")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    # 2. Transform
    dim           = build_legal_persons(raw)
    groups        = build_legal_person_group(raw)
    bank_accounts = build_legal_person_bank_account(raw)
    rooms         = build_legal_person_room(raw)

    print(f"[JAMI] {len(dim)} ta yuridik shaxs, {len(groups)} ta group, "
          f"{len(bank_accounts)} ta bank hisob, {len(rooms)} ta room")

    # 3. Load — Excel
    dim.to_excel(os.path.join(OUTPUT_DIR, "legal_persons.xlsx"),                    index=False)
    groups.to_excel(os.path.join(OUTPUT_DIR, "legal_person_group.xlsx"),            index=False)
    bank_accounts.to_excel(os.path.join(OUTPUT_DIR, "legal_person_bank_account.xlsx"), index=False)
    rooms.to_excel(os.path.join(OUTPUT_DIR, "legal_person_room.xlsx"),              index=False)

    # 4. Load — PostgreSQL
    save_to_db(dim,           "legal_persons")
    save_to_db(groups,        "legal_person_group")
    save_to_db(bank_accounts, "legal_person_bank_account")
    save_to_db(rooms,         "legal_person_room")

    print("=== Legal Person pipeline tugadi ===")
