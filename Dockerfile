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

# Bake the V2 cross-encoder reranker (bge-reranker-v2-m3, ~2.2GB) at the PINNED revision the gate
# validated, so prod loads it offline (local_files_only in skill_rerank_model._load) with no runtime
# HF download. Separate layer after BGE-M3 so each model layer caches independently. Canonical
# AutoModelForSequenceClassification (the reranker HEAD) — NOT sentence_transformers.CrossEncoder
# (headless-load bug); the startup head-control (_warmup_reranker) asserts the head separates.
RUN uv run python -c "\
from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
r='953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'; \
AutoTokenizer.from_pretrained('BAAI/bge-reranker-v2-m3', revision=r); \
AutoModelForSequenceClassification.from_pretrained('BAAI/bge-reranker-v2-m3', revision=r); \
print('bge-reranker-v2-m3 baked in @', r)"

# Source code — busts cache on every change, but the model layers above are preserved.
COPY . .

EXPOSE 8000
ENV SAGE_WARMUP_BGE=1
# Use Railway's $PORT if set, otherwise fall back to 8000 for local dev.
CMD ["sh", "-c", "uv run uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
