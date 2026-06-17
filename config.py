"""Central configuration for the SmartUp ETL.

All secrets and environment-specific values are read from environment
variables — nothing sensitive is hardcoded in source. A local ``.env`` file
is loaded automatically when present (see ``.env.example``).

Backward compatibility: the public names previously exported by this module
(``ENDPOINTS``, ``OUTPUT_DIR``, ``TIMEOUT``, ``DB_URL``, ``get_headers``) are
preserved so existing pipelines keep working unchanged.
"""
from __future__ import annotations

import base64
import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

_ROOT = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    """Best-effort load of a local .env file without a hard dependency.

    Only sets keys that are not already present in the environment so that
    real environment variables (e.g. injected by Airflow/Docker) always win.
    """
    env_path = Path(os.getenv("APP_ENV_FILE", _ROOT / ".env"))
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except OSError:
        # A missing/unreadable .env must never crash configuration loading.
        pass


_load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# ── API ───────────────────────────────────────────────────────────────────────
BASE_URL     = os.getenv("SMARTUP_BASE_URL", "https://smartup.online")
PROJECT_CODE = os.getenv("SMARTUP_PROJECT_CODE", "trade")
FILIAL_ID    = os.getenv("SMARTUP_FILIAL_ID", "86401")
TIMEOUT      = int(os.getenv("SMARTUP_TIMEOUT", "150"))

# Retry policy for transient HTTP failures (see client.py).
HTTP_RETRIES        = int(os.getenv("SMARTUP_HTTP_RETRIES", "5"))
HTTP_BACKOFF_FACTOR = float(os.getenv("SMARTUP_HTTP_BACKOFF", "1.0"))

ENDPOINTS = {
    "inventory":             f"{BASE_URL}/b/anor/mxsx/mr/inventory$export",
    "natural_person":        f"{BASE_URL}/b/anor/mxsx/mr/natural_person$export",
    "legal_person":          f"{BASE_URL}/b/anor/mxsx/mr/legal_person$export",
    "order":                 f"{BASE_URL}/b/trade/txs/tdeal/order$export",
    "return":                f"{BASE_URL}/b/anor/mxsx/mdeal/return$export",
    "visit":                 f"{BASE_URL}/b/trade/txs/tvt/visit$export",
    "writeoff":              f"{BASE_URL}/b/anor/mxsx/mkw/writeoff$export",
    "Return_to_suppliers":   f"{BASE_URL}/b/anor/mxsx/mkw/return$export",
    "Payments_from_clients": f"{BASE_URL}/b/trade/txs/tcs/cashin$export",
    "Bank_Statements":       f"{BASE_URL}/b/anor/mxsx/mkcs/bank_operation$export",
    "Cash_Operations":       f"{BASE_URL}/b/anor/mxsx/mkcs/cash_operation$export",
    "Product_group":         f"{BASE_URL}/b/anor/mxsx/mr/product_group$export",
    "Inventory_price":       f"{BASE_URL}/b/anor/api/v2/mkf/product_price$export",
    "Persons_group":         f"{BASE_URL}/b/anor/mxsx/mr/person_group$export",
}

# ── Database ──────────────────────────────────────────────────────────────────
def _build_db_url() -> str:
    """Build the SQLAlchemy URL from env vars. No password is ever hardcoded."""
    explicit = os.getenv("DB_URL")
    if explicit:
        return explicit

    user     = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5432")
    name     = os.getenv("DB_NAME", "smartup")

    auth = f"{user}:{quote_plus(password)}" if password else user
    return f"postgresql+psycopg2://{auth}@{host}:{port}/{name}"


DB_URL = _build_db_url()

# Load strategy: "upsert" (recommended, idempotent) or "replace" (legacy).
LOAD_STRATEGY = os.getenv("LOAD_STRATEGY", "upsert").strip().lower()

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR    = os.getenv("OUTPUT_DIR", "CleanedData")
WRITE_EXCEL   = _get_bool("WRITE_EXCEL", True)

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_FILE = Path(os.getenv("AUTH_FILE", _ROOT / "auth.json"))


@lru_cache(maxsize=1)
def get_headers() -> dict:
    """Return SmartUp API auth headers (Basic auth, Base64).

    Credentials come from ``SMARTUP_USERNAME``/``SMARTUP_PASSWORD`` env vars
    when set, otherwise from ``auth.json`` (gitignored). The result is cached
    so the file is read at most once per process.
    """
    username = os.getenv("SMARTUP_USERNAME")
    password = os.getenv("SMARTUP_PASSWORD")

    if not (username and password):
        try:
            auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"No SmartUp credentials: set SMARTUP_USERNAME/SMARTUP_PASSWORD "
                f"or create {AUTH_FILE}."
            ) from exc
        username = auth["username"]
        password = auth["password"]

    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "project_code":  PROJECT_CODE,
        "filial_id":     FILIAL_ID,
    }
