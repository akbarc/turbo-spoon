#!/usr/bin/env python3
"""
Investigate why category query is slow and find solutions
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
    'timeout': 60,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

print("="*60)
print("Investigation: Category Query Performance")
print("="*60)

# 1. Check how many categories exist
print("\n1. How many categories exist?")
cursor.execute("""
    SELECT COUNT(DISTINCT CNAME) as category_count
    FROM PUVIEWEXCISETRANSACTION
    WHERE CNAME IS NOT NULL
""")
result = cursor.fetchone()
print(f"   Total categories: {result['category_count']}")

# 2. Check row count for today
print("\n2. How many rows for today?")
cursor.execute("""
    SELECT COUNT(*) as row_count
    FROM PUVIEWEXCISETRANSACTION
    WHERE TRANSACTIONTIME >= %s
""", (today,))
result = cursor.fetchone()
print(f"   Today's rows: {result['row_count']:,}")

# 3. Try getting just category names for today (no aggregation)
print("\n3. Can we get category list for today? (5 sec timeout)")
try:
    cursor.execute("""
        SELECT DISTINCT CNAME
        FROM PUVIEWEXCISETRANSACTION
        WHERE TRANSACTIONTIME >= %s
        AND CNAME IS NOT NULL
    """, (today,))
    categories = cursor.fetchall()
    print(f"   ✅ Found {len(categories)} categories today")
    for i, cat in enumerate(categories[:5]):
        print(f"      {i+1}. {cat['CNAME']}")
    if len(categories) > 5:
        print(f"      ... and {len(categories) - 5} more")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 4. Try aggregation on JUST today's data with short timeout
print("\n4. Try aggregation with FAST approach (10 sec timeout)")
try:
    # Use a CTE to filter first, then aggregate
    cursor.execute("""
        SELECT TOP 10
            CNAME as CategoryName,
            SUM(PRICE * QUANTITY) as revenue,
            SUM((PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)) as gross_profit
        FROM PUVIEWEXCISETRANSACTION
        WHERE TRANSACTIONTIME >= %s
        AND CNAME IS NOT NULL
        GROUP BY CNAME
        ORDER BY gross_profit DESC
    """, (today,))
    results = cursor.fetchall()
    if results:
        print(f"   ✅ SUCCESS! Got {len(results)} categories")
        for cat in results[:3]:
            print(f"      {cat['CategoryName']}: ${cat['gross_profit']:,.2f}")
    else:
        print("   ⚠️ Query succeeded but no results")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Check if there's a Category table we can use instead
print("\n5. Check if Category table exists")
cursor.execute("""
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Category'
""")
result = cursor.fetchone()
if result['count'] > 0:
    print("   ✅ Category table exists!")
    cursor.execute("SELECT TOP 5 ID, Name FROM Category")
    cats = cursor.fetchall()
    print("   Sample categories:")
    for cat in cats:
        print(f"      {cat['ID']}: {cat['Name']}")
else:
    print("   ❌ No Category table found")

cursor.close()
conn.close()

print("\n" + "="*60)
print("Investigation complete!")
