from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.db import Base

def _now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="citizen")  # admin/officer/citizen
    officer_code = Column(String(80), unique=True, nullable=True)
    status = Column(String(30), default="active")
    created_at = Column(DateTime(timezone=True), default=_now)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(180), nullable=True)
    status = Column(String(40), default="pending")
    priority = Column(String(40), default="normal")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    case_no = Column(String(80), unique=True, index=True, nullable=False)
    title = Column(String(160), nullable=False)
    crime_type = Column(String(90), nullable=False)
    location = Column(String(180), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(40), default="open")
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    title = Column(String(160), nullable=False)
    evidence_type = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    collected_by = Column(String(120), nullable=True)
    file_path = Column(String(300), nullable=True)
    status = Column(String(40), default="stored")
    created_at = Column(DateTime(timezone=True), default=_now)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    target_role = Column(String(40), default="all")
    created_at = Column(DateTime(timezone=True), default=_now)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(180), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
