import pandas as pd
from sqlalchemy import create_engine

from config import DB_URL


def save_to_db(df: pd.DataFrame, table: str) -> None:
    """
    DataFrame ni PostgreSQL ga yuklaydi.
    Jadval mavjud bo'lsa — o'chirib qaytadan yaratadi.

    df    — yuklanadigan DataFrame
    table — jadval nomi (masalan: "products")
    """
    if df.empty:
        print(f"[SKIP] '{table}' bo'sh, o'tkazib yuborildi.")
        return

    engine = create_engine(DB_URL)
    df.to_sql(table, engine, if_exists="replace", index=False)
    print(f"[DB] '{table}' — {len(df)} ta qator yuklandi.")
