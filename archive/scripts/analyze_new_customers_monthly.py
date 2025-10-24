#!/usr/bin/env python3

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_new_customers_monthly():
    """Analyze new customers added per month over the past 3 years"""
    
    # Calculate date range - past 3 years from today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*3)
    
    logger.info(f"Analyzing new customers from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Format dates for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # SQL query to get new customers per month
    query = f"""
    WITH CustomerFirstTransaction AS (
        -- Find first transaction date for each customer
        SELECT 
            CustomerID,
            MIN([Time]) as first_transaction_date
        FROM [Transaction]
        WHERE CustomerID IS NOT NULL
            AND CustomerID > 0
            AND [Time] >= '{start_date_str}'
            AND [Time] <= '{end_date_str}'
        GROUP BY CustomerID
    )
    SELECT 
        YEAR(first_transaction_date) as year,
        MONTH(first_transaction_date) as month,
        COUNT(DISTINCT CustomerID) as new_customers
    FROM CustomerFirstTransaction
    WHERE first_transaction_date >= '{start_date_str}'
        AND first_transaction_date <= '{end_date_str}'
    GROUP BY 
        YEAR(first_transaction_date),
        MONTH(first_transaction_date)
    ORDER BY 
        year, month
    """
    
    try:
        with SQLServerConnection() as db:
            # Execute query
            df = db.execute_query(
                query, 
                description="New customers per month analysis"
            )
            
            if df.empty:
                logger.warning("No data returned from query")
                return None
            
            # Add month name for better readability
            df['month_name'] = pd.to_datetime(df[['year', 'month']].assign(day=1)).dt.strftime('%B %Y')
            
            # Calculate statistics
            total_new_customers = df['new_customers'].sum()
            total_months = len(df)
            avg_per_month = df['new_customers'].mean()
            median_per_month = df['new_customers'].median()
            max_month = df.loc[df['new_customers'].idxmax()]
            min_month = df.loc[df['new_customers'].idxmin()]
            
            # Calculate year-over-year growth
            yearly_stats = df.groupby('year')['new_customers'].agg(['sum', 'mean'])
            
            # Print results
            print("\n" + "="*70)
            print("NEW CUSTOMER ACQUISITION ANALYSIS (Past 3 Years)")
            print("="*70)
            print(f"Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"Total Months Analyzed: {total_months}")
            print(f"Total New Customers: {total_new_customers:,}")
            print("-"*70)
            
            print("\n📊 MONTHLY STATISTICS:")
            print(f"  Average per Month: {avg_per_month:.1f} customers")
            print(f"  Median per Month: {median_per_month:.1f} customers")
            print(f"  Best Month: {max_month['month_name']} ({max_month['new_customers']:,} customers)")
            print(f"  Slowest Month: {min_month['month_name']} ({min_month['new_customers']:,} customers)")
            
            print("\n📈 YEARLY BREAKDOWN:")
            for year in yearly_stats.index:
                yearly_total = yearly_stats.loc[year, 'sum']
                yearly_avg = yearly_stats.loc[year, 'mean']
                print(f"  {year}: Total {yearly_total:,.0f} | Monthly Avg {yearly_avg:.1f}")
            
            # Calculate growth rates
            if len(yearly_stats) > 1:
                years = sorted(yearly_stats.index)
                print("\n📊 YEAR-OVER-YEAR GROWTH:")
                for i in range(1, len(years)):
                    prev_year = yearly_stats.loc[years[i-1], 'sum']
                    curr_year = yearly_stats.loc[years[i], 'sum']
                    growth = ((curr_year - prev_year) / prev_year) * 100
                    print(f"  {years[i-1]} to {years[i]}: {growth:+.1f}%")
            
            # Show recent trend (last 6 months)
            recent_df = df.tail(6)
            print("\n🔔 RECENT TREND (Last 6 Months):")
            for _, row in recent_df.iterrows():
                bar = "█" * int(row['new_customers'] / avg_per_month * 20)
                print(f"  {row['month_name']}: {row['new_customers']:3} {bar}")
            
            # Calculate monthly trend
            if len(df) > 12:
                # Simple linear regression for trend
                from scipy import stats
                x = range(len(df))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, df['new_customers'])
                trend = "📈 Increasing" if slope > 0 else "📉 Decreasing"
                print(f"\n🎯 OVERALL TREND: {trend} ({slope:.2f} customers/month)")
            
            # Export detailed data
            output_file = f"new_customers_monthly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(output_file, index=False)
            print(f"\n💾 Detailed data exported to: {output_file}")
            
            return df
            
    except Exception as e:
        logger.error(f"Error analyzing new customers: {e}")
        return None

if __name__ == "__main__":
    result = analyze_new_customers_monthly()
    
    if result is not None:
        print("\n✅ Analysis completed successfully!")
    else:
        print("\n❌ Analysis failed. Please check the logs for details.")