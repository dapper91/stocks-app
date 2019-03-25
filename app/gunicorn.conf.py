"""
gunicorn wsgi server configuration.
"""

import multiprocessing
import os

port = os.environ.get('PORT', '8080')
workers = os.environ.get('HTTP_WORKERS', multiprocessing.cpu_count())
