#!/usr/bin/env python3

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_price_buckets_summary(df):
    """Create price distribution summary"""
    buckets = {
        "$0-$1": ((df['SoldPrice'] >= 0) & (df['SoldPrice'] < 1)).sum(),
        "$1-$2": ((df['SoldPrice'] >= 1) & (df['SoldPrice'] < 2)).sum(),
        "$2-$3": ((df['SoldPrice'] >= 2) & (df['SoldPrice'] < 3)).sum(),
        "$3-$5": ((df['SoldPrice'] >= 3) & (df['SoldPrice'] < 5)).sum(),
        "$5-$10": ((df['SoldPrice'] >= 5) & (df['SoldPrice'] < 10)).sum(),
        "$10-$20": ((df['SoldPrice'] >= 10) & (df['SoldPrice'] < 20)).sum(),
        "$20-$50": ((df['SoldPrice'] >= 20) & (df['SoldPrice'] < 50)).sum(),
        "$50-$100": ((df['SoldPrice'] >= 50) & (df['SoldPrice'] < 100)).sum(),
        "$100-$200": ((df['SoldPrice'] >= 100) & (df['SoldPrice'] < 200)).sum(),
        "$200-$500": ((df['SoldPrice'] >= 200) & (df['SoldPrice'] < 500)).sum(),
        "$500+": (df['SoldPrice'] >= 500).sum()
    }
    return buckets

def analyze_products_fast():
    """Fast comprehensive product analysis using SQL aggregation"""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Analyzing products from {start_date_str} to {end_date_str}")
    
    # Aggregated query for product summary
    summary_query = f"""
    WITH ProductMetrics AS (
        SELECT 
            i.ID as ItemID,
            i.ItemLookupCode,
            i.Description,
            ISNULL(c.Name, 'Uncategorized') as CategoryName,
            COUNT(DISTINCT te.TransactionNumber) as TotalTransactions,
            SUM(te.Quantity) as TotalQuantity,
            AVG(te.Price) as AvgPrice,
            MIN(te.Price) as MinPrice,
            MAX(te.Price) as MaxPrice,
            AVG(te.Cost) as AvgCost,
            MIN(t.[Time]) as FirstSale,
            MAX(t.[Time]) as LastSale,
            COUNT(DISTINCT DATEPART(week, t.[Time])) as WeeksActive,
            -- Price buckets
            SUM(CASE WHEN te.Price >= 0 AND te.Price < 1 THEN te.Quantity ELSE 0 END) as Units_0_1,
            SUM(CASE WHEN te.Price >= 1 AND te.Price < 2 THEN te.Quantity ELSE 0 END) as Units_1_2,
            SUM(CASE WHEN te.Price >= 2 AND te.Price < 3 THEN te.Quantity ELSE 0 END) as Units_2_3,
            SUM(CASE WHEN te.Price >= 3 AND te.Price < 5 THEN te.Quantity ELSE 0 END) as Units_3_5,
            SUM(CASE WHEN te.Price >= 5 AND te.Price < 10 THEN te.Quantity ELSE 0 END) as Units_5_10,
            SUM(CASE WHEN te.Price >= 10 AND te.Price < 20 THEN te.Quantity ELSE 0 END) as Units_10_20,
            SUM(CASE WHEN te.Price >= 20 AND te.Price < 50 THEN te.Quantity ELSE 0 END) as Units_20_50,
            SUM(CASE WHEN te.Price >= 50 AND te.Price < 100 THEN te.Quantity ELSE 0 END) as Units_50_100,
            SUM(CASE WHEN te.Price >= 100 AND te.Price < 200 THEN te.Quantity ELSE 0 END) as Units_100_200,
            SUM(CASE WHEN te.Price >= 200 AND te.Price < 500 THEN te.Quantity ELSE 0 END) as Units_200_500,
            SUM(CASE WHEN te.Price >= 500 THEN te.Quantity ELSE 0 END) as Units_500_plus
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_date_str}'
            AND t.[Time] <= '{end_date_str}'
            AND te.Quantity > 0
        GROUP BY i.ID, i.ItemLookupCode, i.Description, c.Name
    )
    SELECT 
        ItemLookupCode as SKU,
        Description,
        CategoryName as Category,
        TotalQuantity as Total_Quantity_Sold,
        TotalTransactions as Total_Transactions,
        CASE WHEN WeeksActive > 0 THEN TotalQuantity * 1.0 / WeeksActive ELSE 0 END as Avg_Weekly_Quantity,
        ROUND(AvgPrice, 2) as Avg_Price,
        ROUND(MinPrice, 2) as Min_Price,
        ROUND(MaxPrice, 2) as Max_Price,
        ROUND(AvgCost, 2) as Avg_Cost,
        ROUND(AvgPrice - AvgCost, 2) as Margin_Dollar,
        CASE WHEN AvgPrice > 0 THEN ROUND((AvgPrice - AvgCost) * 100.0 / AvgPrice, 1) ELSE 0 END as Margin_Percent,
        FirstSale as First_Sale,
        LastSale as Last_Sale,
        DATEDIFF(day, LastSale, GETDATE()) as Days_Since_Last_Sale,
        WeeksActive as Weeks_Active,
        Units_0_1 as [Units_$0-$1],
        Units_1_2 as [Units_$1-$2],
        Units_2_3 as [Units_$2-$3],
        Units_3_5 as [Units_$3-$5],
        Units_5_10 as [Units_$5-$10],
        Units_10_20 as [Units_$10-$20],
        Units_20_50 as [Units_$20-$50],
        Units_50_100 as [Units_$50-$100],
        Units_100_200 as [Units_$100-$200],
        Units_200_500 as [Units_$200-$500],
        Units_500_plus as [Units_$500+]
    FROM ProductMetrics
    ORDER BY TotalQuantity DESC
    """
    
    # Trend analysis query - simplified for top products only
    trend_query = f"""
    WITH WeeklySales AS (
        SELECT 
            i.ItemLookupCode,
            DATEPART(year, t.[Time]) as Year,
            DATEPART(week, t.[Time]) as Week,
            SUM(te.Quantity) as WeeklyQuantity,
            AVG(te.Price) as WeeklyAvgPrice
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        WHERE t.[Time] >= '{start_date_str}'
            AND t.[Time] <= '{end_date_str}'
            AND te.Quantity > 0
        GROUP BY i.ItemLookupCode, DATEPART(year, t.[Time]), DATEPART(week, t.[Time])
    ),
    TopProducts AS (
        SELECT TOP 500 ItemLookupCode, SUM(WeeklyQuantity) as TotalQty
        FROM WeeklySales
        GROUP BY ItemLookupCode
        ORDER BY SUM(WeeklyQuantity) DESC
    )
    SELECT 
        ws.ItemLookupCode as SKU,
        ws.Year,
        ws.Week,
        ws.WeeklyQuantity,
        ws.WeeklyAvgPrice
    FROM WeeklySales ws
    INNER JOIN TopProducts tp ON ws.ItemLookupCode = tp.ItemLookupCode
    ORDER BY ws.ItemLookupCode, ws.Year, ws.Week
    """
    
    try:
        with SQLServerConnection() as db:
            # Execute queries
            logger.info("Fetching product summary data...")
            df_summary = db.execute_query(summary_query, description="Product summary")
            
            logger.info("Fetching trend data for top products...")
            df_trends = db.execute_query(trend_query, description="Product trends")
            
            if df_summary.empty:
                logger.warning("No sales data found for the period")
                return None, None
            
            # Calculate trends for top products
            logger.info("Calculating trends...")
            trend_results = {}
            
            if not df_trends.empty:
                for sku in df_trends['SKU'].unique():
                    sku_data = df_trends[df_trends['SKU'] == sku].sort_values(['Year', 'Week'])
                    if len(sku_data) > 3:  # Need at least 4 weeks for trend
                        # Simple trend: compare last 4 weeks to first 4 weeks
                        early_avg = sku_data.head(4)['WeeklyQuantity'].mean()
                        recent_avg = sku_data.tail(4)['WeeklyQuantity'].mean()
                        
                        if early_avg > 0:
                            trend_pct = ((recent_avg - early_avg) / early_avg) * 100
                            if trend_pct > 10:
                                trend_results[sku] = ('Up', round(trend_pct, 1))
                            elif trend_pct < -10:
                                trend_results[sku] = ('Down', round(trend_pct, 1))
                            else:
                                trend_results[sku] = ('Stable', round(trend_pct, 1))
                        else:
                            trend_results[sku] = ('New', 0)
                    else:
                        trend_results[sku] = ('Insufficient Data', 0)
            
            # Add trend data to summary
            df_summary['Quantity_Trend'] = df_summary['SKU'].map(lambda x: trend_results.get(x, ('Unknown', 0))[0])
            df_summary['Quantity_Trend_%'] = df_summary['SKU'].map(lambda x: trend_results.get(x, ('Unknown', 0))[1])
            
            # Add recent period metrics
            logger.info("Calculating recent period metrics...")
            recent_query = f"""
            SELECT 
                i.ItemLookupCode as SKU,
                SUM(te.Quantity) as RecentQuantity,
                AVG(te.Price) as RecentAvgPrice,
                COUNT(DISTINCT DATEPART(week, t.[Time])) as RecentWeeks
            FROM [Transaction] t
            INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            INNER JOIN Item i ON te.ItemID = i.ID
            WHERE t.[Time] >= DATEADD(day, -90, GETDATE())
                AND t.[Time] <= GETDATE()
                AND te.Quantity > 0
            GROUP BY i.ItemLookupCode
            """
            
            df_recent = db.execute_query(recent_query, description="Recent period metrics")
            
            if not df_recent.empty:
                df_recent['Recent_Weekly_Avg'] = df_recent['RecentQuantity'] / df_recent['RecentWeeks'].replace(0, 1)
                df_recent = df_recent.round(2)
                
                # Merge with summary
                df_summary = df_summary.merge(
                    df_recent[['SKU', 'Recent_Weekly_Avg', 'RecentAvgPrice']], 
                    on='SKU', 
                    how='left'
                )
                df_summary.rename(columns={'RecentAvgPrice': 'Recent_Avg_Price'}, inplace=True)
                df_summary['Recent_Weekly_Avg'] = df_summary['Recent_Weekly_Avg'].fillna(0)
                df_summary['Recent_Avg_Price'] = df_summary['Recent_Avg_Price'].fillna(df_summary['Avg_Price'])
            
            # Add ranking
            df_summary['Rank'] = range(1, len(df_summary) + 1)
            
            # Reorder columns
            column_order = ['Rank', 'SKU', 'Description', 'Category', 'Total_Quantity_Sold', 
                           'Total_Transactions', 'Avg_Weekly_Quantity', 'Recent_Weekly_Avg',
                           'Avg_Price', 'Recent_Avg_Price', 'Min_Price', 'Max_Price', 
                           'Avg_Cost', 'Margin_Dollar', 'Margin_Percent',
                           'Quantity_Trend', 'Quantity_Trend_%',
                           'First_Sale', 'Last_Sale', 'Days_Since_Last_Sale', 'Weeks_Active',
                           'Units_$0-$1', 'Units_$1-$2', 'Units_$2-$3', 'Units_$3-$5', 
                           'Units_$5-$10', 'Units_$10-$20', 'Units_$20-$50', 
                           'Units_$50-$100', 'Units_$100-$200', 'Units_$200-$500', 'Units_$500+']
            
            # Ensure all columns exist
            for col in column_order:
                if col not in df_summary.columns:
                    df_summary[col] = 0
            
            df_summary = df_summary[column_order]
            
            # Save to Excel with multiple sheets
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_file = f"product_analysis_{timestamp}.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Main analysis sheet
                df_summary.to_excel(writer, sheet_name='All Products', index=False)
                
                # Top 100 products
                df_summary.head(100).to_excel(writer, sheet_name='Top 100 Products', index=False)
                
                # Trending up
                trending_up = df_summary[df_summary['Quantity_Trend'] == 'Up'].sort_values('Quantity_Trend_%', ascending=False)
                if not trending_up.empty:
                    trending_up.head(50).to_excel(writer, sheet_name='Trending Up', index=False)
                
                # Trending down
                trending_down = df_summary[df_summary['Quantity_Trend'] == 'Down'].sort_values('Quantity_Trend_%')
                if not trending_down.empty:
                    trending_down.head(50).to_excel(writer, sheet_name='Trending Down', index=False)
                
                # High margin
                high_margin = df_summary[df_summary['Margin_Percent'] > 25].sort_values('Total_Quantity_Sold', ascending=False)
                if not high_margin.empty:
                    high_margin.head(100).to_excel(writer, sheet_name='High Margin', index=False)
                
                # Category summary
                category_summary = df_summary.groupby('Category').agg({
                    'Total_Quantity_Sold': 'sum',
                    'Total_Transactions': 'sum',
                    'Avg_Price': 'mean',
                    'Margin_Percent': 'mean',
                    'SKU': 'count'
                }).round(2).sort_values('Total_Quantity_Sold', ascending=False)
                category_summary.columns = ['Total_Units', 'Total_Transactions', 'Avg_Price', 'Avg_Margin_%', 'Product_Count']
                category_summary.to_excel(writer, sheet_name='Category Summary')
            
            # Also save as CSV
            csv_file = f"product_analysis_{timestamp}.csv"
            df_summary.to_csv(csv_file, index=False)
            
            # Print summary
            print("\n" + "="*80)
            print("COMPREHENSIVE PRODUCT ANALYSIS COMPLETE")
            print("="*80)
            print(f"Analysis Period: {start_date_str} to {end_date_str} (6 months)")
            print(f"Total Products Analyzed: {len(df_summary):,}")
            print(f"Total Units Sold: {df_summary['Total_Quantity_Sold'].sum():,.0f}")
            print(f"Total Transactions: {df_summary['Total_Transactions'].sum():,}")
            
            print("\n📊 KEY METRICS:")
            up_count = len(df_summary[df_summary['Quantity_Trend'] == 'Up'])
            down_count = len(df_summary[df_summary['Quantity_Trend'] == 'Down'])
            high_margin_count = len(df_summary[df_summary['Margin_Percent'] > 25])
            
            print(f"  • Products Trending Up: {up_count}")
            print(f"  • Products Trending Down: {down_count}")
            print(f"  • High Margin Products (>25%): {high_margin_count}")
            print(f"  • Average Margin: {df_summary['Margin_Percent'].mean():.1f}%")
            
            print("\n🏆 TOP 10 BEST SELLERS:")
            for idx, row in df_summary.head(10).iterrows():
                print(f"  {row['Rank']:2}. {row['Description'][:45]:<45} {row['Total_Quantity_Sold']:>8,.0f} units")
            
            print(f"\n💾 FILES SAVED:")
            print(f"  📊 Excel Report: {excel_file}")
            print(f"  📄 CSV Data: {csv_file}")
            print(f"\n✨ The Excel file contains multiple sheets:")
            print(f"  • All Products - Complete analysis of all {len(df_summary):,} products")
            print(f"  • Top 100 Products - Best sellers by quantity")
            print(f"  • Trending Up/Down - Products with significant trends")
            print(f"  • High Margin - Products with >25% margin")
            print(f"  • Category Summary - Performance by category")
            
            return excel_file, csv_file
            
    except Exception as e:
        logger.error(f"Error analyzing products: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    excel_file, csv_file = analyze_products_fast()
    
    if excel_file:
        print("\n✅ Analysis completed successfully!")
        print(f"📊 Open {excel_file} to view the comprehensive analysis")
    else:
        print("\n❌ Analysis failed. Please check the logs.")