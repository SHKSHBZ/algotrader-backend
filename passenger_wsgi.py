#!/usr/bin/python3
"""
WSGI entry point for Flask app on GoDaddy shared hosting
Configured for addon domain: inditehealthcare.com
"""
import sys
import os

# Add the application directory to Python path for addon domain
sys.path.insert(0, '/home/skshanawaz21/public_html/inditehealthcare.com/api')

# Set environment for shared hosting
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run()