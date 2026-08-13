from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database.db import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, LoginRequest, TokenOut, UserOut
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.dependencies import get_current_user, require_roles
from app.utils.logger import log_action

router = APIRouter(prefix="/api/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)

import os as _os
_VALID_CODES = set(c.strip() for c in _os.getenv("VALID_OFFICER_CODES", "ZR-ADMIN-001,ZR-OFC-101").split(",") if c.strip())

@router.post("/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    if payload.role in ["admin", "officer"] and not payload.officer_code:
        raise HTTPException(status_code=400, detail="Officer/admin code is required")
    if payload.role in ["admin", "officer"] and payload.officer_code not in _VALID_CODES:
        raise HTTPException(status_code=400, detail="Invalid officer/admin code. Contact your administrator.")
    user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        officer_code=payload.officer_code,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, user.id, "REGISTER_USER", f"New {user.role} registered")
    return user

@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username, User.role == payload.role).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username, password, or role")
    if user.role in ["admin", "officer"] and user.officer_code != payload.officer_code:
        raise HTTPException(status_code=401, detail="Invalid officer/admin code")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    log_action(db, user.id, "LOGIN", f"{user.role} logged in")
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password")
def forgot_password(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"message": "If this username exists, a reset request has been sent."}
    from app.models.models import Notification
    db.add(Notification(
        title=f"🔑 Password Reset Request",
        message=f"User '{username}' (ID #{user.id}) has requested a password reset. Please reset via Admin → Users → Profile.",
        target_role="admin"
    ))
    db.commit()
    log_action(db, user.id, "FORGOT_PASSWORD", f"{username} requested reset")
    return {"message": "Reset request sent to administrator. You will be contacted shortly."}
