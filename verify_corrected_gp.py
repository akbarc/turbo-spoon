#!/usr/bin/env python3
"""
Verify the corrected GP calculations
CIGAR GA should now be POSITIVE (not negative)
"""
import os
from datetime import datetime
os.environ['TDSVER'] = '7.0'
import pymssql

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=10
)
cursor = conn.cursor(as_dict=True)

today = datetime.now().date()

print("="*60)
print("Verifying Corrected GP Calculations")
print("="*60)

# Check previously negative categories
print(f"\n1. Previously Negative Categories (should now be positive):\n")
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

for row in cursor.fetchall():
    status = "✅ POSITIVE" if row['GrossProfit'] > 0 else "⚠️ Still negative"
    print(f"   {row['CategoryName']}")
    print(f"      Revenue:    ${row['Revenue']:,.2f}")
    print(f"      COGS:       ${row['COGS']:,.2f}")
    print(f"      Excise Tax: ${row['ExciseTax']:,.2f} (only COLLECTED)")
    print(f"      GP:         ${row['GrossProfit']:,.2f} ({row['GPMargin']:.1f}%) {status}")
    print()

# Overall totals
print("2. Overall Totals:\n")
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
print(f"   Revenue:        ${totals['total_revenue']:,.2f}")
print(f"   COGS:           ${totals['total_cogs']:,.2f}")
print(f"   Excise (COLL):  ${totals['total_excise']:,.2f}")
print(f"   Gross Profit:   ${totals['total_gp']:,.2f}")
print(f"   GP Margin:      {totals['gp_margin']:.2f}%")

# Top 10 categories
print("\n3. Top 10 Categories by GP:\n")
cursor.execute("""
    SELECT TOP 10
        CategoryName,
        GrossProfit,
        CASE
            WHEN Revenue > 0 THEN (GrossProfit / Revenue * 100)
            ELSE 0
        END as GPMargin
    FROM GP_Daily_Summary
    WHERE BusinessDate = %s
    ORDER BY GrossProfit DESC
""", (today,))

for row in cursor.fetchall():
    print(f"   {row['CategoryName']}: ${row['GrossProfit']:,.2f} ({row['GPMargin']:.1f}%)")

cursor.close()
conn.close()

print("\n" + "="*60)
print("✅ Verification complete!")
print("\nDashboard: http://100.126.106.37:8081")
print("="*60)
