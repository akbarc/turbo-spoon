"""
Simple test endpoint - No database required
GET /api/test
"""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import platform
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Simple test endpoint"""
        try:
            response_data = {
                'success': True,
                'message': 'API is working!',
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'python_version': platform.python_version(),
                    'platform': platform.platform(),
                    'vercel_env': os.environ.get('VERCEL_ENV', 'local'),
                    'vercel_region': os.environ.get('VERCEL_REGION', 'unknown')
                },
                'test_results': {
                    'api_routing': 'OK',
                    'json_serialization': 'OK',
                    'environment_variables': 'OK' if os.environ.get('VERCEL_ENV') else 'MISSING',
                }
            }

            response = {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps(response_data, indent=2)
            }
        except Exception as e:
            response = {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            }

        self.send_response(response['statusCode'])
        for key, value in response['headers'].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response['body'].encode())
        return

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return
