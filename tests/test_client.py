import pytest
import requests

import client
from exceptions import FetchError


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _patch(monkeypatch, resp=None, exc=None):
    def fake_request(method, url, **kwargs):
        if exc is not None:
            raise exc
        return resp
    monkeypatch.setattr(client._SESSION, "request", fake_request)


def test_fetch_returns_dataframe(monkeypatch):
    _patch(monkeypatch, FakeResponse(200, {"inventory": [{"a": 1}, {"a": 2}]}))
    df = client.fetch("http://x", {}, "inventory")
    assert df["a"].tolist() == [1, 2]


def test_fetch_empty_records_returns_empty_frame(monkeypatch):
    _patch(monkeypatch, FakeResponse(200, {"inventory": []}))
    assert client.fetch("http://x", {}, "inventory").empty


def test_fetch_non_200_raises(monkeypatch):
    _patch(monkeypatch, FakeResponse(500, {}, "server error"))
    with pytest.raises(FetchError):
        client.fetch("http://x", {}, "inventory")


def test_fetch_non_json_raises(monkeypatch):
    _patch(monkeypatch, FakeResponse(200, None, "<html>not json</html>"))
    with pytest.raises(FetchError):
        client.fetch("http://x", {}, "inventory")


def test_fetch_connection_error_raises_fetcherror(monkeypatch):
    _patch(monkeypatch, exc=requests.ConnectionError("down"))
    with pytest.raises(FetchError):
        client.fetch("http://x", {}, "inventory")


def test_fetch_post_sends_body(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["json"] = kwargs.get("json")
        return FakeResponse(200, {"order": [{"deal_id": 1}]})

    monkeypatch.setattr(client._SESSION, "request", fake_request)
    df = client.fetch_post("http://x", {}, {"begin": "01.01.2026"}, "order")
    assert captured["method"] == "POST"
    assert captured["json"] == {"begin": "01.01.2026"}
    assert df["deal_id"].tolist() == [1]


def test_retry_policy_configured():
    # The mounted adapter should carry the configured retry policy.
    adapter = client._SESSION.get_adapter("https://smartup.online")
    assert adapter.max_retries.total >= 1
    assert 429 in adapter.max_retries.status_forcelist
