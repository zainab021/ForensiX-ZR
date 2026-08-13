from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.schemas.schemas import UserOut, UserUpdate, PasswordChange, RoleUpdate
from app.utils.dependencies import require_roles, get_current_user
from app.utils.security import verify_password, hash_password
from app.utils.logger import log_action

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/officers", response_model=list[UserOut])
def list_officers(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return db.query(User).filter(User.role == "officer").all()

@router.patch("/me", response_model=UserOut)
def update_profile(payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.email is not None:
        existing = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = payload.email
    db.commit()
    db.refresh(current_user)
    log_action(db, current_user.id, "UPDATE_PROFILE", current_user.username)
    return current_user

@router.post("/me/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    log_action(db, current_user.id, "CHANGE_PASSWORD", current_user.username)
    return {"message": "Password changed successfully"}

@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(user_id: int, payload: RoleUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    if payload.role in ("admin", "officer") and not user.officer_code:
        prefix = "ADM" if payload.role == "admin" else "OFC"
        user.officer_code = f"ZR-{prefix}-{user_id:03d}"
    elif payload.role == "citizen":
        user.officer_code = None
    db.commit()
    db.refresh(user)
    log_action(db, current_user.id, "CHANGE_ROLE", f"{user.username} → {payload.role}")
    return user

@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(user_id: int, status: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    if status not in ("active", "inactive", "suspended"):
        raise HTTPException(status_code=400, detail="Invalid status value")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own account status.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = status
    db.commit()
    db.refresh(user)
    log_action(db, current_user.id, "UPDATE_USER_STATUS", f"{user.username} → {status}")
    return user
