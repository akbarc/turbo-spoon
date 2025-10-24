#!/usr/bin/env python3
"""
Working database connection for Tailscale remote access
Uses the exact approach that works with direct pymssql
"""

import pymssql
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

# Set TDS version globally
os.environ['TDSVER'] = '7.0'

def get_working_connection():
    """Get a working database connection using direct pymssql"""
    try:
        conn = pymssql.connect(
            server='10.1.10.105',
            user='amchranya',
            password='2000Akbar!',
            database='GAWDB',
            tds_version='7.0',
            timeout=30,
            login_timeout=10
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def execute_working_query(query, params=None):
    """Execute query using working connection approach"""
    conn = get_working_connection()
    if not conn:
        raise Exception("Could not connect to database")
    
    try:
        cursor = conn.cursor(as_dict=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        df = pd.DataFrame(results)
        return df
        
    finally:
        conn.close()

# Test function
def test_working_connection():
    """Test the working connection"""
    try:
        result = execute_working_query("SELECT COUNT(*) as count FROM [dbo].[Transaction]")
        print(f"✅ Working connection test: {result.iloc[0]['count']} transactions")
        return True
    except Exception as e:
        print(f"❌ Working connection failed: {e}")
        return False

if __name__ == "__main__":
    test_working_connection()
