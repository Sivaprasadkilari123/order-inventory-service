def test_register_success(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "Secret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email(client):
    payload = {"email": "a@example.com", "password": "Secret123"}
    client.post("/auth/register", json=payload)
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 409


def test_register_short_password_rejected(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "123"})
    assert r.status_code == 422


def test_login_success_returns_bearer_token(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "Secret123"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "Secret123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "Secret123"})
    r = client.post("/auth/login", data={"username": "a@example.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", data={"username": "ghost@example.com", "password": "Secret123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_token(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "tester@example.com"


def test_garbage_token_rejected(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401
