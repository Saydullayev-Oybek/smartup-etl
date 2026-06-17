import pandas as pd
import pytest

from core import validation
from core.exceptions import DataValidationError


def _int64(values):
    return pd.Series(values, dtype="Int64")


def test_null_key_warns_by_default(monkeypatch, caplog):
    monkeypatch.setenv("VALIDATION_STRICT", "false")
    df = pd.DataFrame({"id": _int64([1, None])})
    validation.validate_table(df, "t", key="id")  # must not raise


def test_null_key_strict_raises(monkeypatch):
    monkeypatch.setenv("VALIDATION_STRICT", "true")
    df = pd.DataFrame({"id": _int64([1, None])})
    with pytest.raises(DataValidationError):
        validation.validate_table(df, "t", key="id")


def test_duplicate_key_strict_raises(monkeypatch):
    monkeypatch.setenv("VALIDATION_STRICT", "true")
    df = pd.DataFrame({"id": _int64([1, 1])})
    with pytest.raises(DataValidationError):
        validation.validate_table(df, "t", key="id", unique=True)


def test_non_null_columns_strict_raises(monkeypatch):
    monkeypatch.setenv("VALIDATION_STRICT", "true")
    df = pd.DataFrame({"id": _int64([1, 2]), "amount": [1.0, None]})
    with pytest.raises(DataValidationError):
        validation.validate_table(df, "t", key="id", non_null=["amount"])


def test_clean_frame_passes_strict(monkeypatch):
    monkeypatch.setenv("VALIDATION_STRICT", "true")
    df = pd.DataFrame({"id": _int64([1, 2])})
    validation.validate_table(df, "t", key="id", unique=True)  # no raise


def test_empty_frame_noop(monkeypatch):
    monkeypatch.setenv("VALIDATION_STRICT", "true")
    validation.validate_table(pd.DataFrame(), "t", key="id")  # no raise
