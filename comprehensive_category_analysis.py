#!/usr/bin/env python3
"""
Comprehensive Product Category Analysis
Analyzes all categories to identify money makers, money losers, and make keep/kill recommendations
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def comprehensive_category_analysis():
    """
    Complete category performance analysis with keep/kill recommendations
    """

    # Date ranges
    end_date = datetime.now()
    start_12mo = end_date - timedelta(days=365)
    start_24mo = end_date - timedelta(days=730)

    logger.info(f"Analyzing categories from {start_12mo.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Main comprehensive query
    main_query = f"""
    WITH Last12Months AS (
        SELECT
            ISNULL(c.Name, 'Uncategorized') as Category,
            c.ID as CategoryID,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as Units,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            AVG(te.Price * te.Quantity) as AvgTransactionValue,
            COUNT(DISTINCT CAST(t.[Time] AS DATE)) as DaysWithSales,
            MIN(t.[Time]) as FirstSale,
            MAX(t.[Time]) as LastSale
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_12mo.strftime('%Y-%m-%d')}'
            AND t.[Time] <= '{end_date.strftime('%Y-%m-%d')}'
            AND te.Price > 0
        GROUP BY c.Name, c.ID
    ),
    Previous12Months AS (
        SELECT
            ISNULL(c.Name, 'Uncategorized') as Category,
            SUM(te.Price * te.Quantity) as PrevRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as PrevGrossProfit
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_24mo.strftime('%Y-%m-%d')}'
            AND t.[Time] < '{start_12mo.strftime('%Y-%m-%d')}'
            AND te.Price > 0
        GROUP BY c.Name
    ),
    TotalMetrics AS (
        SELECT
            SUM(Revenue) as TotalRevenue,
            SUM(GrossProfit) as TotalGrossProfit
        FROM Last12Months
    )
    SELECT
        l.Category,
        l.CategoryID,
        l.Transactions,
        l.Units,
        l.Revenue,
        l.TotalCost,
        l.GrossProfit,
        CASE
            WHEN l.Revenue > 0 THEN (l.GrossProfit / l.Revenue) * 100
            ELSE 0
        END as MarginPercent,
        CASE
            WHEN t.TotalRevenue > 0 THEN (l.Revenue / t.TotalRevenue) * 100
            ELSE 0
        END as RevenueSharePercent,
        CASE
            WHEN t.TotalGrossProfit > 0 THEN (l.GrossProfit / t.TotalGrossProfit) * 100
            ELSE 0
        END as ProfitContributionPercent,
        l.AvgTransactionValue,
        l.DaysWithSales,
        ISNULL(p.PrevRevenue, 0) as PrevYearRevenue,
        ISNULL(p.PrevGrossProfit, 0) as PrevYearGrossProfit,
        CASE
            WHEN ISNULL(p.PrevRevenue, 0) > 0
            THEN ((l.Revenue - p.PrevRevenue) / p.PrevRevenue) * 100
            ELSE 0
        END as RevenueGrowthPercent,
        l.FirstSale,
        l.LastSale,
        DATEDIFF(day, l.LastSale, GETDATE()) as DaysSinceLastSale
    FROM Last12Months l
    CROSS JOIN TotalMetrics t
    LEFT JOIN Previous12Months p ON l.Category = p.Category
    WHERE l.Revenue > 0
    ORDER BY l.Revenue DESC
    """

    # Category detail with top products
    top_products_query = """
    SELECT
        c.Name as Category,
        i.Description as Product,
        SUM(te.Price * te.Quantity) as ProductRevenue,
        SUM((te.Price - te.Cost) * te.Quantity) as ProductProfit,
        SUM(te.Quantity) as UnitsSold,
        CASE
            WHEN SUM(te.Price * te.Quantity) > 0
            THEN (SUM((te.Price - te.Cost) * te.Quantity) / SUM(te.Price * te.Quantity)) * 100
            ELSE 0
        END as ProductMargin
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    LEFT JOIN Category c ON i.CategoryID = c.ID
    WHERE t.[Time] >= DATEADD(YEAR, -1, GETDATE())
        AND te.Price > 0
    GROUP BY c.Name, i.Description
    ORDER BY c.Name, ProductRevenue DESC
    """

    try:
        with SQLServerConnection() as db:
            # Get main analysis
            df = db.execute_query(main_query, description="Comprehensive category analysis")

            if df.empty:
                logger.warning("No data returned from analysis")
                return None

            # Get top products per category
            df_products = db.execute_query(top_products_query, description="Top products by category")

            # Calculate performance scores
            df['PerformanceScore'] = (
                (df['MarginPercent'] / 100) * 40 +  # 40% weight on margin
                (df['RevenueSharePercent'] / 100) * 30 +  # 30% weight on revenue share
                (df['ProfitContributionPercent'] / 100) * 30  # 30% weight on profit contribution
            ) * 100

            # Classify categories
            def classify_category(row):
                margin = row['MarginPercent']
                revenue_share = row['RevenueSharePercent']
                profit_contrib = row['ProfitContributionPercent']
                growth = row['RevenueGrowthPercent']

                # Money Makers: High margin (>20%) OR significant revenue with decent margin
                if (margin > 20 and revenue_share > 1) or (margin > 15 and revenue_share > 5):
                    return 'MONEY_MAKER'

                # Strategic: Lower margin but high volume/revenue
                elif margin > 5 and revenue_share > 5:
                    return 'STRATEGIC'

                # Money Losers: Negative or very low margin
                elif margin < 5 and profit_contrib < 1:
                    return 'MONEY_LOSER'

                # Underperformer: Low revenue and declining
                elif revenue_share < 1 and growth < -10:
                    return 'UNDERPERFORMER'

                # Investigate: Mixed signals
                else:
                    return 'INVESTIGATE'

            df['Classification'] = df.apply(classify_category, axis=1)

            # Add recommendations
            def get_recommendation(row):
                classification = row['Classification']
                margin = row['MarginPercent']
                revenue_share = row['RevenueSharePercent']
                growth = row['RevenueGrowthPercent']

                if classification == 'MONEY_MAKER':
                    return 'KEEP - Expand inventory and marketing'
                elif classification == 'STRATEGIC':
                    if margin < 10:
                        return 'OPTIMIZE - Find ways to improve margins'
                    else:
                        return 'KEEP - Important for traffic and volume'
                elif classification == 'MONEY_LOSER':
                    return 'KILL - Discontinue or drastically reduce inventory'
                elif classification == 'UNDERPERFORMER':
                    if revenue_share < 0.1:
                        return 'KILL - Minimal impact, poor performance'
                    else:
                        return 'INVESTIGATE - Review SKUs, consider reducing'
                else:
                    return 'INVESTIGATE - Analyze individual SKU performance'

            df['Recommendation'] = df.apply(get_recommendation, axis=1)

            # Print comprehensive report
            print("\n" + "="*100)
            print("COMPREHENSIVE PRODUCT CATEGORY ANALYSIS - LAST 12 MONTHS")
            print("="*100)
            print(f"Analysis Period: {start_12mo.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"Total Categories Analyzed: {len(df)}")

            # Overall metrics
            total_revenue = df['Revenue'].sum()
            total_profit = df['GrossProfit'].sum()
            overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

            print(f"\n📊 OVERALL BUSINESS METRICS:")
            print(f"   Total Revenue:      ${total_revenue:,.2f}")
            print(f"   Total Gross Profit: ${total_profit:,.2f}")
            print(f"   Overall Margin:     {overall_margin:.1f}%")
            print(f"   Total Transactions: {df['Transactions'].sum():,}")
            print(f"   Total Units Sold:   {df['Units'].sum():,.0f}")

            # Classification summary
            print("\n" + "="*100)
            print("CATEGORY CLASSIFICATION SUMMARY")
            print("="*100)

            classification_summary = df.groupby('Classification').agg({
                'Revenue': 'sum',
                'GrossProfit': 'sum',
                'Category': 'count'
            }).reset_index()

            classification_summary['MarginPercent'] = (
                classification_summary['GrossProfit'] / classification_summary['Revenue'] * 100
            )

            for _, row in classification_summary.iterrows():
                classification = row['Classification']
                count = row['Category']
                revenue = row['Revenue']
                profit = row['GrossProfit']
                margin = row['MarginPercent']
                revenue_pct = (revenue / total_revenue * 100)

                print(f"\n{classification}:")
                print(f"   Categories: {count}")
                print(f"   Revenue: ${revenue:,.2f} ({revenue_pct:.1f}% of total)")
                print(f"   Gross Profit: ${profit:,.2f}")
                print(f"   Margin: {margin:.1f}%")

            # Top 20 categories by revenue
            print("\n" + "="*100)
            print("TOP 20 CATEGORIES BY REVENUE")
            print("="*100)
            print(f"{'Rank':<5} {'Category':<25} {'Revenue':<15} {'Margin%':<10} {'Share%':<10} {'Classification':<15} {'Recommendation':<30}")
            print("-"*100)

            for idx, row in df.head(20).iterrows():
                rank = idx + 1
                category = row['Category'][:24]
                revenue = row['Revenue']
                margin = row['MarginPercent']
                share = row['RevenueSharePercent']
                classification = row['Classification']
                recommendation = row['Recommendation'][:29]

                print(f"{rank:<5} {category:<25} ${revenue:>13,.0f} {margin:>8.1f}% {share:>8.1f}% {classification:<15} {recommendation:<30}")

            # Money makers detail
            money_makers = df[df['Classification'] == 'MONEY_MAKER'].sort_values('Revenue', ascending=False)
            if not money_makers.empty:
                print("\n" + "="*100)
                print(f"💰 MONEY MAKERS ({len(money_makers)} categories)")
                print("="*100)
                print(f"Total Revenue: ${money_makers['Revenue'].sum():,.2f} ({money_makers['Revenue'].sum()/total_revenue*100:.1f}% of total)")
                print(f"Total Profit: ${money_makers['GrossProfit'].sum():,.2f}")
                print(f"\n{'Category':<30} {'Revenue':<15} {'Margin%':<10} {'Growth%':<10}")
                print("-"*100)
                for _, row in money_makers.head(15).iterrows():
                    print(f"{row['Category']:<30} ${row['Revenue']:>13,.0f} {row['MarginPercent']:>8.1f}% {row['RevenueGrowthPercent']:>8.1f}%")

            # Money losers detail
            money_losers = df[df['Classification'] == 'MONEY_LOSER'].sort_values('GrossProfit', ascending=True)
            if not money_losers.empty:
                print("\n" + "="*100)
                print(f"❌ MONEY LOSERS ({len(money_losers)} categories)")
                print("="*100)
                print(f"Total Revenue: ${money_losers['Revenue'].sum():,.2f}")
                print(f"Total Profit: ${money_losers['GrossProfit'].sum():,.2f}")
                print(f"\n{'Category':<30} {'Revenue':<15} {'Margin%':<10} {'Profit':<15}")
                print("-"*100)
                for _, row in money_losers.iterrows():
                    print(f"{row['Category']:<30} ${row['Revenue']:>13,.0f} {row['MarginPercent']:>8.1f}% ${row['GrossProfit']:>13,.2f}")

            # Underperformers
            underperformers = df[df['Classification'] == 'UNDERPERFORMER'].sort_values('Revenue', ascending=True)
            if not underperformers.empty:
                print("\n" + "="*100)
                print(f"⚠️  UNDERPERFORMERS ({len(underperformers)} categories)")
                print("="*100)
                print(f"\n{'Category':<30} {'Revenue':<15} {'Margin%':<10} {'Growth%':<10} {'Days Since Sale':<15}")
                print("-"*100)
                for _, row in underperformers.iterrows():
                    print(f"{row['Category']:<30} ${row['Revenue']:>13,.0f} {row['MarginPercent']:>8.1f}% {row['RevenueGrowthPercent']:>8.1f}% {row['DaysSinceLastSale']:>13}")

            # Strategic categories
            strategic = df[df['Classification'] == 'STRATEGIC'].sort_values('Revenue', ascending=False)
            if not strategic.empty:
                print("\n" + "="*100)
                print(f"🎯 STRATEGIC CATEGORIES ({len(strategic)} categories)")
                print("="*100)
                print("High volume/revenue but lower margins - important for traffic")
                print(f"\n{'Category':<30} {'Revenue':<15} {'Margin%':<10} {'Share%':<10} {'Transactions':<12}")
                print("-"*100)
                for _, row in strategic.head(10).iterrows():
                    print(f"{row['Category']:<30} ${row['Revenue']:>13,.0f} {row['MarginPercent']:>8.1f}% {row['RevenueSharePercent']:>8.1f}% {row['Transactions']:>10,}")

            # Key insights
            print("\n" + "="*100)
            print("KEY INSIGHTS & RECOMMENDATIONS")
            print("="*100)

            # Calculate potential impact
            loser_revenue_impact = money_losers['Revenue'].sum() if not money_losers.empty else 0
            loser_profit_impact = money_losers['GrossProfit'].sum() if not money_losers.empty else 0

            print(f"\n1. IMMEDIATE ACTIONS:")
            if not money_losers.empty:
                print(f"   • Eliminate {len(money_losers)} money-losing categories")
                print(f"   • This will reduce revenue by ${loser_revenue_impact:,.2f} ({loser_revenue_impact/total_revenue*100:.1f}%)")
                print(f"   • But IMPROVE profit by ${abs(loser_profit_impact):,.2f}")

            if not money_makers.empty:
                print(f"\n2. GROWTH OPPORTUNITIES:")
                print(f"   • Focus on {len(money_makers)} money-maker categories")
                print(f"   • They generate {money_makers['Revenue'].sum()/total_revenue*100:.1f}% of revenue at {money_makers['GrossProfit'].sum()/money_makers['Revenue'].sum()*100:.1f}% margin")

                # Top growth opportunities
                growth_opps = money_makers[money_makers['RevenueGrowthPercent'] > 10].sort_values('RevenueGrowthPercent', ascending=False)
                if not growth_opps.empty:
                    print(f"   • {len(growth_opps)} categories showing strong growth (>10%)")
                    for _, row in growth_opps.head(5).iterrows():
                        print(f"     - {row['Category']}: +{row['RevenueGrowthPercent']:.1f}% growth, ${row['Revenue']:,.0f} revenue")

            if not strategic.empty:
                print(f"\n3. MARGIN OPTIMIZATION:")
                low_margin_strategic = strategic[strategic['MarginPercent'] < 10]
                if not low_margin_strategic.empty:
                    print(f"   • Review pricing on {len(low_margin_strategic)} strategic categories with <10% margins")
                    for _, row in low_margin_strategic.head(3).iterrows():
                        print(f"     - {row['Category']}: {row['MarginPercent']:.1f}% margin, ${row['Revenue']:,.0f} revenue")
                        potential_gain = row['Revenue'] * 0.02  # 2% margin improvement
                        print(f"       → Even 2% margin improvement = ${potential_gain:,.0f} additional profit")

            # Export data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Main report
            output_file = f"category_analysis_comprehensive_{timestamp}.csv"
            df_export = df[[
                'Category', 'Classification', 'Recommendation', 'Revenue', 'GrossProfit',
                'MarginPercent', 'RevenueSharePercent', 'ProfitContributionPercent',
                'Transactions', 'Units', 'AvgTransactionValue', 'RevenueGrowthPercent',
                'PrevYearRevenue', 'DaysSinceLastSale', 'PerformanceScore'
            ]]
            df_export.to_csv(output_file, index=False)

            # Summary by classification
            summary_file = f"category_classification_summary_{timestamp}.csv"
            classification_summary.to_csv(summary_file, index=False)

            # Top products per category
            products_file = f"category_top_products_{timestamp}.csv"
            df_products.to_csv(products_file, index=False)

            print(f"\n" + "="*100)
            print("📁 DATA EXPORTED")
            print("="*100)
            print(f"   • Comprehensive Analysis: {output_file}")
            print(f"   • Classification Summary: {summary_file}")
            print(f"   • Top Products by Category: {products_file}")

            print("\n✅ Analysis completed successfully!")

            return df, df_products, classification_summary

    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    df_main, df_products, df_summary = comprehensive_category_analysis()

    if df_main is not None:
        print("\n" + "="*100)
        print("ANALYSIS COMPLETE - Review the CSV files for detailed data")
        print("="*100)
