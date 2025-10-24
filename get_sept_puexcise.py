#!/usr/bin/env python3
"""Get all September excise tax data using PUVIEWEXCISETRANSACTION"""
import sys
import time
import os
os.environ['TDSVER'] = '7.0'
sys.path.append('/Users/akbarchranya/georgiadashboard')
import pymssql

# Create connection with extended timeout (5 minutes)
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=300,  # 5 minutes
    login_timeout=10
)
cursor = conn.cursor(as_dict=True)

query = """
SELECT
    CNAME as CategoryName,
    PUESUBDESCRIPTION3 as TaxType,
    COUNT(*) as item_count,
    SUM(PRICE * QUANTITY) as total_revenue,
    SUM(COST * QUANTITY) as total_cogs,
    SUM(PUEPRICEC) as total_excise_tax
FROM PUVIEWEXCISETRANSACTION
WHERE TRANSACTIONTIME >= '2025-09-01'
    AND TRANSACTIONTIME < '2025-10-01'
    AND PUEPRICEC IS NOT NULL
    AND PUEPRICEC > 0
    AND QUANTITY > 0
GROUP BY CNAME, PUESUBDESCRIPTION3
ORDER BY total_excise_tax DESC
"""

print('='*110)
print('September 2025 - Full Excise Tax Data from PUVIEWEXCISETRANSACTION')
print('='*110)
print('Querying... (may take 1-2 minutes)')
print()

start = time.time()
try:
    cursor.execute(query)
    result = cursor.fetchall()
    elapsed = time.time() - start

    print(f'✅ Query completed in {elapsed:.1f} seconds')
    print(f'Results: {len(result)} category/tax-type combinations')
    print()
    print('='*110)
    print(f'{"Category":<30} {"Tax Type":<15} {"Items":<8} {"Revenue":<12} {"COGS":<12} {"Excise Tax":<12}')
    print('='*110)

    total_revenue = 0
    total_cogs = 0
    total_tax = 0

    for row in result:
        cat = row['CategoryName'][:29] if row['CategoryName'] else 'Unknown'
        tax_type = row['TaxType'][:14] if row['TaxType'] else 'N/A'
        items = row['item_count']
        revenue = float(row['total_revenue'] or 0)
        cogs = float(row['total_cogs'] or 0)
        tax = float(row['total_excise_tax'] or 0)

        total_revenue += revenue
        total_cogs += cogs
        total_tax += tax

        print(f'{cat:<30} {tax_type:<15} {items:<8} ${revenue:>10,.0f} ${cogs:>10,.0f} ${tax:>10,.2f}')

    print('='*110)
    print(f'{"TOTALS":<30} {"":15} {"":8} ${total_revenue:>10,.0f} ${total_cogs:>10,.0f} ${total_tax:>10,.2f}')
    print('='*110)
    print(f'\nTotal Excise Tax for September 2025: ${total_tax:,.2f}')

except Exception as e:
    elapsed = time.time() - start
    print(f'\n❌ Query failed after {elapsed:.1f} seconds')
    print(f'Error: {e}')
finally:
    cursor.close()
    conn.close()
