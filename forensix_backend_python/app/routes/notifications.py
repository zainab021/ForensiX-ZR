from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import Notification, User
from app.schemas.schemas import NotificationCreate, NotificationOut
from app.utils.dependencies import get_current_user, require_roles
from app.utils.logger import log_action

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.post("/", response_model=NotificationOut)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    note = Notification(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    log_action(db, current_user.id, "CREATE_NOTIFICATION", note.title)
    return note

@router.get("/", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ("admin", "officer"):
        return db.query(Notification).order_by(Notification.created_at.desc()).all()
    return db.query(Notification).filter(
        (Notification.target_role == "all") | (Notification.target_role == current_user.role)
    ).order_by(Notification.created_at.desc()).all()

@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    note = db.query(Notification).filter(Notification.id == notification_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(note)
    db.commit()
    log_action(db, current_user.id, "DELETE_NOTIFICATION", f"Notification #{notification_id}")
    return {"message": "Notification deleted"}
