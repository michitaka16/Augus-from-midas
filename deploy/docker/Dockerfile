FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/api/ apps/api/

# Install dependencies
RUN uv venv && uv sync --no-dev

# Copy application code
COPY conftest.py .
COPY .env.example .

# Run API server
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "midas_api"]
