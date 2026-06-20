# ---- Build ----
FROM python:3.11-alpine AS builder

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Packages for installing Python deps
RUN apk add --no-cache \
    curl \
    build-base \
    gcc \
    musl-dev \
    libffi-dev

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy dependency
COPY pyproject.toml poetry.lock ./

# Install runtime deps
RUN poetry install --no-root --only main \
    && rm -rf $POETRY_CACHE_DIR

# Copy source
COPY payment_gateway_api payment_gateway_api
COPY main.py .

# ---- Runtime ----
FROM python:3.11-alpine AS runtime

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime packages
RUN apk add --no-cache libstdc++

# Create non-root user and log directory
RUN addgroup -S appgroup \
    && adduser -S appuser -G appgroup \
    && mkdir -p /var/log/payment-gateway \
    && chown -R appuser:appgroup /var/log/payment-gateway /app

# Copy installed packages and app from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER appuser

EXPOSE 8090

CMD ["python", "main.py"]