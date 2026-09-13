import json
from types import SimpleNamespace

import pytest

from src.engine import Engine


class _Request:
    def __init__(self, authorization=None):
        self.headers = {}
        if authorization is not None:
            self.headers["Authorization"] = authorization


def _payload(response):
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_transcripts_handler_returns_503_without_configured_token(monkeypatch):
    monkeypatch.delenv("DANJIK_KNOWLEDGE_TOKEN", raising=False)
    engine = Engine.__new__(Engine)
    engine.session_store = SimpleNamespace(get_live_transcripts=None)

    response = await engine._sessions_transcripts_handler(_Request("Bearer anything"))

    assert response.status == 503
    assert _payload(response) == {"calls": [], "error": "service_unavailable"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "authorization",
    [None, "Basic token", "Bearer wrong", "Bearer 잘못된토큰"],
)
async def test_transcripts_handler_rejects_invalid_bearer_token(monkeypatch, authorization):
    monkeypatch.setenv("DANJIK_KNOWLEDGE_TOKEN", "correct")
    engine = Engine.__new__(Engine)
    engine.session_store = SimpleNamespace(get_live_transcripts=None)

    response = await engine._sessions_transcripts_handler(_Request(authorization))

    assert response.status == 401
    assert _payload(response) == {"calls": [], "error": "unauthorized"}


@pytest.mark.asyncio
async def test_transcripts_handler_returns_store_payload_for_valid_token(monkeypatch):
    monkeypatch.setenv("DANJIK_KNOWLEDGE_TOKEN", "correct")

    async def get_live_transcripts():
        return {"calls": [{"call_id": "call-1", "messages": []}]}

    engine = Engine.__new__(Engine)
    engine.session_store = SimpleNamespace(get_live_transcripts=get_live_transcripts)

    response = await engine._sessions_transcripts_handler(_Request("Bearer correct"))

    assert response.status == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert _payload(response) == {"calls": [{"call_id": "call-1", "messages": []}]}
