from fastapi import WebSocket


class ConnectionManager:
    """Tracks active notification WebSocket connections by user ID and role,
    so broadcasts can be targeted (role-wide today, per-user reserved for
    future use) instead of blasted to every open socket regardless of who
    is authorized to see the notification."""

    def __init__(self):
        self._connections: dict[WebSocket, tuple[int, str]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, role: str):
        await websocket.accept()
        self._connections[websocket] = (user_id, role)

    def disconnect(self, websocket: WebSocket):
        self._connections.pop(websocket, None)

    async def broadcast(self, target_role: str, payload: dict):
        dead = []
        for websocket, (_user_id, role) in self._connections.items():
            if target_role != "all" and role != target_role:
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(websocket)

    async def send_to_user(self, user_id: int, payload: dict):
        dead = []
        for websocket, (uid, _role) in self._connections.items():
            if uid != user_id:
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(websocket)


manager = ConnectionManager()
