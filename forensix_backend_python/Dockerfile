FROM python:3.11-slim

WORKDIR /app

# DEPLOY-04: Install only production (runtime) dependencies.
# Test-only packages (pytest, httpx) are in requirements-dev.txt — not installed here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

# DB-01 / DEPLOY-02 Fix: Use entrypoint.sh so Alembic migrations run before
# uvicorn starts. The entrypoint fails fast if migrations fail.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# DEPLOY-03: Run as a non-root application user.
# The uploads directory must be owned by this user so evidence files can be written.
RUN addgroup --system forensix \
 && adduser  --system --ingroup forensix --no-create-home forensix \
 && chown -R forensix:forensix /app /entrypoint.sh

USER forensix

EXPOSE 8000

# DEPLOY-05: Production should place this container behind an HTTPS reverse proxy
# (nginx, Caddy, AWS ALB, etc.). Port 8000 should NOT be directly internet-exposed.
ENTRYPOINT ["/entrypoint.sh"]
