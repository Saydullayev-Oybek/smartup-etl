import sys
import requests
import pandas as pd

from config import TIMEOUT


def fetch(url: str, headers: dict, key: str) -> pd.DataFrame:
    """
    API dan ma'lumot olib, DataFrame qaytaradi.

    url     — endpoint URL
    headers — Authorization headerlari
    key     — JSON ichidagi kalit (masalan: 'inventory')
    """
    print(f"[FETCH] {url}")

    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        print(f"[XATO] Status: {response.status_code}")
        print(response.text)
        sys.exit(1)

    records = response.json().get(key) or []
    print(f"[OK] {len(records)} ta yozuv olindi")

    if not records:
        return pd.DataFrame()

    return pd.json_normalize(records)
