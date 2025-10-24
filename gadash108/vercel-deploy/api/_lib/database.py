"""
Simplified database connection for Vercel serverless functions
Each function creates a new connection (serverless pattern)
"""
import os
import pymssql
import pandas as pd
from datetime import datetime

class DatabaseConnection:
    """Lightweight database connection for serverless environment"""

    def __init__(self):
        self.connection = None

    def connect(self):
        """Create database connection"""
        try:
            self.connection = pymssql.connect(
                server=os.environ.get('DB_SERVER', '10.1.10.105'),
                user=os.environ.get('DB_USERNAME', 'amchranya'),
                password=os.environ.get('DB_PASSWORD'),
                database=os.environ.get('DB_DATABASE', 'GAWDB'),
                port=int(os.environ.get('DB_PORT', '1433')),
                timeout=20,
                login_timeout=10,
                tds_version=os.environ.get('TDS_VERSION', '7.0')
            )
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def execute_query(self, query, params=None):
        """Execute query and return DataFrame"""
        if not self.connection:
            if not self.connect():
                return pd.DataFrame()

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()

            return pd.DataFrame(results, columns=columns)
        except Exception as e:
            print(f"Query execution error: {e}")
            return pd.DataFrame()

    def close(self):
        """Close connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def quick_query(query, params=None):
    """
    Quick query execution for serverless functions
    Auto-manages connection lifecycle
    """
    with DatabaseConnection() as db:
        return db.execute_query(query, params)
