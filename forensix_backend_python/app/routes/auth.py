from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database.db import get_db
from app.models.models import PasswordReset, User
from app.schemas.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenOut,
    UserCreate,
    UserOut,
)
from app.utils.email import send_otp_email
from app.utils.security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from app.utils.dependencies import get_current_user, require_roles
from app.utils.logger import log_action

router = APIRouter(prefix="/api/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)

import os as _os
import logging as _logging

# SEC-02 / PHASE-4: VALID_OFFICER_CODES must be explicitly set.
# The application will NOT start if this variable is absent, preventing
# production deployments from silently accepting known development codes.
_VALID_CODES_RAW = _os.getenv("VALID_OFFICER_CODES")
if _VALID_CODES_RAW is None:
    raise RuntimeError(
        "[ForensiX] VALID_OFFICER_CODES environment variable is not set. "
        "Set it to a comma-separated list of valid officer/admin registration codes "
        "(e.g. VALID_OFFICER_CODES=ORG-ADMIN-001,ORG-OFC-101) in your .env file. "
        "The application will not start without this value to prevent accidental "
        "production deployments accepting known development codes."
    )
_VALID_CODES = set(c.strip() for c in _VALID_CODES_RAW.split(",") if c.strip())
if not _VALID_CODES:
    raise RuntimeError(
        "[ForensiX] VALID_OFFICER_CODES is set but contains no valid codes. "
        "Provide at least one code, e.g. VALID_OFFICER_CODES=ORG-ADMIN-001"
    )

@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register_user(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    if payload.role in ["admin", "officer"] and not payload.officer_code:
        raise HTTPException(status_code=400, detail="Officer/admin code is required")
    if payload.role in ["admin", "officer"] and payload.officer_code not in _VALID_CODES:
        raise HTTPException(status_code=400, detail="Invalid officer/admin code. Contact your administrator.")
    if payload.officer_code:
        code_taken = db.query(User).filter(User.officer_code == payload.officer_code).first()
        if code_taken:
            raise HTTPException(status_code=400, detail="This officer/admin code is already registered to another account.")
    user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        officer_code=payload.officer_code,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username, email, or officer code is already in use.")
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

_GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "If this username exists and has an email on file, a reset code has been sent."
)
OTP_EXPIRE_MINUTES = 10


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user and user.email:
        db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id, PasswordReset.used == False  # noqa: E712
        ).update({"used": True})
        otp = generate_otp()
        db.add(PasswordReset(
            user_id=user.id,
            otp_hash=hash_otp(otp),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        ))
        db.commit()
        send_otp_email(user.email, otp)
        log_action(db, user.id, "FORGOT_PASSWORD", f"{payload.username} requested a reset code")
    # Always return the same message whether or not the user/email exists,
    # so this endpoint can't be used to enumerate valid usernames.
    return {"message": _GENERIC_FORGOT_PASSWORD_MESSAGE}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or reset code")

    reset = (
        db.query(PasswordReset)
        .filter(PasswordReset.user_id == user.id, PasswordReset.used == False)  # noqa: E712
        .order_by(PasswordReset.created_at.desc())
        .first()
    )
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid username or reset code")

    now = datetime.now(timezone.utc)
    expires_at = reset.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        # SQLite doesn't reliably round-trip tzinfo on DateTime(timezone=True)
        # columns; the value we stored was always UTC, so treat it as such.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not verify_otp(payload.otp, reset.otp_hash) or expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid username or reset code")

    reset.used = True
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    log_action(db, user.id, "RESET_PASSWORD", f"{payload.username} reset their password via OTP")
    return {"message": "Password reset successfully. You can now log in."}
