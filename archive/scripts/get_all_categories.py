#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_categories():
    """Get all categories with complete revenue and margin analysis"""
    
    start_date = '2022-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Getting all categories from {start_date} to {end_date}")
    
    # Query for all categories with metrics - adjusted for excise taxes
    query = f"""
    WITH CategoryMetrics AS (
        SELECT 
            ISNULL(c.Name, 'UNCATEGORIZED') as CategoryName,
            COUNT(DISTINCT i.ID) as ProductCount,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            -- Adjust cost for excise taxes:
            -- CIGARS gets 23% uplift to cost
            -- LT-TAX-COLLECTED gets 10% uplift to cost
            SUM(CASE 
                WHEN UPPER(c.Name) = 'CIGARS' THEN (te.Price - (te.Cost * 1.23)) * te.Quantity
                WHEN UPPER(c.Name) = 'LT-TAX-COLLECTED' THEN (te.Price - (te.Cost * 1.10)) * te.Quantity
                ELSE (te.Price - te.Cost) * te.Quantity
            END) as GrossProfit,
            SUM(CASE
                WHEN UPPER(c.Name) = 'CIGARS' THEN te.Cost * 1.23 * te.Quantity
                WHEN UPPER(c.Name) = 'LT-TAX-COLLECTED' THEN te.Cost * 1.10 * te.Quantity
                ELSE te.Cost * te.Quantity
            END) as TotalCost,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            SUM(te.Quantity) as UnitsSold,
            MIN(t.[Time]) as FirstSale,
            MAX(t.[Time]) as LastSale
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_date}'
            AND t.[Time] <= '{end_date}'
            -- Only include actual sales (positive quantities and prices)
            AND te.Quantity > 0
            AND te.Price > 0
        GROUP BY c.Name
    ),
    GrandTotal AS (
        SELECT 
            SUM(TotalRevenue) as GrandRevenue,
            SUM(GrossProfit) as GrandProfit
        FROM CategoryMetrics
    )
    SELECT 
        ROW_NUMBER() OVER (ORDER BY cm.TotalRevenue DESC) as Rank,
        cm.CategoryName,
        cm.ProductCount,
        cm.TotalRevenue,
        cm.GrossProfit,
        cm.UnitsSold,
        cm.TransactionCount,
        CASE 
            WHEN cm.TotalRevenue > 0 THEN (cm.GrossProfit / cm.TotalRevenue) * 100 
            ELSE 0 
        END as MarginPercent,
        CASE 
            WHEN gt.GrandRevenue > 0 THEN (cm.TotalRevenue / gt.GrandRevenue) * 100 
            ELSE 0 
        END as RevenueSharePercent,
        CASE 
            WHEN cm.UnitsSold > 0 THEN cm.TotalRevenue / cm.UnitsSold
            ELSE 0
        END as AvgPricePerUnit,
        cm.FirstSale,
        cm.LastSale
    FROM CategoryMetrics cm
    CROSS JOIN GrandTotal gt
    ORDER BY cm.TotalRevenue DESC
    """
    
    # Also get all categories from the Category table
    all_categories_query = """
    SELECT 
        c.ID as CategoryID,
        c.Name as CategoryName,
        c.Code,
        d.Name as DepartmentName,
        COUNT(DISTINCT i.ID) as ItemCount
    FROM Category c
    LEFT JOIN Department d ON c.DepartmentID = d.ID
    LEFT JOIN Item i ON i.CategoryID = c.ID
    GROUP BY c.ID, c.Name, c.Code, d.Name
    ORDER BY c.Name
    """
    
    try:
        with SQLServerConnection() as db:
            # Get sales metrics
            df_metrics = db.execute_query(query, description="Category metrics")
            
            # Get all categories
            df_all_cats = db.execute_query(all_categories_query, description="All categories")
            
            if df_metrics.empty:
                logger.warning("No metrics data returned")
                return None, None
            
            # Print comprehensive report
            print("\n" + "="*100)
            print("COMPLETE CATEGORY ANALYSIS (2022 - PRESENT)")
            print("="*100)
            print(f"Analysis Period: {start_date} to {end_date}")
            
            # Summary statistics
            total_revenue = df_metrics['TotalRevenue'].sum()
            total_profit = df_metrics['GrossProfit'].sum()
            overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            print(f"\n📊 OVERALL SUMMARY:")
            print(f"  Total Categories with Sales: {len(df_metrics)}")
            print(f"  Total Revenue: ${total_revenue:,.2f}")
            print(f"  Total Gross Profit: ${total_profit:,.2f}")
            print(f"  Overall Margin: {overall_margin:.1f}%")
            
            # Detailed table of all categories
            print("\n" + "="*100)
            print("ALL CATEGORIES - RANKED BY REVENUE")
            print("="*100)
            print(f"{'#':<4} {'Category':<25} {'Revenue':<15} {'Share':<8} {'Margin':<8} {'Units':<12} {'Avg Price':<10}")
            print("-"*100)
            
            for _, row in df_metrics.iterrows():
                rank = int(row['Rank'])
                category = row['CategoryName'][:24]
                revenue = row['TotalRevenue']
                share = row['RevenueSharePercent']
                margin = row['MarginPercent']
                units = row['UnitsSold']
                avg_price = row['AvgPricePerUnit']
                
                print(f"{rank:<4} {category:<25} ${revenue:>13,.0f} {share:>6.2f}% {margin:>6.1f}% {units:>11,.0f} ${avg_price:>8.2f}")
            
            # Categories by margin tiers
            print("\n" + "="*100)
            print("CATEGORIES BY MARGIN TIER")
            print("="*100)
            
            high_margin = df_metrics[df_metrics['MarginPercent'] >= 25].sort_values('MarginPercent', ascending=False)
            mid_margin = df_metrics[(df_metrics['MarginPercent'] >= 15) & (df_metrics['MarginPercent'] < 25)].sort_values('MarginPercent', ascending=False)
            low_margin = df_metrics[(df_metrics['MarginPercent'] >= 10) & (df_metrics['MarginPercent'] < 15)].sort_values('MarginPercent', ascending=False)
            very_low_margin = df_metrics[df_metrics['MarginPercent'] < 10].sort_values('MarginPercent', ascending=False)
            
            print(f"\n🏆 HIGH MARGIN (≥25%):")
            for _, row in high_margin.iterrows():
                print(f"  • {row['CategoryName']:<25} {row['MarginPercent']:>6.1f}%  Revenue: ${row['TotalRevenue']:>12,.0f}")
            
            print(f"\n✅ GOOD MARGIN (15-25%):")
            for _, row in mid_margin.iterrows():
                print(f"  • {row['CategoryName']:<25} {row['MarginPercent']:>6.1f}%  Revenue: ${row['TotalRevenue']:>12,.0f}")
            
            print(f"\n⚠️  MODERATE MARGIN (10-15%):")
            for _, row in low_margin.iterrows():
                print(f"  • {row['CategoryName']:<25} {row['MarginPercent']:>6.1f}%  Revenue: ${row['TotalRevenue']:>12,.0f}")
            
            print(f"\n🚨 LOW MARGIN (<10%):")
            for _, row in very_low_margin.iterrows():
                print(f"  • {row['CategoryName']:<25} {row['MarginPercent']:>6.1f}%  Revenue: ${row['TotalRevenue']:>12,.0f}")
            
            # Categories in database but no sales
            if not df_all_cats.empty:
                # Find categories with no sales
                categories_with_sales = set(df_metrics['CategoryName'].str.upper())
                all_category_names = set(df_all_cats['CategoryName'].str.upper())
                no_sales = all_category_names - categories_with_sales
                
                if no_sales:
                    print("\n" + "="*100)
                    print("CATEGORIES WITH NO SALES (2022-PRESENT)")
                    print("="*100)
                    for cat in sorted(no_sales):
                        cat_info = df_all_cats[df_all_cats['CategoryName'].str.upper() == cat].iloc[0]
                        print(f"  • {cat_info['CategoryName']} (Code: {cat_info['Code']}, Items: {cat_info['ItemCount']})")
            
            # Export complete data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = f"all_categories_metrics_{timestamp}.csv"
            categories_file = f"all_categories_list_{timestamp}.csv"
            
            df_metrics.to_csv(metrics_file, index=False)
            df_all_cats.to_csv(categories_file, index=False)
            
            print(f"\n💾 Complete data exported to:")
            print(f"  • Metrics: {metrics_file}")
            print(f"  • Category List: {categories_file}")
            
            return df_metrics, df_all_cats
            
    except Exception as e:
        logger.error(f"Error getting all categories: {e}")
        return None, None

if __name__ == "__main__":
    metrics, categories = get_all_categories()
    
    if metrics is not None:
        print("\n✅ Analysis completed successfully!")
    else:
        print("\n❌ Analysis failed. Please check the logs.")