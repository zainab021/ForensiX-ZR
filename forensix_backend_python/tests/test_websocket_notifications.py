def _token_from_headers(headers):
    return headers["Authorization"].split(" ", 1)[1]


def test_officer_receives_sos_broadcast(client, officer_headers, citizen_headers):
    officer_token = _token_from_headers(officer_headers)

    with client.websocket_connect(f"/ws/notifications?token={officer_token}") as ws:
        resp = client.post("/api/reports/", json={
            "title": "Help needed",
            "category": "Emergency SOS",
            "description": "Someone is following me.",
            "priority": "urgent",
        }, headers=citizen_headers)
        assert resp.status_code == 200, resp.text

        message = ws.receive_json()
        assert "EMERGENCY SOS" in message["title"]
        assert message["target_role"] == "officer"


def test_admin_receives_manual_notification_broadcast(client, admin_headers):
    admin_token = _token_from_headers(admin_headers)

    with client.websocket_connect(f"/ws/notifications?token={admin_token}") as ws:
        resp = client.post("/api/notifications/", json={
            "title": "System Maintenance",
            "message": "Scheduled downtime tonight at 11 PM.",
            "target_role": "all",
        }, headers=admin_headers)
        assert resp.status_code == 200, resp.text

        message = ws.receive_json()
        assert message["title"] == "System Maintenance"


def test_citizen_cannot_connect_to_notifications_socket(client, citizen_headers):
    citizen_token = _token_from_headers(citizen_headers)
    try:
        with client.websocket_connect(f"/ws/notifications?token={citizen_token}"):
            assert False, "citizen should not be able to connect"
    except Exception:
        pass


def test_invalid_token_rejected(client):
    try:
        with client.websocket_connect("/ws/notifications?token=not-a-real-token"):
            assert False, "invalid token should not be able to connect"
    except Exception:
        pass
