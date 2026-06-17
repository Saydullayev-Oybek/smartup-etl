import pandas as pd
import pytest
from sqlalchemy import create_engine, text

import loader


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield eng
    eng.dispose()


def _int64(df, col):
    df[col] = df[col].astype("Int64")
    return df


def _rows(engine, sql):
    with engine.begin() as conn:
        return conn.execute(text(sql)).fetchall()


def test_upsert_dimension_preserves_untouched_rows(engine):
    df1 = _int64(pd.DataFrame({"id": [1, 2, 3], "v": ["a", "b", "c"]}), "id")
    loader.save_to_db(df1, "dim", key="id", strategy="upsert", engine=engine)

    df2 = _int64(pd.DataFrame({"id": [2, 4], "v": ["B", "d"]}), "id")
    loader.save_to_db(df2, "dim", key="id", strategy="upsert", engine=engine)

    assert _rows(engine, "select id, v from dim order by id") == [
        (1, "a"), (2, "B"), (3, "c"), (4, "d"),
    ]


def test_child_merge_refreshes_by_parent(engine):
    c1 = _int64(pd.DataFrame({"deal_id": [10, 10, 11], "line": ["x", "y", "z"]}), "deal_id")
    loader.save_to_db(c1, "child", key="deal_id", strategy="upsert", engine=engine)

    # deal 10 now has a single line; deal 11 must remain untouched.
    c2 = _int64(pd.DataFrame({"deal_id": [10], "line": ["only"]}), "deal_id")
    loader.save_to_db(c2, "child", key="deal_id", strategy="upsert", engine=engine)

    assert _rows(engine, "select deal_id, line from child order by deal_id, line") == [
        (10, "only"), (11, "z"),
    ]


def test_replace_strategy(engine):
    df1 = pd.DataFrame({"a": [1, 2]})
    loader.save_to_db(df1, "t", strategy="replace", engine=engine)
    df2 = pd.DataFrame({"a": [3]})
    loader.save_to_db(df2, "t", strategy="replace", engine=engine)
    assert _rows(engine, "select a from t") == [(3,)]


def test_empty_frame_is_skipped(engine):
    df = _int64(pd.DataFrame({"id": [1]}), "id")
    loader.save_to_db(df, "dim", key="id", strategy="upsert", engine=engine)
    loader.save_to_db(pd.DataFrame(), "dim", key="id", strategy="upsert", engine=engine)
    assert _rows(engine, "select id from dim") == [(1,)]


def test_upsert_without_key_falls_back_to_replace(engine):
    df1 = pd.DataFrame({"a": [1, 2]})
    loader.save_to_db(df1, "t", strategy="upsert", engine=engine)  # no key
    df2 = pd.DataFrame({"a": [9]})
    loader.save_to_db(df2, "t", strategy="upsert", engine=engine)
    assert _rows(engine, "select a from t") == [(9,)]
