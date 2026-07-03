FROM python:3.12-slim

# libpq5: runtime library required by psycopg3 (pure-Python implementation).
# python:3.12-slim strips it; without it psycopg raises "libpq library not found".
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files first so this layer is cached until deps change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Bake BGE-M3 into the image before copying source code so the model layer
# survives source-only changes. local_files_only=True in skill_select.py
# picks up the model from HF_HOME at runtime.
ENV HF_HOME=/app/.cache/huggingface
RUN uv run python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('BAAI/bge-m3', revision='5617a9f61b028005a4858fdac845db406aefb181'); \
print('BGE-M3 baked in')"

# Build provenance + cache-bust. RAILWAY_GIT_COMMIT_SHA is baked so "which code is serving" is a
# curl (/health/version), never an inference chain across deploy IDs. This ARG also changes the
# build graph, forcing a rebuild of the source layer below — a defense against Railway's remote
# build cache reusing a stale code layer (observed 2026-07-03: new deploy IDs / SUCCESS / healthy /
# serving traffic, but running pre-#90 code, despite source changes).
ARG RAILWAY_GIT_COMMIT_SHA=unknown
ENV SAGE_BUILD_SHA=$RAILWAY_GIT_COMMIT_SHA

# Source code — busts cache on every change, but BGE-M3 layer above is preserved.
COPY . .

EXPOSE 8000
ENV SAGE_WARMUP_BGE=1
# Use Railway's $PORT if set, otherwise fall back to 8000 for local dev.
CMD ["sh", "-c", "uv run uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
