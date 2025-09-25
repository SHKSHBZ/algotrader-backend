"""
WSGI configuration for AlgoTrader API
This file is used by WSGI-compatible web servers to serve the application.
"""
import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set production environment
os.environ['FLASK_ENV'] = 'production'

from dashboard.app import app

# This is what the WSGI server will use
application = app

if __name__ == "__main__":
    application.run()