#!/usr/bin/env python3
"""Examine the Report table structure"""

import sys
sys.path.insert(0, '/Users/akbarchranya/georgiadashboard')
from database_pymssql import quick_query

# Get Report table columns
columns_query = '''
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Report'
ORDER BY ORDINAL_POSITION
'''

print('=== Report Table Structure ===\n')
try:
    df = quick_query(columns_query)
    print(f'Found {len(df)} columns:\n')
    for _, row in df.iterrows():
        nullable = 'NULL' if row['IS_NULLABLE'] == 'YES' else 'NOT NULL'
        max_len = f"({row['CHARACTER_MAXIMUM_LENGTH']})" if row['CHARACTER_MAXIMUM_LENGTH'] else ''
        print(f"  {row['COLUMN_NAME']:30s} {row['DATA_TYPE']:15s}{max_len:10s} {nullable}")

    # Now get sample data
    print('\n\n=== Sample Report Data ===\n')
    sample_query = 'SELECT TOP 10 * FROM Report'
    df_sample = quick_query(sample_query)
    print(f'Found {len(df_sample)} sample records\n')

    if len(df_sample) > 0:
        # Print column names
        print('Columns:', ', '.join(df_sample.columns.tolist()))
        print('\nFirst 5 records:')
        print(df_sample.head().to_string())

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
