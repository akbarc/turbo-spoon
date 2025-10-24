#!/usr/bin/env python3
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
print(f"Checking GP_Daily_Summary for {today}...")

cursor.execute('SELECT COUNT(*) as cnt FROM GP_Daily_Summary WHERE BusinessDate = %s', (today,))
result = cursor.fetchone()
print(f"\nRecords for {today}: {result['cnt']}")

if result['cnt'] > 0:
    print("\nTop 5 categories by GP:")
    cursor.execute('''
        SELECT CategoryName, Revenue, COGS, ExciseTax, GrossProfit
        FROM GP_Daily_Summary
        WHERE BusinessDate = %s
        ORDER BY GrossProfit DESC
    ''', (today,))
    for row in cursor.fetchall():
        print(f"  {row['CategoryName']}: GP=${row['GrossProfit']:.2f}")
else:
    print("\nNo data found for today. Checking most recent date...")
    cursor.execute('SELECT MAX(BusinessDate) as latest FROM GP_Daily_Summary')
    latest = cursor.fetchone()
    print(f"Latest data: {latest['latest']}")

cursor.close()
conn.close()
