import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_person_groups(raw: pd.DataFrame) -> pd.DataFrame:
    columns = ["person_group_id", "code", "name", "person_kind", "state"]
    df = raw[[c for c in columns if c in raw.columns]].copy()
    df["person_group_id"] = pd.to_numeric(df["person_group_id"], errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_group_id"]).reset_index(drop=True)


def build_person_group_types(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["person_group_id", "person_group_types"]].iterrows():
        items = row["person_group_types"]
        if not isinstance(items, list):
            continue
        for t in items:
            rows.append({
                "person_group_id": row["person_group_id"],
                "person_type_id":  t.get("person_type_id"),
                "code":            t.get("code"),
                "name":            t.get("name"),
                "state":           t.get("state"),
                "order_no":        t.get("order_no"),
            })

    if not rows:
        return pd.DataFrame(columns=["person_group_id", "person_type_id", "code", "name", "state", "order_no"])

    df = pd.DataFrame(rows)
    df["person_group_id"] = pd.to_numeric(df["person_group_id"], errors="coerce").astype("Int64")
    df["person_type_id"]  = pd.to_numeric(df["person_type_id"],  errors="coerce").astype("Int64")
    return df.drop_duplicates(subset=["person_group_id", "person_type_id"]).reset_index(drop=True)


def run():
    print("=== Person Group pipeline ===")

    raw = fetch(ENDPOINTS["Persons_group"], get_headers(), key="person_group")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    groups = build_person_groups(raw)
    types  = build_person_group_types(raw)

    print(f"[JAMI] {len(groups)} ta group, {len(types)} ta type")

    groups.to_excel(os.path.join(OUTPUT_DIR, "person_groups.xlsx"),      index=False)
    types.to_excel(os.path.join(OUTPUT_DIR, "person_group_types.xlsx"),  index=False)

    save_to_db(groups, "person_groups")
    save_to_db(types,  "person_group_types")

    print("=== Person Group pipeline tugadi ===")
