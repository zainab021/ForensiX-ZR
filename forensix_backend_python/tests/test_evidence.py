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


def test_upload_rejects_spoofed_content_type(client, citizen_headers):
    report = client.post("/api/reports/", json={
        "title": "Spoofed Upload Test",
        "category": "Lost Property",
        "description": "Report used to test upload content sniffing.",
    }, headers=citizen_headers).json()

    # Client claims this is a jpeg with a .jpg filename, but the actual bytes
    # are plain text — the server must reject based on real content, not the
    # client-supplied Content-Type header or filename extension.
    files = {"file": ("totally-a-photo.jpg", b"this is not actually an image", "image/jpeg")}
    resp = client.post(f"/api/evidence/upload/report/{report['id']}", files=files, headers=citizen_headers)
    assert resp.status_code == 400


# ── SEC-06 tests: authenticated evidence file serving ────────────────────────

def test_unauthenticated_cannot_access_uploads_directly(client):
    """SEC-06: The legacy /uploads static path must NOT be accessible without auth."""
    # The public StaticFiles mount has been removed; any request to /uploads/...
    # should return 404 (route not found), not 200.
    resp = client.get("/uploads/some-file.jpg")
    assert resp.status_code == 404, (
        f"Expected 404 for removed /uploads static route, got {resp.status_code}"
    )


def test_unauthenticated_cannot_access_evidence_file_endpoint(client, citizen_headers):
    """SEC-06: Unauthenticated requests to /api/evidence/files/<name> must be rejected (401)."""
    report = client.post("/api/reports/", json={
        "title": "Auth File Test Report",
        "category": "Lost Property",
        "description": "Testing authenticated evidence file access.",
    }, headers=citizen_headers).json()

    files = {"file": ("evidence.png", b"\x89PNG\r\n\x1a\nfakepngbytes", "image/png")}
    upload_resp = client.post(
        f"/api/evidence/upload/report/{report['id']}", files=files, headers=citizen_headers
    )
    assert upload_resp.status_code == 200, upload_resp.text
    file_path = upload_resp.json()["file_path"]
    filename = file_path.replace("\\", "/").split("/")[-1]

    # Try to access the file WITHOUT a token.
    unauth_resp = client.get(f"/api/evidence/files/{filename}")
    assert unauth_resp.status_code == 401, (
        f"Expected 401 for unauthenticated evidence file access, got {unauth_resp.status_code}"
    )


def test_authenticated_user_can_access_evidence_file(client, citizen_headers):
    """SEC-06: Authenticated user can retrieve an evidence file they uploaded."""
    report = client.post("/api/reports/", json={
        "title": "Citizen Auth Download Report",
        "category": "Theft",
        "description": "Testing that authenticated user can download evidence.",
    }, headers=citizen_headers).json()

    files = {"file": ("photo.png", b"\x89PNG\r\n\x1a\nfakepngbytes", "image/png")}
    upload_resp = client.post(
        f"/api/evidence/upload/report/{report['id']}", files=files, headers=citizen_headers
    )
    assert upload_resp.status_code == 200, upload_resp.text
    file_path = upload_resp.json()["file_path"]
    filename = file_path.replace("\\", "/").split("/")[-1]

    auth_resp = client.get(f"/api/evidence/files/{filename}", headers=citizen_headers)
    assert auth_resp.status_code == 200, (
        f"Expected 200 for authenticated evidence file access, got {auth_resp.status_code}"
    )
