from app.core.celery_app import celery_app
from celery.app.task import Task
import sys
import traceback

print("Broker URL:", celery_app.conf.broker_url)
print("Result Backend:", celery_app.conf.result_backend)

try:
    # Try to initialize the backend by accessing it
    backend = celery_app.backend
    print("Backend initialized successfully:", backend)
except Exception as e:
    print("Error initializing backend:", e)
    traceback.print_exc()

sys.path.insert(0, '/usr/local/lib/python3.11/site-packages')
try:
    from urllib.parse import urlparse
    print("PARSED BROKER:", urlparse(celery_app.conf.broker_url))
    print("PARSED BACKEND:", urlparse(celery_app.conf.result_backend))
except Exception:
    pass
