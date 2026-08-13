from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import shutil, os, uuid
from app.database.db import get_db
from app.models.models import Evidence, Case, User, Report
from app.schemas.schemas import EvidenceCreate, EvidenceOut
from app.utils.dependencies import require_roles, get_current_user
from app.utils.logger import log_action

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])

@router.post("/", response_model=EvidenceOut)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    if payload.case_id is not None:
        case = db.query(Case).filter(Case.id == payload.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
    evidence = Evidence(**payload.model_dump())
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    log_action(db, current_user.id, "CREATE_EVIDENCE", evidence.title)
    return evidence

@router.get("/", response_model=list[EvidenceOut])
def list_evidence(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return db.query(Evidence).order_by(Evidence.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/case/{case_id}", response_model=list[EvidenceOut])
def evidence_by_case(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return db.query(Evidence).filter(Evidence.case_id == case_id).all()

@router.get("/report/{report_id}", response_model=list[EvidenceOut])
def evidence_by_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "citizen" and report.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(Evidence).filter(Evidence.report_id == report_id).all()

class EvidencePatch(BaseModel):
    case_id: Optional[int] = None
    status: Optional[str] = None

@router.patch("/{evidence_id}", response_model=EvidenceOut)
def update_evidence(evidence_id: int, payload: EvidencePatch, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evidence, key, value)
    db.commit()
    db.refresh(evidence)
    log_action(db, current_user.id, "UPDATE_EVIDENCE", f"Evidence #{evidence_id}")
    return evidence

@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if evidence.file_path and os.path.exists(evidence.file_path):
        os.remove(evidence.file_path)
    db.delete(evidence)
    db.commit()
    log_action(db, current_user.id, "DELETE_EVIDENCE", f"Evidence #{evidence_id}")
    return {"message": "Evidence deleted"}

UPLOAD_DIR = "uploads"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/upload/report/{report_id}", response_model=EvidenceOut)
async def upload_report_evidence(
    report_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "citizen" and report.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed. Use jpg, png, or pdf.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = str(uuid.uuid4()) + ext
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(contents)
    evidence = Evidence(
        report_id=report_id,
        case_id=None,
        title=file.filename,
        evidence_type=file.content_type,
        file_path=file_path,
        collected_by=current_user.full_name,
        status="stored"
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    log_action(db, current_user.id, "UPLOAD_EVIDENCE", f"Report #{report_id}: {file.filename}")
    return evidence
