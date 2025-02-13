import multiprocessing
import os

# Bind to port provided by Render
port = int(os.environ.get("PORT", "10000"))
bind = f"0.0.0.0:{port}"

# Worker configuration
workers = 1  # Réduire le nombre de workers pour Render
worker_class = "gthread"  # Utiliser gthread au lieu de sync
threads = 2
worker_tmp_dir = '/tmp'

# Timeouts
timeout = 120
graceful_timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "debug"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Process naming
proc_name = "hiconvert"

# Server mechanics
preload_app = True
reload = False  # Désactiver le rechargement en production
daemon = False

# Limits
worker_connections = 1000
limit_request_line = 4096
max_requests = 1000
max_requests_jitter = 50

# Server Hooks
def on_starting(server):
    print(f"Starting Gunicorn server on {bind}")

def on_reload(server):
    print("Reloading Gunicorn server")

def post_fork(server, worker):
    print(f"Worker spawned (pid: {worker.pid})")
