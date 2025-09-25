#!/usr/bin/python3

print("Content-Type: application/json")
print("Access-Control-Allow-Origin: *")
print("Access-Control-Allow-Methods: GET, POST, OPTIONS")
print("Access-Control-Allow-Headers: Content-Type, Authorization")
print()

import json
import datetime

# Simple health check response
response = {
    "status": "healthy",
    "timestamp": datetime.datetime.now().isoformat(),
    "service": "AlgoTrader Backend API - CGI Mode",
    "host": "inditehealthcare.com"
}

print(json.dumps(response, indent=2))