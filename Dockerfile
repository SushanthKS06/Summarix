FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for compiling extensions (like asyncpg, FAISS)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# configure pip to be more tolerant of slow downloads and avoid caching large wheels
ENV PIP_DEFAULT_TIMEOUT=1000 \
    PIP_NO_CACHE_DIR=1

RUN pip install \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    --default-timeout=1000 \
    --retries=10 \
    -r requirements.txt

# Pre-download SentenceTransformer model to speed up startup
RUN python -c "import os; os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'; from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-albert-small-v2')"

# Copy application files
COPY . .

# Set environment variables for memory and logs optimization
ENV HF_HUB_DISABLE_PROGRESS_BARS=1 \
    MALLOC_ARENA_MAX=2

# Expose FastAPI port
EXPOSE 8000

# Default command (can be overridden by Railway/docker-compose)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
