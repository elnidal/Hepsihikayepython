import os
import multiprocessing

# Bind to the port provided by Render
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")

# Use multiple workers based on CPU cores
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# Use worker class based on environment variable
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")

# Timeout settings
timeout = 120
keepalive = 5

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 200

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Redirect stdout/stderr to log
capture_output = True
enable_stdio_inheritance = True

# Preload app for better performance
preload_app = True

# Set the process name
proc_name = "hepsihikaye"

# Graceful timeout
graceful_timeout = 30 