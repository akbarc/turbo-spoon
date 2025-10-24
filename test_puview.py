#!/usr/bin/env python3
"""
Test the existing PUVIEWEXCISETRANSACTION view
"""
import os
from datetime import datetime, timedelta
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 30,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

print("Testing PUVIEWEXCISETRANSACTION view...\n")

# Check if view exists
cursor.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.VIEWS
    WHERE TABLE_NAME = 'PUVIEWEXCISETRANSACTION'
""")

result = cursor.fetchone()
if not result:
    print("❌ PUVIEWEXCISETRANSACTION view does not exist!")
    cursor.close()
    conn.close()
    exit(1)

print("✅ PUVIEWEXCISETRANSACTION exists")

# Get structure
print("\nView columns:")
cursor.execute("""
    SELECT TOP 1 *
    FROM PUVIEWEXCISETRANSACTION
""")
row = cursor.fetchone()
if row:
    for key in row.keys():
        print(f"  - {key}")

# Test aggregation for TODAY only (should be fast)
print("\n" + "="*60)
print("Testing TODAY's data aggregation...")
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

try:
    cursor.execute("""
        SELECT
            COUNT(*) as row_count,
            SUM(PRICE * QUANTITY) as total_revenue,
            SUM(COST * QUANTITY) as total_cogs,
            SUM(COALESCE(PUEPRICEC, 0)) as total_excise_tax
        FROM PUVIEWEXCISETRANSACTION
        WHERE TRANSACTIONTIME >= %s
    """, (today,))
    result = cursor.fetchone()
    print(f"✅ Query completed!")
    print(f"  Rows: {result['row_count']:,}")
    print(f"  Revenue: ${result['total_revenue'] or 0:,.2f}")
    print(f"  COGS: ${result['total_cogs'] or 0:,.2f}")
    print(f"  Excise Tax: ${result['total_excise_tax'] or 0:,.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

cursor.close()
conn.close()
