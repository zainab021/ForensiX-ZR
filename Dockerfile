FROM python:3.11-slim

# Default environment variables for production/container deployments
ENV SECRET_KEY="forensix-zr-default-secret-key-change-in-production-12345" \
    DATABASE_URL="sqlite:///./forensix.db" \
    VALID_OFFICER_CODES="ZR-ADMIN-001,ZR-OFC-101,ZR-OFC-102" \
    CORS_ORIGINS="*" \
    ALLOWED_HOSTS="*" \
    SEED_DEMO_USERS="true" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30"

WORKDIR /app

# Install runtime dependencies
COPY forensix_backend_python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY forensix_backend_python/ .

RUN mkdir -p uploads

# Setup entrypoint script
COPY forensix_backend_python/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run as non-root user
RUN addgroup --system forensix \
 && adduser  --system --ingroup forensix --no-create-home forensix \
 && chown -R forensix:forensix /app /entrypoint.sh

USER forensix

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
