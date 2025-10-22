"""
Test script to verify the new fast excise tax calculation.

This compares the old (slow) PUExciseEntry approach with the new (fast) Item-based approach.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, get_excise_breakdown

# Load environment variables
load_dotenv()

def test_excise_calculation():
    """Test the new excise calculation and compare with old approach."""

    print("\n" + "="*60)
    print("EXCISE TAX CALCULATION TEST")
    print("="*60)

    # Test with Last 7 Days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"\nDate Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("-" * 60)

    # NEW APPROACH: Fast Item-based calculation
    print("\n1. NEW APPROACH (Item.SubDescription3):")
    print("   Querying Transaction → TransactionEntry → Item...")

    start_time = datetime.now()
    new_total, error = calculate_excise_tax(
        db,
        start_date.strftime('%Y-%m-%d %H:%M:%S'),
        end_date.strftime('%Y-%m-%d %H:%M:%S')
    )
    new_duration = (datetime.now() - start_time).total_seconds()

    if new_total is not None:
        print(f"   ✓ Success: ${new_total:,.2f}")
        print(f"   ⏱️  Time: {new_duration:.2f}s")
    else:
        print(f"   ✗ Failed: {error}")
        print(f"   ⏱️  Time: {new_duration:.2f}s")

    # OLD APPROACH: Slow PUExciseEntry query
    print("\n2. OLD APPROACH (PUExciseEntry table):")
    print("   Querying PUExciseEntry directly...")

    old_query = f"""
    SELECT SUM(PriceC * Quantity) as TotalExcisePaid
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
      AND TransactionTime <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
      AND SubDescription3 IN ('LT10PAID', 'SL10PAID', 'LC23PAID', 'LC25PAID', 'VO07PAID', 'VD07PAID', 'VC05PAID')
    """

    start_time = datetime.now()
    try:
        old_result = db.execute_query(old_query)
        old_duration = (datetime.now() - start_time).total_seconds()

        if not old_result.empty and old_result['TotalExcisePaid'].iloc[0]:
            old_total = old_result['TotalExcisePaid'].iloc[0]
            print(f"   ✓ Success: ${old_total:,.2f}")
            print(f"   ⏱️  Time: {old_duration:.2f}s")

            # Compare results
            if new_total is not None:
                diff = abs(new_total - old_total)
                diff_pct = (diff / old_total * 100) if old_total > 0 else 0
                print(f"\n3. COMPARISON:")
                print(f"   Difference: ${diff:,.2f} ({diff_pct:.2f}%)")
                print(f"   Speed improvement: {old_duration / new_duration:.1f}x faster")

                if diff_pct < 1:
                    print("   ✓ Results match within 1% tolerance")
                else:
                    print("   ⚠️  Results differ by more than 1%")
        else:
            print(f"   ✗ No data returned")
            print(f"   ⏱️  Time: {old_duration:.2f}s")

    except Exception as e:
        old_duration = (datetime.now() - start_time).total_seconds()
        print(f"   ✗ Failed: {str(e)}")
        print(f"   ⏱️  Time: {old_duration:.2f}s (timeout)")

    # Get breakdown by category
    print("\n4. EXCISE TAX BREAKDOWN:")
    breakdown, error = get_excise_breakdown(
        db,
        start_date.strftime('%Y-%m-%d %H:%M:%S'),
        end_date.strftime('%Y-%m-%d %H:%M:%S')
    )

    if breakdown is not None and not breakdown.empty:
        print(f"\n{'Category':<15} {'Tax Amount':<15} {'Transactions':<15}")
        print("-" * 45)
        for _, row in breakdown.iterrows():
            print(f"{row['Category']:<15} ${row['TotalExcise']:>13,.2f} {row['TransactionCount']:>14,}")
        print("-" * 45)
        print(f"{'TOTAL':<15} ${breakdown['TotalExcise'].sum():>13,.2f} {breakdown['TransactionCount'].sum():>14,}")
    else:
        print(f"   No breakdown data: {error}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_excise_calculation()
