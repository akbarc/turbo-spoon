#!/usr/bin/env python3
"""
Test GP functions one at a time to find the slow one
"""
import sys
sys.path.append('.')

from datetime import datetime
from data_foundation.gross_profit import get_gross_profit_summary, get_gp_by_category, get_excise_tax_breakdown

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

print("=" * 60)
print("Test 1: get_gross_profit_summary()")
print("=" * 60)
try:
    summary = get_gross_profit_summary(today)
    print(f"✅ Completed!")
    print(f"  Revenue: ${summary['total_revenue']:,.2f}")
    print(f"  GP: ${summary['total_gross_profit']:,.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 2: get_gp_by_category()")
print("=" * 60)
try:
    categories = get_gp_by_category(today)
    print(f"✅ Completed! Found {len(categories)} categories")
    if categories:
        print(f"  Top category: {categories[0]['CategoryName']} - ${categories[0]['gross_profit']:,.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 3: get_excise_tax_breakdown()")
print("=" * 60)
try:
    excise = get_excise_tax_breakdown(today)
    print(f"✅ Completed! Found {len(excise)} tax types")
    if excise:
        print(f"  Top type: {excise[0]['ExciseTaxType']} - ${excise[0]['total_excise_tax']:,.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
