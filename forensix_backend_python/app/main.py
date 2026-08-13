from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database.db import Base, engine, SessionLocal
from app.models.models import User
from app.utils.security import hash_password
from app.routes import auth, users, reports, cases, evidence, notifications, dashboard
import os

limiter = Limiter(key_func=get_remote_address)

Base.metadata.create_all(bind=engine)

def _seed():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(full_name="System Admin", username="admin", email="admin@forensix.local",
                        password_hash=hash_password("admin123"), role="admin",
                        officer_code="ZR-ADMIN-001", status="active"))
        if not db.query(User).filter(User.username == "officer").first():
            db.add(User(full_name="Demo Officer", username="officer", email="officer@forensix.local",
                        password_hash=hash_password("officer123"), role="officer",
                        officer_code="ZR-OFC-101", status="active"))
        if not db.query(User).filter(User.username == "citizen").first():
            db.add(User(full_name="Demo Citizen", username="citizen", email="citizen@forensix.local",
                        password_hash=hash_password("citizen123"), role="citizen",
                        officer_code=None, status="active"))
        db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed()
    yield

app = FastAPI(
    title="ForensiX ZR Unit API",
    description="Python FastAPI backend for Secure Crime Analysis System",
    version="1.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://zainab:5500",
        "http://zainab:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(reports.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def home():
    return {"message": "ForensiX ZR Unit Python Backend Running"}

