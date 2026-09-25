# Bob IDE Task Evidence — ForensiX-ZR Audit

This directory holds screenshots captured from actual IBM Bob IDE task sessions
that demonstrate the Release Readiness & Security Audit workflow.

## Required Evidence

Place actual IBM Bob IDE session screenshots here before submission.
**Do NOT create fake or fabricated screenshots.**

Each screenshot should show:
- The Bob task prompt and context
- The task running (tool calls, file reads, command execution)
- The task result or finding output

---

## Recommended File Names

| File | What to Capture |
|---|---|
| `task01_repository_analysis.png` | Bob reading the repo structure, listing files, understanding the architecture |
| `task02_audit_design.png` | Bob designing the audit workflow, identifying the parallel tasks |
| `task03_security_audit.png` | Security audit task: checking .env, docker-compose.yml, auth.py, demo users |
| `task04_configuration_audit.png` | Config audit: config.js localhost, CORS, ALLOWED_HOSTS, env vars |
| `task05_database_audit.png` | Database audit: SQLite fallback, Alembic migrations, create_all conflict |
| `task06_deployment_audit.png` | Deployment audit: Dockerfile, entrypoint.sh, CI/CD check, HTTPS |
| `task07_parallel_audit.png` | IBM Bob multi-task panel showing all 5 audit tasks running in parallel |
| `task08_report_generation.png` | Bob running the audit script, reading JSON output, generating report |

---

## How to Capture

1. Open ForensiX-ZR in IBM Bob IDE
2. Load the repository as Project Context
3. Enable Agent Mode
4. Run each audit task as described in `docs/bob-workflow.md`
5. Take a screenshot at the key moment for each task (see table above)
6. Save each screenshot with the filename from the table above
7. Place it in this directory (`bob_sessions/`)

---

## Notes

- Screenshots should be legible — capture at sufficient resolution
- Include both the prompt and the key output in each screenshot
- The parallel task panel screenshot (task07) is especially important for the
  IBM Bob 2.0 Hackathon judging criteria around parallel execution
- If running tasks sequentially rather than in parallel, note this in your submission

---

## Directory Contents

*(This README will remain. Actual screenshot files will be added here manually.)*
