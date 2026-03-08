# Multi-stage Python build for FLUXION Backend
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install postgres client (for alembic/migrations) and curl (for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure scripts are executable
RUN chmod +x scripts/*.py

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# The CMD should be overridden by docker-compose for api vs bridge
CMD ["python", "-m", "niveau5.src.api"]
