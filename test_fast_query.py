#!/usr/bin/env python3
"""Test FAST query - no PUExciseEntry join!"""
import sys
import time
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

# Query ONLY: TransactionEntry + Item + Category (NO PUExciseEntry!)
query = """
SELECT
    cat.Name as CategoryName,
    COUNT(*) as item_count,
    SUM(te.Price * te.Quantity) as total_revenue,
    SUM(te.Cost * te.Quantity) as total_cogs
FROM TransactionEntry te WITH (NOLOCK)
INNER JOIN Item i WITH (NOLOCK) ON te.ItemID = i.ID
INNER JOIN Category cat WITH (NOLOCK) ON i.CategoryID = cat.ID
WHERE te.TransactionTime >= '2025-09-01'
    AND te.TransactionTime < '2025-10-01'
    AND te.Quantity > 0
GROUP BY cat.Name
ORDER BY total_revenue DESC
"""

print('='*80)
print('FAST Query Test - September 2025 (NO PUExciseEntry join)')
print('='*80)
print('\nRunning query...')

start = time.time()
try:
    result = execute_query(query)
    elapsed = time.time() - start

    print(f'\n✅ SUCCESS! Query completed in {elapsed:.2f} seconds')
    print(f'Categories returned: {len(result)}')
    print('\n' + '='*80)
    print(f'{"Category":<30} {"Items":<10} {"Revenue":<15} {"COGS":<15}')
    print('='*80)

    for row in result[:20]:
        cat = row['CategoryName'][:29] if row['CategoryName'] else 'Unknown'
        items = row['item_count']
        revenue = float(row['total_revenue'] or 0)
        cogs = float(row['total_cogs'] or 0)

        print(f'{cat:<30} {items:<10} ${revenue:>13,.0f} ${cogs:>13,.0f}')

    print('='*80)

except Exception as e:
    elapsed = time.time() - start
    print(f'\n❌ Query failed after {elapsed:.2f} seconds')
    print(f'Error: {e}')
