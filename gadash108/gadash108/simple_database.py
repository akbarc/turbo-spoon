#!/usr/bin/env python3
"""
Ultra-simple database connection for gadash108
Uses only the direct pymssql approach that works
"""

import pymssql
import pandas as pd
import os
import logging

# Set TDS version globally
os.environ['TDSVER'] = '7.0'

logger = logging.getLogger(__name__)

# Working connection parameters
SERVER = '10.1.10.105'
USER = 'amchranya'
PASSWORD = '2000Akbar!'
DATABASE = 'GAWDB'

def execute_query(query, params=None):
    """Execute query using direct pymssql connection - the only approach that works"""
    
    # Create fresh connection every time (the only way that works)
    conn = pymssql.connect(
        server=SERVER,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        tds_version='7.0',
        timeout=30,
        login_timeout=10
    )
    
    try:
        cursor = conn.cursor(as_dict=True)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        return pd.DataFrame(results)
        
    finally:
        conn.close()

def test_database():
    """Test database connection"""
    try:
        result = execute_query("SELECT COUNT(*) as count FROM [dbo].[Transaction]")
        count = result.iloc[0]['count']
        print(f"✅ Database test successful: {count} transactions")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()
