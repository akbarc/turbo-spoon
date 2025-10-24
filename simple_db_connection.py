#!/usr/bin/env python3
"""
Simple database connection that works with Tailscale
"""

import pymssql
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

class SimpleDatabaseConnection:
    def __init__(self):
        self.connection = None
        # Set TDS version immediately
        os.environ['TDSVER'] = '7.0'
    
    def connect(self):
        """Connect using exact working parameters"""
        try:
            self.connection = pymssql.connect(
                server='10.1.10.105',
                user='amchranya',
                password='2000Akbar!',
                database='GAWDB',
                tds_version='7.0',
                timeout=30,
                login_timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def execute_query(self, query, params=None, description="Query"):
        """Execute query and return pandas DataFrame"""
        if not self.connection:
            raise Exception("Not connected to database")
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            return pd.DataFrame(results)
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

# Test the simple connection
if __name__ == "__main__":
    print("Testing simple database connection...")
    
    db = SimpleDatabaseConnection()
    if db.connect():
        print("✅ Simple connection works!")
        
        try:
            result = db.execute_query("SELECT COUNT(*) as count FROM [dbo].[Transaction]")
            print(f"✅ Query works: {result.iloc[0]['count']} total transactions")
        except Exception as e:
            print(f"❌ Query failed: {e}")
        
        db.close()
    else:
        print("❌ Simple connection failed")
