"""
Health check endpoint
GET /api/health
"""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import sys
import os

# Add _lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_lib'))

from database import DatabaseConnection
from utils import json_response, error_response

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check"""
        try:
            # Test database connection
            with DatabaseConnection() as db:
                result = db.execute_query("SELECT @@VERSION as version, DB_NAME() as database")

                if not result.empty:
                    response_data = {
                        'status': 'healthy',
                        'timestamp': datetime.now().isoformat(),
                        'database': {
                            'connected': True,
                            'database': result.iloc[0]['database'] if 'database' in result.columns else 'Unknown',
                            'version': str(result.iloc[0]['version'])[:50] if 'version' in result.columns else 'Unknown'
                        }
                    }
                    response = json_response(response_data, 200)
                else:
                    response = error_response('Database query returned no results', 500)
        except Exception as e:
            response = error_response(f'Health check failed: {str(e)}', 500)

        self.send_response(response['statusCode'])
        for key, value in response['headers'].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response['body'].encode())
        return
