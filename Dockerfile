FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY slurm_exporter ./slurm_exporter
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    slurm-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/slurm_exporter /app/slurm_exporter

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 9341

ENTRYPOINT ["slurm-exporter"]
