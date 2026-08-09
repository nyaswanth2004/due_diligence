import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db import session as db_session
from app.models import User


@pytest.fixture(scope="session")
def analyst_headers(client: TestClient) -> dict[str, str]:
    with db_session.SessionLocal() as session:
        session.add(
            User(
                username="testanalyst",
                email="analyst@test.local",
                password_hash=hash_password("analystpass"),
                role="analyst",
            )
        )
        session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "testanalyst", "password": "analystpass"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture(scope="session")
def viewer_headers(client: TestClient) -> dict[str, str]:
    with db_session.SessionLocal() as session:
        session.add(
            User(
                username="testviewer",
                email="viewer@test.local",
                password_hash=hash_password("viewerpass"),
                role="viewer",
            )
        )
        session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "testviewer", "password": "viewerpass"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_login_returns_token_and_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "testpass"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["username"] == "testadmin"
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "nope"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "nope"},
        headers={"Authorization": ""},
    )
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testadmin"


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": ""})
    assert resp.status_code == 401


def test_health_is_public(client):
    resp = client.get("/api/v1/health", headers={"Authorization": ""})
    assert resp.status_code == 200


def test_viewer_cannot_upload(client, viewer_headers):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("x.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_analyst_can_upload(client, analyst_headers):
    from tests.helpers import make_balance_sheet_pdf, wait_for_status

    resp = client.post(
        "/api/v1/documents",
        files={"file": ("bs.pdf", make_balance_sheet_pdf(), "application/pdf")},
        headers=analyst_headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    wait_for_status(client, doc_id)

    resp = client.delete(f"/api/v1/documents/{doc_id}", headers=analyst_headers)
    assert resp.status_code == 204


def test_viewer_cannot_generate_report(client, viewer_headers):
    resp = client.post(
        "/api/v1/reports/generate",
        json={"document_ids": ["whatever"]},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_viewer_can_search(client, viewer_headers):
    resp = client.get(
        "/api/v1/search/stats",
        headers=viewer_headers,
    )
    assert resp.status_code == 200


def test_viewer_cannot_read_audit_log(client, viewer_headers):
    resp = client.get("/api/v1/audit", headers=viewer_headers)
    assert resp.status_code == 403


def test_admin_can_read_audit_log(client):
    resp = client.get("/api/v1/audit?limit=50")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    actions = {item["action"] for item in resp.json()["items"]}
    assert "auth.login" in actions
