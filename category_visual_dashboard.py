#!/usr/bin/env python3
"""
Create visual dashboard for category analysis
"""

import pandas as pd
import glob
import os

def create_visual_dashboard():
    """Create a simple text-based visual dashboard from the latest analysis"""

    # Find the latest comprehensive analysis file
    files = glob.glob("category_analysis_comprehensive_*.csv")
    if not files:
        print("No analysis files found. Please run comprehensive_category_analysis.py first.")
        return

    latest_file = max(files, key=os.path.getctime)
    print(f"Loading data from: {latest_file}\n")

    df = pd.read_csv(latest_file)

    # Create visual dashboard
    print("="*120)
    print("PRODUCT CATEGORY STRATEGIC DASHBOARD")
    print("="*120)

    # Revenue vs Margin Quadrant Analysis
    print("\n📊 REVENUE vs MARGIN QUADRANT ANALYSIS")
    print("-"*120)

    # Define quadrants
    median_revenue_share = df['RevenueSharePercent'].median()
    median_margin = df['MarginPercent'].median()

    print(f"Median Revenue Share: {median_revenue_share:.2f}% | Median Margin: {median_margin:.2f}%\n")

    # Quadrant 1: High Revenue, High Margin (Stars)
    stars = df[(df['RevenueSharePercent'] > median_revenue_share) &
               (df['MarginPercent'] > median_margin)].sort_values('Revenue', ascending=False)

    print(f"⭐ STARS (High Revenue + High Margin) - {len(stars)} categories")
    print(f"{'Category':<30} {'Revenue':>15} {'Margin%':>10} {'Rev Share%':>12} {'Growth%':>10}")
    print("-"*120)
    for _, row in stars.iterrows():
        print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['MarginPercent']:>9.1f}% {row['RevenueSharePercent']:>11.1f}% {row['RevenueGrowthPercent']:>9.1f}%")

    # Quadrant 2: High Revenue, Low Margin (Cash Cows - but need margin work)
    cash_cows = df[(df['RevenueSharePercent'] > median_revenue_share) &
                   (df['MarginPercent'] <= median_margin)].sort_values('Revenue', ascending=False)

    print(f"\n💵 CASH COWS (High Revenue + Low Margin) - {len(cash_cows)} categories")
    print("ACTION: Improve margins through pricing or cost reduction")
    print(f"{'Category':<30} {'Revenue':>15} {'Margin%':>10} {'Rev Share%':>12} {'Potential Gain':>15}")
    print("-"*120)
    for _, row in cash_cows.iterrows():
        # Calculate potential profit gain with 2% margin improvement
        potential_gain = row['Revenue'] * 0.02
        print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['MarginPercent']:>9.1f}% {row['RevenueSharePercent']:>11.1f}% ${potential_gain:>14,.0f}")

    # Quadrant 3: Low Revenue, High Margin (Question Marks - niche opportunities)
    question_marks = df[(df['RevenueSharePercent'] <= median_revenue_share) &
                       (df['MarginPercent'] > median_margin)].sort_values('MarginPercent', ascending=False)

    print(f"\n❓ QUESTION MARKS (Low Revenue + High Margin) - {len(question_marks)} categories")
    print("ACTION: Consider expanding high-margin niches or maintain as specialty items")
    print(f"{'Category':<30} {'Revenue':>15} {'Margin%':>10} {'Transactions':>12} {'Growth%':>10}")
    print("-"*120)
    for _, row in question_marks.head(15).iterrows():
        print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['MarginPercent']:>9.1f}% {row['Transactions']:>11,} {row['RevenueGrowthPercent']:>9.1f}%")

    # Quadrant 4: Low Revenue, Low Margin (Dogs - consider eliminating)
    dogs = df[(df['RevenueSharePercent'] <= median_revenue_share) &
             (df['MarginPercent'] <= median_margin)].sort_values('GrossProfit', ascending=True)

    print(f"\n🐕 DOGS (Low Revenue + Low Margin) - {len(dogs)} categories")
    print("ACTION: Strong candidates for elimination")
    print(f"{'Category':<30} {'Revenue':>15} {'Margin%':>10} {'Gross Profit':>15} {'Days Since Sale':>15}")
    print("-"*120)
    for _, row in dogs.head(15).iterrows():
        print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['MarginPercent']:>9.1f}% ${row['GrossProfit']:>14,.2f} {row['DaysSinceLastSale']:>14}")

    # Financial Impact Summary
    print("\n" + "="*120)
    print("💰 FINANCIAL IMPACT ANALYSIS")
    print("="*120)

    total_revenue = df['Revenue'].sum()
    total_profit = df['GrossProfit'].sum()

    print(f"\nCurrent State:")
    print(f"  Total Revenue:      ${total_revenue:,.2f}")
    print(f"  Total Gross Profit: ${total_profit:,.2f}")
    print(f"  Overall Margin:     {(total_profit/total_revenue*100):.1f}%")

    # Calculate impact of eliminating dogs with negative profit
    negative_profit_dogs = dogs[dogs['GrossProfit'] < 0]
    if len(negative_profit_dogs) > 0:
        dogs_revenue = negative_profit_dogs['Revenue'].sum()
        dogs_profit = negative_profit_dogs['GrossProfit'].sum()

        print(f"\nIf we eliminate {len(negative_profit_dogs)} categories with NEGATIVE profit:")
        print(f"  Lost Revenue:       ${dogs_revenue:,.2f} ({dogs_revenue/total_revenue*100:.1f}%)")
        print(f"  GAINED Profit:      ${abs(dogs_profit):,.2f}")
        print(f"  New Total Profit:   ${total_profit + abs(dogs_profit):,.2f}")
        print(f"  New Margin:         {((total_profit + abs(dogs_profit))/(total_revenue - dogs_revenue)*100):.1f}%")

    # Calculate impact of improving cash cow margins
    if len(cash_cows) > 0:
        cash_cows_revenue = cash_cows['Revenue'].sum()
        potential_gain_2pct = cash_cows_revenue * 0.02
        potential_gain_3pct = cash_cows_revenue * 0.03

        print(f"\nIf we improve margins on {len(cash_cows)} CASH COW categories:")
        print(f"  Cash Cow Revenue:   ${cash_cows_revenue:,.2f} ({cash_cows_revenue/total_revenue*100:.1f}%)")
        print(f"  +2% margin gain:    ${potential_gain_2pct:,.2f} extra profit")
        print(f"  +3% margin gain:    ${potential_gain_3pct:,.2f} extra profit")

    # Top growth opportunities
    print("\n" + "="*120)
    print("📈 TOP GROWTH OPPORTUNITIES")
    print("="*120)

    growth_opps = df[(df['RevenueGrowthPercent'] > 10) &
                     (df['MarginPercent'] > 15)].sort_values('RevenueGrowthPercent', ascending=False)

    if len(growth_opps) > 0:
        print(f"\nCategories with >10% growth AND >15% margins ({len(growth_opps)} found):")
        print(f"{'Category':<30} {'Revenue':>15} {'Margin%':>10} {'Growth%':>10} {'Action':>30}")
        print("-"*120)
        for _, row in growth_opps.iterrows():
            action = "DOUBLE DOWN - Increase inventory"
            print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['MarginPercent']:>9.1f}% {row['RevenueGrowthPercent']:>9.1f}% {action:>30}")
    else:
        print("No categories with both strong growth AND strong margins found.")

    # Declining high-revenue categories
    print("\n" + "="*120)
    print("⚠️  WARNING: DECLINING HIGH-REVENUE CATEGORIES")
    print("="*120)

    declining_important = df[(df['RevenueSharePercent'] > 5) &
                            (df['RevenueGrowthPercent'] < -5)].sort_values('Revenue', ascending=False)

    if len(declining_important) > 0:
        print(f"\nCategories with >5% revenue share but declining ({len(declining_important)} found):")
        print(f"{'Category':<30} {'Revenue':>15} {'Share%':>10} {'Growth%':>10} {'Action':>30}")
        print("-"*120)
        for _, row in declining_important.iterrows():
            print(f"{row['Category']:<30} ${row['Revenue']:>14,.0f} {row['RevenueSharePercent']:>9.1f}% {row['RevenueGrowthPercent']:>9.1f}% {'INVESTIGATE - Find cause':>30}")

    # FINAL RECOMMENDATIONS
    print("\n" + "="*120)
    print("🎯 FINAL STRATEGIC RECOMMENDATIONS")
    print("="*120)

    print("\n1. IMMEDIATE ELIMINATIONS:")
    kill_list = df[(df['Classification'] == 'MONEY_LOSER') |
                   ((df['Classification'] == 'UNDERPERFORMER') & (df['RevenueSharePercent'] < 0.1))]
    for _, row in kill_list.iterrows():
        print(f"   ❌ {row['Category']:<30} ${row['Revenue']:>12,.0f} revenue, {row['MarginPercent']:>5.1f}% margin")

    print("\n2. FOCUS & EXPAND:")
    expand_list = df[(df['Classification'] == 'MONEY_MAKER') |
                     ((df['MarginPercent'] > 20) & (df['RevenueGrowthPercent'] > 0))]
    for _, row in expand_list.head(10).iterrows():
        print(f"   ✅ {row['Category']:<30} ${row['Revenue']:>12,.0f} revenue, {row['MarginPercent']:>5.1f}% margin")

    print("\n3. OPTIMIZE PRICING:")
    optimize_list = df[(df['Classification'] == 'STRATEGIC') |
                       ((df['RevenueSharePercent'] > 2) & (df['MarginPercent'] < 10))]
    for _, row in optimize_list.head(10).iterrows():
        potential = row['Revenue'] * 0.02
        print(f"   🔧 {row['Category']:<30} Current: {row['MarginPercent']:>5.1f}% → Target: +2% = ${potential:>10,.0f} gain")

    print("\n" + "="*120)
    print("Analysis complete! Review CSV files for detailed product-level data.")
    print("="*120)

if __name__ == "__main__":
    create_visual_dashboard()
