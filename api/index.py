#!/usr/bin/env python3
"""
Vercel API Entry Point for GA Dashboard
"""

import os
import sys
import logging
from flask import Flask, jsonify

# Set up logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    logger.info("Importing unified_dashboard...")
    from unified_dashboard import app
    logger.info("Successfully imported unified_dashboard")
    
    # Add serverless status endpoint
    @app.route('/api/serverless-status')
    def serverless_status():
        """Provide information about serverless deployment status"""
        try:
            from database_pymssql import PYMSSQL_AVAILABLE, DB_CONFIG
            
            return jsonify({
                "status": "success",
                "deployment_environment": "Vercel Serverless",
                "database_driver_available": PYMSSQL_AVAILABLE,
                "database_server": DB_CONFIG.get('server', 'Not configured'),
                "deployment_note": "Local network databases (like 10.1.10.105) cannot be accessed from Vercel's cloud environment",
                "recommendations": [
                    "For full functionality, run dashboard locally on your network",
                    "Consider using a cloud database (Azure SQL, AWS RDS, etc.) for Vercel deployment",
                    "Set up VPN tunnel for secure cloud-to-local database access"
                ] if not PYMSSQL_AVAILABLE else ["Database driver available - check network connectivity"]
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error checking serverless status: {e}"
            })
    
except Exception as e:
    logger.error(f"Failed to import unified_dashboard: {e}")
    # Create a simple Flask app as fallback
    app = Flask(__name__)
    
    @app.route('/')
    def fallback():
        return jsonify({
            "status": "error",
            "message": "Dashboard initialization failed",
            "error": str(e),
            "deployment_info": {
                "environment": "Vercel Serverless",
                "issue": "Dashboard modules failed to load",
                "recommendation": "Check logs for module import errors"
            }
        })

    @app.route('/api/serverless-status')
    def serverless_status():
        """Provide information about serverless deployment status"""
        return jsonify({
            "status": "error", 
            "deployment_environment": "Vercel Serverless",
            "database_driver_available": False,
            "error": "Dashboard modules failed to import",
            "recommendations": [
                "Check Vercel build logs for errors",
                "Verify all dependencies are in requirements.txt",
                "Consider running dashboard locally for full database access"
            ]
        })

# Export the Flask app for Vercel
logger.info("Exporting Flask app for Vercel") 