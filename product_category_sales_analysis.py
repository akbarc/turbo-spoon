#!/usr/bin/env python3
"""
Sales Pattern & Business Segment Analysis
Business-focused insights from customer purchasing behavior
"""

import json
import pandas as pd
from datetime import datetime

def analyze_product_categories():
    """Analyze sales patterns and business segments"""
    
    print("📊 SALES PATTERN & BUSINESS ANALYSIS")
    print("="*70)
    
    # Load reports
    with open('customer_analysis_report_20250903_185552.json', 'r') as f:
        customer_data = json.load(f)
    
    with open('bank_metrics_report_20250903_190744.json', 'r') as f:
        bank_data = json.load(f)
    
    # Extract relevant sections
    customer_groups = customer_data['sections']['customer_groups']
    purchase_patterns = customer_data['sections']['purchase_patterns']
    industry_segments = bank_data['sections']['industry_diversification']['segments']
    retention_data = customer_data['sections']['retention']['monthly_trend']
    
    # 1. CATEGORY PERFORMANCE OVERVIEW
    print("\n1. CATEGORY PERFORMANCE BREAKDOWN")
    print("-"*50)
    print("\nRevenue by Product Category:\n")
    
    # Calculate totals
    total_revenue = sum(float(cat['TotalSales']) for cat in categories)
    total_units = sum(cat['TotalQuantity'] for cat in categories)
    
    print(f"{'Category':<25} {'Revenue':>12} {'% Total':>8} {'Units':>10} {'Avg Price':>10}")
    print("-"*70)
    
    # Sort categories by revenue
    sorted_categories = sorted(categories, key=lambda x: float(x['TotalSales']), reverse=True)
    
    for cat in sorted_categories[:15]:  # Top 15 categories
        revenue = float(cat['TotalSales'])
        pct = (revenue / total_revenue * 100) if total_revenue > 0 else 0
        avg_price = revenue / cat['TotalQuantity'] if cat['TotalQuantity'] > 0 else 0
        
        # Shorten category names for display
        cat_name = cat['CategoryName'][:24]
        print(f"{cat_name:<25} ${revenue:>11,.0f} {pct:>7.1f}% {cat['TotalQuantity']:>10,} ${avg_price:>9.2f}")
    
    # Show summary for remaining categories
    if len(categories) > 15:
        other_revenue = sum(float(cat['TotalSales']) for cat in sorted_categories[15:])
        other_units = sum(cat['TotalQuantity'] for cat in sorted_categories[15:])
        other_pct = (other_revenue / total_revenue * 100) if total_revenue > 0 else 0
        print(f"{'Other Categories':<25} ${other_revenue:>11,.0f} {other_pct:>7.1f}% {other_units:>10,}")
    
    print("-"*70)
    print(f"{'TOTAL':<25} ${total_revenue:>11,.0f} {100.0:>7.1f}% {total_units:>10,}")
    
    # 2. TOBACCO PRODUCTS ANALYSIS
    print("\n\n2. TOBACCO PRODUCTS DEEP DIVE")
    print("-"*50)
    
    tobacco_categories = ['CIGARETTES', 'CIGARS', 'TOBACCO', 'TOBACCO PRODUCTS', 
                         'CIGARETTE', 'LITTLE CIGARS', 'CIGARILLOS']
    
    tobacco_cats = [cat for cat in categories if any(tob in cat['CategoryName'].upper() for tob in tobacco_categories)]
    tobacco_revenue = sum(float(cat['TotalSales']) for cat in tobacco_cats)
    tobacco_units = sum(cat['TotalQuantity'] for cat in tobacco_cats)
    tobacco_pct = (tobacco_revenue / total_revenue * 100) if total_revenue > 0 else 0
    
    print(f"\nTobacco Products Summary:")
    print(f"  • Total Revenue: ${tobacco_revenue:,.0f} ({tobacco_pct:.1f}% of total)")
    print(f"  • Total Units: {tobacco_units:,}")
    print(f"  • Categories: {len(tobacco_cats)}")
    
    if tobacco_cats:
        print("\nTop Tobacco Categories:")
        for cat in sorted(tobacco_cats, key=lambda x: float(x['TotalSales']), reverse=True)[:5]:
            revenue = float(cat['TotalSales'])
            pct = (revenue / tobacco_revenue * 100)
            print(f"  • {cat['CategoryName'][:30]:30s}: ${revenue:>10,.0f} ({pct:>5.1f}% of tobacco)")
    
    # 3. NON-TOBACCO ANALYSIS
    print("\n\n3. NON-TOBACCO PRODUCTS ANALYSIS")
    print("-"*50)
    
    non_tobacco_cats = [cat for cat in categories if not any(tob in cat['CategoryName'].upper() for tob in tobacco_categories)]
    non_tobacco_revenue = sum(float(cat['TotalSales']) for cat in non_tobacco_cats)
    non_tobacco_pct = (non_tobacco_revenue / total_revenue * 100) if total_revenue > 0 else 0
    
    print(f"\nNon-Tobacco Products Summary:")
    print(f"  • Total Revenue: ${non_tobacco_revenue:,.0f} ({non_tobacco_pct:.1f}% of total)")
    print(f"  • Categories: {len(non_tobacco_cats)}")
    
    # Group non-tobacco into logical segments
    beverage_keywords = ['BEER', 'WINE', 'LIQUOR', 'SODA', 'WATER', 'JUICE', 'DRINK', 'BEVERAGE']
    snack_keywords = ['CANDY', 'CHIPS', 'SNACK', 'GUM', 'NUTS', 'POPCORN']
    grocery_keywords = ['GROCERY', 'FOOD', 'DAIRY', 'MEAT', 'PRODUCE']
    other_keywords = ['VAPE', 'CBD', 'KRATOM', 'ACCESSORIES', 'LOTTERY']
    
    segments = {
        'Beverages': [],
        'Snacks & Candy': [],
        'Grocery & Food': [],
        'Vape & Alternative': [],
        'Other Products': []
    }
    
    for cat in non_tobacco_cats:
        cat_upper = cat['CategoryName'].upper()
        assigned = False
        
        if any(keyword in cat_upper for keyword in beverage_keywords):
            segments['Beverages'].append(cat)
            assigned = True
        elif any(keyword in cat_upper for keyword in snack_keywords):
            segments['Snacks & Candy'].append(cat)
            assigned = True
        elif any(keyword in cat_upper for keyword in grocery_keywords):
            segments['Grocery & Food'].append(cat)
            assigned = True
        elif any(keyword in cat_upper for keyword in other_keywords):
            segments['Vape & Alternative'].append(cat)
            assigned = True
        
        if not assigned:
            segments['Other Products'].append(cat)
    
    print("\nNon-Tobacco Segment Breakdown:")
    for segment_name, segment_cats in segments.items():
        if segment_cats:
            segment_revenue = sum(float(cat['TotalSales']) for cat in segment_cats)
            segment_pct = (segment_revenue / non_tobacco_revenue * 100) if non_tobacco_revenue > 0 else 0
            print(f"  • {segment_name:<20}: ${segment_revenue:>10,.0f} ({segment_pct:>5.1f}% of non-tobacco)")
    
    # 4. TOP SELLING PRODUCTS
    print("\n\n4. TOP SELLING PRODUCTS")
    print("-"*50)
    print("\nTop 20 Products by Revenue:\n")
    
    print(f"{'Product':<40} {'Category':<20} {'Revenue':>12} {'Units':>8}")
    print("-"*82)
    
    for i, product in enumerate(top_products[:20], 1):
        prod_name = product['ProductName'][:39]
        cat_name = product['CategoryName'][:19] if product.get('CategoryName') else 'Unknown'
        revenue = float(product['TotalSales'])
        units = product['TotalQuantity']
        
        print(f"{prod_name:<40} {cat_name:<20} ${revenue:>11,.0f} {units:>8,}")
    
    # 5. CATEGORY VELOCITY ANALYSIS
    print("\n\n5. CATEGORY VELOCITY & TURNOVER")
    print("-"*50)
    print("\nFastest Moving Categories (by unit volume):\n")
    
    # Sort by quantity instead of revenue
    sorted_by_units = sorted(categories, key=lambda x: x['TotalQuantity'], reverse=True)
    
    print(f"{'Category':<30} {'Units/Month':>12} {'Customers':>10} {'Avg Units/Order':>15}")
    print("-"*70)
    
    for cat in sorted_by_units[:10]:
        units_per_month = cat['TotalQuantity'] / 12  # Assuming annual data
        avg_units_per_order = cat['TotalQuantity'] / cat['OrderCount'] if cat['OrderCount'] > 0 else 0
        
        cat_name = cat['CategoryName'][:29]
        print(f"{cat_name:<30} {units_per_month:>12,.0f} {cat['CustomerCount']:>10} {avg_units_per_order:>15.1f}")
    
    # 6. CATEGORY CONCENTRATION
    print("\n\n6. CATEGORY CONCENTRATION ANALYSIS")
    print("-"*50)
    
    # Calculate HHI for categories
    category_hhi = sum((float(cat['TotalSales'])/total_revenue * 100)**2 for cat in categories)
    
    print(f"\nCategory Diversity Metrics:")
    print(f"  • Total Categories: {len(categories)}")
    print(f"  • Category HHI: {category_hhi:.0f}")
    
    if category_hhi < 1500:
        concentration = "Well Diversified"
    elif category_hhi < 2500:
        concentration = "Moderately Concentrated"
    else:
        concentration = "Highly Concentrated"
    
    print(f"  • Concentration Level: {concentration}")
    
    # Top category concentrations
    top_5_revenue = sum(float(cat['TotalSales']) for cat in sorted_categories[:5])
    top_10_revenue = sum(float(cat['TotalSales']) for cat in sorted_categories[:10])
    
    print(f"\nRevenue Concentration:")
    print(f"  • Top 5 Categories: {top_5_revenue/total_revenue*100:.1f}% of revenue")
    print(f"  • Top 10 Categories: {top_10_revenue/total_revenue*100:.1f}% of revenue")
    
    # 7. CATEGORY CUSTOMER PENETRATION
    print("\n\n7. CATEGORY CUSTOMER REACH")
    print("-"*50)
    print("\nCategories with Broadest Customer Base:\n")
    
    # Sort by customer count
    sorted_by_customers = sorted(categories, key=lambda x: x['CustomerCount'], reverse=True)
    
    total_active_customers = 676  # From reports
    
    print(f"{'Category':<30} {'Customers':>10} {'Penetration':>12} {'Avg/Customer':>12}")
    print("-"*65)
    
    for cat in sorted_by_customers[:10]:
        penetration = (cat['CustomerCount'] / total_active_customers * 100)
        avg_per_customer = float(cat['TotalSales']) / cat['CustomerCount'] if cat['CustomerCount'] > 0 else 0
        
        cat_name = cat['CategoryName'][:29]
        print(f"{cat_name:<30} {cat['CustomerCount']:>10} {penetration:>11.1f}% ${avg_per_customer:>11,.0f}")
    
    # 8. PROFIT OPPORTUNITY ANALYSIS
    print("\n\n8. PROFIT OPTIMIZATION OPPORTUNITIES")
    print("-"*50)
    
    print("\nHigh-Value, Low-Penetration Categories (Expansion Opportunities):")
    
    # Find categories with high average transaction but low penetration
    opportunities = []
    for cat in categories:
        if cat['CustomerCount'] > 0:
            avg_per_customer = float(cat['TotalSales']) / cat['CustomerCount']
            penetration = (cat['CustomerCount'] / total_active_customers * 100)
            
            if penetration < 20 and avg_per_customer > 1000:  # Low penetration, high value
                opportunities.append({
                    'category': cat['CategoryName'],
                    'penetration': penetration,
                    'avg_value': avg_per_customer,
                    'potential': (total_active_customers * 0.3 - cat['CustomerCount']) * avg_per_customer
                })
    
    opportunities.sort(key=lambda x: x['potential'], reverse=True)
    
    for opp in opportunities[:5]:
        print(f"  • {opp['category'][:30]:30s}: {opp['penetration']:>5.1f}% penetration, ${opp['avg_value']:>8,.0f} avg/customer")
        print(f"    Potential if 30% adoption: ${opp['potential']:>10,.0f}")
    
    # 9. SEASONAL/TRENDING ANALYSIS
    print("\n\n9. PRODUCT MIX INSIGHTS")
    print("-"*50)
    
    # Calculate average basket composition
    avg_categories_per_customer = sum(p['AvgCategories'] for p in purchase_patterns) / len(purchase_patterns)
    
    print(f"\nPurchase Behavior Patterns:")
    print(f"  • Average categories per customer: {avg_categories_per_customer:.1f}")
    print(f"  • Total product categories: {len(categories)}")
    print(f"  • Active categories (>$10K revenue): {len([c for c in categories if float(c['TotalSales']) > 10000])}")
    
    # Basket composition by customer segment
    print("\nCategory Mix by Customer Frequency:")
    for pattern in purchase_patterns:
        print(f"  • {pattern['FrequencySegment']:15s}: {pattern['AvgCategories']:.0f} categories on average")
    
    # 10. STRATEGIC CATEGORY SUMMARY
    print("\n" + "="*70)
    print("CATEGORY STRATEGY SUMMARY")
    print("="*70)
    
    print("""
Key Category Insights:

REVENUE DRIVERS:
• Tobacco products dominate at {:.0f}% of revenue
• Top 5 categories generate {:.0f}% of total revenue
• Average customer purchases from {:.0f} different categories

DIVERSIFICATION:
• {} total active categories
• Category HHI of {:.0f} indicates {}
• Non-tobacco revenue represents ${:,.0f} ({:.0f}%)

GROWTH OPPORTUNITIES:
• Low-penetration, high-value categories identified
• Cross-selling potential in complementary categories
• Expand non-tobacco to reduce concentration risk

OPERATIONAL FOCUS:
• Fast-moving categories require inventory optimization
• High-value categories need premium placement
• Bundle opportunities in frequently co-purchased items
""".format(
        tobacco_pct,
        top_5_revenue/total_revenue*100,
        avg_categories_per_customer,
        len(categories),
        category_hhi,
        concentration,
        non_tobacco_revenue,
        non_tobacco_pct
    ))

if __name__ == "__main__":
    analyze_product_categories()