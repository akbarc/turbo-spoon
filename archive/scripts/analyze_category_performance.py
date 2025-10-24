#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_category_performance():
    """Analyze category distribution by revenue share and profit margins from 2022 to date"""
    
    start_date = '2022-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Analyzing category performance from {start_date} to {end_date}")
    
    # First, let's check the table structure
    check_structure_query = """
    SELECT TOP 1 * FROM TransactionEntry
    """
    
    # Main query for category performance
    category_query = f"""
    WITH CategorySales AS (
        SELECT 
            ISNULL(c.Name, 'Uncategorized') as CategoryName,
            YEAR(t.[Time]) as Year,
            SUM(te.Price * te.Quantity) as Revenue,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            SUM(te.Cost * te.Quantity) as TotalCost,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            SUM(te.Quantity) as UnitsSold
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_date}'
            AND t.[Time] <= '{end_date}'
            AND te.Price > 0
        GROUP BY c.Name, YEAR(t.[Time])
    ),
    TotalSales AS (
        SELECT 
            Year,
            SUM(Revenue) as TotalRevenue,
            SUM(GrossProfit) as TotalGrossProfit
        FROM CategorySales
        GROUP BY Year
    )
    SELECT 
        cs.CategoryName,
        cs.Year,
        cs.Revenue,
        cs.GrossProfit,
        cs.TotalCost,
        cs.UnitsSold,
        cs.TransactionCount,
        CASE 
            WHEN cs.Revenue > 0 THEN (cs.GrossProfit / cs.Revenue) * 100 
            ELSE 0 
        END as MarginPercent,
        CASE 
            WHEN ts.TotalRevenue > 0 THEN (cs.Revenue / ts.TotalRevenue) * 100 
            ELSE 0 
        END as RevenueSharePercent,
        ts.TotalRevenue as YearTotalRevenue
    FROM CategorySales cs
    INNER JOIN TotalSales ts ON cs.Year = ts.Year
    ORDER BY cs.Year DESC, cs.Revenue DESC
    """
    
    # Overall summary query
    summary_query = f"""
    WITH CategoryTotals AS (
        SELECT 
            ISNULL(c.Name, 'Uncategorized') as CategoryName,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as TotalGrossProfit,
            SUM(te.Cost * te.Quantity) as TotalCost,
            COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
            SUM(te.Quantity) as TotalUnits
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_date}'
            AND t.[Time] <= '{end_date}'
            AND te.Price > 0
        GROUP BY c.Name
    ),
    GrandTotal AS (
        SELECT 
            SUM(TotalRevenue) as GrandTotalRevenue,
            SUM(TotalGrossProfit) as GrandTotalProfit
        FROM CategoryTotals
    )
    SELECT 
        ct.CategoryName,
        ct.TotalRevenue,
        ct.TotalGrossProfit,
        ct.TotalTransactions,
        ct.TotalUnits,
        CASE 
            WHEN ct.TotalRevenue > 0 THEN (ct.TotalGrossProfit / ct.TotalRevenue) * 100 
            ELSE 0 
        END as OverallMarginPercent,
        CASE 
            WHEN gt.GrandTotalRevenue > 0 THEN (ct.TotalRevenue / gt.GrandTotalRevenue) * 100 
            ELSE 0 
        END as OverallRevenueSharePercent
    FROM CategoryTotals ct
    CROSS JOIN GrandTotal gt
    WHERE ct.TotalRevenue > 0
    ORDER BY ct.TotalRevenue DESC
    """
    
    try:
        with SQLServerConnection() as db:
            # Check structure first
            df_check = db.execute_query(check_structure_query, description="Check TransactionEntry structure")
            
            # Get detailed category performance
            df_detail = db.execute_query(category_query, description="Category performance by year")
            
            # Get overall summary
            df_summary = db.execute_query(summary_query, description="Overall category summary")
            
            if df_summary.empty:
                logger.warning("No data returned from queries")
                return None, None
            
            # Print overall summary
            print("\n" + "="*80)
            print("CATEGORY PERFORMANCE ANALYSIS (2022 - PRESENT)")
            print("="*80)
            print(f"Period: {start_date} to {end_date}")
            
            # Calculate grand totals
            total_revenue = df_summary['TotalRevenue'].sum()
            total_profit = df_summary['TotalGrossProfit'].sum()
            overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            print(f"\n📊 OVERALL METRICS:")
            print(f"  Total Revenue: ${total_revenue:,.2f}")
            print(f"  Total Gross Profit: ${total_profit:,.2f}")
            print(f"  Overall Margin: {overall_margin:.1f}%")
            
            print("\n" + "="*80)
            print("CATEGORY BREAKDOWN (2022-PRESENT COMBINED)")
            print("="*80)
            print(f"{'Category':<25} {'Revenue Share':<15} {'Margin %':<12} {'Total Revenue':<20}")
            print("-"*80)
            
            # Show top categories
            for _, row in df_summary.head(15).iterrows():
                category = row['CategoryName'][:24]  # Truncate long names
                share = row['OverallRevenueSharePercent']
                margin = row['OverallMarginPercent']
                revenue = row['TotalRevenue']
                
                # Visual bar for revenue share
                bar = "█" * int(share / 2)
                
                print(f"{category:<25} {share:>6.1f}% {bar:<20} {margin:>6.1f}%     ${revenue:>15,.0f}")
            
            # If there are more categories, show summary
            if len(df_summary) > 15:
                remaining = df_summary.iloc[15:]
                other_share = remaining['OverallRevenueSharePercent'].sum()
                other_revenue = remaining['TotalRevenue'].sum()
                print(f"\n{'Other Categories':<25} {other_share:>6.1f}%                      ${other_revenue:>15,.0f}")
            
            # Year-over-year comparison for top categories
            if not df_detail.empty:
                print("\n" + "="*80)
                print("YEAR-OVER-YEAR COMPARISON (TOP 5 CATEGORIES)")
                print("="*80)
                
                # Get top 5 categories by total revenue
                top_categories = df_summary.head(5)['CategoryName'].tolist()
                
                for category in top_categories:
                    cat_data = df_detail[df_detail['CategoryName'] == category]
                    if not cat_data.empty:
                        print(f"\n📦 {category}:")
                        print(f"  {'Year':<8} {'Revenue':<15} {'Share':<10} {'Margin':<10}")
                        print("  " + "-"*50)
                        for _, row in cat_data.iterrows():
                            year = int(row['Year'])
                            revenue = row['Revenue']
                            share = row['RevenueSharePercent']
                            margin = row['MarginPercent']
                            print(f"  {year:<8} ${revenue:>12,.0f}  {share:>6.1f}%   {margin:>6.1f}%")
            
            # Identify trends
            print("\n" + "="*80)
            print("KEY INSIGHTS")
            print("="*80)
            
            # High margin categories
            high_margin = df_summary[df_summary['OverallMarginPercent'] > 30].head(5)
            if not high_margin.empty:
                print("\n💰 HIGH MARGIN CATEGORIES (>30%):")
                for _, row in high_margin.iterrows():
                    print(f"  • {row['CategoryName']}: {row['OverallMarginPercent']:.1f}% margin, {row['OverallRevenueSharePercent']:.1f}% of revenue")
            
            # Low margin categories with significant revenue
            significant_low_margin = df_summary[(df_summary['OverallMarginPercent'] < 15) & 
                                               (df_summary['OverallRevenueSharePercent'] > 5)]
            if not significant_low_margin.empty:
                print("\n⚠️  LOW MARGIN CATEGORIES WITH SIGNIFICANT REVENUE:")
                for _, row in significant_low_margin.iterrows():
                    print(f"  • {row['CategoryName']}: {row['OverallMarginPercent']:.1f}% margin, {row['OverallRevenueSharePercent']:.1f}% of revenue")
            
            # Export detailed data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = f"category_performance_summary_{timestamp}.csv"
            detail_file = f"category_performance_detail_{timestamp}.csv"
            
            df_summary.to_csv(summary_file, index=False)
            df_detail.to_csv(detail_file, index=False)
            
            print(f"\n💾 Data exported to:")
            print(f"  • Summary: {summary_file}")
            print(f"  • Details: {detail_file}")
            
            return df_summary, df_detail
            
    except Exception as e:
        logger.error(f"Error analyzing category performance: {e}")
        return None, None

if __name__ == "__main__":
    summary, detail = analyze_category_performance()
    
    if summary is not None:
        print("\n✅ Analysis completed successfully!")
    else:
        print("\n❌ Analysis failed. Please check the logs for details.")