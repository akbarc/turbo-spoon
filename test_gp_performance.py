#!/usr/bin/env python3
"""Test GP query performance"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query
from datetime import datetime
import time

# Time a direct category query on PUVIEWEXCISETRANSACTION
query = """
SELECT
    CNAME as category_name,
    COUNT(*) as item_count,
    SUM(PRICE * QUANTITY) as revenue,
    SUM(COST * QUANTITY) as cogs,
    SUM(COALESCE(PUEPRICEC, 0)) as excise_tax,
    SUM((PRICE * QUANTITY) - (COST * QUANTITY) - COALESCE(PUEPRICEC, 0)) as gross_profit
FROM PUVIEWEXCISETRANSACTION
WHERE TRANSACTIONTIME >= '2025-01-01'
    AND TRANSACTIONTIME <= '2025-10-15'
    AND CNAME IS NOT NULL
GROUP BY CNAME
ORDER BY gross_profit DESC
"""

start = time.time()
result = execute_query(query)
elapsed = time.time() - start

print(f'Direct PUVIEWEXCISETRANSACTION query: {elapsed:.2f}s')
print(f'Categories returned: {len(result)}')
print(f'\nTop 5 categories:')
for row in result[:5]:
    gp_margin = (float(row['gross_profit']) / float(row['revenue']) * 100) if row['revenue'] else 0
    print(f"  {row['category_name']}: GP=${row['gross_profit']:,.0f} ({gp_margin:.1f}%)")
