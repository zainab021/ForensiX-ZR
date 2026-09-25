from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, Literal
from datetime import datetime

class UserCreate(BaseModel):
    full_name: str = Field(..., max_length=120)
    username: str  = Field(..., max_length=80)
    email: Optional[EmailStr] = None
    password: str  = Field(..., max_length=128)
    role: Literal["citizen", "officer", "admin"] = "citizen"
    officer_code: Optional[str] = Field(None, max_length=80)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        # SEC-07: Minimum raised from 6 to 8 per NIST SP 800-63B.
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name", "username")
    @classmethod
    def no_empty(cls, v):
        if not v.strip():
            raise ValueError("This field cannot be blank")
        return v.strip()

class UserOut(BaseModel):
    id: int
    full_name: str
    username: str
    email: Optional[str]
    role: str
    officer_code: Optional[str]
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str
    officer_code: Optional[str] = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ReportCreate(BaseModel):
    title: str       = Field(..., max_length=160)
    category: str    = Field(..., max_length=80)
    description: str = Field(..., max_length=5000)
    location: Optional[str] = Field(None, max_length=180)
    reporter_name: Optional[str] = Field(None, max_length=120)
    priority: Literal["normal", "high", "urgent"] = "normal"

class ReportUpdate(BaseModel):
    status: Optional[Literal["pending", "verified", "resolved", "rejected", "converted"]] = None
    priority: Optional[Literal["normal", "high", "urgent"]] = None

class ReportOut(BaseModel):
    id: int
    title: str
    category: str
    description: str
    location: Optional[str]
    reporter_name: Optional[str]
    status: str
    priority: str
    created_by: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True

class CaseCreate(BaseModel):
    case_no: str     = Field(..., max_length=80)
    title: str       = Field(..., max_length=160)
    crime_type: str  = Field(..., max_length=90)
    location: Optional[str] = Field(None, max_length=180)
    description: Optional[str] = Field(None, max_length=5000)
    assigned_officer_id: Optional[int] = None

class CaseUpdate(BaseModel):
    status: Optional[Literal["open", "in_progress", "closed"]] = None
    assigned_officer_id: Optional[int] = None

class CaseOut(BaseModel):
    id: int
    case_no: str
    title: str
    crime_type: str
    location: Optional[str]
    description: Optional[str]
    status: str
    assigned_officer_id: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True

class EvidenceCreate(BaseModel):
    case_id: Optional[int] = None
    report_id: Optional[int] = None
    title: str
    evidence_type: str
    description: Optional[str] = None
    collected_by: Optional[str] = None
    file_path: Optional[str] = None
    status: str = "stored"

class EvidenceOut(BaseModel):
    id: int
    case_id: Optional[int]
    report_id: Optional[int]
    title: str
    evidence_type: str
    description: Optional[str]
    collected_by: Optional[str]
    file_path: Optional[str]
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    title: str
    message: str
    target_role: Literal["all", "citizen", "officer", "admin"] = "all"

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    target_role: str
    created_at: datetime
    class Config:
        from_attributes = True

class CaseDeleteRequest(BaseModel):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class RoleUpdate(BaseModel):
    role: Literal["citizen", "officer", "admin"]

class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., max_length=80)

class ResetPasswordRequest(BaseModel):
    username: str = Field(..., max_length=80)
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        # SEC-07: Minimum raised from 6 to 8 per NIST SP 800-63B.
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class AIClassifyRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000)

class AIClassifyOut(BaseModel):
    category: str
    priority: str
    confidence: float

class AIAssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

class AIAssistantOut(BaseModel):
    reply: str
