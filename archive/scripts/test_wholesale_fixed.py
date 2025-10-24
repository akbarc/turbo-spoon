#!/usr/bin/env python3
"""Test the fixed wholesale-retail module"""

from modules.wholesale_retail_fixed import WholesaleRetailAnalysis
from database_pymssql import SQLServerConnection

def test_wholesale_retail():
    db = SQLServerConnection()
    db.connect()
    
    analyzer = WholesaleRetailAnalysis(db)
    
    # Test comparative analysis
    print("Testing Comparative Analysis...")
    results = analyzer.get_comparative_analysis()
    print(f"Got {len(results)} periods")
    for r in results[:2]:  # Show first 2 years
        print(f"  {r['period']}: Wholesale ${r['wholesale_sales']:,.0f} ({r.get('wholesale_pct', 0):.1f}%), Retail ${r['retail_sales']:,.0f}")
    
    # Test wholesale customers
    print("\nTesting Wholesale Customers...")
    customers = analyzer.get_wholesale_customers(5)
    print(f"Got {len(customers)} customers")
    for c in customers:
        print(f"  {c['name']}: ${c['sales_12months']:,.0f}")
    
    # Test monthly analysis
    print("\nTesting Monthly Analysis for 2024...")
    monthly = analyzer.get_monthly_analysis(2024)
    print(f"Got {len(monthly)} months")
    for m in monthly[:3]:  # Show first 3 months
        print(f"  {m['month_name']}: Total ${m['total_sales']:,.0f}, GP ${m['total_gp']:,.0f}")
    
    db.close()
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_wholesale_retail()