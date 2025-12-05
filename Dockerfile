FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY slurm_exporter ./slurm_exporter
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

ARG SLURM_TAG=slurm-25-05-3-1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bzip2 \
    gcc \
    make \
    munge \
    libmunge-dev \
    libmunge2 \
    autoconf \
    automake \
    libtool \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${SLURM_TAG} https://github.com/SchedMD/slurm.git /tmp/slurm \
    && cd /tmp/slurm \
    && ./configure --prefix=/usr --sysconfdir=/etc/slurm \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/slurm

RUN apt-get purge -y gcc make git autoconf automake libtool && apt-get autoremove -y

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/slurm_exporter /app/slurm_exporter

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 9341

ENTRYPOINT ["slurm-exporter"]
