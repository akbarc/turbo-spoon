#!/usr/bin/env python3
import os
os.environ['TDSVER'] = '7.0'

# Test 1: Direct import and connect
print("Test 1: Direct pymssql")
import pymssql
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=30,
    login_timeout=10
)
print("✅ Direct pymssql works!")
conn.close()

# Test 2: Import module then connect
print("\nTest 2: After importing database_pymssql module")
import database_pymssql

conn2 = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=30,
    login_timeout=10
)
print("✅ Still works after importing module!")
conn2.close()
