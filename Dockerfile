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

# Source code — busts cache on every change, but BGE-M3 layer above is preserved.
COPY . .

EXPOSE 8000
ENV SAGE_WARMUP_BGE=1
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
