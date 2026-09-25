from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import User
from app.utils.security import decode_token
from app.utils.ws_manager import manager

router = APIRouter(tags=["WebSocket"])

# Only officer/admin roles get the live notification badge/toast today.
_ALLOWED_ROLES = {"admin", "officer"}


@router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket, token: str = "", db: Session = Depends(get_db)):
    payload = decode_token(token) if token else None
    user = None
    if payload and "sub" in payload:
        user = db.query(User).filter(User.id == int(payload["sub"])).first()

    if not user or user.status != "active":
        await websocket.close(code=4401)
        return
    if user.role not in _ALLOWED_ROLES:
        await websocket.close(code=4403)
        return

    await manager.connect(websocket, user.id, user.role)
    try:
        while True:
            # Clients don't send anything meaningful; this just blocks until
            # the connection is closed so we can detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
