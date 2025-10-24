#!/usr/bin/env python3
"""
Fix GP calculation to handle PAID vs COLL excise tax
PAID = already in COGS, don't subtract
COLL = collected at POS, subtract from GP
"""
import os
from datetime import datetime
os.environ['TDSVER'] = '7.0'
import pymssql

DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'sa',
    'password': 'Tech7World',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 300,
    'login_timeout': 10
}

conn = pymssql.connect(**DB_CONFIG)
cursor = conn.cursor()

today = datetime.now().date()

print("="*60)
print("Fixing Excise Tax Calculation")
print("="*60)
print("\nProblem: Pre-paid excise (PAID) was being double-counted")
print("Solution: Only subtract excise if it's COLLECTED (COLL)")
print()

# Step 1: Clear today's incorrect data
print("1. Clearing today's incorrect data...")
cursor.execute("DELETE FROM GP_Daily_Summary WHERE BusinessDate = %s", (today,))
conn.commit()
print(f"   ✅ Deleted old data for {today}")

# Step 2: Repopulate with CORRECT formula
print("\n2. Repopulating with CORRECT excise tax logic...")
print("   Formula: If excise type ends with 'PAID', don't subtract (already in COGS)")
print("            If excise type ends with 'COLL', subtract (collected at POS)")

query = """
INSERT INTO GP_Daily_Summary (
    BusinessDate,
    CategoryID,
    CategoryName,
    Revenue,
    COGS,
    ExciseTax,
    GrossProfit,
    TransactionCount,
    ItemCount
)
SELECT
    CAST(%s AS DATE) as BusinessDate,
    cat.ID as CategoryID,
    cat.Name as CategoryName,
    SUM(te.Price * te.Quantity) as Revenue,
    SUM(te.Cost * te.Quantity) as COGS,

    -- Only count COLLECTED excise tax (not PAID)
    SUM(CASE
        WHEN pe.SubDescription3 LIKE '%%COLL' THEN COALESCE(pe.PriceC, 0)
        ELSE 0
    END) as ExciseTax,

    -- CORRECT Gross Profit:
    -- Only subtract excise if it's COLLECTED (not if it's PAID)
    SUM(
        (te.Price * te.Quantity) -
        (te.Cost * te.Quantity) -
        CASE
            WHEN pe.SubDescription3 LIKE '%%COLL' THEN COALESCE(pe.PriceC, 0)
            ELSE 0
        END
    ) as GrossProfit,

    COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
    COUNT(*) as ItemCount
FROM [dbo].[TransactionEntry] te
INNER JOIN [dbo].[Item] i ON te.ItemID = i.ID
INNER JOIN [dbo].[Category] cat ON i.CategoryID = cat.ID
LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
WHERE CAST(te.TransactionTime AS DATE) = %s
AND te.Quantity != 0
GROUP BY cat.ID, cat.Name
"""

cursor.execute(query, (today, today))
row_count = cursor.rowcount
conn.commit()

print(f"   ✅ Inserted {row_count} category records with corrected GP")

# Step 3: Show the difference
print("\n3. Checking results - Previously negative categories:")

cursor.execute("""
    SELECT
        CategoryName,
        Revenue,
        COGS,
        ExciseTax,
        GrossProfit,
        CASE
            WHEN Revenue > 0 THEN (GrossProfit / Revenue * 100)
            ELSE 0
        END as GPMargin
    FROM GP_Daily_Summary
    WHERE BusinessDate = %s
    AND CategoryName IN ('CIGAR GA', 'T7 SMOKELESS GA', 'NICOTINE POUCHES', 'HOUSEHOLD GOODS')
    ORDER BY CategoryName
""", (today,))

results = cursor.fetchall()

print("\n   Updated GP for problem categories:\n")
for row in results:
    status = "✅ POSITIVE" if row[4] > 0 else "⚠️ Still negative"
    print(f"   {row[0]}")
    print(f"      Revenue:    ${row[1]:,.2f}")
    print(f"      COGS:       ${row[2]:,.2f}")
    print(f"      Excise Tax: ${row[3]:,.2f} (only COLLECTED)")
    print(f"      GP:         ${row[4]:,.2f} ({row[5]:.1f}%) {status}")
    print()

# Step 4: Overall totals
cursor.execute("""
    SELECT
        SUM(Revenue) as total_revenue,
        SUM(COGS) as total_cogs,
        SUM(ExciseTax) as total_excise,
        SUM(GrossProfit) as total_gp,
        CASE
            WHEN SUM(Revenue) > 0 THEN (SUM(GrossProfit) / SUM(Revenue) * 100)
            ELSE 0
        END as gp_margin
    FROM GP_Daily_Summary
    WHERE BusinessDate = %s
""", (today,))

totals = cursor.fetchone()

print("\n4. New Overall Totals:")
print(f"   Revenue:        ${totals[0]:,.2f}")
print(f"   COGS:           ${totals[1]:,.2f}")
print(f"   Excise (COLL):  ${totals[2]:,.2f}")
print(f"   Gross Profit:   ${totals[3]:,.2f}")
print(f"   GP Margin:      {totals[4]:.2f}%")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ GP calculation fixed!")
print("\nWhat changed:")
print("  • PAID excise tax is NOT subtracted (already in COGS)")
print("  • COLL excise tax IS subtracted (collected at POS)")
print("\nCIGAR GA should now show positive GP!")
print("\nRefresh your dashboard: http://100.126.106.37:8081")
