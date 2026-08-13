import os
import sys

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only-in-ci")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_forensix.db")
os.environ.setdefault("SEED_DEMO_USERS", "false")
os.environ.setdefault("VALID_OFFICER_CODES", "ZR-ADMIN-001,ZR-OFC-101")
os.environ.setdefault("CORS_ORIGINS", "http://127.0.0.1:5500")
os.environ.setdefault("ALLOWED_HOSTS", "*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import engine, Base
from app.routes import auth as auth_routes
from app.routes import evidence as evidence_routes
from app.routes import reports as reports_routes

TEST_DB_FILE = "./test_forensix.db"


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limits():
    # The test suite registers/logs in far more often than the production
    # rate limits allow (e.g. 5/minute on register). Disable limiting for
    # the whole session so functional tests aren't flaky based on how many
    # other tests ran first; rate-limit behavior itself is verified manually.
    for module in (auth_routes, reports_routes, evidence_routes):
        module.limiter.enabled = False


@pytest.fixture(scope="session", autouse=True)
def _clean_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _register_and_login(client, *, username, password, role, full_name, officer_code=None):
    client.post("/api/auth/register", json={
        "full_name": full_name,
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "role": role,
        "officer_code": officer_code,
    })
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
        "role": role,
        "officer_code": officer_code,
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return _register_and_login(
        client, username="test_admin", password="admin_pass1", role="admin",
        full_name="Test Admin", officer_code="ZR-ADMIN-001",
    )


@pytest.fixture(scope="session")
def officer_headers(client):
    return _register_and_login(
        client, username="test_officer", password="officer_pass1", role="officer",
        full_name="Test Officer", officer_code="ZR-OFC-101",
    )


@pytest.fixture(scope="session")
def citizen_headers(client):
    return _register_and_login(
        client, username="test_citizen", password="citizen_pass1", role="citizen",
        full_name="Test Citizen",
    )
