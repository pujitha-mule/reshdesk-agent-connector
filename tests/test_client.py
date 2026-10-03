"""Unit tests for FreshdeskClient. Mocks all HTTP; no real account required."""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock

import pytest
import requests

os.environ.setdefault("FRESHDESK_DOMAIN", "test.freshdesk.com")
os.environ.setdefault("FRESHDESK_API_KEY", "testkey")

from src.freshdesk_client import (  # noqa: E402
    FreshdeskClient,
    FreshdeskAuthError,
    FreshdeskNotFoundError,
    FreshdeskError,
    FreshdeskRateLimitError,
)


def _resp(status: int, json_body=None, headers=None, content=b"x"):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.headers = headers or {}
    r.content = content
    r.json.return_value = json_body if json_body is not None else {}
    r.text = str(json_body)
    return r


@pytest.fixture
def client():
    c = FreshdeskClient(domain="test.freshdesk.com", api_key="testkey")
    c.session = MagicMock()
    return c


def test_list_tickets_happy(client):
    client.session.request.return_value = _resp(200, [{"id": 1}, {"id": 2}])
    out = client.list_tickets(page=1, per_page=30)
    assert out == [{"id": 1}, {"id": 2}]
    _, kwargs = client.session.request.call_args
    assert kwargs["params"] == {"page": 1, "per_page": 30}


def test_list_tickets_clamps_per_page_and_page(client):
    client.session.request.return_value = _resp(200, [])
    client.list_tickets(page=-5, per_page=500)
    _, kwargs = client.session.request.call_args
    assert kwargs["params"]["page"] == 1
    assert kwargs["params"]["per_page"] == 100


def test_get_ticket_happy(client):
    client.session.request.return_value = _resp(200, {"id": 42, "subject": "hi"})
    out = client.get_ticket(42)
    assert out["id"] == 42
    args, _ = client.session.request.call_args
    assert "/tickets/42" in args[1]


def test_search_tickets_quotes_query(client):
    client.session.request.return_value = _resp(200, {"results": [{"id": 7}], "total": 1})
    out = client.search_tickets("status:2")
    assert out == [{"id": 7}]
    _, kwargs = client.session.request.call_args
    assert kwargs["params"]["query"] == '"status:2"'


def test_search_tickets_rejects_empty(client):
    with pytest.raises(FreshdeskError):
        client.search_tickets("   ")


def test_401_raises_auth_error(client):
    client.session.request.return_value = _resp(401, {"error": "bad key"})
    with pytest.raises(FreshdeskAuthError):
        client.get_ticket(1)


def test_403_raises_auth_error(client):
    client.session.request.return_value = _resp(403, {"error": "forbidden"})
    with pytest.raises(FreshdeskAuthError):
        client.list_tickets()


def test_404_raises_not_found(client):
    client.session.request.return_value = _resp(404, {"error": "nope"})
    with pytest.raises(FreshdeskNotFoundError):
        client.get_ticket(999)


def test_429_retries_then_succeeds(client, monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    client.session.request.side_effect = [
        _resp(429, headers={"Retry-After": "2"}),
        _resp(200, [{"id": 1}]),
    ]
    out = client.list_tickets()
    assert out == [{"id": 1}]
    assert sleeps == [2.0]


def test_429_gives_up_after_max_retries(client, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    client.session.request.return_value = _resp(429, headers={"Retry-After": "0"})
    with pytest.raises(FreshdeskRateLimitError):
        client.list_tickets()


def test_5xx_retries_then_succeeds(client, monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    client.session.request.side_effect = [
        _resp(503),
        _resp(502),
        _resp(200, [{"id": 1}]),
    ]
    out = client.list_tickets()
    assert out == [{"id": 1}]
    assert sleeps == [1.0, 2.0]


def test_5xx_gives_up_after_max_retries(client, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    client.session.request.return_value = _resp(500)
    with pytest.raises(FreshdeskError, match="500"):
        client.list_tickets()


def test_timeout_raises_freshdesk_error(client):
    client.session.request.side_effect = requests.Timeout("boom")
    with pytest.raises(FreshdeskError, match="timed out"):
        client.list_tickets()