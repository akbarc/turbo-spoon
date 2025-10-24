"""
Utility functions for API responses
"""
import json
from datetime import datetime
from decimal import Decimal

def decimal_default(obj):
    """JSON encoder for Decimal and datetime objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def json_response(data, status=200):
    """Create JSON response"""
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data, default=decimal_default)
    }

def error_response(message, status=500):
    """Create error response"""
    return json_response({
        'error': message,
        'timestamp': datetime.now().isoformat()
    }, status=status)

def success_response(data):
    """Create success response"""
    return json_response({
        'success': True,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }, status=200)
