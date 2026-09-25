# IBM Bob Workflow — Release Readiness & Security Audit

This document describes the conceptual workflow for using IBM Bob IDE as the
orchestration and developer-workflow layer for the ForensiX-ZR Release Readiness
& Security Audit Assistant.

> **Important:** This document describes the workflow design. No IBM Bob internal API
> or SDK is used — Bob executes the `scripts/release_check.py` script as a terminal
> tool and interprets the structured JSON output.

---

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │       IBM BOB ORCHESTRATOR       │
                    │                                  │
                    │  • Natural language understanding│
                    │  • Project Context (full repo)   │
                    │  • Cross-domain reasoning        │
                    │  • Agent Mode (autonomous tasks) │
                    └─────────────┬───────────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │    PARALLEL TASK DISPATCH    │
                    └──┬──────┬──────┬──────┬─────┘
                       │      │      │      │
              ┌────────▼──┐ ┌─▼────┐ │ ┌───▼───────┐
              │ Security  │ │Config│ │ │ Database  │
              │   Agent   │ │Agent │ │ │   Agent   │
              └────────┬──┘ └─┬────┘ │ └───┬───────┘
                       │      │      │     │
                    ┌──▼──────▼──┐ ┌─▼─────▼─────────┐
                    │ Deployment │ │ Test / Dependency│
                    │   Agent    │ │     Agent        │
                    └──────┬─────┘ └────────┬─────────┘
                           │                │
                    ┌──────▼────────────────▼────────┐
                    │        Finding Consolidator     │
                    │                                 │
                    │  • Merge structured findings    │
                    │  • Deduplicate cross-domain     │
                    │  • Apply severity ranking       │
                    │  • Determine overall status     │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │   Release Readiness Report       │
                    │                                  │
                    │  • Markdown (human-readable)     │
                    │  • JSON (machine-readable)       │
                    │  • Status: READY / NOT READY     │
                    │  • Remediation checklist         │
                    └─────────────────────────────────┘
```

---

## Parallel Audit Tasks

Each of these tasks is **independent** and can run in parallel in IBM Bob IDE.
They share the repository via Project Context but read different files.

### Task 1 — Security Audit

**Prompt for Bob:**
> "Audit the security posture of ForensiX-ZR. Check: (1) .env committed to git?,
> (2) hardcoded PostgreSQL credentials in docker-compose.yml?, (3) SEED_DEMO_USERS
> default value?, (4) VALID_OFFICER_CODES fallback behavior?, (5) JWT algorithm
> and SECRET_KEY startup validation?, (6) evidence files served without auth?,
> (7) WebSocket token in URL?, (8) password minimum length. Return structured
> JSON findings with file evidence."

**Files inspected:**
- `.gitignore`, `docker-compose.yml`
- `app/main.py`, `app/routes/auth.py`
- `app/utils/security.py`, `app/routes/ws.py`
- `app/schemas/schemas.py`

---

### Task 2 — Configuration Audit

**Prompt for Bob:**
> "Audit the configuration of ForensiX-ZR. Check: (1) frontend API URL hardcoded
> to localhost?, (2) CORS wildcard in .env.example or main.py?, (3) ALLOWED_HOSTS
> wildcard?, (4) all required production env vars in .env.example?. Return
> structured JSON findings with file evidence."

**Files inspected:**
- `frontend/js/config.js`
- `forensix_backend_python/.env.example`
- `app/main.py`

---

### Task 3 — Database Audit

**Prompt for Bob:**
> "Audit the database configuration of ForensiX-ZR. Check: (1) DATABASE_URL
> falls back to SQLite silently?, (2) startup warning when SQLite is in use?,
> (3) Alembic migration files exist?, (4) create_all() conflicts with Alembic?. 
> Return structured JSON findings with file evidence."

**Files inspected:**
- `app/database/db.py`
- `app/main.py`
- `alembic/versions/*.py`
- `entrypoint.sh`

---

### Task 4 — Deployment Audit

**Prompt for Bob:**
> "Audit the deployment configuration of ForensiX-ZR. Check: (1) Dockerfile
> and docker-compose.yml exist?, (2) entrypoint.sh runs alembic upgrade head
> with error handling?, (3) any CI/CD pipeline configured?, (4) HTTPS/TLS
> documented or configured?. Return structured JSON findings."

**Files inspected:**
- `Dockerfile`, `docker-compose.yml`
- `entrypoint.sh`
- `.github/workflows/`, `.gitlab-ci.yml`
- `README.md`

---

### Task 5 — Test and Dependency Audit

**Prompt for Bob:**
> "Audit the testing and dependency posture of ForensiX-ZR. (1) Do test files
> exist in tests/? (2) Run pytest and report exact pass/fail with evidence.
> (3) Is pip-audit configured in CI? (4) Run pip-audit -r requirements.txt
> and report actual CVEs found (do not invent CVEs). Return structured JSON."

**Commands executed:**
```bash
python -m pytest --tb=short -q          # Testing
python -m pip_audit -r requirements.txt # Dependencies (if available)
```

---

## Finding Consolidator

After all parallel tasks complete, the Finding Consolidator:

1. **Merges** all structured finding JSON arrays from the 5 tasks
2. **Deduplicates** any findings that reference the same issue
3. **Applies cross-domain reasoning:**
   - "SEC-01 (hardcoded DB creds) + DEPLOY-CI (no CI/CD) = no automated gate
     prevents this committed credential from reaching production. Combined risk."
4. **Determines overall status:**
   - `NOT READY`: Any CONFIRMED CRITICAL or HIGH finding, or test failure
   - `READY WITH WARNINGS`: MEDIUM confirmed/warnings present
   - `READY`: All checks pass
   - `NOT VERIFIED`: Tests or pip-audit not run
5. **Generates Remediation Checklist** ordered by severity

---

## How to Run in IBM Bob IDE

### Option A: Run the audit script directly (Bob executes it as a tool)

```bash
# From repository root
python scripts/release_check.py --run-tests --run-pip-audit
```

Bob reads the JSON output from `reports/release-readiness-report.json` and
interprets findings, explains impact, and suggests fixes.

### Option B: Use Agent Mode for end-to-end workflow

1. Open the ForensiX-ZR repository in IBM Bob IDE
2. Load the repository as **Project Context**
3. Enable **Agent Mode**
4. Enter the following instruction:

```
Run a complete release readiness audit of ForensiX-ZR using the audit engine
at scripts/release_check.py. Execute with --run-tests --run-pip-audit. 
After the audit completes, present a prioritized list of all confirmed and 
warning-level findings. Then, one at a time, fix each HIGH and CRITICAL 
finding, run the test suite after each fix to confirm no regressions, 
and re-run the relevant audit check to verify the fix. When all HIGH and 
CRITICAL findings are resolved, generate the final release readiness report.
```

5. Bob runs autonomously — check back for the final report

### Option C: Parallel task dispatch (IBM Bob multi-task panel)

1. In IBM Bob IDE, open the multi-task panel
2. Create 5 parallel tasks with the prompts from "Parallel Audit Tasks" above
3. Each task runs independently against the shared Project Context
4. When all 5 complete, run the consolidation prompt:

```
Collect the findings JSON from all 5 completed audit tasks. Merge them,
deduplicate, determine overall status, and generate the final
release-readiness-report.md.
```

---

## Incremental Re-Audit Pattern

After fixing a finding, Bob should re-run only the relevant audit check:

```
Developer: "I've fixed SEC-01 (hardcoded DB password in docker-compose.yml)"

Bob: Runs check_hardcoded_db_credentials(repo) → PASSED
Bob: "SEC-01 is now PASSED. The remaining confirmed findings are: [...]"
```

This avoids re-running the entire audit for each fix, making the iteration
cycle much faster than a manual review.

---

## Sample IBM Bob Session Transcript

```
User: "Run a release readiness audit on ForensiX-ZR"

Bob:  "I'll run the audit engine now..."
      [executes: python scripts/release_check.py --run-tests]
      "Audit complete. Status: NOT READY
       
       Confirmed Issues (HIGH):
       - DEPLOY-CI: No CI/CD pipeline found (.github/workflows/ missing)
       
       Confirmed Issues (MEDIUM):
       - DB-01: create_all() and alembic both present (schema conflict)
       
       Warnings (MEDIUM):
       - SEC-02: VALID_OFFICER_CODES fallback emits warning but still uses defaults
       - SEC-06: Evidence files served without authentication (/uploads static mount)
       - CONFIG-03: ALLOWED_HOSTS=* in .env.example
       - DEPLOY-HTTPS: No TLS configuration found (requires human verification)
       
       Tests: pytest PASSED (42 tests)
       
       The application is NOT READY for production release.
       Shall I fix DEPLOY-CI first?"

User: "Yes, fix the CI issue first"

Bob:  "Creating .github/workflows/ci.yml with pytest and pip-audit steps..."
      [creates CI workflow file]
      "Done. Re-running audit..."
      [executes: python scripts/release_check.py --run-tests]
      "DEPLOY-CI is now PASSED. 
       Overall status updated to: READY WITH WARNINGS
       Remaining warnings: SEC-02, SEC-06, CONFIG-03, DEPLOY-HTTPS"
```

---

## Evidence-Based Principle

Every Bob action in this workflow is grounded in **actual repository evidence**:

- Bob does not claim a finding is resolved without re-running the check
- Bob does not invent CVEs — it reports exactly what pip-audit returns
- Bob does not mark tests as passing unless `pytest` actually ran with exit code 0
- Bob acknowledges when checks cannot be performed ("REQUIRES_HUMAN_VERIFICATION")

This makes the audit defensible and trustworthy for release decisions.
