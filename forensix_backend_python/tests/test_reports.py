def test_citizen_can_create_and_view_own_report(client, citizen_headers):
    resp = client.post("/api/reports/", json={
        "title": "Stolen Bicycle",
        "category": "Theft",
        "description": "My bicycle was stolen from outside my house.",
        "location": "Model Town",
        "priority": "normal",
    }, headers=citizen_headers)
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["title"] == "Stolen Bicycle"

    listed = client.get("/api/reports/", headers=citizen_headers)
    assert listed.status_code == 200
    assert any(r["id"] == report["id"] for r in listed.json())


def test_report_creation_requires_auth(client):
    resp = client.post("/api/reports/", json={
        "title": "Unauthenticated",
        "category": "Theft",
        "description": "Should be rejected",
    })
    assert resp.status_code == 401


def test_citizen_cannot_view_other_citizens_report(client, citizen_headers):
    resp = client.post("/api/reports/", json={
        "title": "Private Report",
        "category": "Theft",
        "description": "Only visible to owner and staff.",
    }, headers=citizen_headers)
    report_id = resp.json()["id"]

    other_headers = _register_and_login(client, "another_citizen", "otherpass1")
    forbidden = client.get(f"/api/reports/{report_id}", headers=other_headers)
    assert forbidden.status_code == 403


def test_officer_can_view_and_update_report(client, citizen_headers, officer_headers):
    resp = client.post("/api/reports/", json={
        "title": "Vandalism",
        "category": "Property Damage",
        "description": "Graffiti on public wall.",
    }, headers=citizen_headers)
    report_id = resp.json()["id"]

    officer_view = client.get(f"/api/reports/{report_id}", headers=officer_headers)
    assert officer_view.status_code == 200

    updated = client.patch(f"/api/reports/{report_id}", json={"status": "verified"}, headers=officer_headers)
    assert updated.status_code == 200
    assert updated.json()["status"] == "verified"


def _register_and_login(client, username, password):
    client.post("/api/auth/register", json={
        "full_name": "Extra Citizen",
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "role": "citizen",
    })
    resp = client.post("/api/auth/login", json={"username": username, "password": password, "role": "citizen"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
