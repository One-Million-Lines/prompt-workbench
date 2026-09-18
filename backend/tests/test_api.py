"""HTTP API: auth, JWT lifecycle and capture-key scope enforcement (A35, A45, A49)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from prompt_workbench.app import create_app


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def _login(client) -> str:
    r = client.post("/api/v1/auth/login", json={"username": "demo@promptworkbench.dev", "password": "workbench"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_and_me(client):
    assert client.post("/api/v1/auth/login", json={"username": "x", "password": "y"}).status_code == 401
    token = _login(client)
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["username"] == "demo@promptworkbench.dev"


def test_protected_routes_require_auth(client):
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/projects", headers={"Authorization": "Bearer bogus.token"}).status_code == 401


def test_logout_invalidates_token(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    # token_version bumped -> old token now rejected
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_capture_key_scope_enforcement(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    projects = client.get("/api/v1/projects", headers=headers).json()
    project_id = projects[0]["id"]

    created = client.post("/api/v1/api-keys", headers=headers, json={"name": "intake", "scopes": ["captures:write"]})
    api_key = created.json()["api_key"]
    key_headers = {"Authorization": f"Bearer {api_key}"}

    # capture-only key CAN write a capture
    ingest = client.post(
        "/api/v1/captures",
        headers={**key_headers, "Idempotency-Key": "k1"},
        json={"project_id": project_id, "source": "test", "mode": "rendered",
              "rendered_messages": [{"role": "user", "content": "hi"}], "output": {"text": "ok"}},
    )
    assert ingest.status_code in (200, 201), ingest.text

    # ... but CANNOT read captures (needs captures:read) or list prompts
    assert client.get(f"/api/v1/captures?project_id={project_id}", headers=key_headers).status_code == 403
    assert client.get(f"/api/v1/prompts?project_id={project_id}", headers=key_headers).status_code == 403


def test_secret_never_leaks_in_connection_read(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    connections = client.get("/api/v1/connections", headers=headers).json()
    for conn in connections:
        assert "secret_env_name" not in conn or conn.get("secret_env_name") is None
        assert "secret_value" not in conn
