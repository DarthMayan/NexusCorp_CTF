"""
Gunicorn configuration for NEXUS Corp CTF
Optimized for handling concurrent attack traffic (brute-force, sqlmap, etc.)
"""

import multiprocessing

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
# More workers = more concurrent requests handled
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4

# Timeouts
timeout = 120          # Kill worker if it hangs for 2 min
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Preload app for shared memory (rate limiter)
preload_app = True
