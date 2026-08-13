def test_register_citizen_success(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Alice Citizen",
        "username": "alice_citizen",
        "email": "alice@example.com",
        "password": "alicepass1",
        "role": "citizen",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "alice_citizen"
    assert body["role"] == "citizen"


def test_register_officer_requires_valid_code(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Bad Officer",
        "username": "bad_officer",
        "email": "bad_officer@example.com",
        "password": "badpass123",
        "role": "officer",
        "officer_code": "NOT-A-REAL-CODE",
    })
    assert resp.status_code == 400
    assert "Invalid officer" in resp.json()["detail"]


def test_register_officer_missing_code(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "No Code Officer",
        "username": "nocode_officer",
        "email": "nocode@example.com",
        "password": "nocodepass1",
        "role": "officer",
    })
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"]


def test_register_duplicate_officer_code_rejected_cleanly(client):
    first = client.post("/api/auth/register", json={
        "full_name": "First Officer",
        "username": "first_officer_dup_code",
        "email": "first_officer_dup_code@example.com",
        "password": "firstpass123",
        "role": "officer",
        "officer_code": "ZR-OFC-102",
    })
    assert first.status_code == 200, first.text

    second = client.post("/api/auth/register", json={
        "full_name": "Second Officer",
        "username": "second_officer_dup_code",
        "email": "second_officer_dup_code@example.com",
        "password": "secondpass123",
        "role": "officer",
        "officer_code": "ZR-OFC-102",
    })
    assert second.status_code == 400
    assert "already" in second.json()["detail"].lower()


def test_register_duplicate_username_rejected(client):
    payload = {
        "full_name": "Dup User",
        "username": "dup_user",
        "email": "dup1@example.com",
        "password": "duppass123",
        "role": "citizen",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200
    payload["email"] = "dup2@example.com"
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


def test_login_success_and_returns_token(client):
    client.post("/api/auth/register", json={
        "full_name": "Login User",
        "username": "login_user",
        "email": "login_user@example.com",
        "password": "loginpass1",
        "role": "citizen",
    })
    resp = client.post("/api/auth/login", json={
        "username": "login_user",
        "password": "loginpass1",
        "role": "citizen",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "login_user"


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={
        "full_name": "Wrongpass User",
        "username": "wrongpass_user",
        "email": "wrongpass@example.com",
        "password": "correctpass1",
        "role": "citizen",
    })
    resp = client.post("/api/auth/login", json={
        "username": "wrongpass_user",
        "password": "incorrectpass",
        "role": "citizen",
    })
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, citizen_headers):
    resp = client.get("/api/auth/me", headers=citizen_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "test_citizen"
