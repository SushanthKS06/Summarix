from app.core.config import Settings
import os

try:
    s = Settings(
        GROQ_API_KEY="test", 
        TELEGRAM_TOKEN="test", 
        REDIS_URL="redis://default:ASgyAAIncDIyNjM1MTM5ZGM1ZmU0NzczODRlZGE0M2JlMDNiODZlYXAyMTAyOTA@alert-caiman-10290.upstash.io:6379?ssl_cert_reqs=none",
        CELERY_BROKER_URL="redis://default:ASgyAAIncDIyNjM1MTM5ZGM1ZmU0NzczODRlZGE0M2JlMDNiODZlYXAyMTAyOTA@alert-caiman-10290.upstash.io:6379?ssl_cert_reqs=none",
        CELERY_RESULT_BACKEND="redis://default:ASgyAAIncDIyNjM1MTM5ZGM1ZmU0NzczODRlZGE0M2JlMDNiODZlYXAyMTAyOTA@alert-caiman-10290.upstash.io:6379?ssl_cert_reqs=none"
    )
    print("REDIS_URL:", s.REDIS_URL)
    print("CELERY_BROKER_URL:", s.CELERY_BROKER_URL)
    print("CELERY_RESULT_BACKEND:", s.CELERY_RESULT_BACKEND)
except Exception as e:
    print("Error:", e)
