from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import ActivityLog

def log_action(db: Session, user_id: Optional[int], action: str, details: Optional[str] = None):
    log = ActivityLog(user_id=user_id, action=action, details=details)
    db.add(log)
    db.commit()
