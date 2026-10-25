import os

bind = f"[::]:{os.getenv('PORT', '5000')}"
accesslog = "-"
access_log_format = "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s in %(M)sms"  # noqa: E501

# One process per core: each one runs the models with MODEL_THREADS threads (1 by default).
workers = int(os.getenv("GUNICORN_WORKERS", 1))
threads = 1

timeout = int(os.getenv("REQ_TIMEOUT", 300))
