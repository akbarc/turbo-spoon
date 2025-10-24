#!/usr/bin/env python3
"""Verify PUExciseEntry table exists and has data"""

import sys
sys.path.insert(0, '/Users/akbarchranya/georgiadashboard')
from database_pymssql import quick_query

print('=' * 100)
print('EXCISE TABLE VERIFICATION')
print('=' * 100)

try:
    # Check if PUExciseEntry table exists
    table_check = '''
    SELECT
        COUNT(*) as TableExists
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'PUExciseEntry'
    '''

    result = quick_query(table_check)
    table_exists = result.iloc[0]['TableExists'] > 0

    print(f'\n✅ PUExciseEntry table exists: {table_exists}\n')

    if table_exists:
        # Get table structure
        print('📋 PUExciseEntry Table Structure:')
        print('-' * 100)
        columns_query = '''
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'PUExciseEntry'
        ORDER BY ORDINAL_POSITION
        '''

        df_cols = quick_query(columns_query)
        for _, row in df_cols.iterrows():
            nullable = 'NULL' if row['IS_NULLABLE'] == 'YES' else 'NOT NULL'
            max_len = f"({row['CHARACTER_MAXIMUM_LENGTH']})" if row['CHARACTER_MAXIMUM_LENGTH'] else ''
            print(f"  {row['COLUMN_NAME']:30s} {row['DATA_TYPE']:15s}{max_len:10s} {nullable}")

        # Get row count
        print(f'\n📊 Data Statistics:')
        print('-' * 100)
        count_query = 'SELECT COUNT(*) as TotalRows FROM PUExciseEntry'
        count_result = quick_query(count_query)

        if len(count_result) == 0 or count_result.empty:
            print('  ⚠️  No data returned from count query')
            row_count = 0
        else:
            row_count = count_result.iloc[0]['TotalRows']
        print(f'  Total rows: {row_count:,}')

        if row_count > 0:
            # Get date range
            date_range_query = '''
            SELECT
                MIN(TransactionTime) as EarliestDate,
                MAX(TransactionTime) as LatestDate,
                COUNT(DISTINCT TransactionNumber) as UniqueTransactions,
                COUNT(DISTINCT ItemID) as UniqueItems,
                SUM(PriceC * Quantity) as TotalExciseTax
            FROM PUExciseEntry
            '''

            df_range = quick_query(date_range_query)
            print(f"  Date range: {df_range.iloc[0]['EarliestDate']} to {df_range.iloc[0]['LatestDate']}")
            print(f"  Unique transactions: {df_range.iloc[0]['UniqueTransactions']:,}")
            print(f"  Unique items: {df_range.iloc[0]['UniqueItems']:,}")
            print(f"  Total excise tax: ${df_range.iloc[0]['TotalExciseTax']:,.2f}")

            # Get sample records
            print(f'\n📝 Sample Records (first 5):')
            print('-' * 100)
            sample_query = 'SELECT TOP 5 * FROM PUExciseEntry ORDER BY TransactionTime DESC'
            df_sample = quick_query(sample_query)
            print(df_sample.to_string())

            print(f'\n✅ PUExciseEntry table is populated and ready for excise reports')
        else:
            print(f'\n⚠️  PUExciseEntry table exists but has no data')
            print('   Excise reports will not work until data is populated')
    else:
        print('❌ PUExciseEntry table does NOT exist')
        print('   Excise reports are NOT available in this database')
        print('   The POS system must be configured to track excise tax')

    print(f'\n' + '=' * 100)

except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
