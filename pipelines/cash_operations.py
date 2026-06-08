import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_cash_operations(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "operation_id", "filial_code", "external_id",
        "operation_date", "operation_number", "subfilial_code",
        "posted", "cashbox_code", "cashflow_reason_code",
        "cashflow_kind", "corr_coa_code", "corr_person_code",
        "currency_code", "amount", "responsible_person_code",
        "collector_code", "note",
    ]
    df = raw[[c for c in columns if c in raw.columns]].copy()

    df["operation_id"] = pd.to_numeric(df["operation_id"], errors="coerce").astype("Int64")
    df["amount"]       = pd.to_numeric(df["amount"],       errors="coerce")

    return df.drop_duplicates(subset=["operation_id"]).reset_index(drop=True)


def build_cash_operation_refs(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw[["operation_id", "ref_codes"]].iterrows():
        items = row["ref_codes"]
        if not isinstance(items, list):
            continue
        for item in items:
            item["operation_id"] = row["operation_id"]
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["operation_id"] = pd.to_numeric(df["operation_id"], errors="coerce").astype("Int64")
    return df.reset_index(drop=True)


def run():
    print("=== Cash Operations pipeline ===")

    raw = fetch(ENDPOINTS["Cash_Operations"], get_headers(), key="cash_operation")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    ops  = build_cash_operations(raw)
    refs = build_cash_operation_refs(raw)

    print(f"[JAMI] {len(ops)} ta operatsiya, {len(refs)} ta ref")

    ops.to_excel(os.path.join(OUTPUT_DIR, "cash_operations.xlsx"),      index=False)
    if not refs.empty:
        refs.to_excel(os.path.join(OUTPUT_DIR, "cash_operation_refs.xlsx"), index=False)

    save_to_db(ops, "cash_operations")
    if not refs.empty:
        save_to_db(refs, "cash_operation_refs")

    print("=== Cash Operations pipeline tugadi ===")
