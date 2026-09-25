from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database.db import Base, engine, SessionLocal
from app.models.models import User
from app.utils.security import hash_password
from app.routes import auth, users, reports, cases, evidence, notifications, dashboard, ai, ws
from app.utils.dependencies import get_current_user
import os
import logging
import pathlib

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

# DB-01 / DB-02: Determine the database URL early so we can decide whether to
# use create_all() (dev/test convenience) or Alembic-only (production).
_db_url = os.getenv("DATABASE_URL", "sqlite:///./forensix.db")

if _db_url.startswith("sqlite"):
    # Dev / test mode: create_all() creates the schema so tests and local runs
    # work without running Alembic migrations manually.
    Base.metadata.create_all(bind=engine)
    logging.basicConfig(level=logging.WARNING)
    logging.warning(
        "[ForensiX] DATABASE_URL is using SQLite (%s). "
        "SQLite is suitable for local development only. "
        "Set DATABASE_URL to a PostgreSQL connection string for production.",
        _db_url,
    )
else:
    # Production mode: schema management is handled exclusively by Alembic
    # (run via entrypoint.sh before uvicorn starts).
    # create_all() is intentionally SKIPPED to avoid silently bypassing migrations.
    logger.info(
        "[ForensiX] PostgreSQL detected — skipping create_all(). "
        "Alembic is the authoritative schema migration mechanism."
    )

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
    # SEC-03: Default is "false" — demo seeding must be explicitly enabled.
    # Set SEED_DEMO_USERS=true only in local development/testing environments.
    if os.getenv("SEED_DEMO_USERS", "false").lower() == "true":
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

allowed_hosts = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

cors_origins = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500"
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(ai.router)
app.include_router(ws.router)

os.makedirs("uploads", exist_ok=True)
# SEC-06 fix: Evidence files are now served through the authenticated endpoint
# /api/evidence/files/<filename> which requires a valid JWT.
# The unauthenticated public static directory has been removed.

_UPLOADS_DIR = pathlib.Path("uploads").resolve()

@app.get("/api/evidence/files/{filename}")
def serve_evidence_file(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """
    SEC-06: Authenticated evidence file serving endpoint.
    The old unauthenticated static file mount has been removed.
    Requires a valid JWT; all roles may access files served here.
    File names are UUID-based (set at upload time) to prevent enumeration.
    """
    # Guard against path traversal: only allow a plain filename, no subdirs.
    safe_name = pathlib.Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid file path")
    file_path = _UPLOADS_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/")
def home():
    return {"message": "ForensiX ZR Unit Python Backend Running"}

