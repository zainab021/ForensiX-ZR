#!/bin/bash
# DB-01 / DEPLOY-02 Fix: Docker entrypoint that runs Alembic migrations before
# starting the application. Fails safely — the container exits with a non-zero
# code if migrations fail, preventing the application from starting against an
# out-of-date or broken schema.
#
# This replaces a bare `uvicorn` CMD so that every container restart also
# guarantees migrations are up to date without manual intervention.

set -e  # Exit immediately if any command returns a non-zero status

echo "[ForensiX] ============================================"
echo "[ForensiX] Starting ForensiX ZR Unit Backend"
echo "[ForensiX] ============================================"

echo "[ForensiX] Running Alembic database migrations..."
if ! alembic upgrade head; then
    echo "[ForensiX] ERROR: Alembic migration failed. Container will not start."
    echo "[ForensiX] Fix the migration error and redeploy."
    exit 1
fi
echo "[ForensiX] Migrations applied successfully."

echo "[ForensiX] Starting FastAPI application (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
