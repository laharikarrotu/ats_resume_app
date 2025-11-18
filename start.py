#!/usr/bin/env python3
"""
Railway startup script that reads PORT from environment variable.
"""
import os
import sys
import subprocess

# Get PORT from environment (Railway sets this automatically)
port = os.getenv("PORT", "8000")

# Start uvicorn with the port
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "src.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    str(port)
]

# Execute the command
sys.exit(subprocess.run(cmd).returncode)

