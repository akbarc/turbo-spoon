"""
Executive Summary API
GET /api/executive-summary
"""
from http.server import BaseHTTPRequestHandler
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add _lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '_lib'))

from database import DatabaseConnection
from utils import json_response, error_response, success_response

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Get executive summary metrics"""
        try:
            with DatabaseConnection() as db:
                # Today's sales
                today_query = """
                SELECT
                    ISNULL(SUM(extPrice), 0) as today_sales
                FROM puViewDailySales
                WHERE CONVERT(date, tranDate) = CONVERT(date, GETDATE())
                """
                today_result = db.execute_query(today_query)
                today_sales = float(today_result.iloc[0]['today_sales']) if not today_result.empty else 0

                # YTD Revenue
                ytd_query = """
                SELECT
                    ISNULL(SUM(extPrice), 0) as ytd_revenue
                FROM puViewDailySales
                WHERE YEAR(tranDate) = YEAR(GETDATE())
                """
                ytd_result = db.execute_query(ytd_query)
                ytd_revenue = float(ytd_result.iloc[0]['ytd_revenue']) if not ytd_result.empty else 0

                # Customer count
                customer_query = """
                SELECT COUNT(DISTINCT custno) as customer_count
                FROM puViewDailySales
                WHERE tranDate >= DATEADD(day, -30, GETDATE())
                """
                customer_result = db.execute_query(customer_query)
                customer_count = int(customer_result.iloc[0]['customer_count']) if not customer_result.empty else 0

                # AR Balance
                ar_query = """
                SELECT ISNULL(SUM(balance), 0) as ar_balance
                FROM arcust
                WHERE balance > 0
                """
                ar_result = db.execute_query(ar_query)
                ar_balance = float(ar_result.iloc[0]['ar_balance']) if not ar_result.empty else 0

                data = {
                    'today_sales': today_sales,
                    'ytd_revenue': ytd_revenue,
                    'customer_count': customer_count,
                    'ar_balance': ar_balance,
                    'profit_margin': 0.234,  # Placeholder
                    'timestamp': datetime.now().isoformat()
                }

                response = success_response(data)
        except Exception as e:
            response = error_response(f'Failed to fetch executive summary: {str(e)}', 500)

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
