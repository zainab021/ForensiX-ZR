from datetime import datetime, timedelta, timezone

from app.database.db import SessionLocal
from app.models.models import PasswordReset, User
from app.utils.security import hash_otp


def test_forgot_password_generic_message_for_unknown_user(client):
    resp = client.post("/api/auth/forgot-password", json={"username": "no_such_user"})
    assert resp.status_code == 200
    assert "reset code" in resp.json()["message"]


def test_forgot_password_and_reset_round_trip(client, monkeypatch):
    captured = {}

    def fake_send_otp_email(to, otp):
        captured["to"] = to
        captured["otp"] = otp
        return True

    monkeypatch.setattr("app.routes.auth.send_otp_email", fake_send_otp_email)

    client.post("/api/auth/register", json={
        "full_name": "Reset Flow User",
        "username": "reset_flow_user",
        "email": "reset_flow_user@example.com",
        "password": "originalpass1",
        "role": "citizen",
    })

    resp = client.post("/api/auth/forgot-password", json={"username": "reset_flow_user"})
    assert resp.status_code == 200
    assert captured["to"] == "reset_flow_user@example.com"
    assert len(captured["otp"]) == 6

    reset_resp = client.post("/api/auth/reset-password", json={
        "username": "reset_flow_user",
        "otp": captured["otp"],
        "new_password": "brandnewpass1",
    })
    assert reset_resp.status_code == 200, reset_resp.text

    old_login = client.post("/api/auth/login", json={
        "username": "reset_flow_user", "password": "originalpass1", "role": "citizen",
    })
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={
        "username": "reset_flow_user", "password": "brandnewpass1", "role": "citizen",
    })
    assert new_login.status_code == 200

    reused_resp = client.post("/api/auth/reset-password", json={
        "username": "reset_flow_user",
        "otp": captured["otp"],
        "new_password": "anotherpass1",
    })
    assert reused_resp.status_code == 400


def test_reset_password_wrong_otp_rejected(client):
    client.post("/api/auth/register", json={
        "full_name": "Wrong OTP User",
        "username": "wrong_otp_user",
        "email": "wrong_otp_user@example.com",
        "password": "originalpass1",
        "role": "citizen",
    })
    user = _get_user("wrong_otp_user")
    _insert_reset(user.id, "111111", expires_in_minutes=10)

    resp = client.post("/api/auth/reset-password", json={
        "username": "wrong_otp_user",
        "otp": "999999",
        "new_password": "newpass123",
    })
    assert resp.status_code == 400


def test_reset_password_expired_otp_rejected(client):
    client.post("/api/auth/register", json={
        "full_name": "Expired OTP User",
        "username": "expired_otp_user",
        "email": "expired_otp_user@example.com",
        "password": "originalpass1",
        "role": "citizen",
    })
    user = _get_user("expired_otp_user")
    _insert_reset(user.id, "222222", expires_in_minutes=-1)

    resp = client.post("/api/auth/reset-password", json={
        "username": "expired_otp_user",
        "otp": "222222",
        "new_password": "newpass123",
    })
    assert resp.status_code == 400


def _get_user(username: str) -> User:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()


def _insert_reset(user_id: int, otp: str, expires_in_minutes: int):
    db = SessionLocal()
    try:
        db.add(PasswordReset(
            user_id=user_id,
            otp_hash=hash_otp(otp),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        ))
        db.commit()
    finally:
        db.close()
