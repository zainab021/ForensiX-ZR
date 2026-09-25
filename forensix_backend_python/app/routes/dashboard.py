from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.database.db import get_db
from app.models.models import User, Report, Case, Evidence, ActivityLog
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return {
        "users": db.query(User).count(),
        "citizens": db.query(User).filter(User.role == "citizen").count(),
        "officers": db.query(User).filter(User.role == "officer").count(),
        "reports": db.query(Report).count(),
        "pending_reports": db.query(Report).filter(Report.status == "pending").count(),
        "cases": db.query(Case).count(),
        "open_cases": db.query(Case).filter(Case.status == "open").count(),
        "evidence": db.query(Evidence).count(),
    }

@router.get("/activity")
def recent_activity(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50).all()
    user_ids = {l.user_id for l in logs if l.user_id}
    users = {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "username": users.get(l.user_id, "System"),
            "action": l.action,
            "details": l.details,
            "created_at": l.created_at
        }
        for l in logs
    ]

@router.get("/trends")
def report_trends(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    now = datetime.now(timezone.utc)
    result = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timedelta(days=1)
        count = db.query(Report).filter(
            Report.created_at >= day_start,
            Report.created_at < day_end
        ).count()
        result.append({"day": day_start.strftime("%a"), "count": count})
    return result
