#!/usr/bin/env python3
"""
Working Database Connection for gadash108
Uses the ONLY approach that works: direct pymssql calls
"""

import pymssql
import pandas as pd
import os
import logging
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Critical: Set TDS version for SQL Server 2008 R2
os.environ['TDSVER'] = '7.0'

# Working connection parameters (hardcoded because they work)
SERVER = '10.1.10.105'  # Accessible via Tailscale subnet routing
USER = 'amchranya'
PASSWORD = '2000Akbar!'
DATABASE = 'GAWDB'

# Thread lock
db_lock = threading.Lock()

# Exception classes
class DatabaseConnectionError(Exception):
    pass

class DatabaseQueryError(Exception):
    pass

def get_connection():
    """Get a working database connection - the ONLY way that works"""
    return pymssql.connect(
        server=SERVER,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        tds_version='7.0',
        timeout=30,
        login_timeout=10
    )

def execute_query(query, params=None, description="Query"):
    """Execute query using working direct connection approach"""
    try:
        logger.debug(f"🔍 Executing: {description}")
        
        # Get fresh connection (only approach that works)
        conn = get_connection()
        
        try:
            cursor = conn.cursor(as_dict=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            df = pd.DataFrame(results)
            
            logger.debug(f"✅ {description} successful: {len(df)} rows")
            return df
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        raise DatabaseQueryError(f"Query execution failed: {e}")

class SQLServerConnection:
    """Simple wrapper that uses the working direct approach"""
    
    def __init__(self):
        self.connected = False
    
    def connect(self):
        """Test if we can connect"""
        try:
            conn = get_connection()
            conn.close()
            self.connected = True
            logger.info("✅ Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.connected = False
            return False
    
    def execute_query(self, query, params=None, description="Query"):
        """Execute query using working approach"""
        return execute_query(query, params, description)
    
    def close(self):
        """No-op since we use fresh connections"""
        pass

# Decorator for thread-safe operations
def with_db_lock(func):
    def wrapper(*args, **kwargs):
        with db_lock:
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Test the connection
if __name__ == "__main__":
    print("🧪 Testing gadash108 database...")
    
    try:
        result = execute_query("SELECT COUNT(*) as count FROM [dbo].[Transaction]")
        count = result.iloc[0]['count']
        print(f"✅ SUCCESS: {count} transactions in database")
        
        # Test class wrapper
        db = SQLServerConnection()
        if db.connect():
            print("✅ Class wrapper also works!")
        else:
            print("❌ Class wrapper failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")