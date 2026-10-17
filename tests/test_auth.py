from .conftest import register


def test_register_returns_token(client):
    res = register(client)
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["email"] == "dev@example.com"
    assert body["token"]


def test_register_validates_input(client):
    res = client.post("/api/auth/register", json={"email": "bad", "password": "x"})
    assert res.status_code == 422
    details = res.get_json()["details"]
    assert set(details) == {"email", "name", "password"}


def test_duplicate_email_rejected(client):
    register(client)
    res = register(client, email="DEV@example.com")
    assert res.status_code == 409


def test_login_success_and_failure(client):
    register(client)
    ok = client.post(
        "/api/auth/login", json={"email": "dev@example.com", "password": "password123"}
    )
    assert ok.status_code == 200
    bad = client.post(
        "/api/auth/login", json={"email": "dev@example.com", "password": "wrong-pass"}
    )
    assert bad.status_code == 401


def test_me_requires_token(client, auth_headers):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["user"]["name"] == "Dev"
