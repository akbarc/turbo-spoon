#!/usr/bin/env python3
"""Fast September excise query - PUExciseEntry table only"""
import sys
import time
import os
os.environ['TDSVER'] = '7.0'
sys.path.append('/Users/akbarchranya/georgiadashboard')
import pymssql

conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=60,
    login_timeout=10
)

# Query PUExciseEntry directly - much faster!
query = """
SELECT
    SubDescription3 as TaxType,
    CASE
        WHEN SubDescription3 LIKE '%COLL' THEN 'COLLECTED'
        WHEN SubDescription3 LIKE '%PAID' THEN 'PRE-PAID'
        ELSE 'OTHER'
    END as TaxCategory,
    COUNT(DISTINCT TransactionNumber) as TransactionCount,
    COUNT(*) as LineItems,
    SUM(Quantity) as TotalQuantity,
    SUM(Price * Quantity) as TotalRevenue,
    SUM(Cost * Quantity) as TotalCost,
    SUM(PriceC) as TotalExciseTax,  -- This is the excise tax amount
    AVG(PriceC) as AvgExciseTaxPerItem,
    MIN(TransactionTime) as FirstTransaction,
    MAX(TransactionTime) as LastTransaction
FROM PUExciseEntry
WHERE TransactionTime >= '2025-09-01'
  AND TransactionTime < '2025-10-01'
  AND PriceC > 0  -- Only items with excise tax
GROUP BY SubDescription3
ORDER BY TotalExciseTax DESC
"""

print('='*110)
print('September 2025 - FAST Excise Tax Report (PUExciseEntry Table)')
print('='*110)
print()

start = time.time()
cursor = conn.cursor(as_dict=True)

try:
    cursor.execute(query)
    results = cursor.fetchall()
    elapsed = time.time() - start

    print(f'✅ Query completed in {elapsed:.2f} seconds')
    print(f'Tax types found: {len(results)}')
    print()

    # Separate COLLECTED and PAID
    collected_taxes = []
    paid_taxes = []

    for row in results:
        if row['TaxCategory'] == 'COLLECTED':
            collected_taxes.append(row)
        elif row['TaxCategory'] == 'PRE-PAID':
            paid_taxes.append(row)

    # Show COLLECTED taxes (subtract from GP)
    print('='*110)
    print('COLLECTED TAX (Subtract from GP)')
    print('='*110)
    print(f'{"Tax Type":<15} {"Transactions":<12} {"Items":<8} {"Revenue":<15} {"Excise Tax":<15} {"% of Revenue":<12}')
    print('='*110)

    coll_total = 0
    for row in collected_taxes:
        tax = float(row['TotalExciseTax'] or 0)
        revenue = float(row['TotalRevenue'] or 0)
        pct_of_revenue = (tax / revenue * 100) if revenue > 0 else 0
        coll_total += tax

        print(f'{row["TaxType"]:<15} {row["TransactionCount"]:<12} {row["LineItems"]:<8} '
              f'${revenue:>13,.0f} ${tax:>13,.2f} {pct_of_revenue:>10.2f}%')

    print('='*110)
    print(f'{"TOTAL COLLECTED":<15} {"":<12} {"":<8} {"":<15} ${coll_total:>13,.2f}')
    print('='*110)

    # Show PAID taxes (already in COGS)
    print()
    print('='*110)
    print('PRE-PAID TAX (Already in COGS - Do NOT Subtract)')
    print('='*110)
    print(f'{"Tax Type":<15} {"Transactions":<12} {"Items":<8} {"Revenue":<15} {"Excise Tax":<15} {"% of Revenue":<12}')
    print('='*110)

    paid_total = 0
    for row in paid_taxes:
        tax = float(row['TotalExciseTax'] or 0)
        revenue = float(row['TotalRevenue'] or 0)
        pct_of_revenue = (tax / revenue * 100) if revenue > 0 else 0
        paid_total += tax

        print(f'{row["TaxType"]:<15} {row["TransactionCount"]:<12} {row["LineItems"]:<8} '
              f'${revenue:>13,.0f} ${tax:>13,.2f} {pct_of_revenue:>10.2f}%')

    print('='*110)
    print(f'{"TOTAL PRE-PAID":<15} {"":<12} {"":<8} {"":<15} ${paid_total:>13,.2f}')
    print('='*110)

    print()
    print('='*110)
    print('SUMMARY')
    print('='*110)
    print(f'Total Excise Tax (all types):          ${coll_total + paid_total:>15,.2f}')
    print(f'Amount to SUBTRACT from GP (COLL):     ${coll_total:>15,.2f}')
    print(f'Amount already in COGS (PAID):         ${paid_total:>15,.2f}')
    print('='*110)

except Exception as e:
    elapsed = time.time() - start
    print(f'❌ Error: {str(e)}')
    print(f'Time elapsed: {elapsed:.2f}s')
finally:
    cursor.close()
    conn.close()
