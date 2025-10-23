"""
Diagnose PUExciseEntry table performance issues.

This script will:
1. Check table size (row count)
2. Check indexes on TransactionTime and SubDescription3
3. Test query performance with different approaches
4. Recommend optimization strategies
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db

# Load environment variables
load_dotenv()

def diagnose_performance():
    """Diagnose PUExciseEntry performance issues."""

    print("\n" + "="*80)
    print("PUEXCISEENTRY PERFORMANCE DIAGNOSIS")
    print("="*80)

    # 1. Check table size
    print("\n1. TABLE SIZE:")
    print("-" * 80)

    size_query = """
    SELECT
        COUNT(*) as TotalRows,
        MIN(TransactionTime) as EarliestTransaction,
        MAX(TransactionTime) as LatestTransaction,
        COUNT(DISTINCT SubDescription3) as UniqueCategories
    FROM PUExciseEntry WITH (NOLOCK)
    """

    try:
        result = db.execute_query(size_query)
        if not result.empty:
            print(f"Total Rows: {result['TotalRows'].iloc[0]:,}")
            print(f"Date Range: {result['EarliestTransaction'].iloc[0]} to {result['LatestTransaction'].iloc[0]}")
            print(f"Unique Tax Categories: {result['UniqueCategories'].iloc[0]}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Check indexes
    print("\n2. INDEXES ON PUEXCISEENTRY:")
    print("-" * 80)

    index_query = """
    SELECT
        i.name as IndexName,
        i.type_desc as IndexType,
        COL_NAME(ic.object_id, ic.column_id) as ColumnName,
        ic.key_ordinal as KeyOrder,
        i.is_unique,
        i.fill_factor
    FROM sys.indexes i
    INNER JOIN sys.index_columns ic
        ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    WHERE i.object_id = OBJECT_ID('PUExciseEntry')
        AND i.type > 0
    ORDER BY i.name, ic.key_ordinal
    """

    try:
        indexes = db.execute_query(index_query)
        if not indexes.empty:
            print(indexes.to_string(index=False))
        else:
            print("⚠️ NO INDEXES FOUND (or limited permissions to view)")
    except Exception as e:
        print(f"Error checking indexes: {e}")

    # 3. Test query performance - different approaches
    print("\n3. QUERY PERFORMANCE TESTS (Last 7 Days):")
    print("-" * 80)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

    # Test 1: Current approach (LIKE '%PAID')
    print("\nTest 1: Current Query (LIKE '%PAID')")
    query1 = f"""
    SELECT SUM(PriceC * Quantity) as Total
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_str}'
      AND TransactionTime <= '{end_str}'
      AND SubDescription3 LIKE '%PAID'
    """

    start_time = time.time()
    try:
        result1 = db.execute_query(query1)
        duration1 = time.time() - start_time
        total1 = result1['Total'].iloc[0] if not result1.empty else 0
        print(f"  Result: ${total1:,.2f}")
        print(f"  Time: {duration1:.2f}s")
    except Exception as e:
        duration1 = time.time() - start_time
        print(f"  ✗ FAILED after {duration1:.2f}s")
        print(f"  Error: {str(e)[:100]}")

    # Test 2: Using IN clause instead of LIKE
    print("\nTest 2: Using IN clause (explicit codes)")
    query2 = f"""
    SELECT SUM(PriceC * Quantity) as Total
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_str}'
      AND TransactionTime <= '{end_str}'
      AND SubDescription3 IN ('LT10PAID', 'SL10PAID', 'LC23PAID', 'LC25PAID', 'VO07PAID', 'VD07PAID', 'VC05PAID')
    """

    start_time = time.time()
    try:
        result2 = db.execute_query(query2)
        duration2 = time.time() - start_time
        total2 = result2['Total'].iloc[0] if not result2.empty else 0
        print(f"  Result: ${total2:,.2f}")
        print(f"  Time: {duration2:.2f}s")
        if duration1:
            improvement = ((duration1 - duration2) / duration1 * 100)
            print(f"  Improvement: {improvement:.1f}% faster")
    except Exception as e:
        duration2 = time.time() - start_time
        print(f"  ✗ FAILED after {duration2:.2f}s")
        print(f"  Error: {str(e)[:100]}")

    # Test 3: Date filter only (no SubDescription3 filter)
    print("\nTest 3: Date filter only (to test index)")
    query3 = f"""
    SELECT COUNT(*) as RowCount
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_str}'
      AND TransactionTime <= '{end_str}'
    """

    start_time = time.time()
    try:
        result3 = db.execute_query(query3)
        duration3 = time.time() - start_time
        count3 = result3['RowCount'].iloc[0] if not result3.empty else 0
        print(f"  Rows in range: {count3:,}")
        print(f"  Time: {duration3:.2f}s")
    except Exception as e:
        duration3 = time.time() - start_time
        print(f"  ✗ FAILED after {duration3:.2f}s")
        print(f"  Error: {str(e)[:100]}")

    # Test 4: Sample query (TOP 1000)
    print("\nTest 4: Sample query (TOP 1000 rows)")
    query4 = f"""
    SELECT TOP 1000
        TransactionTime,
        SubDescription3,
        PriceC,
        Quantity
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_str}'
      AND TransactionTime <= '{end_str}'
    """

    start_time = time.time()
    try:
        result4 = db.execute_query(query4)
        duration4 = time.time() - start_time
        print(f"  Rows returned: {len(result4):,}")
        print(f"  Time: {duration4:.2f}s")
    except Exception as e:
        duration4 = time.time() - start_time
        print(f"  ✗ FAILED after {duration4:.2f}s")
        print(f"  Error: {str(e)[:100]}")

    # 4. Recommendations
    print("\n4. ANALYSIS & RECOMMENDATIONS:")
    print("-" * 80)

    print("""
Potential Issues:
1. If Test 3 (date filter only) is slow → TransactionTime likely has NO INDEX
2. If Test 1 is much slower than Test 2 → LIKE '%PAID' is inefficient (use IN clause)
3. If all tests timeout → Table is too large or network is too slow

Possible Solutions:
A. Create index on TransactionTime (if you have DBA access)
B. Use IN clause instead of LIKE for SubDescription3
C. Cache/pre-aggregate results (store in SQLite overlay)
D. Query only recent data (e.g., last 30 days) and cache historical
E. Use a summary table if one exists in the database
    """)

    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    diagnose_performance()
