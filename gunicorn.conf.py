workers = 1
worker_class = 'gthread'
threads = 2
worker_tmp_dir = '/dev/shm'
worker_max_requests = 1000
worker_max_requests_jitter = 50
timeout = 600  # Augmenté à 10 minutes
graceful_timeout = 300
keep_alive = 5
bind = "0.0.0.0:10000"
max_requests = 1000
max_requests_jitter = 50
preload_app = True
# Configuration de la mémoire
worker_connections = 1000
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
