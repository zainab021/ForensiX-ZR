def test_officer_can_create_and_list_evidence_for_case(client, officer_headers):
    case = client.post("/api/cases/", json={
        "case_no": "CASE-EVID-1",
        "title": "Robbery Investigation",
        "crime_type": "Robbery",
    }, headers=officer_headers).json()

    created = client.post("/api/evidence/", json={
        "case_id": case["id"],
        "title": "CCTV Footage",
        "evidence_type": "video",
        "description": "Footage from the corner store camera.",
    }, headers=officer_headers)
    assert created.status_code == 200, created.text

    listed = client.get(f"/api/evidence/case/{case['id']}", headers=officer_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_evidence_for_nonexistent_case_rejected(client, officer_headers):
    resp = client.post("/api/evidence/", json={
        "case_id": 999999,
        "title": "Orphan Evidence",
        "evidence_type": "document",
    }, headers=officer_headers)
    assert resp.status_code == 404


def test_citizen_cannot_create_evidence(client, citizen_headers):
    resp = client.post("/api/evidence/", json={
        "title": "Should fail",
        "evidence_type": "document",
    }, headers=citizen_headers)
    assert resp.status_code == 403


def test_citizen_can_upload_evidence_to_own_report(client, citizen_headers):
    report = client.post("/api/reports/", json={
        "title": "Lost Wallet",
        "category": "Lost Property",
        "description": "Wallet lost near the market.",
    }, headers=citizen_headers).json()

    files = {"file": ("receipt.png", b"\x89PNG\r\n\x1a\nfakepngbytes", "image/png")}
    resp = client.post(f"/api/evidence/upload/report/{report['id']}", files=files, headers=citizen_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["report_id"] == report["id"]
