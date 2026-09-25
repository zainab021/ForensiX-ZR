#!/usr/bin/env python3
"""
ForensiX-ZR Release Readiness & Security Audit Script
IBM Bob 2.0 Hackathon — Deterministic Evidence-Based Audit Engine

Inspects the repository using static analysis, file pattern matching, and
optional subprocess execution (pytest, pip-audit). Every finding is backed
by actual repository evidence. No CVEs are invented. No commands are claimed
to pass unless they are actually executed.

Usage:
    python scripts/release_check.py [options]

Options:
    --repo PATH         Path to repository root (default: parent of scripts/)
    --output-dir PATH   Directory to write reports (default: <repo>/reports/)
    --run-tests         Execute the pytest test suite and include results
    --run-pip-audit     Execute pip-audit and include dependency scan results
    --json              Write JSON report in addition to Markdown
"""

import os
import re
import sys
import json
import argparse
import datetime
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Finding data model
# ─────────────────────────────────────────────────────────────────────────────

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VALID_STATUSES = {
    "CONFIRMED", "WARNING", "RECOMMENDATION",
    "REQUIRES_HUMAN_VERIFICATION", "PASSED", "NOT_VERIFIED",
}


@dataclass
class Finding:
    id: str
    category: str       # Security | Configuration | Database | Deployment | Testing | Dependencies
    severity: str       # CRITICAL | HIGH | MEDIUM | LOW | INFO
    status: str         # CONFIRMED | WARNING | RECOMMENDATION | REQUIRES_HUMAN_VERIFICATION | PASSED | NOT_VERIFIED
    confidence: str     # HIGH | MEDIUM | LOW
    title: str
    file: str           # repo-relative path or "N/A"
    location: str       # line/pattern reference or "N/A"
    evidence: str       # exact text from file, or brief description of what was found
    description: str
    impact: str
    remediation: str
    verification: str   # how was this check performed

    def as_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _read(path: Path) -> Optional[str]:
    """Read file text; return None on any failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _find_line(content: str, pattern: str, regex: bool = False) -> Tuple[bool, str, int]:
    """
    Search content for pattern.
    Returns (found, matched_line_text, 1-indexed line number).
    """
    if regex:
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line):
                return True, line.strip(), i
    else:
        for i, line in enumerate(content.splitlines(), 1):
            if pattern in line:
                return True, line.strip(), i
    return False, "", 0


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 120) -> Tuple[int, str, str]:
    """
    Run a subprocess command.
    Returns (returncode, stdout, stderr).
    Special return codes:
        -1  command not found (FileNotFoundError)
        -2  timed out
        -3  other OS-level error
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Command timed out after {timeout}s"
    except Exception as exc:
        return -3, "", str(exc)


def _rel(path: Path, base: Path) -> str:
    """Return path relative to base, or str(path) if that fails."""
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ─────────────────────────────────────────────────────────────────────────────
# Security Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_env_not_committed(repo: Path) -> Finding:
    """Check that .env is not tracked by git and is in .gitignore."""
    fid = "SEC-ENV-01"
    env_file = repo / "forensix_backend_python" / ".env"
    gitignore = repo / ".gitignore"
    gi_content = _read(gitignore) or ""
    in_gitignore = ".env" in gi_content

    # Prefer git ls-files over guessing
    rc, stdout, _ = _run(
        ["git", "ls-files", "--error-unmatch",
         str(env_file.relative_to(repo))],
        cwd=repo,
    )
    if rc == 0:
        # exit 0 means git found the file — it IS committed
        return Finding(
            id=fid, category="Security", severity="CRITICAL", status="CONFIRMED",
            confidence="HIGH",
            title=".env file is committed to the repository",
            file="forensix_backend_python/.env",
            location="git index",
            evidence="git ls-files --error-unmatch returned 0 for .env",
            description=(
                "The .env file containing SECRET_KEY, SMTP credentials, and API keys "
                "is tracked by git and visible to all repository readers."
            ),
            impact="All secrets in .env are exposed to anyone with repository access.",
            remediation=(
                "Run: git rm --cached forensix_backend_python/.env\n"
                "Ensure forensix_backend_python/.env is in .gitignore."
            ),
            verification="git ls-files --error-unmatch forensix_backend_python/.env",
        )

    if rc == 1:
        # git exit 1 = file not tracked (good)
        evidence = (
            f".env in .gitignore: {in_gitignore}; "
            "git ls-files --error-unmatch confirmed file is not tracked"
        )
        status, severity = "PASSED", "INFO"
    elif rc == -1:
        # git not available, fall back to .gitignore check
        if in_gitignore:
            evidence = ".env found in .gitignore (git not available for tracking confirmation)"
            status, severity = "PASSED", "INFO"
        else:
            evidence = "git unavailable AND .env not found in .gitignore"
            status, severity = "REQUIRES_HUMAN_VERIFICATION", "HIGH"
    else:
        evidence = f"git returned unexpected code {rc}"
        status, severity = "NOT_VERIFIED", "MEDIUM"

    return Finding(
        id=fid, category="Security", severity=severity, status=status,
        confidence="HIGH" if rc in (1, -1) else "LOW",
        title=".env file is not committed to the repository",
        file=".gitignore",
        location="'.env' entry",
        evidence=evidence,
        description="Verifies that .env (containing application secrets) is excluded from git tracking.",
        impact="If .env were committed, all secrets would be exposed to repository readers.",
        remediation="Ensure .env is in .gitignore and not tracked by git.",
        verification="git ls-files --error-unmatch forensix_backend_python/.env",
    )


def check_hardcoded_db_credentials(repo: Path) -> Finding:
    """Check docker-compose.yml for hardcoded PostgreSQL passwords."""
    fid = "SEC-01"
    compose = repo / "docker-compose.yml"
    content = _read(compose)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="HIGH", status="NOT_VERIFIED",
            confidence="LOW", title="docker-compose.yml not found",
            file="docker-compose.yml", location="N/A", evidence="File not found",
            description="Could not locate docker-compose.yml to check for hardcoded credentials.",
            impact="Unknown",
            remediation="Ensure docker-compose.yml exists.",
            verification="File existence check",
        )

    # A hardcoded password has a literal value (not ${...} substitution)
    m = re.search(r"POSTGRES_PASSWORD:\s*(?!\$\{)([^\n\r]+)", content)
    if m:
        literal_value = m.group(1).strip()
        # Skip obvious placeholder/variable patterns
        if not re.match(r"^\$\{", literal_value) and literal_value not in ("", "~"):
            return Finding(
                id=fid, category="Security", severity="HIGH", status="CONFIRMED",
                confidence="HIGH",
                title="Hardcoded PostgreSQL password in docker-compose.yml",
                file="docker-compose.yml",
                location=f"POSTGRES_PASSWORD: {literal_value[:20]}...",
                evidence=m.group().strip(),
                description=(
                    "The PostgreSQL password is committed as a literal string in docker-compose.yml, "
                    "which is version-controlled."
                ),
                impact=(
                    "Anyone with repository access has the database password. "
                    "If the repo is made public, the password is immediately compromised."
                ),
                remediation=(
                    "Replace with ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in .env} "
                    "and set POSTGRES_PASSWORD in a root-level .env file (gitignored)."
                ),
                verification=(
                    "Regex search for 'POSTGRES_PASSWORD:' without ${} substitution "
                    "in docker-compose.yml"
                ),
            )

    return Finding(
        id=fid, category="Security", severity="INFO", status="PASSED",
        confidence="HIGH",
        title="PostgreSQL credentials use environment variable substitution in docker-compose.yml",
        file="docker-compose.yml", location="POSTGRES_PASSWORD field",
        evidence="No literal password found; ${} substitution pattern detected",
        description=(
            "docker-compose.yml uses ${POSTGRES_PASSWORD} substitution. "
            "The actual password must be supplied via a root-level .env file."
        ),
        impact="N/A",
        remediation="N/A",
        verification=(
            "Regex search for literal POSTGRES_PASSWORD value in docker-compose.yml"
        ),
    )


def check_demo_user_default(repo: Path) -> Finding:
    """Check that SEED_DEMO_USERS defaults to 'false'."""
    fid = "SEC-03"
    main_py = repo / "forensix_backend_python" / "app" / "main.py"
    content = _read(main_py)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="HIGH", status="NOT_VERIFIED",
            confidence="LOW", title="app/main.py not found",
            file="forensix_backend_python/app/main.py", location="N/A",
            evidence="File not found",
            description="Cannot verify SEED_DEMO_USERS default.",
            impact="Unknown",
            remediation="Locate app/main.py",
            verification="File existence check",
        )

    m_true = re.search(r'getenv\("SEED_DEMO_USERS",\s*"true"\)', content)
    m_false = re.search(r'getenv\("SEED_DEMO_USERS",\s*"false"\)', content)

    if m_true:
        return Finding(
            id=fid, category="Security", severity="HIGH", status="CONFIRMED",
            confidence="HIGH",
            title='SEED_DEMO_USERS defaults to "true" — demo accounts created automatically',
            file="forensix_backend_python/app/main.py",
            location='getenv("SEED_DEMO_USERS", "true")',
            evidence=m_true.group(),
            description=(
                'When SEED_DEMO_USERS is not explicitly set, demo accounts with known weak '
                'passwords (admin/admin123, officer/officer123, citizen/citizen123) are created '
                'on every startup.'
            ),
            impact=(
                "Production deployments without SEED_DEMO_USERS=false will have backdoor "
                "accounts with publicly-known credentials."
            ),
            remediation='Change default to "false": os.getenv("SEED_DEMO_USERS", "false")',
            verification='Regex search for getenv("SEED_DEMO_USERS", "true") in app/main.py',
        )

    if m_false:
        return Finding(
            id=fid, category="Security", severity="INFO", status="PASSED",
            confidence="HIGH",
            title='SEED_DEMO_USERS defaults to "false" — demo accounts not created automatically',
            file="forensix_backend_python/app/main.py",
            location='getenv("SEED_DEMO_USERS", "false")',
            evidence=m_false.group(),
            description=(
                'Demo user seeding is disabled by default. '
                'Must be explicitly enabled (SEED_DEMO_USERS=true) for development.'
            ),
            impact="N/A",
            remediation="N/A",
            verification='Regex search for getenv("SEED_DEMO_USERS", ...) in app/main.py',
        )

    return Finding(
        id=fid, category="Security", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="LOW", title="Could not determine SEED_DEMO_USERS default",
        file="forensix_backend_python/app/main.py",
        location="SEED_DEMO_USERS getenv call",
        evidence="Neither 'true' nor 'false' default pattern detected",
        description="Unable to determine the default value for SEED_DEMO_USERS.",
        impact="Unknown",
        remediation="Manually verify SEED_DEMO_USERS default in app/main.py",
        verification="Regex search for getenv(SEED_DEMO_USERS, ...) in app/main.py",
    )


def check_officer_codes_fallback(repo: Path) -> Finding:
    """Check whether VALID_OFFICER_CODES has a silent fallback in auth.py."""
    fid = "SEC-02"
    auth_py = repo / "forensix_backend_python" / "app" / "routes" / "auth.py"
    content = _read(auth_py)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="LOW", title="auth.py not found",
            file="forensix_backend_python/app/routes/auth.py", location="N/A",
            evidence="File not found",
            description="Cannot verify VALID_OFFICER_CODES fallback behavior.",
            impact="Unknown",
            remediation="Locate auth.py",
            verification="File existence check",
        )

    # Check for a fallback with a literal default
    m = re.search(r'getenv\("VALID_OFFICER_CODES",\s*"([^"]+)"\)', content)
    has_warning_log = "[SECURITY WARNING]" in content or "SECURITY WARNING" in content

    if m:
        fallback_codes = m.group(1)
        if has_warning_log:
            return Finding(
                id=fid, category="Security", severity="MEDIUM", status="WARNING",
                confidence="HIGH",
                title=(
                    "VALID_OFFICER_CODES falls back to known development codes, "
                    "but emits a startup warning"
                ),
                file="forensix_backend_python/app/routes/auth.py",
                location='getenv("VALID_OFFICER_CODES", "...")',
                evidence=m.group(),
                description=(
                    f"VALID_OFFICER_CODES falls back to '{fallback_codes}' if not explicitly set. "
                    "A [SECURITY WARNING] log is emitted at startup when this occurs."
                ),
                impact=(
                    "If VALID_OFFICER_CODES is not set in production, these codes remain valid "
                    "for officer/admin registration."
                ),
                remediation=(
                    "Explicitly set VALID_OFFICER_CODES in production .env with your "
                    "real internal codes."
                ),
                verification="Regex search for getenv('VALID_OFFICER_CODES', ...) in auth.py",
            )
        else:
            return Finding(
                id=fid, category="Security", severity="HIGH", status="CONFIRMED",
                confidence="HIGH",
                title="VALID_OFFICER_CODES falls back to known codes without any warning",
                file="forensix_backend_python/app/routes/auth.py",
                location='getenv("VALID_OFFICER_CODES", "...")',
                evidence=m.group(),
                description=(
                    f"VALID_OFFICER_CODES silently falls back to '{fallback_codes}' if not set. "
                    "No warning is logged."
                ),
                impact=(
                    "Production deployments without VALID_OFFICER_CODES set will silently "
                    "accept these known codes for officer/admin registration."
                ),
                remediation=(
                    "Add a startup warning log when the fallback is used. "
                    "Explicitly set VALID_OFFICER_CODES in production."
                ),
                verification="Regex search for getenv('VALID_OFFICER_CODES', ...) in auth.py",
            )

    # No fallback — check if it's read without default (better)
    if "VALID_OFFICER_CODES" in (content or ""):
        return Finding(
            id=fid, category="Security", severity="INFO", status="PASSED",
            confidence="MEDIUM",
            title="VALID_OFFICER_CODES read from environment without a hardcoded fallback",
            file="forensix_backend_python/app/routes/auth.py",
            location="VALID_OFFICER_CODES usage",
            evidence="No hardcoded fallback detected in getenv call",
            description=(
                "VALID_OFFICER_CODES is read from the environment. "
                "If not set, the application must handle the absence explicitly."
            ),
            impact="N/A",
            remediation="Ensure VALID_OFFICER_CODES is set in production .env.",
            verification="Regex search for getenv('VALID_OFFICER_CODES', ...) in auth.py",
        )

    return Finding(
        id=fid, category="Security", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="LOW",
        title="Could not determine VALID_OFFICER_CODES configuration",
        file="forensix_backend_python/app/routes/auth.py", location="N/A",
        evidence="Pattern not found",
        description="Unable to verify VALID_OFFICER_CODES fallback behavior.",
        impact="Unknown",
        remediation="Manually verify auth.py",
        verification="Regex search in auth.py",
    )


def check_auth_security_config(repo: Path) -> List[Finding]:
    """Check JWT algorithm, SECRET_KEY startup validation, bcrypt, timing-safe OTP."""
    findings = []
    security_py = repo / "forensix_backend_python" / "app" / "utils" / "security.py"
    content = _read(security_py)

    if content is None:
        findings.append(Finding(
            id="SEC-AUTH-01", category="Security", severity="HIGH", status="NOT_VERIFIED",
            confidence="LOW", title="security.py not found",
            file="forensix_backend_python/app/utils/security.py", location="N/A",
            evidence="File not found",
            description="Cannot verify authentication security configuration.",
            impact="Unknown",
            remediation="Locate security.py",
            verification="File existence check",
        ))
        return findings

    # JWT algorithm
    alg_m = re.search(r'ALGORITHM\s*=\s*"(\w+)"', content)
    if alg_m:
        findings.append(Finding(
            id="SEC-AUTH-01", category="Security", severity="INFO", status="PASSED",
            confidence="HIGH", title=f"JWT algorithm: {alg_m.group(1)}",
            file="forensix_backend_python/app/utils/security.py",
            location=f'ALGORITHM = "{alg_m.group(1)}"',
            evidence=alg_m.group(),
            description=f"JWT tokens use {alg_m.group(1)}.",
            impact="N/A",
            remediation="HS256 is acceptable; RS256/ES256 provides non-repudiation if required.",
            verification="Regex search for ALGORITHM = in security.py",
        ))

    # SECRET_KEY startup validation
    has_guard, guard_line, guard_lineno = _find_line(content, "raise RuntimeError")
    if has_guard and "SECRET_KEY" in content:
        findings.append(Finding(
            id="SEC-AUTH-02", category="Security", severity="INFO", status="PASSED",
            confidence="HIGH",
            title="SECRET_KEY validated at startup — server will not start without it",
            file="forensix_backend_python/app/utils/security.py",
            location=f"Line {guard_lineno}: {guard_line}",
            evidence=guard_line,
            description=(
                "The application raises RuntimeError if SECRET_KEY is not set, "
                "preventing accidental startup with no JWT signing key."
            ),
            impact="N/A",
            remediation="N/A",
            verification="Search for 'raise RuntimeError' near SECRET_KEY in security.py",
        ))
    elif "SECRET_KEY" in content:
        findings.append(Finding(
            id="SEC-AUTH-02", category="Security", severity="HIGH", status="CONFIRMED",
            confidence="MEDIUM",
            title="No startup guard for missing SECRET_KEY detected",
            file="forensix_backend_python/app/utils/security.py",
            location="SECRET_KEY assignment",
            evidence="SECRET_KEY present but 'raise RuntimeError' guard not found",
            description="Application may start with a missing or empty SECRET_KEY.",
            impact="JWT tokens could be signed with an empty key, making them trivially forgeable.",
            remediation=(
                "Add: if not SECRET_KEY: raise RuntimeError("
                "'SECRET_KEY environment variable is not set')"
            ),
            verification="Search for RuntimeError near SECRET_KEY in security.py",
        ))

    # bcrypt
    if "bcrypt" in content.lower():
        findings.append(Finding(
            id="SEC-AUTH-03", category="Security", severity="INFO", status="PASSED",
            confidence="HIGH", title="bcrypt used for password hashing",
            file="forensix_backend_python/app/utils/security.py",
            location="pwd_context definition",
            evidence="'bcrypt' referenced in security.py",
            description="Passwords are hashed with bcrypt, a suitable adaptive hash function.",
            impact="N/A",
            remediation="N/A",
            verification="String search for 'bcrypt' in security.py",
        ))

    # Timing-safe OTP comparison
    if "hmac.compare_digest" in content:
        findings.append(Finding(
            id="SEC-AUTH-04", category="Security", severity="INFO", status="PASSED",
            confidence="HIGH",
            title="OTP verification uses timing-safe comparison (hmac.compare_digest)",
            file="forensix_backend_python/app/utils/security.py",
            location="verify_otp function",
            evidence="hmac.compare_digest found",
            description="OTP verification is immune to timing-based side-channel attacks.",
            impact="N/A",
            remediation="N/A",
            verification="String search for 'hmac.compare_digest' in security.py",
        ))

    return findings


def check_evidence_upload_auth(repo: Path) -> Finding:
    """Check whether uploaded evidence is served without authentication."""
    fid = "SEC-06"
    main_py = repo / "forensix_backend_python" / "app" / "main.py"
    content = _read(main_py)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="LOW", title="app/main.py not found",
            file="forensix_backend_python/app/main.py", location="N/A",
            evidence="File not found",
            description="Cannot verify evidence file access controls.",
            impact="Unknown",
            remediation="Locate app/main.py",
            verification="File existence check",
        )

    # Check for authenticated evidence file endpoint (the remediated state)
    has_auth_endpoint = bool(
        re.search(r"/api/evidence/files", content)
    ) and bool(
        re.search(r"get_current_user|Depends.*auth|require_roles", content)
    )

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        # Skip comment lines — a comment mentioning StaticFiles is not an active mount.
        if stripped.startswith("#"):
            continue
        if "StaticFiles" in line and "uploads" in line:
            return Finding(
                id=fid, category="Security", severity="MEDIUM", status="WARNING",
                confidence="HIGH",
                title="Evidence files served as public static directory without authentication",
                file="forensix_backend_python/app/main.py",
                location=f"Line {lineno}: {stripped}",
                evidence=stripped,
                description=(
                    "The /uploads directory is mounted as a public static file server. "
                    "Any file at a known URL can be downloaded without authentication."
                ),
                impact=(
                    "Evidence files (crime photos, PDFs) are publicly accessible if "
                    "their UUID-based URL is known. UUID filenames reduce enumeration "
                    "risk but are not true access control."
                ),
                remediation=(
                    "Replace static mount with an authenticated file-serving endpoint "
                    "that verifies user role and ownership before streaming files."
                ),
                verification="Search for StaticFiles mount of /uploads in main.py",
            )


    if has_auth_endpoint:
        return Finding(
            id=fid, category="Security", severity="INFO", status="PASSED",
            confidence="HIGH",
            title="Evidence files served via authenticated endpoint — no public static mount",
            file="forensix_backend_python/app/main.py",
            location="/api/evidence/files/{filename} endpoint",
            evidence=(
                "StaticFiles mount for /uploads not found; "
                "/api/evidence/files endpoint with get_current_user dependency detected"
            ),
            description=(
                "Uploaded evidence is served through /api/evidence/files/<filename> "
                "which requires a valid JWT (get_current_user dependency). "
                "The /uploads directory is not publicly accessible."
            ),
            impact="N/A",
            remediation="N/A",
            verification="Search for /api/evidence/files and get_current_user in main.py",
        )

    return Finding(
        id=fid, category="Security", severity="INFO", status="PASSED",
        confidence="MEDIUM",
        title="No unauthenticated static evidence file mount detected",
        file="forensix_backend_python/app/main.py",
        location="StaticFiles usage", evidence="StaticFiles mount for /uploads not found",
        description="Uploads directory is not served as an unauthenticated public static mount.",
        impact="N/A",
        remediation="N/A",
        verification="Search for StaticFiles mount in main.py",
    )



def check_websocket_token_in_url(repo: Path) -> Finding:
    """Check whether JWT is passed as a WebSocket query parameter."""
    fid = "SEC-04"
    ws_py = repo / "forensix_backend_python" / "app" / "routes" / "ws.py"
    content = _read(ws_py)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="LOW", status="NOT_VERIFIED",
            confidence="LOW", title="ws.py not found",
            file="forensix_backend_python/app/routes/ws.py", location="N/A",
            evidence="File not found",
            description="Cannot verify WebSocket authentication method.",
            impact="Unknown",
            remediation="N/A",
            verification="File existence check",
        )

    found, line, lineno = _find_line(content, 'token: str = ""')
    if found:
        return Finding(
            id=fid, category="Security", severity="LOW", status="WARNING",
            confidence="HIGH",
            title="JWT passed as WebSocket query parameter — may appear in server logs",
            file="forensix_backend_python/app/routes/ws.py",
            location=f"Line {lineno}: {line}",
            evidence=line,
            description=(
                "The JWT is transmitted as ?token=<jwt> in the WebSocket URL. "
                "Query parameters may be captured in web server access logs, "
                "proxy logs, and browser history."
            ),
            impact="JWT token leakage through log files or browser history.",
            remediation=(
                "This is a known limitation of the browser WebSocket API (no custom headers). "
                "Consider short-lived WebSocket tokens, or sending credentials as the first "
                "message after connection."
            ),
            verification="Search for 'token: str' query parameter in ws.py",
        )

    return Finding(
        id=fid, category="Security", severity="INFO", status="PASSED",
        confidence="MEDIUM",
        title="WebSocket does not use a JWT query parameter",
        file="forensix_backend_python/app/routes/ws.py",
        location="N/A", evidence="'token: str' query parameter not detected",
        description="No JWT-in-URL pattern detected for WebSocket endpoint.",
        impact="N/A",
        remediation="N/A",
        verification="Search for 'token: str' in ws.py",
    )


def check_password_min_length(repo: Path) -> Finding:
    """Check the minimum password length enforced by schemas."""
    fid = "SEC-07"
    schemas_py = repo / "forensix_backend_python" / "app" / "schemas" / "schemas.py"
    content = _read(schemas_py)

    if content is None:
        return Finding(
            id=fid, category="Security", severity="LOW", status="NOT_VERIFIED",
            confidence="LOW", title="schemas.py not found",
            file="forensix_backend_python/app/schemas/schemas.py", location="N/A",
            evidence="File not found",
            description="Cannot verify password minimum length.",
            impact="Unknown",
            remediation="N/A",
            verification="File existence check",
        )

    m = re.search(r"len\(v\)\s*<\s*(\d+)", content)
    if m:
        min_len = int(m.group(1))
        if min_len < 8:
            return Finding(
                id=fid, category="Security", severity="LOW", status="RECOMMENDATION",
                confidence="HIGH",
                title=f"Password minimum length is {min_len} characters (NIST recommends 8+)",
                file="forensix_backend_python/app/schemas/schemas.py",
                location=f"Password validator: len(v) < {min_len}",
                evidence=m.group(),
                description=(
                    f"The minimum password length is {min_len} characters. "
                    "NIST SP 800-63B recommends 8+ for user-chosen passwords; "
                    "OWASP recommends 12+ for privileged accounts."
                ),
                impact="Short passwords are more vulnerable to brute-force attacks.",
                remediation=(
                    "Increase minimum to 8 characters for all users; "
                    "consider 12 for officer/admin accounts."
                ),
                verification="Regex search for password length validator in schemas.py",
            )
        return Finding(
            id=fid, category="Security", severity="INFO", status="PASSED",
            confidence="HIGH",
            title=f"Password minimum length is {min_len} characters",
            file="forensix_backend_python/app/schemas/schemas.py",
            location=f"len(v) < {min_len}", evidence=m.group(),
            description="Password minimum length meets recommended standards.",
            impact="N/A",
            remediation="N/A",
            verification="Regex search for password length validator in schemas.py",
        )

    return Finding(
        id=fid, category="Security", severity="LOW", status="NOT_VERIFIED",
        confidence="LOW", title="Could not determine password minimum length",
        file="forensix_backend_python/app/schemas/schemas.py",
        location="N/A", evidence="Password length validator not found",
        description="Unable to verify password strength requirements.",
        impact="Unknown",
        remediation="Manually verify password validation in schemas.py",
        verification="Regex search for length validator in schemas.py",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_localhost_api_url(repo: Path) -> Finding:
    """Check whether the frontend API URL is hardcoded to localhost."""
    fid = "CONFIG-01"
    config_js = repo / "frontend" / "js" / "config.js"
    content = _read(config_js)

    if content is None:
        return Finding(
            id=fid, category="Configuration", severity="HIGH", status="NOT_VERIFIED",
            confidence="LOW", title="frontend/js/config.js not found",
            file="frontend/js/config.js", location="N/A", evidence="File not found",
            description="Cannot verify frontend API URL configuration.",
            impact="Unknown",
            remediation="Ensure config.js exists.",
            verification="File existence check",
        )

    # Direct hardcoded assignment without dynamic detection
    direct_m = re.search(
        r'window\.FORENSIX_API_BASE\s*=\s*"http://(127\.0\.0\.1|localhost)',
        content,
    )
    has_dynamic = bool(re.search(r"window\.location\.hostname", content))

    if direct_m and not has_dynamic:
        return Finding(
            id=fid, category="Configuration", severity="HIGH", status="CONFIRMED",
            confidence="HIGH",
            title="Frontend API URL hardcoded to localhost — breaks all non-local deployments",
            file="frontend/js/config.js",
            location=f"Direct assignment: {direct_m.group()[:80]}",
            evidence=direct_m.group(),
            description=(
                "The frontend API base URL is hardcoded to localhost/127.0.0.1. "
                "Any deployment to a non-local host will silently fail to connect to the backend."
            ),
            impact=(
                "Application is non-functional in any non-local deployment "
                "(Docker, cloud, hackathon demo URL)."
            ),
            remediation=(
                "Use dynamic hostname detection or a configurable override mechanism. "
                "See CONFIG-01 fix in config.js."
            ),
            verification=(
                "Regex search for direct localhost assignment without "
                "window.location.hostname detection in config.js"
            ),
        )

    if has_dynamic:
        return Finding(
            id=fid, category="Configuration", severity="INFO", status="PASSED",
            confidence="HIGH",
            title="Frontend API URL uses dynamic hostname detection",
            file="frontend/js/config.js",
            location="window.location.hostname conditional",
            evidence="window.location.hostname detected in config.js",
            description=(
                "config.js detects the runtime hostname and sets the API base URL accordingly. "
                "Local development works automatically; production deployments use the correct host."
            ),
            impact="N/A",
            remediation="N/A",
            verification="Search for window.location.hostname in config.js",
        )

    return Finding(
        id=fid, category="Configuration", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="LOW", title="Cannot determine API URL configuration method",
        file="frontend/js/config.js", location="N/A",
        evidence=content[:200] if content else "Empty file",
        description="Unable to determine how the frontend API URL is configured.",
        impact="May be non-functional in production.",
        remediation="Verify config.js manually.",
        verification="Manual inspection of config.js",
    )


def check_cors_wildcard(repo: Path) -> Finding:
    """Check for wildcard CORS origin in .env.example or main.py defaults."""
    fid = "CONFIG-02"
    env_example = repo / "forensix_backend_python" / ".env.example"
    main_py = repo / "forensix_backend_python" / "app" / "main.py"
    env_content = _read(env_example) or ""
    main_content = _read(main_py) or ""

    if "CORS_ORIGINS=*" in env_content:
        return Finding(
            id=fid, category="Configuration", severity="HIGH", status="CONFIRMED",
            confidence="HIGH",
            title="CORS_ORIGINS=* in .env.example — wildcard allows any origin",
            file="forensix_backend_python/.env.example",
            location="CORS_ORIGINS= line",
            evidence="CORS_ORIGINS=*",
            description="A wildcard CORS origin permits any domain to make cross-origin requests.",
            impact="Cross-origin attacks from any malicious website become possible.",
            remediation="Set CORS_ORIGINS to specific allowed origins: http://yourdomain.com",
            verification="String search for CORS_ORIGINS=* in .env.example",
        )

    m = re.search(r'CORS_ORIGINS["\']?,\s*"([^"]*\*[^"]*)"', main_content)
    if m:
        return Finding(
            id=fid, category="Configuration", severity="HIGH", status="CONFIRMED",
            confidence="HIGH", title="CORS_ORIGINS default contains wildcard in main.py",
            file="forensix_backend_python/app/main.py",
            location=m.group()[:80],
            evidence=m.group(),
            description="The default CORS_ORIGINS in main.py includes a wildcard.",
            impact="Any origin can make cross-origin requests.",
            remediation="Set specific allowed origins in .env",
            verification="Regex search for CORS wildcard in main.py",
        )

    cors_line = next(
        (l.strip() for l in env_content.splitlines() if "CORS_ORIGINS" in l), "Not found"
    )
    return Finding(
        id=fid, category="Configuration", severity="INFO", status="PASSED",
        confidence="MEDIUM",
        title="CORS_ORIGINS does not use a wildcard in .env.example",
        file="forensix_backend_python/.env.example",
        location="CORS_ORIGINS= line",
        evidence=cors_line,
        description="CORS is configured with specific origins, not a wildcard.",
        impact="N/A",
        remediation="Ensure production .env has real domain origins, not localhost.",
        verification="String search for CORS_ORIGINS=* in .env.example and main.py",
    )


def check_allowed_hosts_wildcard(repo: Path) -> Finding:
    """Check for ALLOWED_HOSTS=* in .env.example."""
    fid = "CONFIG-03"
    env_example = repo / "forensix_backend_python" / ".env.example"
    content = _read(env_example) or ""

    found, line, lineno = _find_line(content, "ALLOWED_HOSTS=*")
    if found:
        return Finding(
            id=fid, category="Configuration", severity="MEDIUM", status="WARNING",
            confidence="HIGH",
            title=(
                "ALLOWED_HOSTS=* in .env.example — acceptable for dev, "
                "must be restricted in production"
            ),
            file="forensix_backend_python/.env.example",
            location=f"Line {lineno}: {line}",
            evidence=line,
            description=(
                "The example config sets ALLOWED_HOSTS=* which allows any Host header. "
                "This is acceptable for local development but must be restricted in production."
            ),
            impact="Host header injection attacks possible in production if not overridden.",
            remediation="Set ALLOWED_HOSTS to your actual domain(s) in production .env.",
            verification="String search for ALLOWED_HOSTS=* in .env.example",
        )

    ah_line = next(
        (l.strip() for l in content.splitlines() if "ALLOWED_HOSTS" in l), "Not found"
    )
    return Finding(
        id=fid, category="Configuration", severity="INFO", status="PASSED",
        confidence="MEDIUM",
        title="ALLOWED_HOSTS does not use wildcard in .env.example",
        file="forensix_backend_python/.env.example",
        location="ALLOWED_HOSTS= line",
        evidence=ah_line,
        description="ALLOWED_HOSTS is configured without a wildcard.",
        impact="N/A",
        remediation="N/A",
        verification="String search for ALLOWED_HOSTS=* in .env.example",
    )


def check_required_env_vars(repo: Path) -> Finding:
    """Verify all required production variables are documented in .env.example."""
    fid = "CONFIG-04"
    env_example = repo / "forensix_backend_python" / ".env.example"
    content = _read(env_example) or ""

    required = [
        "SECRET_KEY", "DATABASE_URL", "ACCESS_TOKEN_EXPIRE_MINUTES",
        "VALID_OFFICER_CODES", "CORS_ORIGINS", "ALLOWED_HOSTS",
        "SEED_DEMO_USERS", "SMTP_HOST", "SMTP_PORT", "SMTP_USER",
        "SMTP_PASSWORD", "POSTGRES_PASSWORD",
    ]
    missing = [v for v in required if v not in content]

    if missing:
        return Finding(
            id=fid, category="Configuration", severity="MEDIUM", status="WARNING",
            confidence="HIGH",
            title=f"Missing required variables in .env.example: {', '.join(missing)}",
            file="forensix_backend_python/.env.example",
            location="Variable definitions",
            evidence=f"Missing: {', '.join(missing)}",
            description=".env.example is missing some required production environment variables.",
            impact="Developers may miss required configuration during deployment.",
            remediation=(
                f"Add {', '.join(missing)} to .env.example with descriptive placeholder values."
            ),
            verification="String search for each required variable name in .env.example",
        )

    return Finding(
        id=fid, category="Configuration", severity="INFO", status="PASSED",
        confidence="HIGH",
        title="All required environment variables are documented in .env.example",
        file="forensix_backend_python/.env.example",
        location="Variable definitions",
        evidence=f"Found all {len(required)} required variables",
        description=".env.example documents all required production environment variables.",
        impact="N/A",
        remediation="N/A",
        verification="String search for each required variable name in .env.example",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Database Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_sqlite_production_fallback(repo: Path) -> Finding:
    """Check whether DATABASE_URL silently falls back to SQLite."""
    fid = "DB-02"
    db_py = repo / "forensix_backend_python" / "app" / "database" / "db.py"
    content = _read(db_py)

    if content is None:
        return Finding(
            id=fid, category="Database", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="LOW", title="database/db.py not found",
            file="forensix_backend_python/app/database/db.py", location="N/A",
            evidence="File not found",
            description="Cannot verify DATABASE_URL fallback.",
            impact="Unknown",
            remediation="N/A",
            verification="File existence check",
        )

    m = re.search(r'getenv\("DATABASE_URL",\s*"(sqlite[^"]+)"\)', content)
    if m:
        sqlite_url = m.group(1)
        # Check whether a warning is emitted when SQLite is used.
        # The warning may be in db.py itself or in main.py (startup code).
        main_py = repo / "forensix_backend_python" / "app" / "main.py"
        main_content = _read(main_py) or ""
        combined = content + "\n" + main_content
        has_warning = bool(
            re.search(r"warn.*sqlite|sqlite.*warn", combined, re.IGNORECASE)
        ) or ("logging.warning" in combined and "sqlite" in combined.lower())

        if has_warning:
            return Finding(
                id=fid, category="Database", severity="INFO", status="PASSED",
                confidence="MEDIUM",
                title="SQLite fallback present with startup warning logged",
                file="forensix_backend_python/app/database/db.py",
                location=f"getenv('DATABASE_URL', '{sqlite_url}')",
                evidence=m.group(),
                description=(
                    "DATABASE_URL falls back to SQLite for local development. "
                    "A warning is logged at startup when SQLite is detected."
                ),
                impact="N/A (warning is present)",
                remediation="N/A",
                verification="Regex search for DATABASE_URL default and warning in db.py/main.py",
            )

        return Finding(
            id=fid, category="Database", severity="MEDIUM", status="WARNING",
            confidence="HIGH",
            title=f"DATABASE_URL silently falls back to SQLite: {sqlite_url}",
            file="forensix_backend_python/app/database/db.py",
            location=f"getenv('DATABASE_URL', '{sqlite_url}')",
            evidence=m.group(),
            description=(
                "If DATABASE_URL is not set, the application silently uses SQLite "
                "with no warning to operators."
            ),
            impact=(
                "Production deployments with a missing DATABASE_URL will use SQLite, "
                "which serializes writes and is unsuitable for concurrent production workloads."
            ),
            remediation=(
                "Add a startup warning log when SQLite is detected, "
                "or make DATABASE_URL a required variable."
            ),
            verification="Regex search for DATABASE_URL SQLite default in db.py",
        )


    # Also check main.py for the warning (it may be there instead)
    main_py = repo / "forensix_backend_python" / "app" / "main.py"
    main_content = _read(main_py) or ""
    if "sqlite" in main_content.lower() and (
        "warn" in main_content.lower() or "WARNING" in main_content
    ):
        return Finding(
            id=fid, category="Database", severity="INFO", status="PASSED",
            confidence="MEDIUM",
            title="SQLite startup warning found in main.py",
            file="forensix_backend_python/app/main.py",
            location="SQLite detection + warning block",
            evidence="SQLite + warning pattern found in main.py",
            description=(
                "A startup warning is emitted when SQLite is the active database."
            ),
            impact="N/A",
            remediation="N/A",
            verification="String search for sqlite + warn in main.py",
        )

    return Finding(
        id=fid, category="Database", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="LOW", title="Cannot determine DATABASE_URL fallback configuration",
        file="forensix_backend_python/app/database/db.py",
        location="N/A", evidence="DATABASE_URL getenv pattern not found",
        description="Unable to verify database fallback behavior.",
        impact="Unknown",
        remediation="Manually verify db.py",
        verification="Regex search in db.py",
    )


def check_alembic_migrations_exist(repo: Path) -> Finding:
    """Check that Alembic migration version files exist."""
    fid = "DB-ALEMBIC-01"
    versions_dir = repo / "forensix_backend_python" / "alembic" / "versions"

    if not versions_dir.exists():
        return Finding(
            id=fid, category="Database", severity="HIGH", status="CONFIRMED",
            confidence="HIGH", title="Alembic versions directory not found",
            file="forensix_backend_python/alembic/versions/",
            location="N/A", evidence="Directory does not exist",
            description="No Alembic migration version directory found.",
            impact=(
                "No migration history exists. "
                "Database schema changes cannot be applied incrementally."
            ),
            remediation=(
                "Initialize Alembic: alembic init alembic && "
                "alembic revision --autogenerate -m 'initial'"
            ),
            verification="Path existence check for alembic/versions/",
        )

    migrations = sorted(versions_dir.glob("*.py"))
    if not migrations:
        return Finding(
            id=fid, category="Database", severity="HIGH", status="CONFIRMED",
            confidence="HIGH", title="No Alembic migration files found",
            file="forensix_backend_python/alembic/versions/",
            location="N/A", evidence="Directory is empty (no *.py files)",
            description="Alembic versions directory exists but contains no migration files.",
            impact="Database schema cannot be managed incrementally.",
            remediation=(
                "Create initial migration: "
                "alembic revision --autogenerate -m 'initial'"
            ),
            verification="Glob for *.py in alembic/versions/",
        )

    return Finding(
        id=fid, category="Database", severity="INFO", status="PASSED",
        confidence="HIGH",
        title=f"{len(migrations)} Alembic migration file(s) found",
        file="forensix_backend_python/alembic/versions/",
        location="alembic/versions/*.py",
        evidence=", ".join(m.name for m in migrations),
        description=f"Alembic migration history exists with {len(migrations)} file(s).",
        impact="N/A",
        remediation="N/A",
        verification="Glob for *.py in alembic/versions/",
    )


def check_create_all_vs_alembic(repo: Path) -> Finding:
    """Check for create_all/Alembic dual-strategy schema management conflict."""
    fid = "DB-01"
    main_py = repo / "forensix_backend_python" / "app" / "main.py"
    entrypoint = repo / "forensix_backend_python" / "entrypoint.sh"

    main_content = _read(main_py) or ""
    entrypoint_content = _read(entrypoint) or ""

    has_create_all, ca_line, ca_lineno = _find_line(main_content, "create_all")
    entrypoint_runs_alembic = "alembic upgrade head" in entrypoint_content

    # Detect the guarded pattern: create_all() only called when the database URL
    # starts with "sqlite" (i.e. local dev/test mode only).
    # This is the correct production-safe pattern — Alembic is authoritative for PostgreSQL.
    is_guarded = bool(
        re.search(
            r"if\s+[_\w]*(?:db_url|database_url|DATABASE_URL)[^\n]*startswith\(['\"]sqlite['\"]",
            main_content,
            re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"startswith\(['\"]sqlite['\"]\)[^\n]*\n(?:[^\n]*\n){0,3}[^\n]*create_all",
            main_content,
        )
    )

    if has_create_all and entrypoint_runs_alembic and is_guarded:
        return Finding(
            id=fid, category="Database", severity="INFO", status="PASSED",
            confidence="HIGH",
            title=(
                "create_all() guarded to SQLite/dev mode; "
                "Alembic is authoritative for production (PostgreSQL)"
            ),
            file="forensix_backend_python/app/main.py",
            location=f"Line {ca_lineno}: {ca_line}",
            evidence=(
                f"create_all() guarded by 'if sqlite' check in main.py (line {ca_lineno}); "
                "alembic upgrade head in entrypoint.sh"
            ),
            description=(
                "create_all() is only called when DATABASE_URL points to SQLite (local dev/test). "
                "For PostgreSQL (production), create_all() is skipped and Alembic handles all "
                "schema management via entrypoint.sh. This is the recommended pattern."
            ),
            impact="N/A",
            remediation="N/A",
            verification=(
                "Regex search for sqlite-guarded create_all in main.py + "
                "alembic upgrade head in entrypoint.sh"
            ),
        )

    if has_create_all and entrypoint_runs_alembic:
        return Finding(
            id=fid, category="Database", severity="MEDIUM", status="WARNING",
            confidence="HIGH",
            title=(
                "Both create_all() and Alembic (entrypoint) present — "
                "potential schema management conflict"
            ),
            file="forensix_backend_python/app/main.py",
            location=f"Line {ca_lineno}: {ca_line}",
            evidence=(
                f"create_all() in main.py (line {ca_lineno}) + "
                "alembic upgrade head in entrypoint.sh"
            ),
            description=(
                "create_all() creates tables from models but does not apply migrations. "
                "alembic upgrade head applies incremental migrations. "
                "For fresh deployments both are equivalent, but for upgrades create_all() "
                "will not add new columns to existing tables while Alembic will."
            ),
            impact=(
                "Schema upgrades on existing databases may be incomplete "
                "if relying on create_all() instead of Alembic."
            ),
            remediation=(
                "Remove create_all() from main.py and rely exclusively on "
                "'alembic upgrade head' via entrypoint.sh for all schema management."
            ),
            verification=(
                "String search for create_all in main.py + "
                "alembic upgrade head in entrypoint.sh"
            ),
        )


    if has_create_all and not entrypoint_runs_alembic:
        return Finding(
            id=fid, category="Database", severity="MEDIUM", status="CONFIRMED",
            confidence="HIGH",
            title="create_all() used without Alembic migration execution in entrypoint",
            file="forensix_backend_python/app/main.py",
            location=f"Line {ca_lineno}: {ca_line}",
            evidence=ca_line,
            description=(
                "create_all() creates tables from models but does not apply Alembic migrations. "
                "Existing database upgrades will not receive new columns/tables from migrations."
            ),
            impact=(
                "Schema migrations are bypassed in production, potentially leaving "
                "the database in an incorrect state after updates."
            ),
            remediation=(
                "Create entrypoint.sh that runs 'alembic upgrade head' before starting uvicorn. "
                "Remove or conditionally guard create_all()."
            ),
            verification=(
                "String search for create_all in main.py + "
                "alembic upgrade head in entrypoint.sh"
            ),
        )

    if not has_create_all and entrypoint_runs_alembic:
        return Finding(
            id=fid, category="Database", severity="INFO", status="PASSED",
            confidence="HIGH",
            title=(
                "Schema managed via Alembic exclusively — "
                "alembic upgrade head runs in entrypoint.sh"
            ),
            file="forensix_backend_python/entrypoint.sh",
            location="alembic upgrade head",
            evidence=(
                "alembic upgrade head in entrypoint.sh; "
                "create_all() not detected in main.py"
            ),
            description=(
                "Database schema is managed through Alembic migrations only. "
                "This is the recommended approach for production."
            ),
            impact="N/A",
            remediation="N/A",
            verification=(
                "String search for create_all in main.py + "
                "alembic in entrypoint.sh"
            ),
        )

    return Finding(
        id=fid, category="Database", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="LOW", title="Schema management strategy is unclear",
        file="forensix_backend_python/app/main.py",
        location="N/A",
        evidence=(
            f"create_all detected: {has_create_all}, "
            f"alembic in entrypoint: {entrypoint_runs_alembic}"
        ),
        description="Could not determine the schema management strategy.",
        impact="Unknown",
        remediation="Verify how database schema is initialized and updated.",
        verification="Manual inspection of main.py and entrypoint scripts",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Deployment Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_docker_configuration(repo: Path) -> List[Finding]:
    """Check for Dockerfile and docker-compose.yml existence."""
    findings = []
    dockerfile = repo / "forensix_backend_python" / "Dockerfile"
    compose = repo / "docker-compose.yml"

    if dockerfile.exists():
        content = _read(dockerfile) or ""
        base_m = re.search(r"FROM\s+(\S+)", content)
        base = base_m.group(1) if base_m else "unknown"
        findings.append(Finding(
            id="DEPLOY-DOCKERFILE", category="Deployment", severity="INFO", status="PASSED",
            confidence="HIGH", title=f"Dockerfile exists (base image: {base})",
            file="forensix_backend_python/Dockerfile",
            location=f"FROM {base}", evidence=f"FROM {base}",
            description=f"Backend Dockerfile present, using {base} as base image.",
            impact="N/A",
            remediation="N/A",
            verification="File existence + FROM line inspection",
        ))
    else:
        findings.append(Finding(
            id="DEPLOY-DOCKERFILE", category="Deployment", severity="HIGH", status="CONFIRMED",
            confidence="HIGH", title="Dockerfile not found",
            file="forensix_backend_python/Dockerfile",
            location="N/A", evidence="File not found",
            description="No Dockerfile found for backend containerization.",
            impact="Cannot build a Docker container for the backend.",
            remediation="Create a Dockerfile.",
            verification="File existence check",
        ))

    if compose.exists():
        findings.append(Finding(
            id="DEPLOY-COMPOSE", category="Deployment", severity="INFO", status="PASSED",
            confidence="HIGH", title="docker-compose.yml exists",
            file="docker-compose.yml",
            location="N/A", evidence="File found",
            description="Docker Compose configuration present for full-stack deployment.",
            impact="N/A",
            remediation="N/A",
            verification="File existence check",
        ))
    else:
        findings.append(Finding(
            id="DEPLOY-COMPOSE", category="Deployment", severity="MEDIUM", status="WARNING",
            confidence="HIGH", title="docker-compose.yml not found",
            file="docker-compose.yml",
            location="N/A", evidence="File not found",
            description="No Docker Compose file found.",
            impact="No documented multi-service deployment configuration.",
            remediation="Create docker-compose.yml.",
            verification="File existence check",
        ))

    return findings


def check_entrypoint_migrations(repo: Path) -> Finding:
    """Check that entrypoint.sh runs alembic upgrade head before the app."""
    fid = "DEPLOY-02"
    entrypoint = repo / "forensix_backend_python" / "entrypoint.sh"
    content = _read(entrypoint)

    if content is None:
        return Finding(
            id=fid, category="Deployment", severity="MEDIUM", status="WARNING",
            confidence="HIGH",
            title=(
                "entrypoint.sh not found — "
                "Alembic migrations not run automatically on container start"
            ),
            file="forensix_backend_python/entrypoint.sh",
            location="N/A", evidence="File not found",
            description=(
                "No entrypoint script found that runs 'alembic upgrade head' "
                "before starting the application."
            ),
            impact=(
                "Database migrations must be run manually. "
                "Fresh or upgraded deployments may start with outdated schema."
            ),
            remediation=(
                "Create entrypoint.sh that runs 'alembic upgrade head' "
                "then 'exec uvicorn app.main:app ...'"
            ),
            verification="File existence check for entrypoint.sh",
        )

    has_alembic = "alembic upgrade head" in content
    has_uvicorn = "uvicorn" in content
    has_set_e = "set -e" in content
    has_exit1 = "exit 1" in content

    if has_alembic and has_uvicorn and (has_set_e or has_exit1):
        return Finding(
            id=fid, category="Deployment", severity="INFO", status="PASSED",
            confidence="HIGH",
            title=(
                "entrypoint.sh runs Alembic migrations before app start "
                "with fail-safe error handling"
            ),
            file="forensix_backend_python/entrypoint.sh",
            location="alembic upgrade head + set -e/exit 1",
            evidence=(
                f"alembic upgrade head: {has_alembic}, "
                f"set -e: {has_set_e}, exit 1: {has_exit1}, "
                f"uvicorn: {has_uvicorn}"
            ),
            description=(
                "The Docker entrypoint runs Alembic migrations before starting the "
                "application, and exits with an error if migrations fail."
            ),
            impact="N/A",
            remediation="N/A",
            verification="String search for alembic, set -e/exit 1, uvicorn in entrypoint.sh",
        )

    if has_alembic:
        return Finding(
            id=fid, category="Deployment", severity="LOW", status="WARNING",
            confidence="MEDIUM",
            title="entrypoint.sh runs Alembic but error handling may be incomplete",
            file="forensix_backend_python/entrypoint.sh",
            location="alembic upgrade head",
            evidence=(
                f"set -e: {has_set_e}, exit 1: {has_exit1}"
            ),
            description=(
                "Alembic migrations are run in entrypoint.sh but "
                "'set -e' or explicit 'exit 1' on failure not confirmed."
            ),
            impact="Migration failure may not prevent the application from starting.",
            remediation="Add 'set -e' at the top of entrypoint.sh to fail fast on any error.",
            verification="String search in entrypoint.sh",
        )

    return Finding(
        id=fid, category="Deployment", severity="MEDIUM", status="CONFIRMED",
        confidence="HIGH",
        title="entrypoint.sh exists but does not run Alembic migrations",
        file="forensix_backend_python/entrypoint.sh",
        location="N/A", evidence="'alembic upgrade head' not found in entrypoint.sh",
        description="entrypoint.sh exists but does not run Alembic migrations.",
        impact="Database schema migrations are not applied on container start.",
        remediation=(
            "Add 'alembic upgrade head' to entrypoint.sh before starting uvicorn."
        ),
        verification="String search for 'alembic upgrade head' in entrypoint.sh",
    )


def check_ci_cd_presence(repo: Path) -> Finding:
    """Check for any CI/CD pipeline configuration."""
    fid = "DEPLOY-CI"
    github_workflows = repo / ".github" / "workflows"
    ci_candidates = [
        repo / ".gitlab-ci.yml",
        repo / "Jenkinsfile",
        repo / ".circleci",
        repo / "azure-pipelines.yml",
        repo / ".travis.yml",
    ]

    if github_workflows.exists():
        wfs = list(github_workflows.glob("*.yml")) + list(github_workflows.glob("*.yaml"))
        if wfs:
            return Finding(
                id=fid, category="Deployment", severity="INFO", status="PASSED",
                confidence="HIGH",
                title=f"GitHub Actions CI found ({len(wfs)} workflow file(s))",
                file=".github/workflows/",
                location="N/A", evidence=", ".join(w.name for w in wfs),
                description="GitHub Actions CI/CD workflow(s) are present.",
                impact="N/A",
                remediation="N/A",
                verification="Directory listing of .github/workflows/",
            )

    for ci_file in ci_candidates:
        if ci_file.exists():
            return Finding(
                id=fid, category="Deployment", severity="INFO", status="PASSED",
                confidence="HIGH",
                title=f"CI/CD configuration found: {ci_file.name}",
                file=_rel(ci_file, repo),
                location="N/A", evidence=f"File found: {ci_file.name}",
                description="CI/CD configuration is present.",
                impact="N/A",
                remediation="N/A",
                verification="File existence check",
            )

    return Finding(
        id=fid, category="Deployment", severity="HIGH", status="CONFIRMED",
        confidence="HIGH",
        title="No CI/CD pipeline configuration found",
        file="N/A",
        location="N/A",
        evidence=(
            "Checked: .github/workflows/, .gitlab-ci.yml, "
            "Jenkinsfile, .circleci, azure-pipelines.yml, .travis.yml"
        ),
        description=(
            "No automated CI/CD pipeline is configured. "
            "Tests must be run manually before deployment."
        ),
        impact=(
            "No automated gate prevents broken code, "
            "undetected secrets, or failing tests from reaching deployment."
        ),
        remediation=(
            "Add .github/workflows/ci.yml to run pytest and pip-audit on every push."
        ),
        verification=(
            "File existence checks for common CI/CD configurations"
        ),
    )


def check_https_documentation(repo: Path) -> Finding:
    """Check for HTTPS/TLS documentation or configuration."""
    fid = "DEPLOY-HTTPS"
    readme = repo / "README.md"
    compose = repo / "docker-compose.yml"

    readme_content = _read(readme) or ""
    compose_content = _read(compose) or ""

    has_ssl_compose = bool(
        re.search(r"ssl|tls|443|https", compose_content, re.IGNORECASE)
    )
    has_https_readme = bool(
        re.search(
            r"https|tls|ssl|certbot|letsencrypt|nginx.*ssl",
            readme_content, re.IGNORECASE,
        )
    )

    if has_ssl_compose:
        return Finding(
            id=fid, category="Deployment", severity="INFO", status="PASSED",
            confidence="MEDIUM",
            title="HTTPS/TLS configuration found in docker-compose.yml",
            file="docker-compose.yml",
            location="TLS/SSL or port 443 reference",
            evidence="SSL/TLS or port 443 reference found in compose",
            description="Docker Compose configuration references HTTPS/TLS.",
            impact="N/A",
            remediation="N/A",
            verification="Regex search for ssl/tls/443 in docker-compose.yml",
        )

    if has_https_readme:
        return Finding(
            id=fid, category="Deployment", severity="INFO", status="PASSED",
            confidence="LOW",
            title="HTTPS strategy documented in README.md",
            file="README.md",
            location="HTTPS/TLS section",
            evidence="https/tls/ssl keyword found in README.md",
            description="README documents the HTTPS/TLS strategy.",
            impact="N/A",
            remediation="N/A",
            verification="Regex search for https/tls/ssl in README.md",
        )

    return Finding(
        id=fid, category="Deployment", severity="MEDIUM",
        status="REQUIRES_HUMAN_VERIFICATION",
        confidence="LOW",
        title=(
            "No HTTPS/TLS configuration in repository — "
            "may be handled by external infrastructure"
        ),
        file="docker-compose.yml",
        location="N/A",
        evidence=(
            "No SSL/TLS references in docker-compose.yml or README.md"
        ),
        description=(
            "No HTTPS/TLS configuration is present in the repository. "
            "This may be intentional if TLS is terminated at an external "
            "load balancer, CDN, or reverse proxy (Nginx, Cloudflare, AWS ALB)."
        ),
        impact=(
            "If TLS is not terminated externally, all traffic (JWT tokens, "
            "evidence uploads, crime reports) travels in plaintext."
        ),
        remediation=(
            "Document your TLS strategy in README.md. "
            "If using external TLS termination, state this explicitly. "
            "If serving directly, configure SSL in nginx or use Certbot."
        ),
        verification=(
            "Regex search for https/tls/ssl/443 in docker-compose.yml and README.md. "
            "REQUIRES HUMAN VERIFICATION of actual infrastructure."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Testing Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_test_suite(repo: Path) -> Finding:
    """Check that test files exist."""
    fid = "TEST-01"
    tests_dir = repo / "forensix_backend_python" / "tests"

    if not tests_dir.exists():
        return Finding(
            id=fid, category="Testing", severity="HIGH", status="CONFIRMED",
            confidence="HIGH", title="No test directory found",
            file="forensix_backend_python/tests/",
            location="N/A", evidence="Directory not found",
            description="No test suite found.",
            impact="No automated regression testing is possible.",
            remediation="Create tests/ directory and add test files.",
            verification="Directory existence check",
        )

    test_files = sorted(tests_dir.glob("test_*.py"))
    if not test_files:
        return Finding(
            id=fid, category="Testing", severity="HIGH", status="CONFIRMED",
            confidence="HIGH",
            title="Test directory exists but contains no test_*.py files",
            file="forensix_backend_python/tests/",
            location="N/A", evidence="No test_*.py files found",
            description="Test directory present but empty.",
            impact="No automated tests.",
            remediation="Add test_*.py files.",
            verification="Glob for test_*.py in tests/",
        )

    return Finding(
        id=fid, category="Testing", severity="INFO", status="PASSED",
        confidence="HIGH",
        title=f"{len(test_files)} test file(s) found",
        file="forensix_backend_python/tests/",
        location="tests/*.py",
        evidence=", ".join(f.name for f in test_files),
        description=f"Test suite contains {len(test_files)} test file(s).",
        impact="N/A",
        remediation="N/A",
        verification="Glob for test_*.py in tests/",
    )


def run_pytest_check(repo: Path) -> Finding:
    """Run pytest and report actual results."""
    fid = "TEST-PYTEST"
    backend_dir = repo / "forensix_backend_python"

    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pytest", "--tb=short", "-q"],
        cwd=backend_dir,
        timeout=300,
    )

    if rc == -1:
        return Finding(
            id=fid, category="Testing", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="HIGH", title="pytest not available or failed to start",
            file="N/A", location="N/A", evidence=stderr,
            description="pytest could not be found or executed.",
            impact="Test results unknown.",
            remediation="Install pytest: pip install pytest",
            verification="python -m pytest --tb=short -q",
        )

    if rc == -2:
        return Finding(
            id=fid, category="Testing", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="HIGH", title="pytest timed out",
            file="N/A", location="N/A",
            evidence=f"Timed out after 300 seconds",
            description="Test suite took too long to complete.",
            impact="Test results unknown.",
            remediation="Investigate slow tests. Run manually: python -m pytest -v",
            verification="python -m pytest --tb=short -q (timed out)",
        )

    combined = stdout + "\n" + stderr
    # Extract summary line
    summary = ""
    for line in combined.splitlines():
        if "passed" in line or "failed" in line or "error" in line:
            summary = line.strip()
            break

    if rc == 0:
        return Finding(
            id=fid, category="Testing", severity="INFO", status="PASSED",
            confidence="HIGH",
            title=f"pytest PASSED — {summary}",
            file="forensix_backend_python/tests/",
            location="N/A",
            evidence=summary or (stdout[-300:] if stdout else "No output"),
            description="All tests passed.",
            impact="N/A",
            remediation="N/A",
            verification="python -m pytest --tb=short -q (exit code 0)",
        )

    return Finding(
        id=fid, category="Testing", severity="HIGH", status="CONFIRMED",
        confidence="HIGH",
        title=f"pytest FAILED — {summary}",
        file="forensix_backend_python/tests/",
        location="N/A",
        evidence=(combined[-1500:]).strip(),
        description="The test suite failed. See evidence for details.",
        impact="Failing tests indicate regressions or broken functionality.",
        remediation="Fix failing tests before deployment.",
        verification="python -m pytest --tb=short -q (non-zero exit code)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dependency Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_dep_scanning_configured(repo: Path) -> Finding:
    """Check whether automated dependency scanning is configured."""
    fid = "DEP-CONFIG"
    dependabot = repo / ".github" / "dependabot.yml"
    has_dependabot = dependabot.exists()
    has_pip_audit_in_ci = False

    workflows_dir = repo / ".github" / "workflows"
    if workflows_dir.exists():
        for wf in workflows_dir.glob("*.yml"):
            wf_content = _read(wf) or ""
            if "pip-audit" in wf_content or "pip_audit" in wf_content or "safety" in wf_content:
                has_pip_audit_in_ci = True
                break

    if has_dependabot or has_pip_audit_in_ci:
        return Finding(
            id=fid, category="Dependencies", severity="INFO", status="PASSED",
            confidence="HIGH", title="Automated dependency scanning configured",
            file=".github/",
            location="dependabot.yml or CI workflow",
            evidence=(
                f"Dependabot: {has_dependabot}, "
                f"pip-audit in CI: {has_pip_audit_in_ci}"
            ),
            description="Automated dependency vulnerability scanning is configured.",
            impact="N/A",
            remediation="N/A",
            verification=(
                "File existence for dependabot.yml; "
                "string search in CI workflows for pip-audit/safety"
            ),
        )

    return Finding(
        id=fid, category="Dependencies", severity="MEDIUM", status="RECOMMENDATION",
        confidence="HIGH",
        title="No automated dependency vulnerability scanning configured",
        file="N/A",
        location="N/A",
        evidence=(
            "No dependabot.yml found; "
            "no pip-audit/safety in CI workflows"
        ),
        description=(
            "No automated dependency scanning is configured. "
            "Known CVEs in dependencies may go undetected."
        ),
        impact="Vulnerable dependencies may be deployed without detection.",
        remediation=(
            "Add pip-audit to CI pipeline or configure "
            "Dependabot in .github/dependabot.yml."
        ),
        verification=(
            "File existence check for dependabot.yml; "
            "string search for pip-audit in CI workflows"
        ),
    )


def run_pip_audit_check(repo: Path) -> Finding:
    """Run pip-audit if available and report actual results."""
    fid = "DEP-AUDIT"
    req_file = repo / "forensix_backend_python" / "requirements.txt"

    if not req_file.exists():
        return Finding(
            id=fid, category="Dependencies", severity="MEDIUM", status="NOT_VERIFIED",
            confidence="HIGH", title="requirements.txt not found",
            file="forensix_backend_python/requirements.txt",
            location="N/A", evidence="File not found",
            description="Cannot run dependency audit without requirements.txt.",
            impact="Unknown",
            remediation="Ensure requirements.txt exists.",
            verification="File existence check",
        )

    # Check if pip-audit is available
    rc_check, _, err_check = _run([sys.executable, "-m", "pip_audit", "--version"])
    if rc_check == -1:
        return Finding(
            id=fid, category="Dependencies", severity="LOW", status="NOT_VERIFIED",
            confidence="HIGH",
            title="pip-audit not installed — dependency vulnerability scan not performed",
            file="forensix_backend_python/requirements.txt",
            location="N/A",
            evidence="pip_audit module not found",
            description=(
                "pip-audit is not installed. "
                "No dependency vulnerability scan was performed."
            ),
            impact="Known CVEs in dependencies may be present.",
            remediation=(
                "Install pip-audit: pip install pip-audit\n"
                "Then run: pip-audit -r requirements.txt"
            ),
            verification="python -m pip_audit --version (command not found)",
        )

    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pip_audit", "-r", str(req_file)],
        cwd=repo / "forensix_backend_python",
        timeout=180,
    )

    combined = (stdout + "\n" + stderr).strip()

    if rc == 0:
        return Finding(
            id=fid, category="Dependencies", severity="INFO", status="PASSED",
            confidence="HIGH",
            title="pip-audit: no known vulnerabilities found",
            file="forensix_backend_python/requirements.txt",
            location="N/A",
            evidence=combined[:500] if combined else "No output (clean)",
            description="No known CVEs found in project dependencies.",
            impact="N/A",
            remediation="N/A",
            verification="python -m pip_audit -r requirements.txt (exit code 0)",
        )

    # Non-zero: vulnerabilities found or scan error
    cves = list(set(re.findall(r"CVE-\d{4}-\d+", combined)))
    if cves:
        return Finding(
            id=fid, category="Dependencies", severity="HIGH", status="CONFIRMED",
            confidence="HIGH",
            title=f"pip-audit found {len(cves)} CVE(s): {', '.join(cves[:5])}",
            file="forensix_backend_python/requirements.txt",
            location="N/A",
            evidence=combined[:1500],
            description="pip-audit identified CVEs in project dependencies.",
            impact="Vulnerable dependencies may be exploitable.",
            remediation="Update affected packages to patched versions.",
            verification=(
                "python -m pip_audit -r requirements.txt (non-zero exit code with CVEs)"
            ),
        )

    return Finding(
        id=fid, category="Dependencies", severity="MEDIUM", status="NOT_VERIFIED",
        confidence="MEDIUM",
        title="pip-audit completed with non-zero exit code (no CVEs extracted)",
        file="forensix_backend_python/requirements.txt",
        location="N/A",
        evidence=combined[:500],
        description=(
            "pip-audit ran but returned a non-zero exit code. "
            "No CVE identifiers were extracted. "
            "Review the output manually."
        ),
        impact="Unknown",
        remediation="Review pip-audit output manually.",
        verification=(
            "python -m pip_audit -r requirements.txt (non-zero exit code)"
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_all_checks(
    repo: Path,
    run_tests: bool = False,
    run_audit: bool = False,
) -> List[Finding]:
    findings: List[Finding] = []

    print("  [Security]       Checking secrets, auth, and code security patterns...")
    findings.append(check_env_not_committed(repo))
    findings.append(check_hardcoded_db_credentials(repo))
    findings.append(check_demo_user_default(repo))
    findings.append(check_officer_codes_fallback(repo))
    findings.extend(check_auth_security_config(repo))
    findings.append(check_evidence_upload_auth(repo))
    findings.append(check_websocket_token_in_url(repo))
    findings.append(check_password_min_length(repo))

    print("  [Configuration]  Checking environment and API configuration...")
    findings.append(check_localhost_api_url(repo))
    findings.append(check_cors_wildcard(repo))
    findings.append(check_allowed_hosts_wildcard(repo))
    findings.append(check_required_env_vars(repo))

    print("  [Database]       Checking schema management and migration strategy...")
    findings.append(check_sqlite_production_fallback(repo))
    findings.append(check_alembic_migrations_exist(repo))
    findings.append(check_create_all_vs_alembic(repo))

    print("  [Deployment]     Checking Docker, entrypoint, CI/CD, and HTTPS...")
    findings.extend(check_docker_configuration(repo))
    findings.append(check_entrypoint_migrations(repo))
    findings.append(check_ci_cd_presence(repo))
    findings.append(check_https_documentation(repo))

    print("  [Testing]        Checking test suite presence...")
    findings.append(check_test_suite(repo))
    if run_tests:
        print("  [Testing]        Running pytest (may take a moment)...")
        findings.append(run_pytest_check(repo))
    else:
        findings.append(Finding(
            id="TEST-PYTEST", category="Testing", severity="MEDIUM",
            status="NOT_VERIFIED", confidence="HIGH",
            title="pytest not run — pass --run-tests to execute",
            file="forensix_backend_python/tests/",
            location="N/A", evidence="Skipped — user did not pass --run-tests",
            description=(
                "Test suite was not executed in this audit run. "
                "Pass --run-tests to run pytest and include results."
            ),
            impact="Test pass/fail status is unknown for this audit.",
            remediation="Run: python scripts/release_check.py --run-tests",
            verification="N/A — not executed",
        ))

    print("  [Dependencies]   Checking dependency scanning configuration...")
    findings.append(check_dep_scanning_configured(repo))
    if run_audit:
        print("  [Dependencies]   Running pip-audit (may take a moment)...")
        findings.append(run_pip_audit_check(repo))
    else:
        findings.append(Finding(
            id="DEP-AUDIT", category="Dependencies", severity="LOW",
            status="NOT_VERIFIED", confidence="HIGH",
            title="pip-audit not run — pass --run-pip-audit to execute",
            file="forensix_backend_python/requirements.txt",
            location="N/A", evidence="Skipped — user did not pass --run-pip-audit",
            description=(
                "Dependency vulnerability scan was not performed. "
                "Pass --run-pip-audit to run pip-audit."
            ),
            impact="Known CVEs in dependencies may be present.",
            remediation="Run: python scripts/release_check.py --run-pip-audit",
            verification="N/A — not executed",
        ))

    return findings


# ─────────────────────────────────────────────────────────────────────────────
# Status determination
# ─────────────────────────────────────────────────────────────────────────────

def determine_overall_status(findings: List[Finding]) -> Tuple[str, str]:
    """
    Returns (status_label, explanation).
    Labels: NOT READY | READY WITH WARNINGS | READY | NOT VERIFIED
    """
    critical_confirmed = [
        f for f in findings
        if f.status == "CONFIRMED" and f.severity == "CRITICAL"
    ]
    high_confirmed = [
        f for f in findings
        if f.status == "CONFIRMED" and f.severity == "HIGH"
    ]
    test_failed = [
        f for f in findings
        if f.id == "TEST-PYTEST" and f.status == "CONFIRMED"
    ]
    medium_issues = [
        f for f in findings
        if f.status in ("CONFIRMED", "WARNING") and f.severity == "MEDIUM"
    ]
    low_issues = [
        f for f in findings
        if f.status in ("CONFIRMED", "WARNING", "RECOMMENDATION")
        and f.severity == "LOW"
    ]
    human_verify = [
        f for f in findings
        if f.status == "REQUIRES_HUMAN_VERIFICATION"
    ]
    not_verified = [
        f for f in findings
        if f.status == "NOT_VERIFIED"
    ]

    if critical_confirmed or high_confirmed or test_failed:
        blockers = []
        if critical_confirmed:
            blockers.append(
                f"{len(critical_confirmed)} CRITICAL confirmed finding(s)"
            )
        if high_confirmed:
            ids = ", ".join(f.id for f in high_confirmed[:5])
            blockers.append(
                f"{len(high_confirmed)} HIGH confirmed finding(s) ({ids})"
            )
        if test_failed:
            blockers.append("test suite failure")
        return (
            "NOT READY",
            f"Blocked by: {'; '.join(blockers)}. These must be resolved before release.",
        )

    if medium_issues:
        ids = ", ".join(f.id for f in medium_issues[:5])
        return (
            "READY WITH WARNINGS",
            (
                f"{len(medium_issues)} MEDIUM finding(s) require attention ({ids}). "
                "Not blocking release, but should be addressed before or shortly after launch."
            ),
        )

    if not_verified and not human_verify:
        return (
            "NOT VERIFIED",
            (
                f"{len(not_verified)} check(s) could not be verified automatically "
                "(e.g., tests not run, pip-audit not run). "
                "Re-run with --run-tests --run-pip-audit for a complete assessment."
            ),
        )

    if human_verify:
        return (
            "READY WITH WARNINGS",
            (
                f"{len(human_verify)} item(s) require human verification "
                "before deployment status can be fully confirmed. "
                "See 'Human Verification Items' section."
            ),
        )

    if low_issues:
        return (
            "READY WITH WARNINGS",
            (
                f"{len(low_issues)} LOW severity recommendation(s) exist. "
                "These are not blocking."
            ),
        )

    return (
        "READY",
        "All automated checks passed. Review any human-verification items before deployment.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

_SEV_ICON = {
    "CRITICAL": "🔴", "HIGH": "🔴", "MEDIUM": "🟡",
    "LOW": "🔵", "INFO": "✅",
}
_STATUS_ICON = {
    "CONFIRMED": "🔴 CONFIRMED",
    "WARNING": "🟡 WARNING",
    "RECOMMENDATION": "🔵 RECOMMENDATION",
    "REQUIRES_HUMAN_VERIFICATION": "⚪ REQUIRES HUMAN VERIFICATION",
    "PASSED": "✅ PASSED",
    "NOT_VERIFIED": "❓ NOT VERIFIED",
}
_STATUS_LABEL = {
    "NOT READY": "🔴 NOT READY",
    "READY WITH WARNINGS": "🟡 READY WITH WARNINGS",
    "READY": "✅ READY",
    "NOT VERIFIED": "❓ NOT VERIFIED",
}


def _finding_md(f: Finding, show_passed: bool = True) -> str:
    if not show_passed and f.status == "PASSED":
        return ""
    lines = [
        f"#### {_STATUS_ICON.get(f.status, f.status)} — {f.id}: {f.title}",
        f"",
        f"| Field | Value |",
        f"|---|---|",
        f"| **Category** | {f.category} |",
        f"| **Severity** | {_SEV_ICON.get(f.severity, '')} {f.severity} |",
        f"| **Confidence** | {f.confidence} |",
        f"| **File** | `{f.file}` |",
        f"| **Location** | {f.location} |",
        f"",
        f"**Evidence:**",
        f"```",
        f.evidence[:400] if f.evidence else "N/A",
        f"```",
        f"",
        f"**Description:** {f.description}",
        f"",
        f"**Impact:** {f.impact}",
        f"",
        f"**Remediation:** {f.remediation}",
        f"",
        f"**Verification:** _{f.verification}_",
        f"",
        f"---",
        f"",
    ]
    return "\n".join(lines)


def generate_markdown_report(
    findings: List[Finding],
    repo: Path,
    output_path: Path,
) -> str:
    now = datetime.datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    overall_status, status_explanation = determine_overall_status(findings)

    categories = ["Security", "Configuration", "Database", "Deployment", "Testing", "Dependencies"]

    by_status = {s: [] for s in VALID_STATUSES}
    for f in findings:
        by_status.setdefault(f.status, []).append(f)

    confirmed = [f for f in findings if f.status == "CONFIRMED"]
    warnings = [f for f in findings if f.status == "WARNING"]
    passed = [f for f in findings if f.status == "PASSED"]
    not_verified = [f for f in findings if f.status == "NOT_VERIFIED"]
    human_verify = [f for f in findings if f.status == "REQUIRES_HUMAN_VERIFICATION"]
    recommendations = [f for f in findings if f.status == "RECOMMENDATION"]

    lines = []
    lines.append("# Release Readiness Report")
    lines.append("")
    lines.append("> **Generated by:** ForensiX-ZR Release Readiness & Security Audit Script  ")
    lines.append("> **IBM Bob 2.0 Hackathon** — Deterministic Evidence-Based Audit Engine")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(
        f"This report was generated by running the automated release readiness audit against "
        f"the ForensiX-ZR repository. Every finding is backed by actual repository evidence. "
        f"No CVEs are invented, and no commands are claimed to pass unless actually executed."
    )
    lines.append("")

    # 2. Audit Timestamp
    lines.append("## 2. Audit Timestamp")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Audit Run** | {timestamp} |")
    lines.append(f"| **Script Version** | 1.0.0 |")
    lines.append(f"| **Total Checks** | {len(findings)} |")
    lines.append("")

    # 3. Repository Information
    lines.append("## 3. Repository Information")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Repository Root** | `{repo}` |")
    lines.append(f"| **Backend** | `forensix_backend_python/` (FastAPI + Python) |")
    lines.append(f"| **Frontend** | `frontend/` (Vanilla HTML/CSS/JS) |")
    lines.append(f"| **Database** | SQLite (dev) / PostgreSQL (production) |")
    lines.append(f"| **Auth** | JWT (HS256) + bcrypt + OTP password reset |")
    lines.append("")

    # 4. Overall Status
    lines.append("## 4. Overall Status")
    lines.append("")
    lines.append(f"### {_STATUS_LABEL.get(overall_status, overall_status)}")
    lines.append("")
    lines.append(f"> {status_explanation}")
    lines.append("")

    # 5. Finding Summary
    lines.append("## 5. Finding Summary")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|---|---|")
    lines.append(f"| 🔴 Confirmed Issues | {len(confirmed)} |")
    lines.append(f"| 🟡 Warnings | {len(warnings)} |")
    lines.append(f"| 🔵 Recommendations | {len(recommendations)} |")
    lines.append(f"| ⚪ Requires Human Verification | {len(human_verify)} |")
    lines.append(f"| ✅ Passed | {len(passed)} |")
    lines.append(f"| ❓ Not Verified | {len(not_verified)} |")
    lines.append(f"| **Total** | **{len(findings)}** |")
    lines.append("")
    lines.append("**Breakdown by severity (confirmed + warning only):**")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = len([
            f for f in findings
            if f.severity == sev and f.status in ("CONFIRMED", "WARNING")
        ])
        if count > 0:
            lines.append(f"| {_SEV_ICON.get(sev, '')} {sev} | {count} |")
    lines.append("")

    # 6-11. Findings by Category
    for cat in categories:
        section_map = {
            "Security": "6", "Configuration": "7", "Database": "8",
            "Deployment": "9", "Testing": "10", "Dependencies": "11",
        }
        sec_num = section_map.get(cat, "?")
        cat_findings = [f for f in findings if f.category == cat]
        if not cat_findings:
            continue

        lines.append(f"## {sec_num}. {cat} Findings")
        lines.append("")

        non_passed = [f for f in cat_findings if f.status != "PASSED"]
        passed_cat = [f for f in cat_findings if f.status == "PASSED"]

        for f in non_passed:
            lines.append(_finding_md(f))

        if passed_cat:
            lines.append(
                f"<details><summary>✅ {len(passed_cat)} passed check(s)</summary>"
            )
            lines.append("")
            for f in passed_cat:
                lines.append(_finding_md(f))
            lines.append("</details>")
            lines.append("")

    # 12. Human Verification Items
    lines.append("## 12. Human Verification Items")
    lines.append("")
    if human_verify:
        for f in human_verify:
            lines.append(f"- **{f.id}**: {f.title}")
            lines.append(f"  - {f.remediation}")
            lines.append("")
    else:
        lines.append("No items require human verification in this audit run.")
        lines.append("")

    # 13. Passed Checks
    lines.append("## 13. Passed Checks")
    lines.append("")
    if passed:
        lines.append("| ID | Title |")
        lines.append("|---|---|")
        for f in passed:
            lines.append(f"| `{f.id}` | {f.title} |")
    else:
        lines.append("No checks passed in this audit run.")
    lines.append("")

    # 14. Remediation Checklist
    lines.append("## 14. Remediation Checklist")
    lines.append("")
    lines.append("Address items in this order (highest severity first):")
    lines.append("")
    priority_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    for sev in priority_order:
        sev_findings = [
            f for f in findings
            if f.severity == sev and f.status in ("CONFIRMED", "WARNING")
        ]
        if sev_findings:
            lines.append(f"### {_SEV_ICON.get(sev, '')} {sev}")
            lines.append("")
            for f in sev_findings:
                lines.append(f"- [ ] **{f.id}**: {f.title}")
                lines.append(f"  - *{f.remediation}*")
                lines.append("")

    # 15. Release Checklist
    lines.append("## 15. Release Checklist")
    lines.append("")
    lines.append("Before deploying to production, verify each of the following:")
    lines.append("")
    checklist = [
        ("SEC-ENV-01", "`.env` is not committed to git and is in `.gitignore`"),
        ("SEC-01", "`docker-compose.yml` uses `${POSTGRES_PASSWORD}` substitution, not a hardcoded password"),
        ("SEC-03", "`SEED_DEMO_USERS` defaults to `false` in `app/main.py`"),
        ("SEC-02", "`VALID_OFFICER_CODES` is explicitly set in production `.env`"),
        ("CONFIG-01", "Frontend API URL uses dynamic detection, not hardcoded `localhost`"),
        ("CONFIG-02", "`CORS_ORIGINS` is set to specific domains in production `.env`"),
        ("CONFIG-03", "`ALLOWED_HOSTS` is set to specific domains in production `.env`"),
        ("DB-01", "`alembic upgrade head` runs before application startup (entrypoint.sh)"),
        ("DB-02", "SQLite startup warning is present for non-production detection"),
        ("DB-ALEMBIC-01", "Alembic migration files are present and up to date"),
        ("DEPLOY-02", "entrypoint.sh uses `set -e` and exits on migration failure"),
        ("DEPLOY-CI", "CI/CD pipeline runs tests before deployment"),
        ("DEPLOY-HTTPS", "TLS strategy is confirmed (external termination or nginx SSL)"),
        ("TEST-PYTEST", "All tests pass on the deployment target"),
        ("DEP-AUDIT", "No critical/high CVEs in dependencies (run pip-audit)"),
    ]
    for finding_id, item in checklist:
        matching = [f for f in findings if f.id == finding_id]
        if matching and matching[0].status == "PASSED":
            lines.append(f"- [x] **{finding_id}**: {item}")
        else:
            lines.append(f"- [ ] **{finding_id}**: {item}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*This report was generated automatically. "
        "All findings are based on actual repository evidence. "
        "Human verification items must be confirmed by a developer before release.*"
    )

    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content


def generate_json_report(
    findings: List[Finding],
    repo: Path,
    output_path: Path,
) -> dict:
    now = datetime.datetime.utcnow()
    overall_status, explanation = determine_overall_status(findings)

    report = {
        "meta": {
            "generated_at": now.isoformat() + "Z",
            "script_version": "1.0.0",
            "repository": str(repo),
            "total_checks": len(findings),
        },
        "overall_status": overall_status,
        "overall_status_explanation": explanation,
        "summary": {
            "confirmed": len([f for f in findings if f.status == "CONFIRMED"]),
            "warning": len([f for f in findings if f.status == "WARNING"]),
            "recommendation": len([f for f in findings if f.status == "RECOMMENDATION"]),
            "requires_human_verification": len(
                [f for f in findings if f.status == "REQUIRES_HUMAN_VERIFICATION"]
            ),
            "passed": len([f for f in findings if f.status == "PASSED"]),
            "not_verified": len([f for f in findings if f.status == "NOT_VERIFIED"]),
        },
        "findings": [f.as_dict() for f in findings],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(findings: List[Finding], overall_status: str, explanation: str) -> None:
    confirmed = [f for f in findings if f.status == "CONFIRMED"]
    warnings = [f for f in findings if f.status == "WARNING"]
    passed = [f for f in findings if f.status == "PASSED"]
    not_verified = [f for f in findings if f.status == "NOT_VERIFIED"]
    human_verify = [f for f in findings if f.status == "REQUIRES_HUMAN_VERIFICATION"]

    print()
    print("=" * 60)
    print(f"  OVERALL STATUS: {overall_status}")
    print("=" * 60)
    print(f"  {explanation}")
    print()
    print(f"  Confirmed Issues :  {len(confirmed)}")
    print(f"  Warnings         :  {len(warnings)}")
    print(f"  Passed           :  {len(passed)}")
    print(f"  Not Verified     :  {len(not_verified)}")
    print(f"  Human Verify     :  {len(human_verify)}")
    print()

    if confirmed:
        print("  CONFIRMED ISSUES:")
        for f in confirmed:
            print(f"    [{f.severity:8s}] {f.id}: {f.title}")
    if warnings:
        print("  WARNINGS:")
        for f in warnings:
            print(f"    [{f.severity:8s}] {f.id}: {f.title}")
    print("=" * 60)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ForensiX-ZR Release Readiness & Security Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to repository root (default: parent of scripts/ directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write reports (default: <repo>/reports/)",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Execute the pytest test suite and include results",
    )
    parser.add_argument(
        "--run-pip-audit",
        action="store_true",
        help="Execute pip-audit dependency scanner and include results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write JSON report in addition to Markdown",
    )
    args = parser.parse_args()

    # Reconfigure stdout/stderr to utf-8 on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Resolve repo root
    if args.repo is not None:
        repo = args.repo.resolve()
    else:
        # Default: parent of the directory containing this script
        repo = (Path(__file__).parent.parent).resolve()

    if not repo.is_dir():
        print(f"ERROR: Repository path does not exist or is not a directory: {repo}")
        return 1

    # Resolve output directory
    output_dir = args.output_dir.resolve() if args.output_dir else repo / "reports"

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     ForensiX-ZR Release Readiness & Security Audit          ║")
    print("║     IBM Bob 2.0 Hackathon — Deterministic Audit Engine      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  Repository : {repo}")
    print(f"  Output Dir : {output_dir}")
    print(f"  Run Tests  : {args.run_tests}")
    print(f"  pip-audit  : {args.run_pip_audit}")
    print()
    print("Running checks...")
    print()

    findings = run_all_checks(
        repo=repo,
        run_tests=args.run_tests,
        run_audit=args.run_pip_audit,
    )

    overall_status, explanation = determine_overall_status(findings)
    _print_summary(findings, overall_status, explanation)

    # Write Markdown report
    md_path = output_dir / "release-readiness-report.md"
    generate_markdown_report(findings, repo, md_path)
    print(f"  Markdown report : {md_path}")

    # Write JSON report
    json_path = output_dir / "release-readiness-report.json"
    generate_json_report(findings, repo, json_path)
    print(f"  JSON report     : {json_path}")
    print()

    # Return non-zero if NOT READY
    return 1 if overall_status == "NOT READY" else 0


if __name__ == "__main__":
    sys.exit(main())
