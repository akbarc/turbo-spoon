#!/usr/bin/env python3
"""
Test the GP_Daily_Summary table
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
    'timeout': 10,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

print("="*60)
print("Testing GP_Daily_Summary Table")
print("="*60)

# 1. Check if table exists and has data
print("\n1. Check table status")
cursor.execute("SELECT COUNT(*) as row_count FROM GP_Daily_Summary")
result = cursor.fetchone()
print(f"   Total rows: {result['row_count']:,}")

if result['row_count'] == 0:
    print("   ⚠️  Table is empty! Need to populate it.")
    print("   Run: EXEC sp_UpdateGPDailySummary '2025-10-01', '2025-10-15'")
else:
    # 2. Check date range
    print("\n2. Check date range")
    cursor.execute("""
        SELECT
            MIN(BusinessDate) as earliest,
            MAX(BusinessDate) as latest
        FROM GP_Daily_Summary
    """)
    result = cursor.fetchone()
    print(f"   Earliest: {result['earliest']}")
    print(f"   Latest: {result['latest']}")

    # 3. Get today's categories (SHOULD BE INSTANT!)
    print("\n3. Get today's category GP (should be INSTANT!)")
    today = datetime.now().date()

    try:
        cursor.execute("""
            SELECT
                CategoryName,
                Revenue,
                COGS,
                ExciseTax,
                GrossProfit,
                ItemCount
            FROM GP_Daily_Summary
            WHERE BusinessDate = %s
            ORDER BY GrossProfit DESC
        """, (today,))

        categories = cursor.fetchall()
        if categories:
            print(f"   ✅ INSTANT! Found {len(categories)} categories for {today}")
            print("\n   Top 5 Categories by GP:")
            for i, cat in enumerate(categories[:5], 1):
                gp_margin = (cat['GrossProfit'] / cat['Revenue'] * 100) if cat['Revenue'] > 0 else 0
                print(f"      {i}. {cat['CategoryName']}")
                print(f"         Revenue: ${cat['Revenue']:,.2f}")
                print(f"         GP: ${cat['GrossProfit']:,.2f} ({gp_margin:.1f}%)")
        else:
            print(f"   ⚠️  No data for {today}")
            print("   Need to update: EXEC sp_UpdateGPDailySummary")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. Get last 7 days aggregated
    print("\n4. Get last 7 days aggregated")
    week_ago = today - timedelta(days=7)

    try:
        cursor.execute("""
            SELECT
                CategoryName,
                SUM(Revenue) as Revenue,
                SUM(GrossProfit) as GrossProfit,
                SUM(ItemCount) as ItemCount
            FROM GP_Daily_Summary
            WHERE BusinessDate BETWEEN %s AND %s
            GROUP BY CategoryName
            ORDER BY GrossProfit DESC
        """, (week_ago, today))

        categories = cursor.fetchall()
        print(f"   ✅ INSTANT! Top 3 categories (last 7 days):")
        for i, cat in enumerate(categories[:3], 1):
            print(f"      {i}. {cat['CategoryName']}: ${cat['GrossProfit']:,.2f}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

cursor.close()
conn.close()

print("\n" + "="*60)
print("Test complete!")
