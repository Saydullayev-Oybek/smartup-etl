import pandas as pd

from transforms import explode_records, nested_columns, select, to_int64, to_numeric


def test_to_int64_coerces_and_nulls():
    df = pd.DataFrame({"a": ["1", "2", "x"]})
    to_int64(df, ["a"])
    assert str(df["a"].dtype) == "Int64"
    assert df["a"].iloc[0] == 1 and df["a"].iloc[1] == 2
    assert pd.isna(df["a"].iloc[2])


def test_to_numeric_ignores_missing_column():
    df = pd.DataFrame({"a": ["1.5"]})
    to_numeric(df, ["a", "does_not_exist"])
    assert df["a"].iloc[0] == 1.5


def test_select_keeps_only_existing_in_order():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    out = select(df, ["c", "a", "missing"])
    assert list(out.columns) == ["c", "a"]
    # returns a copy
    out["a"] = 99
    assert df["a"].iloc[0] == 1


def test_explode_records_single_parent():
    raw = pd.DataFrame({"deal_id": [1, 2], "items": [[{"x": 1}, {"x": 2}], []]})
    out = explode_records(raw, "deal_id", "items")
    assert len(out) == 2
    assert out["deal_id"].tolist() == [1, 1]
    assert out["x"].tolist() == [1, 2]


def test_explode_records_multi_parent():
    raw = pd.DataFrame({"pid": [10], "code": ["A"], "pt": [[{"price": 5}]]})
    out = explode_records(raw, ["pid", "code"], "pt")
    assert out.loc[0, "pid"] == 10
    assert out.loc[0, "code"] == "A"
    assert out.loc[0, "price"] == 5


def test_explode_records_empty_and_missing():
    raw = pd.DataFrame({"deal_id": [1], "items": [None]})
    assert explode_records(raw, "deal_id", "items").empty
    assert explode_records(raw, "deal_id", "missing").empty


def test_nested_columns():
    df = pd.DataFrame({"a": [[1]], "b": [1], "c": [None]})
    assert nested_columns(df) == ["a"]
