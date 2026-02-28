#!/bin/bash
# Start Celery worker in the background
celery -A app.core.celery_app.celery_app worker --loglevel=info &

# Start Uvicorn in the foreground
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
