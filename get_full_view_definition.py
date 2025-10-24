#!/usr/bin/env python3
"""Get full PUVIEWEXCISETRANSACTION view definition"""
import sys
sys.path.append('/Users/akbarchranya/georgiadashboard')
from data_foundation.gross_profit import execute_query

# Get the complete view definition
query = """
SELECT OBJECT_DEFINITION(OBJECT_ID('PUVIEWEXCISETRANSACTION')) as view_definition
"""

result = execute_query(query)
if result and result[0]['view_definition']:
    definition = result[0]['view_definition']

    # Save to file
    with open('/Users/akbarchranya/georgiadashboard/PUVIEWEXCISETRANSACTION_definition.sql', 'w') as f:
        f.write(definition)

    print("✅ View definition saved to: PUVIEWEXCISETRANSACTION_definition.sql")
    print(f"Length: {len(definition)} characters")
    print("\n" + "="*80)
    print("View Definition:")
    print("="*80)
    print(definition)
else:
    print("❌ Could not retrieve view definition")
