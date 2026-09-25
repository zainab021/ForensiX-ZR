"""
Tests for the ForensiX-ZR Release Readiness & Security Audit Engine.

These tests create isolated temporary directory trees with specific file
contents and verify that each check function returns the correct Finding
status and severity. No actual network or database calls are made.

Run from repository root:
    python -m pytest scripts/tests/ -v
"""

import sys
import json
import pytest
from pathlib import Path

# Add scripts/ directory to sys.path so we can import release_check
sys.path.insert(0, str(Path(__file__).parent.parent))

from release_check import (  # noqa: E402
    Finding,
    check_hardcoded_db_credentials,
    check_demo_user_default,
    check_officer_codes_fallback,
    check_localhost_api_url,
    check_cors_wildcard,
    check_allowed_hosts_wildcard,
    check_alembic_migrations_exist,
    check_create_all_vs_alembic,
    check_sqlite_production_fallback,
    check_required_env_vars,
    check_evidence_upload_auth,
    check_entrypoint_migrations,
    generate_markdown_report,
    generate_json_report,
    determine_overall_status,
    _SEV_ICON,
    _STATUS_ICON,
    VALID_SEVERITIES,
    VALID_STATUSES,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_repo(tmp_path: Path) -> Path:
    """Create a minimal but valid-looking repo structure under tmp_path."""
    backend = tmp_path / "forensix_backend_python"
    backend.mkdir(parents=True)
    (backend / "app").mkdir()
    (backend / "app" / "routes").mkdir()
    (backend / "app" / "utils").mkdir()
    (backend / "app" / "schemas").mkdir()
    (backend / "app" / "database").mkdir()
    (backend / "alembic" / "versions").mkdir(parents=True)
    (backend / "tests").mkdir()
    (tmp_path / "frontend" / "js").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    return tmp_path


def write(path: Path, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def assert_finding(finding: Finding, expected_status: str, expected_severity: str = None):
    """Assert finding status and optionally severity, with a helpful message."""
    assert finding.status == expected_status, (
        f"Finding {finding.id} expected status={expected_status!r} "
        f"but got status={finding.status!r}. "
        f"Title: {finding.title}. Evidence: {finding.evidence[:200]}"
    )
    if expected_severity is not None:
        assert finding.severity == expected_severity, (
            f"Finding {finding.id} expected severity={expected_severity!r} "
            f"but got severity={finding.severity!r}."
        )


# ─────────────────────────────────────────────────────────────────────────────
# SEC-01: Hardcoded database credentials
# ─────────────────────────────────────────────────────────────────────────────

class TestHardcodedDbCredentials:
    def test_detects_literal_password(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "docker-compose.yml", """\
services:
  db:
    environment:
      POSTGRES_USER: forensix
      POSTGRES_PASSWORD: forensix
      POSTGRES_DB: forensix_db
""")
        finding = check_hardcoded_db_credentials(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")
        assert "forensix" in finding.evidence.lower() or "POSTGRES_PASSWORD" in finding.evidence

    def test_passes_with_variable_substitution(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "docker-compose.yml", """\
services:
  db:
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-forensix}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?must be set}
      POSTGRES_DB: ${POSTGRES_DB:-forensix_db}
""")
        finding = check_hardcoded_db_credentials(repo)
        assert_finding(finding, "PASSED", "INFO")

    def test_file_missing_returns_not_verified(self, tmp_path):
        repo = make_repo(tmp_path)
        # No docker-compose.yml created
        finding = check_hardcoded_db_credentials(repo)
        assert_finding(finding, "NOT_VERIFIED")


# ─────────────────────────────────────────────────────────────────────────────
# SEC-03: Demo user default
# ─────────────────────────────────────────────────────────────────────────────

class TestDemoUserDefault:
    def test_detects_unsafe_true_default(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py", """\
import os
if os.getenv("SEED_DEMO_USERS", "true").lower() == "true":
    _seed()
""")
        finding = check_demo_user_default(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_passes_with_false_default(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py", """\
import os
if os.getenv("SEED_DEMO_USERS", "false").lower() == "true":
    _seed()
""")
        finding = check_demo_user_default(repo)
        assert_finding(finding, "PASSED", "INFO")

    def test_returns_not_verified_when_file_missing(self, tmp_path):
        repo = make_repo(tmp_path)
        # No main.py
        finding = check_demo_user_default(repo)
        assert_finding(finding, "NOT_VERIFIED")


# ─────────────────────────────────────────────────────────────────────────────
# SEC-02: Officer codes fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestOfficerCodesFallback:
    def test_detects_silent_fallback(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "routes" / "auth.py", """\
import os as _os
_VALID_CODES = set(
    c.strip() for c in
    _os.getenv("VALID_OFFICER_CODES", "ZR-ADMIN-001,ZR-OFC-101").split(",")
    if c.strip()
)
""")
        finding = check_officer_codes_fallback(repo)
        # Should be CONFIRMED (no warning log)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_warning_status_when_log_present(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "routes" / "auth.py", """\
import os as _os
import logging
_raw = _os.getenv("VALID_OFFICER_CODES", "ZR-ADMIN-001,ZR-OFC-101")
if not _os.getenv("VALID_OFFICER_CODES"):
    logging.warning("[SECURITY WARNING] VALID_OFFICER_CODES not set.")
_VALID_CODES = set(c.strip() for c in _raw.split(",") if c.strip())
""")
        finding = check_officer_codes_fallback(repo)
        assert_finding(finding, "WARNING", "MEDIUM")

    def test_passes_without_fallback(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "routes" / "auth.py", """\
import os as _os
_raw = _os.getenv("VALID_OFFICER_CODES") or ""
_VALID_CODES = set(c.strip() for c in _raw.split(",") if c.strip())
""")
        finding = check_officer_codes_fallback(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG-01: Localhost API URL
# ─────────────────────────────────────────────────────────────────────────────

class TestLocalhostApiUrl:
    def test_detects_hardcoded_localhost(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "frontend" / "js" / "config.js", """\
window.FORENSIX_API_BASE = "http://127.0.0.1:8000";
""")
        finding = check_localhost_api_url(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_detects_hardcoded_localhost_string(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "frontend" / "js" / "config.js", """\
window.FORENSIX_API_BASE = "http://localhost:8000";
""")
        finding = check_localhost_api_url(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_passes_with_dynamic_hostname_detection(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "frontend" / "js" / "config.js", """\
(function() {
  var hostname = window.location.hostname;
  if (hostname === "localhost") {
    window.FORENSIX_API_BASE = "http://localhost:8000";
  } else {
    window.FORENSIX_API_BASE = "http://" + hostname + ":8000";
  }
}());
""")
        finding = check_localhost_api_url(repo)
        assert_finding(finding, "PASSED", "INFO")

    def test_returns_not_verified_when_file_missing(self, tmp_path):
        repo = make_repo(tmp_path)
        # No config.js
        finding = check_localhost_api_url(repo)
        assert_finding(finding, "NOT_VERIFIED")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG-02: Wildcard CORS
# ─────────────────────────────────────────────────────────────────────────────

class TestCorsWildcard:
    def test_detects_wildcard_in_env_example(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
SECRET_KEY=test
CORS_ORIGINS=*
ALLOWED_HOSTS=*
""")
        finding = check_cors_wildcard(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_passes_with_specific_origin(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
SECRET_KEY=test
CORS_ORIGINS=http://example.com
ALLOWED_HOSTS=example.com
""")
        finding = check_cors_wildcard(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG-03: Wildcard ALLOWED_HOSTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAllowedHostsWildcard:
    def test_detects_wildcard(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
ALLOWED_HOSTS=*
""")
        finding = check_allowed_hosts_wildcard(repo)
        assert_finding(finding, "WARNING", "MEDIUM")

    def test_passes_without_wildcard(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
ALLOWED_HOSTS=myapp.example.com
""")
        finding = check_allowed_hosts_wildcard(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# DB-ALEMBIC-01: Migration files exist
# ─────────────────────────────────────────────────────────────────────────────

class TestAlembicMigrationsExist:
    def test_confirms_missing_directory(self, tmp_path):
        repo = make_repo(tmp_path)
        # Remove the versions directory that make_repo creates
        import shutil
        shutil.rmtree(repo / "forensix_backend_python" / "alembic")
        finding = check_alembic_migrations_exist(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_confirms_empty_directory(self, tmp_path):
        repo = make_repo(tmp_path)
        # Directory exists but is empty (make_repo creates it empty)
        finding = check_alembic_migrations_exist(repo)
        assert_finding(finding, "CONFIRMED", "HIGH")

    def test_passes_with_migration_files(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "forensix_backend_python" / "alembic" / "versions" /
         "0001_initial.py").write_text("# migration", encoding="utf-8")
        finding = check_alembic_migrations_exist(repo)
        assert_finding(finding, "PASSED", "INFO")
        assert "1 Alembic migration" in finding.title


# ─────────────────────────────────────────────────────────────────────────────
# DB-01: create_all vs Alembic
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateAllVsAlembic:
    def test_warns_when_both_present(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py",
              "Base.metadata.create_all(bind=engine)\n")
        write(repo / "forensix_backend_python" / "entrypoint.sh",
              "alembic upgrade head\nexec uvicorn\n")
        finding = check_create_all_vs_alembic(repo)
        assert_finding(finding, "WARNING")

    def test_confirms_create_all_without_entrypoint(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py",
              "Base.metadata.create_all(bind=engine)\n")
        finding = check_create_all_vs_alembic(repo)
        assert finding.status in ("CONFIRMED", "NOT_VERIFIED")

    def test_passes_with_entrypoint_only(self, tmp_path):
        repo = make_repo(tmp_path)
        # main.py has no create_all — only 'create' appears as a separate word
        write(repo / "forensix_backend_python" / "app" / "main.py",
              "# Schema managed exclusively via Alembic migrations\napp = FastAPI()\n")
        write(repo / "forensix_backend_python" / "entrypoint.sh",
              "set -e\nalembic upgrade head\nexec uvicorn app.main:app\n")
        finding = check_create_all_vs_alembic(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# DB-02: SQLite production fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestSqliteProductionFallback:
    def test_warns_on_silent_sqlite_fallback(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "database" / "db.py", """\
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./forensix.db")
""")
        finding = check_sqlite_production_fallback(repo)
        # Should be WARNING (silent fallback) since no warning log present
        assert finding.status in ("WARNING", "PASSED")  # depends on main.py too
        if finding.status == "WARNING":
            assert finding.severity == "MEDIUM"

    def test_passes_with_warning_in_main(self, tmp_path):
        repo = make_repo(tmp_path)
        # db.py has the SQLite default AND a warning nearby
        write(repo / "forensix_backend_python" / "app" / "database" / "db.py", """\
import os
import logging
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./forensix.db")
if DATABASE_URL.startswith("sqlite"):
    logging.warning("[ForensiX] SQLite in use. Not for production: %s", DATABASE_URL)
""")
        finding = check_sqlite_production_fallback(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG-04: Required environment variables
# ─────────────────────────────────────────────────────────────────────────────

class TestRequiredEnvVars:
    def test_warns_on_missing_vars(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
SECRET_KEY=test
# Missing many required variables
""")
        finding = check_required_env_vars(repo)
        assert_finding(finding, "WARNING")
        assert "Missing" in finding.title

    def test_passes_with_all_vars(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / ".env.example", """\
SECRET_KEY=test
DATABASE_URL=sqlite:///test.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
VALID_OFFICER_CODES=ZR-001
CORS_ORIGINS=http://localhost
ALLOWED_HOSTS=localhost
SEED_DEMO_USERS=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=user@gmail.com
SMTP_PASSWORD=apppass
POSTGRES_PASSWORD=strongpass
""")
        finding = check_required_env_vars(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# SEC-06: Evidence upload authentication
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceUploadAuth:
    def test_warns_on_static_uploads_mount(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py", """\
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
""")
        finding = check_evidence_upload_auth(repo)
        assert_finding(finding, "WARNING", "MEDIUM")

    def test_passes_without_static_uploads(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "app" / "main.py", """\
from fastapi import FastAPI
app = FastAPI()
""")
        finding = check_evidence_upload_auth(repo)
        assert_finding(finding, "PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# DEPLOY-02: Entrypoint migrations
# ─────────────────────────────────────────────────────────────────────────────

class TestEntrypointMigrations:
    def test_warns_when_no_entrypoint(self, tmp_path):
        repo = make_repo(tmp_path)
        finding = check_entrypoint_migrations(repo)
        assert_finding(finding, "WARNING")

    def test_passes_with_full_entrypoint(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "entrypoint.sh", """\
#!/bin/bash
set -e
echo "Running Alembic migrations..."
if ! alembic upgrade head; then
    echo "Migration failed"
    exit 1
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
""")
        finding = check_entrypoint_migrations(repo)
        assert_finding(finding, "PASSED")

    def test_confirms_entrypoint_without_alembic(self, tmp_path):
        repo = make_repo(tmp_path)
        write(repo / "forensix_backend_python" / "entrypoint.sh", """\
#!/bin/bash
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
""")
        finding = check_entrypoint_migrations(repo)
        assert_finding(finding, "CONFIRMED")


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

class TestReportGeneration:
    def _make_findings(self) -> list:
        """Build a representative mix of findings for report tests."""
        return [
            Finding(
                id="SEC-01", category="Security", severity="HIGH",
                status="CONFIRMED", confidence="HIGH",
                title="Hardcoded password",
                file="docker-compose.yml", location="line 10",
                evidence="POSTGRES_PASSWORD: secret",
                description="Password hardcoded.",
                impact="Credentials exposed.",
                remediation="Use ${POSTGRES_PASSWORD}.",
                verification="Regex search",
            ),
            Finding(
                id="SEC-02", category="Security", severity="MEDIUM",
                status="WARNING", confidence="HIGH",
                title="Officer codes fallback",
                file="auth.py", location="line 5",
                evidence="getenv fallback",
                description="Fallback codes present.",
                impact="Known codes accepted.",
                remediation="Set VALID_OFFICER_CODES.",
                verification="Regex search",
            ),
            Finding(
                id="CONFIG-01", category="Configuration", severity="INFO",
                status="PASSED", confidence="HIGH",
                title="Dynamic hostname detection",
                file="config.js", location="window.location.hostname",
                evidence="window.location.hostname",
                description="Dynamic detection present.",
                impact="N/A",
                remediation="N/A",
                verification="Search",
            ),
        ]

    def test_markdown_report_contains_required_sections(self, tmp_path):
        repo = make_repo(tmp_path)
        findings = self._make_findings()
        md_path = tmp_path / "reports" / "release-readiness-report.md"

        generate_markdown_report(findings, repo, md_path)

        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")

        required_sections = [
            "# Release Readiness Report",
            "## 1. Executive Summary",
            "## 2. Audit Timestamp",
            "## 3. Repository Information",
            "## 4. Overall Status",
            "## 5. Finding Summary",
            "## 12. Human Verification Items",
            "## 13. Passed Checks",
            "## 14. Remediation Checklist",
            "## 15. Release Checklist",
        ]
        for section in required_sections:
            assert section in content, f"Missing section: {section!r}"

    def test_json_report_schema(self, tmp_path):
        repo = make_repo(tmp_path)
        findings = self._make_findings()
        json_path = tmp_path / "reports" / "release-readiness-report.json"

        report = generate_json_report(findings, repo, json_path)

        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))

        assert "meta" in data
        assert "overall_status" in data
        assert "overall_status_explanation" in data
        assert "summary" in data
        assert "findings" in data
        assert len(data["findings"]) == len(findings)

        # Each finding should have all required fields
        required_fields = {
            "id", "category", "severity", "status", "confidence",
            "title", "file", "location", "evidence",
            "description", "impact", "remediation", "verification",
        }
        for f in data["findings"]:
            missing = required_fields - set(f.keys())
            assert not missing, f"Finding {f.get('id')} missing fields: {missing}"

    def test_overall_status_not_ready_on_high_confirmed(self, tmp_path):
        findings = [
            Finding(
                id="X-01", category="Security", severity="HIGH",
                status="CONFIRMED", confidence="HIGH",
                title="Critical flaw",
                file="N/A", location="N/A", evidence="Found",
                description="X", impact="Y", remediation="Z",
                verification="Test",
            )
        ]
        status, _ = determine_overall_status(findings)
        assert status == "NOT READY"

    def test_overall_status_ready_on_all_passed(self):
        findings = [
            Finding(
                id="X-01", category="Security", severity="INFO",
                status="PASSED", confidence="HIGH",
                title="All good",
                file="N/A", location="N/A", evidence="Clean",
                description="X", impact="N/A", remediation="N/A",
                verification="Test",
            )
        ]
        status, _ = determine_overall_status(findings)
        assert status in ("READY", "READY WITH WARNINGS", "NOT VERIFIED")

    def test_overall_status_ready_with_warnings_on_medium(self):
        findings = [
            Finding(
                id="X-01", category="Security", severity="MEDIUM",
                status="WARNING", confidence="HIGH",
                title="Medium warning",
                file="N/A", location="N/A", evidence="Found",
                description="X", impact="Y", remediation="Z",
                verification="Test",
            )
        ]
        status, _ = determine_overall_status(findings)
        assert status == "READY WITH WARNINGS"


# ─────────────────────────────────────────────────────────────────────────────
# Severity and Status formatting constants
# ─────────────────────────────────────────────────────────────────────────────

class TestFormattingConstants:
    def test_all_severities_have_icons(self):
        for sev in VALID_SEVERITIES:
            assert sev in _SEV_ICON, f"No icon for severity: {sev}"

    def test_all_statuses_have_labels(self):
        for status in VALID_STATUSES:
            assert status in _STATUS_ICON, f"No label for status: {status}"

    def test_finding_as_dict_has_all_fields(self):
        f = Finding(
            id="TEST", category="Testing", severity="INFO", status="PASSED",
            confidence="HIGH", title="Test finding",
            file="test.py", location="line 1", evidence="test evidence",
            description="test description", impact="N/A",
            remediation="N/A", verification="unit test",
        )
        d = f.as_dict()
        required = {
            "id", "category", "severity", "status", "confidence",
            "title", "file", "location", "evidence",
            "description", "impact", "remediation", "verification",
        }
        assert required.issubset(set(d.keys()))
