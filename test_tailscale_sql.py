#!/usr/bin/env python3
"""Test SQL Server connection via Tailscale"""
import pymssql
import os

# Set TDS version
os.environ['TDSVER'] = '7.0'

print("Testing SQL Server connection via Tailscale...")
print(f"Server: 100.84.221.9")
print(f"Port: 1433")
print(f"Database: GAWDB")
print(f"User: amchranya")
print()

try:
    print("Attempting connection...")
    conn = pymssql.connect(
        server='100.84.221.9',
        user='amchranya',
        password='2000Akbar!',
        database='GAWDB',
        port=1433,
        tds_version='7.0',
        timeout=15,
        login_timeout=10
    )

    print("✅ Connection successful!")

    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
    result = cursor.fetchone()

    print(f"\n📊 Server Info:")
    print(f"   Version: {result[0][:50]}...")
    print(f"   Server: {result[1]}")
    print(f"   Database: {result[2]}")

    cursor.close()
    conn.close()

    print("\n✅ All tests passed!")

except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print(f"\nError type: {type(e).__name__}")
