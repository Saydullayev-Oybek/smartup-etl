"""HTTP client for the SmartUp API.

A single pooled :class:`requests.Session` with automatic retry/backoff is
shared across the process. Transient failures (429/5xx, connection resets)
are retried; permanent failures raise :class:`FetchError` so the orchestrator
can handle them — the client never calls ``sys.exit``.
"""
from __future__ import annotations

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import HTTP_BACKOFF_FACTOR, HTTP_RETRIES, TIMEOUT
from core.exceptions import FetchError
from core.logging_config import get_logger

log = get_logger(__name__)

_MAX_ERR_SNIPPET = 500


def _build_session() -> requests.Session:
    retry = Retry(
        total=HTTP_RETRIES,
        connect=HTTP_RETRIES,
        read=HTTP_RETRIES,
        status=HTTP_RETRIES,
        backoff_factor=HTTP_BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Module-level singleton — connection pool reused across all requests.
_SESSION = _build_session()


def _records_to_frame(payload: dict, key: str) -> pd.DataFrame:
    records = (payload or {}).get(key) or []
    log.info("Received %d records (key=%s)", len(records), key)
    if not records:
        return pd.DataFrame()
    return pd.json_normalize(records)


def _request(
    method: str, url: str, headers: dict, key: str, *, json_body: dict | None = None,
) -> pd.DataFrame:
    log.info("[%s] %s", method, url)
    try:
        response = _SESSION.request(
            method, url, headers=headers, json=json_body, timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise FetchError(f"{method} {url} failed: {exc}") from exc

    if response.status_code != 200:
        snippet = (response.text or "")[:_MAX_ERR_SNIPPET].replace("\n", " ")
        log.error("HTTP %s for %s — %s", response.status_code, url, snippet)
        raise FetchError(f"HTTP {response.status_code} for {url}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchError(f"Non-JSON response from {url}") from exc

    return _records_to_frame(payload, key)


def fetch(url: str, headers: dict, key: str) -> pd.DataFrame:
    """GET ``url`` and return the records under ``key`` as a DataFrame."""
    return _request("GET", url, headers, key)


def fetch_post(url: str, headers: dict, body: dict, key: str) -> pd.DataFrame:
    """POST ``body`` to ``url`` and return the records under ``key``."""
    return _request("POST", url, headers, key, json_body=body)
