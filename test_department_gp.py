#!/usr/bin/env python3
"""
Test department-level GP analysis
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
    timeout=30
)
cursor = conn.cursor(as_dict=True)

today = datetime.now().date()

print("="*60)
print("Department-Level GP Analysis")
print("="*60)

# Department GP Summary
print(f"\n1. GP by Department for {today}:\n")
cursor.execute("""
    SELECT
        d.DepartmentName,
        SUM(gp.Revenue) as Revenue,
        SUM(gp.COGS) as COGS,
        SUM(gp.ExciseTax) as ExciseTax,
        SUM(gp.GrossProfit) as GP,
        CASE
            WHEN SUM(gp.Revenue) > 0
            THEN (SUM(gp.GrossProfit) / SUM(gp.Revenue) * 100)
            ELSE 0
        END as GPMargin,
        SUM(gp.ItemCount) as ItemCount
    FROM GP_Daily_Summary gp
    INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
    INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
    WHERE gp.BusinessDate = %s
    GROUP BY d.DepartmentName, d.SortOrder
    ORDER BY d.SortOrder
""", (today,))

total_rev = 0
total_gp = 0

for row in cursor.fetchall():
    total_rev += row['Revenue']
    total_gp += row['GP']
    print(f"   {row['DepartmentName']}")
    print(f"      Revenue:    ${row['Revenue']:,.2f}")
    print(f"      GP:         ${row['GP']:,.2f} ({row['GPMargin']:.1f}%)")
    print(f"      Items Sold: {row['ItemCount']}")
    print()

print(f"   TOTAL")
print(f"      Revenue:    ${total_rev:,.2f}")
print(f"      GP:         ${total_gp:,.2f} ({total_gp/total_rev*100:.1f}%)")

# Top categories by department
print(f"\n2. Top Category in Each Department:\n")
cursor.execute("""
    SELECT
        d.DepartmentName,
        gp.CategoryName,
        gp.Revenue,
        gp.GrossProfit,
        CASE
            WHEN gp.Revenue > 0
            THEN (gp.GrossProfit / gp.Revenue * 100)
            ELSE 0
        END as GPMargin
    FROM (
        SELECT
            cm.DepartmentID,
            gp.CategoryID,
            gp.CategoryName,
            gp.Revenue,
            gp.GrossProfit,
            ROW_NUMBER() OVER (PARTITION BY cm.DepartmentID ORDER BY gp.GrossProfit DESC) as rn
        FROM GP_Daily_Summary gp
        INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
        WHERE gp.BusinessDate = %s
    ) gp
    INNER JOIN Departments d ON gp.DepartmentID = d.DepartmentID
    WHERE gp.rn = 1
    ORDER BY d.SortOrder
""", (today,))

for row in cursor.fetchall():
    print(f"   {row['DepartmentName']}")
    print(f"      Top: {row['CategoryName']}")
    print(f"      Revenue: ${row['Revenue']:,.2f}")
    print(f"      GP: ${row['GrossProfit']:,.2f} ({row['GPMargin']:.1f}%)")
    print()

cursor.close()
conn.close()

print("="*60)
print("✅ Department analysis complete!")
print(f"\nDashboard: http://100.126.106.37:8081")
print("="*60)
