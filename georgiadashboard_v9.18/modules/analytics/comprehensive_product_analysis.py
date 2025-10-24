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

def create_price_buckets(prices):
    """Create price distribution buckets"""
    buckets = {}
    
    # Define price ranges
    ranges = [
        (0, 1, "$0-$1"),
        (1, 2, "$1-$2"),
        (2, 3, "$2-$3"),
        (3, 5, "$3-$5"),
        (5, 10, "$5-$10"),
        (10, 20, "$10-$20"),
        (20, 50, "$20-$50"),
        (50, 100, "$50-$100"),
        (100, 200, "$100-$200"),
        (200, 500, "$200-$500"),
        (500, float('inf'), "$500+")
    ]
    
    for min_price, max_price, label in ranges:
        if min_price < float('inf'):
            count = len([p for p in prices if min_price <= p < max_price])
            if count > 0:
                buckets[label] = count
    
    return buckets

def calculate_trend(df, column='quantity'):
    """Calculate trend direction and strength"""
    if len(df) < 2:
        return 'Stable', 0
    
    try:
        # Convert to numeric and handle any non-numeric values
        y = pd.to_numeric(df[column], errors='coerce').fillna(0).values
        x = np.arange(len(y))
        
        if len(x) > 1 and np.std(y) > 0:
            # Simple linear regression trend
            z = np.polyfit(x, y.astype(float), 1)
            slope = z[0]
            
            # Calculate percentage change
            avg_value = np.mean(y)
            if avg_value > 0:
                trend_pct = (slope / avg_value) * 100
                
                if trend_pct > 5:
                    return 'Up', trend_pct
                elif trend_pct < -5:
                    return 'Down', trend_pct
                else:
                    return 'Stable', trend_pct
            else:
                return 'Stable', 0
        else:
            return 'Stable', 0
    except Exception as e:
        logger.debug(f"Trend calculation error: {e}")
        return 'Stable', 0

def analyze_all_products():
    """Comprehensive product analysis for past 6 months"""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Analyzing products from {start_date_str} to {end_date_str}")
    
    # Main query for product data
    query = f"""
    WITH ProductSales AS (
        SELECT 
            i.ID as ItemID,
            i.ItemLookupCode,
            i.Description,
            i.CategoryID,
            c.Name as CategoryName,
            te.Price as SoldPrice,
            te.Cost as SoldCost,
            te.Quantity,
            t.[Time] as TransactionDate,
            DATEPART(year, t.[Time]) as Year,
            DATEPART(week, t.[Time]) as Week,
            DATEPART(month, t.[Time]) as Month
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.[Time] >= '{start_date_str}'
            AND t.[Time] <= '{end_date_str}'
            AND te.Quantity > 0
            AND te.Price >= 0
    )
    SELECT 
        ItemID,
        ItemLookupCode,
        Description,
        CategoryName,
        SoldPrice,
        SoldCost,
        Quantity,
        TransactionDate,
        Year,
        Week,
        Month
    FROM ProductSales
    ORDER BY Description, TransactionDate
    """
    
    try:
        with SQLServerConnection() as db:
            # Execute main query
            logger.info("Fetching product sales data...")
            df = db.execute_query(query, description="Product sales data")
            
            if df.empty:
                logger.warning("No sales data found for the period")
                return None
            
            logger.info(f"Processing {len(df)} transaction records...")
            
            # Calculate metrics for each product
            products_data = []
            
            # Group by product
            grouped = df.groupby(['ItemID', 'ItemLookupCode', 'Description', 'CategoryName'])
            
            total_products = len(grouped)
            logger.info(f"Analyzing {total_products} unique products...")
            
            for idx, ((item_id, sku, description, category), product_df) in enumerate(grouped):
                if idx % 100 == 0:
                    logger.info(f"Processing product {idx+1}/{total_products}...")
                
                # Basic metrics
                total_quantity = product_df['Quantity'].sum()
                total_transactions = len(product_df)
                avg_price = product_df['SoldPrice'].mean()
                avg_cost = product_df['SoldCost'].mean()
                min_price = product_df['SoldPrice'].min()
                max_price = product_df['SoldPrice'].max()
                
                # Weekly metrics
                weeks_active = product_df['Week'].nunique()
                avg_weekly_qty = total_quantity / weeks_active if weeks_active > 0 else 0
                
                # Price distribution buckets
                price_buckets = create_price_buckets(product_df['SoldPrice'].values)
                
                # Trend analysis - group by week for trend
                weekly_data = product_df.groupby(['Year', 'Week']).agg({
                    'Quantity': 'sum',
                    'SoldPrice': 'mean'
                }).reset_index()
                
                qty_trend, qty_trend_pct = calculate_trend(weekly_data, 'Quantity')
                price_trend, price_trend_pct = calculate_trend(weekly_data, 'SoldPrice')
                
                # Monthly averages for last 3 months
                recent_months = product_df[product_df['TransactionDate'] >= (end_date - timedelta(days=90))]
                if not recent_months.empty:
                    recent_avg_qty = recent_months['Quantity'].sum() / 12  # 12 weeks in 3 months
                    recent_avg_price = recent_months['SoldPrice'].mean()
                else:
                    recent_avg_qty = 0
                    recent_avg_price = avg_price
                
                # Margin calculations
                margin_dollars = avg_price - avg_cost
                margin_pct = (margin_dollars / avg_price * 100) if avg_price > 0 else 0
                
                # First and last sale dates
                first_sale = product_df['TransactionDate'].min()
                last_sale = product_df['TransactionDate'].max()
                days_since_last_sale = (end_date - last_sale).days
                
                # Compile product data
                product_info = {
                    'SKU': sku,
                    'Description': description,
                    'Category': category if category else 'Uncategorized',
                    'Total_Quantity_Sold': total_quantity,
                    'Total_Transactions': total_transactions,
                    'Avg_Weekly_Quantity': round(avg_weekly_qty, 2),
                    'Recent_Weekly_Avg_(90d)': round(recent_avg_qty, 2),
                    'Avg_Price': round(avg_price, 2),
                    'Recent_Avg_Price_(90d)': round(recent_avg_price, 2),
                    'Min_Price': round(min_price, 2),
                    'Max_Price': round(max_price, 2),
                    'Avg_Cost': round(avg_cost, 2),
                    'Margin_$': round(margin_dollars, 2),
                    'Margin_%': round(margin_pct, 1),
                    'Quantity_Trend': qty_trend,
                    'Quantity_Trend_%': round(qty_trend_pct, 1),
                    'Price_Trend': price_trend,
                    'Price_Trend_%': round(price_trend_pct, 1),
                    'First_Sale': first_sale.strftime('%Y-%m-%d'),
                    'Last_Sale': last_sale.strftime('%Y-%m-%d'),
                    'Days_Since_Last_Sale': days_since_last_sale,
                    'Weeks_Active': weeks_active
                }
                
                # Add price bucket columns
                for bucket_label in ["$0-$1", "$1-$2", "$2-$3", "$3-$5", "$5-$10", 
                                    "$10-$20", "$20-$50", "$50-$100", "$100-$200", 
                                    "$200-$500", "$500+"]:
                    product_info[f'Units_{bucket_label}'] = price_buckets.get(bucket_label, 0)
                
                products_data.append(product_info)
            
            # Create DataFrame
            results_df = pd.DataFrame(products_data)
            
            # Sort by total quantity sold (best sellers first)
            results_df = results_df.sort_values('Total_Quantity_Sold', ascending=False)
            
            # Add ranking
            results_df['Rank'] = range(1, len(results_df) + 1)
            
            # Reorder columns for better readability
            column_order = ['Rank', 'SKU', 'Description', 'Category', 'Total_Quantity_Sold', 
                           'Total_Transactions', 'Avg_Weekly_Quantity', 'Recent_Weekly_Avg_(90d)',
                           'Avg_Price', 'Recent_Avg_Price_(90d)', 'Min_Price', 'Max_Price', 
                           'Avg_Cost', 'Margin_$', 'Margin_%', 
                           'Quantity_Trend', 'Quantity_Trend_%', 'Price_Trend', 'Price_Trend_%',
                           'First_Sale', 'Last_Sale', 'Days_Since_Last_Sale', 'Weeks_Active']
            
            # Add price bucket columns to order
            bucket_columns = [col for col in results_df.columns if col.startswith('Units_$')]
            column_order.extend(bucket_columns)
            
            results_df = results_df[column_order]
            
            # Save to Excel with multiple sheets
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_file = f"comprehensive_product_analysis_{timestamp}.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Main analysis sheet
                results_df.to_excel(writer, sheet_name='Product Analysis', index=False)
                
                # Top performers sheet
                top_50 = results_df.head(50)[['Rank', 'SKU', 'Description', 'Category', 
                                              'Total_Quantity_Sold', 'Avg_Weekly_Quantity', 
                                              'Avg_Price', 'Margin_%', 'Quantity_Trend']]
                top_50.to_excel(writer, sheet_name='Top 50 Products', index=False)
                
                # Trending up products
                trending_up = results_df[results_df['Quantity_Trend'] == 'Up'].sort_values('Quantity_Trend_%', ascending=False)
                trending_up[['Rank', 'SKU', 'Description', 'Quantity_Trend_%', 'Price_Trend_%', 
                            'Recent_Weekly_Avg_(90d)', 'Avg_Price']].to_excel(writer, sheet_name='Trending Up', index=False)
                
                # Trending down products
                trending_down = results_df[results_df['Quantity_Trend'] == 'Down'].sort_values('Quantity_Trend_%')
                trending_down[['Rank', 'SKU', 'Description', 'Quantity_Trend_%', 'Price_Trend_%', 
                              'Recent_Weekly_Avg_(90d)', 'Avg_Price']].to_excel(writer, sheet_name='Trending Down', index=False)
                
                # High margin products
                high_margin = results_df[results_df['Margin_%'] > 25].sort_values('Margin_%', ascending=False)
                high_margin[['Rank', 'SKU', 'Description', 'Margin_%', 'Margin_$', 
                            'Total_Quantity_Sold', 'Avg_Price', 'Avg_Cost']].to_excel(writer, sheet_name='High Margin (>25%)', index=False)
                
                # Category summary
                category_summary = results_df.groupby('Category').agg({
                    'Total_Quantity_Sold': 'sum',
                    'Total_Transactions': 'sum',
                    'Avg_Price': 'mean',
                    'Margin_%': 'mean',
                    'SKU': 'count'
                }).round(2).sort_values('Total_Quantity_Sold', ascending=False)
                category_summary.columns = ['Total_Units', 'Total_Transactions', 'Avg_Price', 'Avg_Margin_%', 'Product_Count']
                category_summary.to_excel(writer, sheet_name='Category Summary')
            
            # Also save main data as CSV
            csv_file = f"product_analysis_{timestamp}.csv"
            results_df.to_csv(csv_file, index=False)
            
            # Print summary
            print("\n" + "="*80)
            print("COMPREHENSIVE PRODUCT ANALYSIS COMPLETE")
            print("="*80)
            print(f"Analysis Period: {start_date_str} to {end_date_str} (6 months)")
            print(f"Total Products Analyzed: {len(results_df):,}")
            print(f"Total Units Sold: {results_df['Total_Quantity_Sold'].sum():,.0f}")
            print(f"Total Transactions: {results_df['Total_Transactions'].sum():,}")
            
            print("\n📊 KEY METRICS:")
            print(f"  • Products Trending Up: {len(trending_up)} ({len(trending_up)/len(results_df)*100:.1f}%)")
            print(f"  • Products Trending Down: {len(trending_down)} ({len(trending_down)/len(results_df)*100:.1f}%)")
            print(f"  • High Margin Products (>25%): {len(high_margin)}")
            print(f"  • Average Margin: {results_df['Margin_%'].mean():.1f}%")
            
            print("\n🏆 TOP 5 BEST SELLERS:")
            for idx, row in results_df.head(5).iterrows():
                print(f"  {row['Rank']}. {row['Description'][:40]}: {row['Total_Quantity_Sold']:,.0f} units")
            
            print("\n📈 TOP 5 TRENDING UP:")
            if len(trending_up) > 0:
                for idx, row in trending_up.head(5).iterrows():
                    print(f"  • {row['Description'][:40]}: +{row['Quantity_Trend_%']:.1f}% trend")
            
            print(f"\n💾 FILES SAVED:")
            print(f"  📊 Excel Report: {excel_file}")
            print(f"  📄 CSV Data: {csv_file}")
            
            return excel_file, csv_file
            
    except Exception as e:
        logger.error(f"Error analyzing products: {e}")
        return None, None

if __name__ == "__main__":
    excel_file, csv_file = analyze_all_products()
    
    if excel_file:
        print("\n✅ Analysis completed successfully!")
        print(f"📊 Open {excel_file} to view the comprehensive analysis")
    else:
        print("\n❌ Analysis failed. Please check the logs.")