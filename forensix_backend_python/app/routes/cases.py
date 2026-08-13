from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import Case, User, Evidence
from app.schemas.schemas import CaseCreate, CaseUpdate, CaseOut, CaseDeleteRequest
from app.utils.dependencies import require_roles
from app.utils.logger import log_action
from app.utils.security import verify_password
import os

router = APIRouter(prefix="/api/cases", tags=["Cases"])

@router.post("/", response_model=CaseOut)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    existing = db.query(Case).filter(Case.case_no == payload.case_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Case number already exists")
    case = Case(**payload.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    log_action(db, current_user.id, "CREATE_CASE", case.case_no)
    return case

@router.get("/", response_model=list[CaseOut])
def list_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return db.query(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    log_action(db, current_user.id, "UPDATE_CASE", case.case_no)
    return case

def _delete_case_with_cleanup(case_id: int, db: Session):
    evidence_list = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    for ev in evidence_list:
        if ev.file_path and os.path.exists(ev.file_path):
            try: os.remove(ev.file_path)
            except OSError: pass
        db.delete(ev)

@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _delete_case_with_cleanup(case_id, db)
    db.delete(case)
    db.commit()
    log_action(db, current_user.id, "DELETE_CASE", f"Case #{case_id}")
    return {"message": "Case deleted"}

@router.post("/{case_id}/delete")
def secure_delete_case(case_id: int, payload: CaseDeleteRequest,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(require_roles("admin", "officer"))):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case_no = case.case_no
    _delete_case_with_cleanup(case.id, db)
    db.delete(case)
    db.commit()
    log_action(db, current_user.id, "DELETE_CASE",
               f"{case_no} deleted by {current_user.role} ({current_user.username})")
    return {"message": "Case deleted", "case_no": case_no}
