#!/usr/bin/env python3
"""Investigate PUVIEWEXCISETRANSACTION structure and performance"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

# Check if it's a view or table
query1 = """
SELECT
    o.type_desc as object_type,
    CASE
        WHEN o.type = 'V' THEN 'VIEW'
        WHEN o.type = 'U' THEN 'TABLE'
        ELSE o.type_desc
    END as type
FROM sys.objects o
WHERE o.name = 'PUVIEWEXCISETRANSACTION'
"""

print("="*60)
print("PUVIEWEXCISETRANSACTION Object Type:")
print("="*60)
result = execute_query(query1)
for row in result:
    print(f"Type: {row['object_type']}")

# Get the view definition if it's a view
query2 = """
SELECT OBJECT_DEFINITION(OBJECT_ID('PUVIEWEXCISETRANSACTION')) as view_definition
"""

print("\n" + "="*60)
print("View Definition (first 2000 chars):")
print("="*60)
result = execute_query(query2)
if result and result[0]['view_definition']:
    definition = result[0]['view_definition']
    print(definition[:2000])
    print(f"\n... (total length: {len(definition)} chars)")
else:
    print("Not a view or definition not available")

# Check row count
query3 = """
SELECT COUNT(*) as total_rows
FROM PUVIEWEXCISETRANSACTION
WHERE TRANSACTIONTIME >= '2025-01-01' AND TRANSACTIONTIME <= '2025-10-15'
"""

print("\n" + "="*60)
print("Row Count (YTD):")
print("="*60)
result = execute_query(query3)
if result:
    print(f"Total rows: {result[0]['total_rows']:,}")
