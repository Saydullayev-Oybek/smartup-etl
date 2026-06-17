"""Centralised logging for the SmartUp ETL.

Replaces scattered ``print`` calls with the stdlib ``logging`` module so that
output has levels, timestamps and (optionally) structured JSON — and so it
integrates cleanly with Airflow's task log capture.

Usage::

    from logging_config import get_logger
    log = get_logger(__name__)
    log.info("Products pipeline started")
"""
from __future__ import annotations

import json
import logging
import os
import sys

_CONFIGURED = False

_TEXT_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


class _JsonFormatter(logging.Formatter):
    """Minimal structured-logging formatter (no external dependency)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      self.formatTime(record),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None, *, json_logs: bool | None = None) -> None:
    """Configure the root logger once. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    if json_logs is None:
        json_logs = os.getenv("LOG_JSON", "false").strip().lower() in {"1", "true", "yes", "on"}

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter() if json_logs else logging.Formatter(_TEXT_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))

    # Quieten noisy third-party loggers.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Configures logging on first use."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
