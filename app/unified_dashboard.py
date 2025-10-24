#!/usr/bin/env python3
"""
Unified Dashboard Entry Point
This file exists to maintain compatibility with api/index.py imports
All main functionality is in app.py
"""

# Import everything from the main application
from app import *

# Ensure the Flask app is available for import
from app import app

# Export analytics engine for any code that needs it
from app import analytics

if __name__ == '__main__':
    # Run the application (delegated to app.py)
    from app import app
    import os
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 