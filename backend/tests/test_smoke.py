"""End-to-end smoke test (agent calls are mocked — no API key needed)."""
import uuid

import pytest

from app.agent import service


@pytest.fixture(autouse=True)
def _mock_agent(monkeypatch):
    monkeypatch.setattr(
        service,
        "invoke_keeper",
        lambda session, user, message, **kwargs: f"[mocked] {user.username}: {message}",
    )


def _auth(client):
    username = f"tester_{uuid.uuid4().hex[:8]}"
    client.post("/auth/register", json={"username": username, "password": "pw123456"})
    r = client.post("/auth/login", data={"username": username, "password": "pw123456"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_chat_invoke(client):
    headers = _auth(client)
    r = client.post("/agent/invoke", json={"message": "Where is my order?"}, headers=headers)
    assert r.status_code == 200
    assert "mocked" in r.json()["reply"]
