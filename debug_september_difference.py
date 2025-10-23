"""
Debug the $1,245.16 difference between our calculation and the actual report.

Our calculation: $66,828.73
Actual report:   $68,073.89
Difference:      $1,245.16

Possible causes:
1. Date/time boundaries different (time zones, exact cutoff times)
2. Missing transaction types
3. Returns/voids handled differently
4. Report includes different SubDescription3 codes
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db

# Load environment variables
load_dotenv()

def debug_september():
    """Debug September excise calculation."""

    print("\n" + "="*80)
    print("SEPTEMBER EXCISE TAX DEBUG")
    print("="*80)

    # Try different date boundaries
    scenarios = [
        ("Exact calendar month", "2024-09-01 00:00:00", "2024-09-30 23:59:59"),
        ("Full last second", "2024-09-01 00:00:00", "2024-10-01 00:00:00"),
        ("Business day boundaries", "2024-09-01 06:00:00", "2024-10-01 05:59:59"),
    ]

    for name, start, end in scenarios:
        print(f"\n{name}: {start} to {end}")
        print("-" * 80)

        query = f"""
        SELECT
            SUM(CASE WHEN SubDescription3 LIKE '%PAID' THEN PriceC * Quantity ELSE 0 END) as TotalPaid,
            SUM(CASE WHEN SubDescription3 LIKE '%COLL' THEN PriceC * Quantity ELSE 0 END) as TotalCollected,
            COUNT(*) as TotalEntries
        FROM PUExciseEntry WITH (NOLOCK)
        WHERE TransactionTime >= '{start}'
          AND TransactionTime <= '{end}'
        """

        try:
            result = db.execute_query(query)
            if not result.empty:
                paid = result['TotalPaid'].iloc[0] or 0
                coll = result['TotalCollected'].iloc[0] or 0
                entries = result['TotalEntries'].iloc[0] or 0
                print(f"  PAID: ${paid:,.2f}")
                print(f"  COLLECTED: ${coll:,.2f}")
                print(f"  Total Entries: {entries:,}")

                diff = 68073.89 - coll
                print(f"  Difference from report: ${diff:,.2f}")
        except Exception as e:
            print(f"  Error: {e}")

    # Check all SubDescription3 codes for September
    print("\n" + "="*80)
    print("ALL TAX CATEGORIES IN SEPTEMBER")
    print("="*80)

    codes_query = """
    SELECT
        SubDescription3,
        COUNT(*) as EntryCount,
        SUM(PriceC * Quantity) as TotalTax
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '2024-09-01 00:00:00'
      AND TransactionTime <= '2024-09-30 23:59:59'
    GROUP BY SubDescription3
    ORDER BY TotalTax DESC
    """

    try:
        codes = db.execute_query(codes_query)
        if not codes.empty:
            print("\nAll Tax Categories:")
            print(codes.to_string(index=False))

            paid_total = codes[codes['SubDescription3'].str.contains('PAID', na=False)]['TotalTax'].sum()
            coll_total = codes[codes['SubDescription3'].str.contains('COLL', na=False)]['TotalTax'].sum()

            print(f"\n** PAID Total: ${paid_total:,.2f}")
            print(f"** COLL Total: ${coll_total:,.2f}")
            print(f"** Difference from $68,073.89: ${68073.89 - coll_total:,.2f}")
    except Exception as e:
        print(f"Error: {e}")

    # Check for edge-case transactions (Oct 1)
    print("\n" + "="*80)
    print("TRANSACTIONS NEAR MONTH BOUNDARY")
    print("="*80)

    boundary_query = """
    SELECT
        CAST(TransactionTime as DATE) as Date,
        SubDescription3,
        COUNT(*) as Count,
        SUM(PriceC * Quantity) as Total
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '2024-09-30 00:00:00'
      AND TransactionTime <= '2024-10-01 23:59:59'
      AND SubDescription3 LIKE '%COLL'
    GROUP BY CAST(TransactionTime as DATE), SubDescription3
    ORDER BY Date, SubDescription3
    """

    try:
        boundary = db.execute_query(boundary_query)
        if not boundary.empty:
            print(boundary.to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)
    print("\nPlease check your September report:")
    print("1. What is the exact date range?")
    print("2. Are there any filters or exclusions?")
    print("3. Does it include returns/voids differently?")
    print("="*80 + "\n")


if __name__ == "__main__":
    debug_september()
