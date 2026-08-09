import pytest

from app.core.security import hash_password
from app.db import session as db_session
from app.models import User


@pytest.fixture(scope="session")
def viewer_headers(client):
    with db_session.SessionLocal() as session:
        session.add(
            User(
                username="users_viewer",
                email="users_viewer@test.local",
                password_hash=hash_password("viewerpass"),
                role="viewer",
            )
        )
        session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "users_viewer", "password": "viewerpass"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_can_list_users(client):
    resp = client.get("/api/v1/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(u["username"] == "testadmin" for u in body["items"])


def test_admin_can_create_and_update_user(client):
    resp = client.post(
        "/api/v1/users",
        json={
            "username": "newanalyst",
            "email": "newanalyst@test.local",
            "password": "somepass123",
            "role": "analyst",
        },
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]
    assert resp.json()["role"] == "analyst"

    resp = client.patch(f"/api/v1/users/{user_id}", json={"role": "viewer", "is_active": False})
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"
    assert resp.json()["is_active"] is False

    resp = client.delete(f"/api/v1/users/{user_id}")
    assert resp.status_code == 204


def test_create_user_duplicate_conflict(client):
    resp = client.post(
        "/api/v1/users",
        json={
            "username": "testadmin",
            "email": "someone-else@test.local",
            "password": "somepass123",
            "role": "viewer",
        },
    )
    assert resp.status_code == 409


def test_viewer_cannot_manage_users(client, viewer_headers):
    assert client.get("/api/v1/users", headers=viewer_headers).status_code == 403
    assert client.post(
        "/api/v1/users",
        json={
            "username": "x",
            "email": "x@test.local",
            "password": "somepass123",
            "role": "viewer",
        },
        headers=viewer_headers,
    ).status_code == 403


def test_admin_cannot_delete_self(client):
    me = client.get("/api/v1/auth/me").json()
    resp = client.delete(f"/api/v1/users/{me['id']}")
    assert resp.status_code == 400
