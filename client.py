import sys
import requests
import pandas as pd

from config import TIMEOUT


def _safe_print(text: str):
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
    sys.stdout.buffer.flush()


def fetch_post(url: str, headers: dict, body: dict, key: str) -> pd.DataFrame:
    """POST so'rov yuborib DataFrame qaytaradi."""
    print(f"[FETCH POST] {url}")

    response = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)

    if response.status_code != 200:
        print(f"[XATO] Status: {response.status_code}")
        _safe_print(response.text)
        sys.exit(1)

    records = response.json().get(key) or []
    print(f"[OK] {len(records)} ta yozuv olindi")

    if not records:
        return pd.DataFrame()

    return pd.json_normalize(records)


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
        _safe_print(response.text)
        sys.exit(1)

    records = response.json().get(key) or []
    print(f"[OK] {len(records)} ta yozuv olindi")

    if not records:
        return pd.DataFrame()

    return pd.json_normalize(records)
