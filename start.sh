#!/bin/bash
export HF_HUB_DISABLE_PROGRESS_BARS=1
export MALLOC_ARENA_MAX=2

# Start Celery worker in the background
celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=1 --max-tasks-per-child=1 &

# Start Uvicorn in the foreground
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
