#!/usr/bin/env python3
"""
Try querying categories directly from base tables
"""
import os
from datetime import datetime
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

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

print("="*60)
print("Testing Direct Table Queries for Categories")
print("="*60)

# Try 1: Query TransactionEntry + Category directly
print("\n1. Query TransactionEntry with Category join (today only)")
try:
    cursor.execute("""
        SELECT TOP 10
            cat.Name as CategoryName,
            SUM(te.Price * te.Quantity) as revenue,
            SUM(te.Cost * te.Quantity) as cogs,
            SUM(COALESCE(pe.PriceC, 0)) as excise_tax,
            SUM((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) as gross_profit
        FROM [dbo].[TransactionEntry] te
        INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
        INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
        LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
        WHERE te.TransactionTime >= %s
        AND te.Quantity != 0
        GROUP BY cat.Name
        ORDER BY gross_profit DESC
    """, (today,))

    results = cursor.fetchall()
    if results:
        print(f"   ✅ SUCCESS! Got {len(results)} categories")
        print("\n   Top 5 Categories by GP:")
        for cat in results[:5]:
            gp_margin = (cat['gross_profit'] / cat['revenue'] * 100) if cat['revenue'] > 0 else 0
            print(f"      {cat['CategoryName']}: ${cat['gross_profit']:,.2f} ({gp_margin:.1f}%)")
    else:
        print("   ⚠️ Query succeeded but no results")

except Exception as e:
    print(f"   ❌ Error: {e}")

cursor.close()
conn.close()

print("\n" + "="*60)
print("Test complete!")
