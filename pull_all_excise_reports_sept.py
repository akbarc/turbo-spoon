#!/usr/bin/env python3
"""Pull all excise-related views/tables for September 2025"""
import sys
import time
import os
os.environ['TDSVER'] = '7.0'
sys.path.append('/Users/akbarchranya/georgiadashboard')
import pymssql

# Create connection with extended timeout
conn = pymssql.connect(
    server='10.1.10.105',
    user='amchranya',
    password='2000Akbar!',
    database='GAWDB',
    tds_version='7.0',
    timeout=300,
    login_timeout=10
)

# All excise views to query
excise_sources = [
    'PUVIEWEXCISECOLLECT',
    'PUVIEWEXCISEPAID',
    'PUVIEWEXCISETRANSACTION',
    'VIEWEXCISETAXCOLLECT',
    'VIEWEXCISETAXPAID',
    'VIEWHOLDEXCISETAX',
    'VIEWPOEXCISETAX',
    'PUExciseEntry'  # The base table
]

print('='*100)
print('September 2025 - All Excise Reports')
print('='*100)
print()

for source in excise_sources:
    print(f'\n{"="*100}')
    print(f'SOURCE: {source}')
    print('='*100)

    cursor = conn.cursor(as_dict=True)

    # Try to query each source
    try:
        # First, get column names
        query_columns = f"SELECT TOP 1 * FROM {source}"

        start = time.time()
        cursor.execute(query_columns)
        sample = cursor.fetchone()

        if sample:
            columns = list(sample.keys())
            print(f'Columns ({len(columns)}): {", ".join(columns[:10])}{"..." if len(columns) > 10 else ""}')
            print()

            # Now get September data with proper date column
            # Try common date column names
            date_columns = ['TIME', 'TRANSACTIONTIME', 'Date', 'TransactionDate']
            date_col = None

            for col in date_columns:
                if col in [c.upper() for c in columns]:
                    date_col = col
                    break

            if not date_col:
                # Check for columns with 'TIME' or 'DATE' in the name
                for col in columns:
                    if 'TIME' in col.upper() or 'DATE' in col.upper():
                        date_col = col
                        break

            if date_col:
                query_sept = f"""
                SELECT COUNT(*) as record_count,
                       MIN({date_col}) as first_date,
                       MAX({date_col}) as last_date
                FROM {source}
                WHERE {date_col} >= '2025-09-01'
                  AND {date_col} < '2025-10-01'
                """

                cursor.execute(query_sept)
                result = cursor.fetchone()
                elapsed = time.time() - start

                if result and result['record_count'] > 0:
                    print(f'✅ September Records: {result["record_count"]:,}')
                    print(f'   Date Range: {result["first_date"]} to {result["last_date"]}')
                    print(f'   Query Time: {elapsed:.2f}s')

                    # Get sample row
                    query_sample = f"""
                    SELECT TOP 5 *
                    FROM {source}
                    WHERE {date_col} >= '2025-09-01'
                      AND {date_col} < '2025-10-01'
                    """
                    cursor.execute(query_sample)
                    samples = cursor.fetchall()

                    if samples:
                        print(f'\n   Sample Records:')
                        for i, row in enumerate(samples[:2], 1):
                            print(f'   Record {i}:')
                            # Show first 5 columns
                            for col in list(row.keys())[:5]:
                                print(f'      {col}: {row[col]}')
                else:
                    print(f'⚠️  No records found for September')
                    print(f'   Query Time: {elapsed:.2f}s')
            else:
                print(f'⚠️  Could not identify date column')
                print(f'   Available columns: {", ".join(columns[:15])}...')
        else:
            print(f'⚠️  No data in this view/table')

    except Exception as e:
        elapsed = time.time() - start
        print(f'❌ Error querying {source}: {str(e)[:200]}')
        print(f'   Time elapsed: {elapsed:.2f}s')
    finally:
        cursor.close()

conn.close()

print()
print('='*100)
print('Report Complete')
print('='*100)
