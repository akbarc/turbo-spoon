#!/usr/bin/env python3
"""
Investigate why some categories have negative GP
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

today = datetime.now().date()

print("="*60)
print("Investigating Negative Gross Profit Categories")
print("="*60)

# 1. Find all categories with negative GP today
print(f"\n1. Categories with NEGATIVE GP on {today}:")
cursor.execute("""
    SELECT
        CategoryName,
        Revenue,
        COGS,
        ExciseTax,
        GrossProfit,
        ItemCount,
        TransactionCount
    FROM GP_Daily_Summary
    WHERE BusinessDate = %s
    AND GrossProfit < 0
    ORDER BY GrossProfit ASC
""", (today,))

negative_cats = cursor.fetchall()

if negative_cats:
    print(f"\n   Found {len(negative_cats)} categories with negative GP:\n")
    for cat in negative_cats:
        print(f"   📊 {cat['CategoryName']}")
        print(f"      Revenue:    ${cat['Revenue']:,.2f}")
        print(f"      COGS:       ${cat['COGS']:,.2f}")
        print(f"      Excise Tax: ${cat['ExciseTax']:,.2f}")
        print(f"      GP:         ${cat['GrossProfit']:,.2f} ⚠️ NEGATIVE")
        print(f"      Items:      {cat['ItemCount']}")
        print(f"      Trans:      {cat['TransactionCount']}")

        # Calculate what's eating into profit
        if cat['Revenue'] != 0:
            cogs_percent = (cat['COGS'] / abs(cat['Revenue'])) * 100
            excise_percent = (cat['ExciseTax'] / abs(cat['Revenue'])) * 100
            print(f"      COGS %:     {cogs_percent:.1f}%")
            print(f"      Excise %:   {excise_percent:.1f}%")
        print()
else:
    print("   ✅ No categories with negative GP found!")

# 2. Look at individual transactions for one problematic category
if negative_cats:
    problem_cat = negative_cats[0]['CategoryName']
    print(f"\n2. Sample transactions for '{problem_cat}':")

    cursor.execute("""
        SELECT TOP 10
            te.TransactionNumber,
            te.Quantity,
            te.Price as UnitPrice,
            te.Cost as UnitCost,
            (te.Price * te.Quantity) as Revenue,
            (te.Cost * te.Quantity) as COGS,
            COALESCE(pe.PriceC, 0) as ExciseTax,
            (te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0) as GP,
            i.Description as ItemName
        FROM [dbo].[TransactionEntry] te
        INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
        INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
        LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
        WHERE CAST(te.TransactionTime AS DATE) = %s
        AND cat.Name = %s
        ORDER BY te.TransactionTime DESC
    """, (today, problem_cat))

    transactions = cursor.fetchall()

    print(f"\n   Found {len(transactions)} sample transactions:\n")
    for t in transactions:
        print(f"   Trans #{t['TransactionNumber']} - {t['ItemName']}")
        print(f"      Qty: {t['Quantity']}")
        print(f"      Unit Price: ${t['UnitPrice']:.2f}, Unit Cost: ${t['UnitCost']:.2f}")
        print(f"      Revenue: ${t['Revenue']:.2f}, COGS: ${t['COGS']:.2f}, Excise: ${t['ExciseTax']:.2f}")
        print(f"      GP: ${t['GP']:.2f}")

        # Identify the problem
        if t['Quantity'] < 0:
            print(f"      ⚠️  RETURN (negative quantity)")
        if t['UnitCost'] > t['UnitPrice']:
            print(f"      ⚠️  COST HIGHER THAN PRICE (selling at loss)")
        if t['GP'] < 0:
            print(f"      ⚠️  NEGATIVE GP")
        print()

# 3. Check for returns
print(f"\n3. Checking for RETURNS in negative GP categories:")
for cat in negative_cats[:3]:  # Check first 3
    cursor.execute("""
        SELECT
            COUNT(*) as total_items,
            SUM(CASE WHEN te.Quantity < 0 THEN 1 ELSE 0 END) as returns,
            SUM(CASE WHEN te.Quantity < 0 THEN te.Quantity ELSE 0 END) as return_qty,
            SUM(CASE WHEN te.Cost > te.Price THEN 1 ELSE 0 END) as sold_below_cost
        FROM [dbo].[TransactionEntry] te
        INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
        INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
        WHERE CAST(te.TransactionTime AS DATE) = %s
        AND cat.Name = %s
    """, (today, cat['CategoryName']))

    stats = cursor.fetchone()

    print(f"\n   {cat['CategoryName']}:")
    print(f"      Total items: {stats['total_items']}")
    print(f"      Returns: {stats['returns']} ({stats['return_qty']} items returned)")
    print(f"      Sold below cost: {stats['sold_below_cost']}")

cursor.close()
conn.close()

print("\n" + "="*60)
print("Investigation complete!")
