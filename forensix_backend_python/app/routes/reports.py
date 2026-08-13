from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database.db import get_db
from app.models.models import Report, User, Notification
from app.schemas.schemas import ReportCreate, ReportUpdate, ReportOut
from app.utils.dependencies import get_current_user, require_roles
from app.utils.logger import log_action

router = APIRouter(prefix="/api/reports", tags=["Reports"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=ReportOut)
@limiter.limit("10/minute")
def create_report(request: Request, payload: ReportCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = Report(**payload.model_dump(), created_by=current_user.id)
    db.add(report)
    db.commit()
    db.refresh(report)
    log_action(db, current_user.id, "CREATE_REPORT", report.title)
    if payload.category == "Emergency SOS" and payload.priority == "urgent":
        db.add(Notification(
            title=f"🚨 EMERGENCY SOS — Report #{report.id}",
            message=f"{current_user.full_name} (Citizen #{current_user.id}) sent an emergency SOS alert. Immediate response required.",
            target_role="officer"
        ))
        db.commit()
    return report

@router.get("/", response_model=list[ReportOut])
def list_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "citizen":
        return db.query(Report).filter(Report.created_by == current_user.id).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    return db.query(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "citizen" and report.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return report

@router.patch("/{report_id}", response_model=ReportOut)
def update_report(report_id: int, payload: ReportUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, key, value)
    db.commit()
    db.refresh(report)
    log_action(db, current_user.id, "UPDATE_REPORT", f"Report #{report.id}")
    return report

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "citizen":
        if report.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="You can only withdraw your own reports")
        if report.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending reports can be withdrawn")
    elif current_user.role not in ("admin", "officer"):
        raise HTTPException(status_code=403, detail="Permission denied")
    db.delete(report)
    db.commit()
    log_action(db, current_user.id, "DELETE_REPORT", f"Report #{report_id}")
    return {"message": "Report deleted"}
