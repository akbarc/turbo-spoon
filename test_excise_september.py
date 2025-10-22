"""
Test excise tax calculation against known September 2024 numbers.

Expected Results (from actual report):
- Excise Paid: $30,568.20
- Excise Collected: $66,828.73
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected, get_excise_breakdown

# Load environment variables
load_dotenv()

def test_september():
    """Test excise calculation for September 2024."""

    print("\n" + "="*70)
    print("EXCISE TAX CALCULATION TEST - SEPTEMBER 2024")
    print("="*70)

    # September 2024
    start_date = "2024-09-01 00:00:00"
    end_date = "2024-09-30 23:59:59"

    print(f"\nDate Range: September 2024")
    print("-" * 70)

    # Expected values from actual report
    expected_paid = 30568.20
    expected_collected = 66828.73

    # Test PAID calculation
    print("\n1. EXCISE TAX PAID TO STATE:")
    start_time = datetime.now()
    paid_total, error = calculate_excise_tax(db, start_date, end_date)
    paid_duration = (datetime.now() - start_time).total_seconds()

    if paid_total is not None:
        diff = abs(paid_total - expected_paid)
        match = "✓ MATCH" if diff < 1.0 else "✗ MISMATCH"

        print(f"   Calculated: ${paid_total:,.2f}")
        print(f"   Expected:   ${expected_paid:,.2f}")
        print(f"   Difference: ${diff:,.2f}")
        print(f"   {match}")
        print(f"   Time: {paid_duration:.2f}s")
    else:
        print(f"   ✗ Failed: {error}")

    # Test COLLECTED calculation
    print("\n2. EXCISE TAX COLLECTED FROM CUSTOMERS:")
    start_time = datetime.now()
    coll_total, error = calculate_excise_collected(db, start_date, end_date)
    coll_duration = (datetime.now() - start_time).total_seconds()

    if coll_total is not None:
        diff = abs(coll_total - expected_collected)
        match = "✓ MATCH" if diff < 1.0 else "✗ MISMATCH"

        print(f"   Calculated: ${coll_total:,.2f}")
        print(f"   Expected:   ${expected_collected:,.2f}")
        print(f"   Difference: ${diff:,.2f}")
        print(f"   {match}")
        print(f"   Time: {coll_duration:.2f}s")
    else:
        print(f"   ✗ Failed: {error}")

    # Get breakdown
    print("\n3. BREAKDOWN BY CATEGORY (COLLECTED):")
    breakdown, error = get_excise_breakdown(db, start_date, end_date, 'COLL')

    if breakdown is not None and not breakdown.empty:
        print(f"\n{'Category':<15} {'Total Excise':<15} {'Entries':<10}")
        print("-" * 40)
        for _, row in breakdown.iterrows():
            print(f"{row['Category']:<15} ${row['TotalExcise']:>13,.2f} {row['EntryCount']:>8,}")
        print("-" * 40)
        print(f"{'TOTAL':<15} ${breakdown['TotalExcise'].sum():>13,.2f}")
    else:
        print(f"   Error: {error}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_september()
