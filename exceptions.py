"""Custom exception hierarchy for the SmartUp ETL.

Raising typed exceptions (instead of calling ``sys.exit``) lets the
orchestrator — Airflow or ``main.py`` — decide how to handle, retry and
report failures, and keeps library code free of process-level side effects.
"""
from __future__ import annotations


class ETLError(Exception):
    """Base class for all ETL errors."""


class FetchError(ETLError):
    """Raised when extracting data from the API fails."""


class LoadError(ETLError):
    """Raised when loading data into the database fails."""


class DataValidationError(ETLError):
    """Raised when transformed data fails a quality/validation check."""
