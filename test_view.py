#!/usr/bin/env python3
"""
Quick test to see if vw_TransactionGrossProfit view exists and works
"""
import os
import sys
from datetime import datetime, timedelta

# Set TDS version BEFORE importing pymssql
os.environ['TDSVER'] = '7.0'

import pymssql

# Database configuration
DB_CONFIG = {
    'server': '10.1.10.105',
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 10,
    'login_timeout': 10
}

def test_view_exists():
    """Check if view exists"""
    print("Testing if vw_TransactionGrossProfit exists...")

    conn = pymssql.connect(
        server=DB_CONFIG['server'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        tds_version=DB_CONFIG['tds_version'],
        timeout=DB_CONFIG['timeout'],
        login_timeout=DB_CONFIG['login_timeout']
    )

    cursor = conn.cursor(as_dict=True)

    # Check if view exists
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_NAME = 'vw_TransactionGrossProfit'
    """)

    result = cursor.fetchone()

    if result:
        print(f"✅ View exists: {result['TABLE_NAME']}")
    else:
        print("❌ View does NOT exist!")
        cursor.close()
        conn.close()
        return False

    # Try to query just ONE row from view
    print("\nTrying to fetch ONE row from view...")
    try:
        cursor.execute("SELECT TOP 1 * FROM vw_TransactionGrossProfit")
        row = cursor.fetchone()
        if row:
            print(f"✅ Successfully queried view! Sample columns:")
            for key in list(row.keys())[:5]:  # Show first 5 columns
                print(f"  - {key}: {row[key]}")
        else:
            print("⚠️ View exists but returned no data")
    except Exception as e:
        print(f"❌ Error querying view: {e}")
        cursor.close()
        conn.close()
        return False

    # Try a COUNT query (faster than full data fetch)
    print("\nTrying COUNT query...")
    try:
        cursor.execute("SELECT COUNT(*) as row_count FROM vw_TransactionGrossProfit")
        result = cursor.fetchone()
        print(f"✅ View has {result['row_count']:,} total rows")
    except Exception as e:
        print(f"❌ Error counting rows: {e}")

    # Try a simple aggregation for today
    print("\nTrying aggregation for today...")
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute("""
            SELECT
                COUNT(*) as row_count,
                SUM(Revenue) as total_revenue
            FROM vw_TransactionGrossProfit
            WHERE TransactionTime >= %s
        """, (today,))
        result = cursor.fetchone()
        print(f"✅ Today's data: {result['row_count']} rows, ${result['total_revenue']:,.2f} revenue")
    except Exception as e:
        print(f"❌ Error with today's query: {e}")

    cursor.close()
    conn.close()
    return True

if __name__ == '__main__':
    try:
        test_view_exists()
        print("\n✅ All view tests completed!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
