def test_officer_can_create_case(client, officer_headers):
    resp = client.post("/api/cases/", json={
        "case_no": "CASE-1001",
        "title": "Burglary Investigation",
        "crime_type": "Burglary",
        "location": "Sector 5",
        "description": "Break-in reported overnight.",
    }, headers=officer_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["case_no"] == "CASE-1001"


def test_duplicate_case_no_rejected(client, officer_headers):
    payload = {
        "case_no": "CASE-DUP-1",
        "title": "First",
        "crime_type": "Theft",
    }
    first = client.post("/api/cases/", json=payload, headers=officer_headers)
    assert first.status_code == 200
    second = client.post("/api/cases/", json=payload, headers=officer_headers)
    assert second.status_code == 400


def test_citizen_cannot_create_case(client, citizen_headers):
    resp = client.post("/api/cases/", json={
        "case_no": "CASE-CITIZEN-1",
        "title": "Should fail",
        "crime_type": "Theft",
    }, headers=citizen_headers)
    assert resp.status_code == 403


def test_officer_can_assign_case_to_officer(client, officer_headers, admin_headers):
    created = client.post("/api/cases/", json={
        "case_no": "CASE-ASSIGN-1",
        "title": "Assault Investigation",
        "crime_type": "Assault",
    }, headers=officer_headers)
    case_id = created.json()["id"]

    me = client.get("/api/auth/me", headers=officer_headers).json()

    updated = client.patch(f"/api/cases/{case_id}", json={
        "status": "in_progress",
        "assigned_officer_id": me["id"],
    }, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["assigned_officer_id"] == me["id"]
    assert updated.json()["status"] == "in_progress"


def test_only_admin_can_hard_delete_case(client, officer_headers, admin_headers):
    created = client.post("/api/cases/", json={
        "case_no": "CASE-DELETE-1",
        "title": "To Be Deleted",
        "crime_type": "Fraud",
    }, headers=officer_headers)
    case_id = created.json()["id"]

    denied = client.delete(f"/api/cases/{case_id}", headers=officer_headers)
    assert denied.status_code == 403

    allowed = client.delete(f"/api/cases/{case_id}", headers=admin_headers)
    assert allowed.status_code == 200
