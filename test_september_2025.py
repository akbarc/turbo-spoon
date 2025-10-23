"""
Test September 2025 excise tax calculation to verify dashboard numbers.

Dashboard shows (for "Last Month" = Sept 2025):
- Excise Tax PAID: $24,998.18
- Excise Tax COLLECTED: $68,073.89
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected

# Load environment variables
load_dotenv()

def test_september_2025():
    """Test excise calculation for September 2025."""

    print("\n" + "="*70)
    print("EXCISE TAX TEST - SEPTEMBER 2025")
    print("="*70)

    # September 2025 (what the dashboard shows for "Last Month")
    start_date = "2025-09-01 00:00:00"
    end_date = "2025-09-30 23:59:59"

    print(f"\nDate Range: September 2025")
    print("-" * 70)

    # Expected values from dashboard
    expected_paid = 24998.18
    expected_collected = 68073.89

    # Test PAID calculation
    print("\n1. EXCISE TAX PAID TO SUPPLIERS:")
    paid_total, error = calculate_excise_tax(db, start_date, end_date)

    if paid_total is not None:
        diff = abs(paid_total - expected_paid)
        match = "✓ MATCH" if diff < 1.0 else "⚠ CLOSE" if diff < 100 else "✗ MISMATCH"

        print(f"   Calculated: ${paid_total:,.2f}")
        print(f"   Expected:   ${expected_paid:,.2f}")
        print(f"   Difference: ${diff:,.2f}")
        print(f"   {match}")
    else:
        print(f"   ✗ Failed: {error}")

    # Test COLLECTED calculation
    print("\n2. EXCISE TAX COLLECTED FROM CUSTOMERS:")
    coll_total, error = calculate_excise_collected(db, start_date, end_date)

    if coll_total is not None:
        diff = abs(coll_total - expected_collected)
        match = "✓ MATCH" if diff < 1.0 else "⚠ CLOSE" if diff < 100 else "✗ MISMATCH"

        print(f"   Calculated: ${coll_total:,.2f}")
        print(f"   Expected:   ${expected_collected:,.2f}")
        print(f"   Difference: ${diff:,.2f}")
        print(f"   {match}")
    else:
        print(f"   ✗ Failed: {error}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

    if paid_total and coll_total:
        print("\n📝 NOTES:")
        print("- Excise PAID: Already in COGS (what we paid suppliers)")
        print("- Excise COLLECTED: Must remit to state (subtract from GP)")
        print(f"\nNet Excise Obligation: ${coll_total - paid_total:,.2f}")
        print("="*70 + "\n")


if __name__ == "__main__":
    test_september_2025()
