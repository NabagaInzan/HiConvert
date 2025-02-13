import multiprocessing
import os

# Bind to 0.0.0.0:$PORT
port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"

# Configuration du nombre de workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2
worker_tmp_dir = '/dev/shm'
worker_max_requests = 1000
worker_max_requests_jitter = 50

# Timeouts
timeout = 120
graceful_timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "debug"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# SSL configuration
keyfile = None
certfile = None

# Process Naming
proc_name = "hiconvert"

# Server Mechanics
preload_app = True
reload = True
daemon = False

# Server Hooks
def on_starting(server):
    print(f"Starting Gunicorn server on {bind}")

def on_reload(server):
    print("Reloading Gunicorn server")

def post_fork(server, worker):
    print(f"Worker spawned (pid: {worker.pid})")

# Configuration de la mémoire
worker_connections = 1000
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
