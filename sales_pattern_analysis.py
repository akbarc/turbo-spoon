#!/usr/bin/env python3
"""
Sales Pattern & Industry Analysis
Business insights from customer behavior and industry segments
"""

import json
from datetime import datetime

def analyze_sales_patterns():
    """Analyze sales patterns across business segments"""
    
    print("📊 SALES PATTERN & INDUSTRY ANALYSIS")
    print("="*70)
    
    # Load reports
    with open('customer_analysis_report_20250903_185552.json', 'r') as f:
        customer_data = json.load(f)
    
    with open('bank_metrics_report_20250903_190744.json', 'r') as f:
        bank_data = json.load(f)
    
    # Extract data
    customer_groups = customer_data['sections']['customer_groups']
    purchase_patterns = customer_data['sections']['purchase_patterns']
    industry_segments = bank_data['sections']['industry_diversification']['segments']
    retention_data = customer_data['sections']['retention']['monthly_trend']
    concentration = customer_data['sections']['concentration']
    
    # 1. INDUSTRY SEGMENT PERFORMANCE
    print("\n1. INDUSTRY SEGMENT ANALYSIS")
    print("-"*50)
    print("\nRevenue by Industry Segment:\n")
    
    total_revenue = sum(float(seg['SegmentRevenue']) for seg in industry_segments)
    
    print(f"{'Industry Segment':<25} {'Customers':>10} {'Revenue':>15} {'% Total':>8} {'Avg Sale':>10}")
    print("-"*80)
    
    for seg in industry_segments:
        revenue = float(seg['SegmentRevenue'])
        pct = float(seg['RevenuePercent'])
        avg_sale = float(seg['AvgTransactionSize'])
        
        print(f"{seg['IndustrySegment']:<25} {seg['CustomerCount']:>10} ${revenue:>14,.0f} {pct:>7.1f}% ${avg_sale:>9,.0f}")
    
    print("-"*80)
    print(f"{'TOTAL':<25} {sum(s['CustomerCount'] for s in industry_segments):>10} ${total_revenue:>14,.0f} {100.0:>7.1f}%")
    
    # 2. SALES VELOCITY BY SEGMENT
    print("\n\n2. SALES VELOCITY & FREQUENCY")
    print("-"*50)
    print("\nTransaction Patterns by Industry:\n")
    
    print(f"{'Industry':<25} {'Transactions':>12} {'Trans/Customer':>15} {'Revenue/Trans':>15}")
    print("-"*70)
    
    for seg in sorted(industry_segments, key=lambda x: x['TransactionCount'], reverse=True):
        trans_per_cust = seg['TransactionCount'] / seg['CustomerCount'] if seg['CustomerCount'] > 0 else 0
        revenue_per_trans = float(seg['SegmentRevenue']) / seg['TransactionCount'] if seg['TransactionCount'] > 0 else 0
        
        print(f"{seg['IndustrySegment']:<25} {seg['TransactionCount']:>12,} {trans_per_cust:>15.1f} ${revenue_per_trans:>14,.0f}")
    
    # 3. CUSTOMER GROUP PERFORMANCE
    print("\n\n3. CUSTOMER GROUP DYNAMICS")
    print("-"*50)
    print("\nBusiness Type Performance Metrics:\n")
    
    total_group_revenue = sum(float(g['TotalSales']) for g in customer_groups)
    
    print(f"{'Customer Group':<30} {'Customers':>10} {'Avg Ticket':>12} {'Annual/Cust':>15} {'% Revenue':>10}")
    print("-"*80)
    
    for group in sorted(customer_groups, key=lambda x: float(x['TotalSales']), reverse=True):
        revenue = float(group['TotalSales'])
        pct = (revenue / total_group_revenue * 100) if total_group_revenue > 0 else 0
        
        print(f"{group['CustomerGroup']:<30} {group['CustomerCount']:>10} ${float(group['AvgTicket']):>11,.0f} ${float(group['AvgSalesPerCustomer']):>14,.0f} {pct:>9.1f}%")
    
    # 4. PURCHASE BEHAVIOR PATTERNS
    print("\n\n4. PURCHASE BEHAVIOR ANALYSIS")
    print("-"*50)
    print("\nCustomer Engagement Levels:\n")
    
    print(f"{'Frequency Segment':<20} {'Customers':>10} {'Avg Days':>10} {'Categories':>12} {'Characteristics':<30}")
    print("-"*85)
    
    for pattern in purchase_patterns:
        if pattern['FrequencySegment'] == 'Weekly Regular':
            characteristics = "Core customers, highest loyalty"
        elif pattern['FrequencySegment'] == 'Monthly Regular':
            characteristics = "Steady business, growth potential"
        elif pattern['FrequencySegment'] == 'Occasional':
            characteristics = "Opportunity for frequency increase"
        elif pattern['FrequencySegment'] == 'Rare':
            characteristics = "Re-engagement candidates"
        else:
            characteristics = "Win-back targets"
        
        print(f"{pattern['FrequencySegment']:<20} {pattern['CustomerCount']:>10} {pattern['AvgPurchaseDays']:>10.0f} {pattern['AvgCategories']:>12.0f} {characteristics:<30}")
    
    # 5. MONTHLY SALES TRENDS
    print("\n\n5. SALES MOMENTUM & TRENDS")
    print("-"*50)
    print("\nRecent Monthly Performance:\n")
    
    print(f"{'Period':<12} {'Active Customers':>17} {'Revenue':>15} {'Avg/Customer':>15} {'YoY Growth':>12}")
    print("-"*80)
    
    # Show last 6 months
    for month_data in retention_data[:6]:
        revenue = float(month_data['TotalSales'])
        avg_per_cust = revenue / month_data['ActiveCustomers'] if month_data['ActiveCustomers'] > 0 else 0
        yoy_growth = float(month_data.get('YoYGrowth', 0))
        
        period = f"{month_data['Year']}-{month_data['Month']:02d}"
        print(f"{period:<12} {month_data['ActiveCustomers']:>17} ${revenue:>14,.0f} ${avg_per_cust:>14,.0f} {yoy_growth:>11.1f}%")
    
    # 6. CONCENTRATION & RISK ANALYSIS
    print("\n\n6. SALES CONCENTRATION ANALYSIS")
    print("-"*50)
    
    print(f"\nRevenue Concentration Metrics:")
    # Calculate largest customer percent from top_customers data
    if concentration['top_customers']:
        largest_customer_pct = float(concentration['top_customers'][0]['Sales12M']) / total_group_revenue * 100
        print(f"  • Largest customer: {largest_customer_pct:.1f}% of revenue")
    print(f"  • Top 10 customers: {sum(float(c['Sales12M']) for c in concentration['top_customers'][:10])/total_group_revenue*100:.1f}% of revenue")
    print(f"  • Top 20% of customers: {concentration['pareto_80_20']['sales_from_top_20_percent']} of revenue")
    
    # Revenue brackets analysis
    brackets = concentration['revenue_brackets']
    total_customers = sum(brackets.values())
    
    print(f"\nCustomer Distribution by Annual Sales Volume:")
    print(f"  • >$100K: {brackets['over_100k']} customers ({brackets['over_100k']/total_customers*100:.1f}%)")
    print(f"  • $50-100K: {brackets['50k_to_100k']} customers ({brackets['50k_to_100k']/total_customers*100:.1f}%)")
    print(f"  • $20-50K: {brackets['20k_to_50k']} customers ({brackets['20k_to_50k']/total_customers*100:.1f}%)")
    print(f"  • $10-20K: {brackets['10k_to_20k']} customers ({brackets['10k_to_20k']/total_customers*100:.1f}%)")
    print(f"  • <$10K: {brackets['under_10k']} customers ({brackets['under_10k']/total_customers*100:.1f}%)")
    
    # 7. TOP ACCOUNTS ANALYSIS
    print("\n\n7. KEY ACCOUNT ANALYSIS")
    print("-"*50)
    print("\nTop 15 Revenue Generating Accounts:\n")
    
    print(f"{'Customer':<35} {'Company':<25} {'Annual Sales':>15} {'% of Total':>10}")
    print("-"*87)
    
    for customer in concentration['top_customers'][:15]:
        name = customer['CustomerName'][:34]
        company = customer['Company'][:24] if customer['Company'] else 'N/A'
        sales = float(customer['Sales12M'])
        pct = (sales / total_group_revenue * 100)
        
        print(f"{name:<35} {company:<25} ${sales:>14,.0f} {pct:>9.1f}%")
    
    # 8. CROSS-SELLING OPPORTUNITIES
    print("\n\n8. CROSS-SELLING & EXPANSION METRICS")
    print("-"*50)
    
    # Category breadth by frequency segment
    print("\nCategory Penetration by Customer Segment:\n")
    
    avg_categories = sum(p['AvgCategories'] for p in purchase_patterns) / len(purchase_patterns)
    
    print(f"Overall Average Categories per Customer: {avg_categories:.1f}")
    print("\nBy Purchase Frequency:")
    
    for pattern in sorted(purchase_patterns, key=lambda x: x['AvgCategories'], reverse=True):
        expansion_potential = pattern['AvgCategories'] - avg_categories
        if expansion_potential > 0:
            status = f"+{expansion_potential:.1f} above average"
        else:
            status = f"{expansion_potential:.1f} below average"
        
        print(f"  • {pattern['FrequencySegment']:<20}: {pattern['AvgCategories']:>3.0f} categories ({status})")
    
    # 9. GROWTH OPPORTUNITIES
    print("\n\n9. GROWTH OPPORTUNITY IDENTIFICATION")
    print("-"*50)
    
    growing_customers = customer_data['sections']['growth_opportunities']['growing_customers']
    at_risk = customer_data['sections']['at_risk_customers']
    
    print(f"\nGrowth Segments:")
    print(f"  • Growing Accounts: {growing_customers['count']} customers")
    print(f"    - Current Revenue: ${growing_customers['total_current_revenue']:,.0f}")
    if growing_customers['top_growing']:
        # Calculate average growth from top growing customers
        avg_growth = sum(float(c.get('GrowthPercent', 0)) for c in growing_customers['top_growing'][:5]) / min(5, len(growing_customers['top_growing']))
        print(f"    - Avg Growth (top 5): {avg_growth:.1f}%")
    
    print(f"\n  • At-Risk Accounts: {at_risk['count']} customers")
    print(f"    - Revenue at Risk: ${at_risk['total_revenue_at_risk']:,.0f}")
    print(f"    - Action Required: Immediate retention efforts")
    
    # Calculate expansion potential
    weekly_customers = next(p['CustomerCount'] for p in purchase_patterns if p['FrequencySegment'] == 'Weekly Regular')
    monthly_customers = next(p['CustomerCount'] for p in purchase_patterns if p['FrequencySegment'] == 'Monthly Regular')
    occasional_customers = next(p['CustomerCount'] for p in purchase_patterns if p['FrequencySegment'] == 'Occasional')
    
    # Estimate revenue impact of moving customers up frequency tiers
    avg_weekly_value = total_group_revenue * 0.30 / weekly_customers if weekly_customers > 0 else 50000
    avg_monthly_value = total_group_revenue * 0.25 / monthly_customers if monthly_customers > 0 else 25000
    
    print(f"\nFrequency Improvement Opportunities:")
    print(f"  • Convert 20% of Monthly to Weekly: ${monthly_customers * 0.2 * (avg_weekly_value - avg_monthly_value):,.0f} potential")
    print(f"  • Convert 30% of Occasional to Monthly: ${occasional_customers * 0.3 * avg_monthly_value:,.0f} potential")
    
    # 10. STRATEGIC SUMMARY
    print("\n" + "="*70)
    print("SALES STRATEGY SUMMARY")
    print("="*70)
    
    print(f"""
Key Sales Insights:

INDUSTRY DIVERSIFICATION:
• Diversified Retail drives 50% of revenue with 340 customers
• Energy/Gas segment provides 28% with 143 strategic accounts
• 8 distinct industry segments reduce concentration risk

CUSTOMER ENGAGEMENT:
• 74 Weekly Regulars form the core business foundation
• 163 Monthly Regulars offer frequency increase potential
• Average customer shops {avg_categories:.0f} product categories

REVENUE CONCENTRATION:
• Largest customer only {largest_customer_pct:.1f}% (excellent diversification)
• Top 20% generate {concentration['pareto_80_20']['sales_from_top_20_percent']} of revenue (healthy)
• 169 accounts over $50K provide stable base

GROWTH OPPORTUNITIES:
• {growing_customers['count']} growing accounts showing positive momentum
• Cross-selling potential in low-category customers
• Frequency improvement could add significant revenue

ACTION PRIORITIES:
1. Protect and expand Weekly Regular accounts
2. Increase purchase frequency of Monthly customers
3. Reactivate {at_risk['count']} at-risk accounts worth ${at_risk['total_revenue_at_risk']:,.0f}
4. Expand category penetration in single-category buyers
""")

if __name__ == "__main__":
    analyze_sales_patterns()