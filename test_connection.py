"""Quick test of SQL Server connection."""
import os
os.environ['TDSVER'] = '7.0'
import pymssql
import sys

try:
    print("Connecting to SQL Server...")
    conn = pymssql.connect(
        server='10.1.10.105',
        user='amchranya',
        password='2000Akbar!',
        database='GAWDB',
        tds_version='7.0',
        timeout=10,
        login_timeout=10
    )
    print("✅ Connected successfully!")
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()[0]
    print(f"SQL Server Version: {version[:100]}...")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
    sys.exit(1)
