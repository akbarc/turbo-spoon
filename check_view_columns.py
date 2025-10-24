#!/usr/bin/env python3
"""Check PUVIEWEXCISETRANSACTION columns"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

# Get column names from view
query = """
SELECT TOP 1 *
FROM PUVIEWEXCISETRANSACTION
"""

result = execute_query(query)
if result:
    print("PUVIEWEXCISETRANSACTION columns:")
    for col in sorted(result[0].keys()):
        print(f"  - {col}")
