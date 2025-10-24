#!/usr/bin/env python3
"""
Check if the indexes were created on base tables
"""
import os
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 10,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

print("Checking for indexes on TransactionEntry and Transaction tables...\n")

# Check indexes on TransactionEntry
cursor.execute("""
    SELECT
        i.name as index_name,
        t.name as table_name,
        COL_NAME(ic.object_id, ic.column_id) as column_name
    FROM sys.indexes i
    INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    INNER JOIN sys.tables t ON i.object_id = t.object_id
    WHERE t.name IN ('TransactionEntry', 'Transaction')
    AND i.name LIKE '%TransactionTime%' OR i.name LIKE '%CustomerID%' OR i.name LIKE '%vw_Transaction%'
    ORDER BY t.name, i.name
""")

results = cursor.fetchall()

if results:
    print("✅ Found related indexes:")
    for row in results:
        print(f"  {row['table_name']}.{row['column_name']} - Index: {row['index_name']}")
else:
    print("⚠️  No GP-related indexes found")

# Check existing indexes on TransactionEntry
print("\n" + "="*60)
print("All indexes on TransactionEntry:")
cursor.execute("""
    SELECT
        i.name as index_name,
        i.type_desc,
        COL_NAME(ic.object_id, ic.column_id) as column_name
    FROM sys.indexes i
    INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    INNER JOIN sys.tables t ON i.object_id = t.object_id
    WHERE t.name = 'TransactionEntry'
    ORDER BY i.name, ic.key_ordinal
""")

results = cursor.fetchall()
for row in results:
    print(f"  {row['index_name']} ({row['type_desc']}): {row['column_name']}")

cursor.close()
conn.close()
