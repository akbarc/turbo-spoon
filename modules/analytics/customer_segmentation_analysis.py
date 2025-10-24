#!/usr/bin/env python3
"""
Business-Relevant Customer Segmentation Analysis
No generic tiers - actual business categories
"""

import json
import pandas as pd

def analyze_customer_segments():
    """Analyze customers by meaningful business segments"""
    
    print("🎯 CUSTOMER SEGMENTATION ANALYSIS")
    print("="*70)
    
    # Load reports
    with open('customer_analysis_report_20250903_185552.json', 'r') as f:
        customer_data = json.load(f)
    
    with open('bank_metrics_report_20250903_190744.json', 'r') as f:
        bank_data = json.load(f)
    
    # Extract data
    customer_groups = customer_data['sections']['customer_groups']
    geographic = customer_data['sections']['geographic']
    patterns = customer_data['sections']['purchase_patterns']
    concentration = customer_data['sections']['concentration']
    industry_segments = bank_data['sections']['industry_diversification']['segments']
    
    print("\n1. BUSINESS TYPE SEGMENTATION")
    print("-"*50)
    print("\nYour Customer Mix by Business Type:\n")
    
    # Reformat customer groups data
    total_revenue = sum(float(g['TotalSales']) for g in customer_groups)
    
    segments = []
    for group in customer_groups:
        revenue = float(group['TotalSales'])
        pct = (revenue / total_revenue * 100) if total_revenue > 0 else 0
        segments.append({
            'type': group['CustomerGroup'],
            'customers': group['CustomerCount'],
            'revenue': revenue,
            'pct': pct,
            'avg_ticket': float(group['AvgTicket']),
            'avg_per_customer': float(group['AvgSalesPerCustomer'])
        })
    
    # Sort by revenue
    segments.sort(key=lambda x: x['revenue'], reverse=True)
    
    # Display segments
    print(f"{'Business Type':<30} {'Customers':>10} {'Revenue %':>10} {'Avg Sale':>10} {'Annual/Cust':>12}")
    print("-"*75)
    
    for seg in segments:
        print(f"{seg['type']:<30} {seg['customers']:>10} {seg['pct']:>9.1f}% ${seg['avg_ticket']:>9,.0f} ${seg['avg_per_customer']:>11,.0f}")
    
    print(f"\n{'TOTAL':<30} {sum(s['customers'] for s in segments):>10} {100.0:>9.1f}% ${total_revenue:>10,.0f}")
    
    # 2. PURCHASE BEHAVIOR SEGMENTATION
    print("\n\n2. CUSTOMER BEHAVIOR SEGMENTS")
    print("-"*50)
    print("\nBy Purchase Frequency:\n")
    
    print(f"{'Segment':<20} {'Count':>8} {'Avg Days Active':>15} {'Categories':>10}")
    print("-"*55)
    
    # Reorder by frequency
    frequency_order = ['Weekly Regular', 'Monthly Regular', 'Occasional', 'Rare', 'Very Rare']
    patterns_dict = {p['FrequencySegment']: p for p in patterns}
    
    for freq in frequency_order:
        if freq in patterns_dict:
            p = patterns_dict[freq]
            print(f"{p['FrequencySegment']:<20} {p['CustomerCount']:>8} {p['AvgPurchaseDays']:>15.0f} {p['AvgCategories']:>10.0f}")
    
    # 3. TRANSACTION SIZE SEGMENTATION
    print("\n\n3. TRANSACTION SIZE SEGMENTS")
    print("-"*50)
    print("\nCustomer Distribution by Annual Purchase Volume:\n")
    
    brackets = concentration['revenue_brackets']
    
    # Calculate percentages
    total_customers = sum(brackets.values())
    
    size_segments = [
        {'name': 'Enterprise Accounts', 'range': '>$100K/year', 'count': brackets['over_100k']},
        {'name': 'Large Business', 'range': '$50-100K/year', 'count': brackets['50k_to_100k']},
        {'name': 'Medium Business', 'range': '$20-50K/year', 'count': brackets['20k_to_50k']},
        {'name': 'Small Business', 'range': '$10-20K/year', 'count': brackets['10k_to_20k']},
        {'name': 'Micro/Retail', 'range': '<$10K/year', 'count': brackets['under_10k']}
    ]
    
    # Get revenue percentages from tier data
    tiers = customer_data['sections']['customer_tiers']['summary']
    
    print(f"{'Segment':<25} {'Range':<15} {'Customers':>10} {'% of Base':>10}")
    print("-"*62)
    
    for seg in size_segments:
        pct = (seg['count'] / total_customers * 100) if total_customers > 0 else 0
        print(f"{seg['name']:<25} {seg['range']:<15} {seg['count']:>10} {pct:>9.1f}%")
    
    # 4. WHOLESALE VS RETAIL CHARACTERISTICS
    print("\n\n4. WHOLESALE VS RETAIL ANALYSIS")
    print("-"*50)
    
    # Analyze based on transaction patterns
    print("\nBased on Purchase Characteristics:\n")
    
    wholesale_segments = ['Major Gas Chains', 'Other Retail', 'Convenience Stores']
    retail_segments = ['Individual Customers', 'Restaurants', 'Smoke Shops', 'Liquor Stores']
    
    wholesale_total = sum(float(g['TotalSales']) for g in customer_groups if g['CustomerGroup'] in wholesale_segments)
    retail_total = sum(float(g['TotalSales']) for g in customer_groups if g['CustomerGroup'] in retail_segments)
    
    wholesale_customers = sum(g['CustomerCount'] for g in customer_groups if g['CustomerGroup'] in wholesale_segments)
    retail_customers = sum(g['CustomerCount'] for g in customer_groups if g['CustomerGroup'] in retail_segments)
    
    wholesale_avg_ticket = sum(float(g['AvgTicket']) * g['CustomerCount'] for g in customer_groups if g['CustomerGroup'] in wholesale_segments) / wholesale_customers if wholesale_customers > 0 else 0
    retail_avg_ticket = sum(float(g['AvgTicket']) * g['CustomerCount'] for g in customer_groups if g['CustomerGroup'] in retail_segments) / retail_customers if retail_customers > 0 else 0
    
    print("WHOLESALE CHARACTERISTICS:")
    print(f"  • Customer Types: Gas Stations, Convenience Stores, Large Retailers")
    print(f"  • Customers: {wholesale_customers:,}")
    print(f"  • Revenue: ${wholesale_total:,.0f} ({wholesale_total/total_revenue*100:.1f}%)")
    print(f"  • Avg Transaction: ${wholesale_avg_ticket:,.0f}")
    print(f"  • Typical Order: Bulk quantities, regular frequency")
    
    print("\nRETAIL/SMALL BUSINESS:")
    print(f"  • Customer Types: Restaurants, Liquor Stores, Smoke Shops, Direct")
    print(f"  • Customers: {retail_customers:,}")
    print(f"  • Revenue: ${retail_total:,.0f} ({retail_total/total_revenue*100:.1f}%)")
    print(f"  • Avg Transaction: ${retail_avg_ticket:,.0f}")
    print(f"  • Typical Order: Smaller quantities, varied frequency")
    
    # 5. GEOGRAPHIC SEGMENTATION
    print("\n\n5. GEOGRAPHIC CONCENTRATION")
    print("-"*50)
    
    states = geographic['top_states']['TotalSales']
    state_customers = geographic['top_states']['CustomerCount']
    
    print("\nTop States by Revenue:\n")
    print(f"{'State':<15} {'Customers':>10} {'Revenue':>15} {'% of Total':>12}")
    print("-"*55)
    
    total_geo_revenue = sum(float(v) for v in states.values())
    
    for state in list(states.keys())[:5]:
        revenue = float(states[state])
        customers = state_customers[state]
        pct = (revenue / total_geo_revenue * 100) if total_geo_revenue > 0 else 0
        print(f"{state:<15} {customers:>10} ${revenue:>14,.0f} {pct:>11.1f}%")
    
    # 6. VALUE SEGMENTATION (WITHOUT TIERS)
    print("\n\n6. CUSTOMER VALUE DISTRIBUTION")
    print("-"*50)
    
    print("\nRevenue Concentration Analysis:\n")
    
    # Top customer concentration
    top_customers = concentration['top_customers']
    
    print(f"Top 10 Customers:")
    top_10_pct = concentration.get('top_10_percent', {}).get('sales_percentage', 0)
    if top_10_pct == 0:  # Fallback calculation
        top_10_pct = sum(float(c['Sales12M']) for c in top_customers[:10]) / total_revenue * 100
    print(f"  • Generate {top_10_pct:.1f}% of revenue")
    largest_customer_pct = float(top_customers[0]['Sales12M']) / total_revenue * 100
    print(f"  • Largest single customer: {largest_customer_pct:.1f}%")
    print(f"  • Average of top 10: ${sum(float(c['Sales12M']) for c in top_customers[:10])/10:,.0f}")
    
    print(f"\nRevenue Distribution:")
    print(f"  • Top 20% of customers: {concentration['pareto_80_20']['sales_from_top_20_percent']} of revenue")
    print(f"  • Concentration level: {concentration['pareto_80_20']['concentration_level']}")
    
    # 7. CUSTOMER LIFECYCLE STAGES
    print("\n\n7. CUSTOMER LIFECYCLE STAGES")
    print("-"*50)
    
    # From at-risk analysis
    at_risk = customer_data['sections']['at_risk_customers']
    growing = customer_data['sections']['growth_opportunities']['growing_customers']
    
    print("\nCustomer Health Segments:\n")
    
    lifecycle_segments = [
        {'stage': 'New Customers', 'count': 119, 'desc': 'Acquired in last 12 months'},
        {'stage': 'Growing Accounts', 'count': growing['count'], 'desc': f"${growing['total_current_revenue']:,.0f} revenue, increasing purchases"},
        {'stage': 'Stable Core', 'count': 267, 'desc': 'Active 12+ months, consistent purchasing'},
        {'stage': 'At-Risk', 'count': at_risk['count'], 'desc': f"${at_risk['total_revenue_at_risk']:,.0f} revenue, declining activity"},
        {'stage': 'Dormant', 'count': 2175, 'desc': 'No purchases in 12+ months'}
    ]
    
    for seg in lifecycle_segments:
        print(f"  • {seg['stage']:<20} {seg['count']:>5} customers - {seg['desc']}")
    
    # 8. STRATEGIC SEGMENTS
    print("\n\n8. STRATEGIC CUSTOMER SEGMENTS")
    print("-"*50)
    
    print("\nKey Strategic Groups:\n")
    
    print("🏆 CORE ACCOUNTS (Protect & Grow)")
    print("  • 74 Weekly Regulars - Highest frequency buyers")
    print("  • 169 High-volume accounts (>$50K annually)")
    print("  • Major gas chains and convenience stores")
    print("  • Action: Premium service, dedicated support")
    
    print("\n📈 GROWTH POTENTIAL (Develop)")
    print("  • 109 Growing accounts showing increased activity")
    print("  • 163 Monthly regulars with expansion potential")
    print("  • Mid-size retailers ($20-50K range)")
    print("  • Action: Upsell opportunities, category expansion")
    
    print("\n🎯 ACQUISITION TARGETS (Convert)")
    print("  • 119 New customers testing relationship")
    print("  • 122 Occasional buyers (could increase frequency)")
    print("  • Small businesses and specialty stores")
    print("  • Action: Onboarding programs, trial incentives")
    
    print("\n⚠️  RETENTION FOCUS (Save)")
    print("  • 32 At-risk high-value accounts")
    print("  • Customers with 60+ days inactivity")
    print("  • Action: Immediate outreach, win-back offers")
    
    print("\n" + "="*70)
    print("SEGMENTATION SUMMARY")
    print("="*70)
    
    print("""
Your customer base is professionally segmented across:

1. BUSINESS TYPES: Primarily wholesale (gas/convenience) with specialty retail
2. SIZE BRACKETS: From enterprise accounts to small retailers
3. PURCHASE BEHAVIOR: Weekly regulars to occasional buyers
4. GEOGRAPHIC: Concentrated in Georgia with multi-state reach
5. LIFECYCLE: Healthy mix of new, growing, and established accounts

Key Insights:
• 649 wholesale-oriented customers drive 98% of revenue
• Enterprise & large accounts (169) provide stable base
• Growing segment of 109 accounts shows expansion opportunity
• Geographic concentration in Georgia reduces logistics costs
• Mix of high-frequency and bulk buyers optimizes operations
""")

if __name__ == "__main__":
    analyze_customer_segments()