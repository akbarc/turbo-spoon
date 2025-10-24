#!/usr/bin/env python3
"""
Quick check of FRE costs and CIGAR GA excise
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
    'timeout': 10,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor(as_dict=True)

today = datetime.now().date()

print("="*60)
print("Quick Investigation: FRE and CIGAR GA")
print("="*60)

# 1. FRE COSTS from today's transactions
print("\n1. FRE Products - Actual Costs from Today's Sales:")
cursor.execute("""
    SELECT DISTINCT
        i.Description,
        te.Cost as SoldAtCost,
        te.Price as SoldAtPrice,
        (te.Price - te.Cost) as Margin
    FROM [dbo].[TransactionEntry] te
    INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
    WHERE CAST(te.TransactionTime AS DATE) = %s
    AND i.Description LIKE '%FRE%'
    AND cat.Name = 'NICOTINE POUCHES'
    ORDER BY i.Description
""", (today,))

fre = cursor.fetchall()
print(f"\n   FRE products sold today:\n")
for f in fre:
    status = "⚠️ LOSS" if f['Margin'] < 0 else "✅ OK"
    print(f"   {f['Description']}")
    print(f"      Price: ${f['SoldAtPrice']:.2f}, Cost: ${f['SoldAtCost']:.2f}, Margin: ${f['Margin']:.2f} {status}\n")

# 2. What excise tax types exist?
print("\n2. All Excise Tax Types:")
cursor.execute("""
    SELECT DISTINCT SubDescription3
    FROM PUExciseEntry
    WHERE SubDescription3 IS NOT NULL
    ORDER BY SubDescription3
""")

tax_types = cursor.fetchall()
for tt in tax_types:
    paid_or_coll = ""
    if 'PAID' in tt['SubDescription3']:
        paid_or_coll = " <- PRE-PAID (already in COGS)"
    elif 'COLL' in tt['SubDescription3']:
        paid_or_coll = " <- COLLECTED (added at POS)"

    print(f"   {tt['SubDescription3']}{paid_or_coll}")

# 3. CIGAR GA - Sample transactions with excise
print("\n3. CIGAR GA Sample - Today's Transactions:")
cursor.execute("""
    SELECT TOP 5
        i.Description,
        te.Quantity,
        te.Price as UnitPrice,
        te.Cost as UnitCost,
        pe.PriceC as ExciseTax,
        pe.SubDescription3 as TaxType
    FROM [dbo].[TransactionEntry] te
    INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
    LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
    WHERE CAST(te.TransactionTime AS DATE) = %s
    AND cat.Name = 'CIGAR GA'
    AND te.Quantity > 0
""", (today,))

cigars = cursor.fetchall()
print()
for c in cigars:
    print(f"   {c['Description']} (Qty: {c['Quantity']})")
    print(f"      Price: ${c['UnitPrice']:.2f}, Cost: ${c['UnitCost']:.2f}")
    if c['ExciseTax']:
        tax_note = ""
        if c['TaxType'] and 'PAID' in c['TaxType']:
            tax_note = " ⚠️ PRE-PAID (double counting!)"
        print(f"      Excise: ${c['ExciseTax']:.2f} ({c['TaxType']}){tax_note}")
    else:
        print(f"      Excise: None")
    print()

cursor.close()
conn.close()

print("="*60)
