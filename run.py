#!/usr/bin/env python3
"""
Georgia Dashboard - Run Script
Usage: python run.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    # Get configuration - now reads from .env file
    port = int(os.environ.get('PORT', 5050))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'

    print(f"🚀 Starting Georgia Dashboard on {host}:{port}")
    print(f"📊 Debug mode: {debug}")
    print(f"🌐 Access at: http://localhost:{port}")

    app.run(
        host=host,
        port=port,
        debug=debug
    )