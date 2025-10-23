"""
Health check endpoints for API monitoring and status.
"""
import sys
from pathlib import Path
from datetime import datetime
from flask import Blueprint, jsonify

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database.sql_server import db

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/health

    Health check endpoint that confirms API is running and checks database connectivity.

    Returns:
        JSON with status, timestamp, and database connection status

    Example:
        GET /api/health

        Response:
        {
            "status": "running",
            "timestamp": "2025-10-23T15:30:00.000Z",
            "database": {
                "sql_server": {
                    "status": "connected",
                    "message": "Connection successful"
                }
            },
            "version": "1.0.0"
        }
    """
    # Test SQL Server connection
    sql_connected, sql_message = db.test_connection()

    overall_status = "running" if sql_connected else "degraded"

    return jsonify({
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "database": {
            "sql_server": {
                "status": "connected" if sql_connected else "disconnected",
                "message": sql_message
            }
        },
        "version": "1.0.0"
    })

@health_bp.route('/ping', methods=['GET'])
def ping():
    """
    GET /api/ping

    Simple ping endpoint for load balancer health checks.
    Does not check database connectivity.

    Returns:
        JSON with status "ok"
    """
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})
