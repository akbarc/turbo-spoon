#!/usr/bin/env python3
"""
Investigate FRE costs and CIGAR GA excise tax (might be pre-paid)
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
print("Investigating FRE Costs and CIGAR GA Excise Tax")
print("="*60)

# 1. FRE Product Costs
print("\n1. FRE NICOTINE POUCH Products - Cost Analysis:")
cursor.execute("""
    SELECT
        i.ItemLookupCode,
        i.Description,
        i.Cost,
        i.Price,
        (i.Price - i.Cost) as Margin,
        CASE
            WHEN i.Price > 0 THEN ((i.Price - i.Cost) / i.Price * 100)
            ELSE 0
        END as MarginPercent
    FROM Item i
    INNER JOIN Category cat ON i.CategoryID = cat.ID
    WHERE i.Description LIKE '%FRE%'
    AND cat.Name = 'NICOTINE POUCHES'
    ORDER BY i.Description
""")

fre_products = cursor.fetchall()
print(f"\n   Found {len(fre_products)} FRE products:\n")
for p in fre_products:
    margin_indicator = "✅" if p['Margin'] > 0 else "⚠️ LOSS"
    print(f"   {p['Description']}")
    print(f"      Code: {p['ItemLookupCode']}")
    print(f"      Price: ${p['Price']:.2f}, Cost: ${p['Cost']:.2f}")
    print(f"      Margin: ${p['Margin']:.2f} ({p['MarginPercent']:.1f}%) {margin_indicator}")
    print()

# 2. CIGAR GA - Sample Transactions
print("\n2. CIGAR GA Transactions - Checking Excise Tax:")
cursor.execute("""
    SELECT TOP 10
        te.TransactionNumber,
        i.Description as ItemName,
        te.Quantity,
        te.Price as UnitPrice,
        te.Cost as UnitCost,
        (te.Price * te.Quantity) as Revenue,
        (te.Cost * te.Quantity) as COGS,
        pe.PriceC as ExciseTaxAmount,
        pe.SubDescription3 as ExciseTaxType,
        (te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0) as GP
    FROM [dbo].[TransactionEntry] te
    INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
    LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
    WHERE CAST(te.TransactionTime AS DATE) = %s
    AND cat.Name = 'CIGAR GA'
    ORDER BY te.TransactionTime DESC
""", (today,))

cigar_transactions = cursor.fetchall()
print(f"\n   Found {len(cigar_transactions)} CIGAR GA transactions today:\n")

for t in cigar_transactions:
    print(f"   Trans #{t['TransactionNumber']} - {t['ItemName']}")
    print(f"      Qty: {t['Quantity']}")
    print(f"      Unit Price: ${t['UnitPrice']:.2f}, Unit Cost: ${t['UnitCost']:.2f}")
    print(f"      Revenue: ${t['Revenue']:.2f}, COGS: ${t['COGS']:.2f}")

    if t['ExciseTaxAmount'] is not None:
        print(f"      Excise Tax: ${t['ExciseTaxAmount']:.2f} (Type: {t['ExciseTaxType']})")

        # Check if it's PAID or COLL
        if 'PAID' in str(t['ExciseTaxType']):
            print(f"      ⚠️  EXCISE TAX PRE-PAID (already in cost!)")
        elif 'COLL' in str(t['ExciseTaxType']):
            print(f"      ✅ EXCISE TAX COLLECTED (not in cost)")
    else:
        print(f"      No excise tax entry")

    print(f"      GP (after excise): ${t['GP']:.2f}")
    print()

# 3. Check excise tax types breakdown
print("\n3. All Excise Tax Types in Database:")
cursor.execute("""
    SELECT DISTINCT
        SubDescription3 as TaxType,
        COUNT(*) as Count
    FROM PUExciseEntry
    WHERE SubDescription3 IS NOT NULL
    GROUP BY SubDescription3
    ORDER BY Count DESC
""")

tax_types = cursor.fetchall()
print(f"\n   Found {len(tax_types)} different excise tax types:\n")
for tt in tax_types:
    paid_or_coll = ""
    if 'PAID' in str(tt['TaxType']):
        paid_or_coll = " (PRE-PAID - already in cost)"
    elif 'COLL' in str(tt['TaxType']):
        paid_or_coll = " (COLLECTED - added at sale)"

    print(f"      {tt['TaxType']}: {tt['Count']:,} transactions{paid_or_coll}")

# 4. CIGAR GA specific excise breakdown
print("\n4. CIGAR GA - Excise Tax Breakdown:")
cursor.execute("""
    SELECT
        pe.SubDescription3 as TaxType,
        COUNT(*) as Count,
        SUM(pe.PriceC) as TotalTax,
        AVG(pe.PriceC) as AvgTax
    FROM [dbo].[PUExciseEntry] pe
    INNER JOIN [dbo].[TransactionEntry] te ON pe.TransactionEntryID = te.ID
    INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
    INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
    WHERE CAST(te.TransactionTime AS DATE) = %s
    AND cat.Name = 'CIGAR GA'
    AND pe.SubDescription3 IS NOT NULL
    GROUP BY pe.SubDescription3
    ORDER BY TotalTax DESC
""", (today,))

cigar_excise = cursor.fetchall()
if cigar_excise:
    print(f"\n   Excise tax on CIGAR GA today:\n")
    for ce in cigar_excise:
        print(f"      {ce['TaxType']}: {ce['Count']} items, ${ce['TotalTax']:.2f} total, ${ce['AvgTax']:.2f} avg")
else:
    print("\n   No excise tax entries found for CIGAR GA")

# 5. Sample CIGAR GA items - what's the actual cost structure?
print("\n5. CIGAR GA Items - Cost Structure in Item Master:")
cursor.execute("""
    SELECT TOP 10
        i.ItemLookupCode,
        i.Description,
        i.Cost,
        i.Price,
        (i.Price - i.Cost) as Margin,
        CASE
            WHEN i.Price > 0 THEN ((i.Price - i.Cost) / i.Price * 100)
            ELSE 0
        END as MarginPercent
    FROM Item i
    INNER JOIN Category cat ON i.CategoryID = cat.ID
    WHERE cat.Name = 'CIGAR GA'
    ORDER BY i.Description
""")

cigar_items = cursor.fetchall()
print(f"\n   Sample CIGAR GA items from master:\n")
for ci in cigar_items:
    print(f"   {ci['Description']}")
    print(f"      Price: ${ci['Price']:.2f}, Cost: ${ci['Cost']:.2f}")
    print(f"      Margin before excise: ${ci['Margin']:.2f} ({ci['MarginPercent']:.1f}%)")
    print()

cursor.close()
conn.close()

print("="*60)
print("Investigation complete!")
print("\nKEY QUESTION: If CIGAR GA has 'PAID' excise tax,")
print("that means the excise is ALREADY IN the COGS,")
print("so we shouldn't subtract it again from GP!")
