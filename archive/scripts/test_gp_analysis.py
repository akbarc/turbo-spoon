#!/usr/bin/env python3
"""Test the GP Analysis module"""

from modules.gp_analysis import GPAnalysis
from database_pymssql import SQLServerConnection
import json

def test_gp_analysis():
    db = SQLServerConnection()
    db.connect()
    
    analyzer = GPAnalysis(db)
    
    # Test executive summary
    print("Testing Executive Summary (YTD)...")
    summary = analyzer.get_executive_summary('YTD')
    print(f"  Total GP: ${summary.get('total_gp', 0):,.0f}")
    print(f"  GP Margin: {summary.get('gp_margin', 0):.1f}%")
    print(f"  Best Category: {summary.get('best_category', {}).get('name', 'N/A')}")
    print(f"  Active Customers: {summary.get('active_customers', 0)}")
    
    # Test category analysis
    print("\nTesting Category Analysis...")
    categories = analyzer.get_category_gp_analysis('YTD')
    print(f"  Found {len(categories)} categories")
    for cat in categories[:3]:  # Show top 3
        print(f"    {cat['category']}: GP ${cat['gp']:,.0f} ({cat['margin']:.1f}%)")
    
    # Test customer profitability
    print("\nTesting Customer Profitability...")
    customers = analyzer.get_customer_gp_analysis('YTD', limit=5)
    print(f"  Top 5 customers by GP:")
    for cust in customers:
        print(f"    {cust['customer']}: GP ${cust['gp']:,.0f} ({cust['margin']:.1f}%)")
    
    # Test trending
    print("\nTesting GP Trending...")
    trending = analyzer.get_gp_trending('12M')
    print(f"  Got {len(trending)} periods")
    if trending:
        latest = trending[-1]
        print(f"  Latest: {latest['period']} - GP ${latest['gp']:,.0f}")
    
    # Test opportunities
    print("\nTesting GP Opportunities...")
    opportunities = analyzer.get_gp_opportunities('YTD')
    print(f"  Found {len(opportunities)} opportunities")
    for opp in opportunities[:2]:  # Show first 2
        print(f"    {opp['opportunity']}: Potential ${opp['impact']:,.0f}")
    
    db.close()
    print("\n✅ All GP Analysis tests passed!")

if __name__ == "__main__":
    test_gp_analysis()