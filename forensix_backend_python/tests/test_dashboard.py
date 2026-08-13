def test_dashboard_stats_requires_officer_or_admin(client, citizen_headers):
    resp = client.get("/api/dashboard/stats", headers=citizen_headers)
    assert resp.status_code == 403


def test_dashboard_stats_shape_for_officer(client, officer_headers, citizen_headers):
    client.post("/api/reports/", json={
        "title": "Dashboard Test Report",
        "category": "Theft",
        "description": "Used to populate dashboard counts.",
    }, headers=citizen_headers)

    resp = client.get("/api/dashboard/stats", headers=officer_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in ["users", "citizens", "officers", "reports", "pending_reports", "cases", "open_cases", "evidence"]:
        assert key in body
        assert isinstance(body[key], int)


def test_dashboard_trends_returns_seven_days(client, officer_headers):
    resp = client.get("/api/dashboard/trends", headers=officer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 7
    assert all("day" in item and "count" in item for item in body)


def test_dashboard_activity_requires_auth(client):
    resp = client.get("/api/dashboard/activity")
    assert resp.status_code == 401
