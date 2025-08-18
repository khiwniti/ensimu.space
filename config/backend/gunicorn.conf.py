# Gunicorn configuration for EnsimuSpace production backend

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv("BACKEND_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
timeout = 30
keepalive = 2
graceful_timeout = 30

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "ensimu-backend"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if enabled)
keyfile = os.getenv("SSL_KEY_PATH")
certfile = os.getenv("SSL_CERT_PATH")
ca_certs = os.getenv("SSL_CA_BUNDLE_PATH")
ssl_version = 2  # Use latest SSL version
cert_reqs = 0    # No client certificate required
suppress_ragged_eofs = True

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
preload_app = True
sendfile = True
reuse_port = True

# Memory optimization
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"

# Monitoring
statsd_host = os.getenv("STATSD_HOST")
statsd_prefix = "ensimu.backend"

def when_ready(server):
    """Called when the server is ready to receive connections."""
    server.log.info("EnsimuSpace backend server is ready")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker received SIGINT or SIGQUIT")

def pre_fork(server, worker):
    """Called before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called after a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called after a worker has been initialized."""
    worker.log.info("Worker initialized")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT")

def pre_exec(server):
    """Called before a new master process is forked."""
    server.log.info("Forked child, re-executing")

def pre_request(worker, req):
    """Called before a request is processed."""
    worker.log.debug("%s %s", req.method, req.path)

def post_request(worker, req, environ, resp):
    """Called after a request has been processed."""
    pass

def child_exit(server, worker):
    """Called when a worker is exiting."""
    server.log.info("Worker exited (pid: %s)", worker.pid)

def worker_exit(server, worker):
    """Called when a worker is exiting."""
    server.log.info("Worker exited (pid: %s)", worker.pid)

def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers is changed."""
    server.log.info("Number of workers changed from %s to %s", old_value, new_value)

def on_exit(server):
    """Called when gunicorn is about to exit."""
    server.log.info("EnsimuSpace backend server is shutting down")

def on_reload(server):
    """Called when gunicorn is reloaded."""
    server.log.info("EnsimuSpace backend server is reloading")

# Environment-specific configurations
if os.getenv("ENVIRONMENT") == "production":
    # Production-specific settings
    workers = max(workers, 4)  # Minimum 4 workers in production
    worker_connections = 1000
    timeout = 30
    keepalive = 2
elif os.getenv("ENVIRONMENT") == "development":
    # Development-specific settings
    workers = 1
    reload = True
    timeout = 120
    loglevel = "debug"