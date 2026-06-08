import os
import pandas as pd

from config import ENDPOINTS, OUTPUT_DIR, get_headers
from client import fetch
from loader import save_to_db


def build_payments(raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "cashin_id", "filial_code", "external_id",
        "cashin_time", "cashin_date", "cashin_number",
        "bill_collector_code", "client_code", "client_id",
        "client_name", "client_tin", "subfilial_code",
        "contract_code", "payment_type_code", "currency_code",
        "cashbox_code", "bank_account_code", "amount", "posted",
        "bank_trans_number", "bank_trans_date", "purpose", "note",
    ]
    df = raw[[c for c in columns if c in raw.columns]].copy()

    df["cashin_id"] = pd.to_numeric(df["cashin_id"], errors="coerce").astype("Int64")
    df["client_id"] = pd.to_numeric(df["client_id"], errors="coerce").astype("Int64")
    df["amount"]    = pd.to_numeric(df["amount"],    errors="coerce")

    return df.drop_duplicates(subset=["cashin_id"]).reset_index(drop=True)


def run():
    print("=== Payments pipeline ===")

    raw = fetch(ENDPOINTS["Payments_from_clients"], get_headers(), key="cashin")
    if raw.empty:
        print("[INFO] Hech qanday ma'lumot topilmadi.")
        return

    payments = build_payments(raw)
    print(f"[JAMI] {len(payments)} ta to'lov")

    payments.to_excel(os.path.join(OUTPUT_DIR, "payments.xlsx"), index=False)
    save_to_db(payments, "payments")

    print("=== Payments pipeline tugadi ===")

