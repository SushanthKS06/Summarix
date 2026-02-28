from celery import Celery

broker_url = "rediss://default:ASgyAAIncDIyNjM1MTM5ZGM1ZmU0NzczODRlZGE0M2JlMDNiODZlYXAyMTAyOTA@alert-caiman-10290.upstash.io:6379?ssl_cert_reqs=none"
backend_url = "rediss://default:ASgyAAIncDIyNjM1MTM5ZGM1ZmU0NzczODRlZGE0M2JlMDNiODZlYXAyMTAyOTA@alert-caiman-10290.upstash.io:6379?ssl_cert_reqs=none"

app = Celery('test', broker=broker_url, backend=backend_url)

@app.task
def add(x, y):
    return x + y

if __name__ == '__main__':
    try:
        # Try to connect and send a task
        print("Sending task...")
        result = add.delay(4, 4)
        print("Task sent. ID:", result.id)
        print("Waiting for result...")
        # Since we don't have a worker running, we might not get a result quickly, 
        # but if we can publish it, broker connection works.
        # However, backend connection can be tested by accessing result backend properties
        backend = app.backend
        print("Backend client:", backend.client)
        print("Connection successful!")
    except Exception as e:
        print("Error:", e)
