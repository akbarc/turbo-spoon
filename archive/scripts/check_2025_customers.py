#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_2025_customers():
    """Check new customers for all of 2025"""
    
    # Define date range for 2025
    start_date_str = '2025-01-01'
    end_date_str = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Checking new customers for 2025: {start_date_str} to {end_date_str}")
    
    # SQL query to get new customers in 2025
    query = f"""
    -- First, get all customers who had their FIRST transaction ever in 2025
    WITH CustomerFirstEver AS (
        -- Get the very first transaction date for each customer (all time)
        SELECT 
            CustomerID,
            MIN([Time]) as first_ever_transaction
        FROM [Transaction]
        WHERE CustomerID IS NOT NULL
            AND CustomerID > 0
        GROUP BY CustomerID
    ),
    NewCustomers2025 AS (
        -- Filter to only those whose first transaction was in 2025
        SELECT 
            CustomerID,
            first_ever_transaction
        FROM CustomerFirstEver
        WHERE first_ever_transaction >= '{start_date_str}'
            AND first_ever_transaction <= '{end_date_str}'
    )
    SELECT 
        COUNT(DISTINCT CustomerID) as total_new_customers,
        MIN(first_ever_transaction) as earliest_new_customer,
        MAX(first_ever_transaction) as latest_new_customer
    FROM NewCustomers2025
    """
    
    # Get month-by-month breakdown for 2025
    monthly_query = f"""
    WITH CustomerFirstEver AS (
        SELECT 
            CustomerID,
            MIN([Time]) as first_ever_transaction
        FROM [Transaction]
        WHERE CustomerID IS NOT NULL
            AND CustomerID > 0
        GROUP BY CustomerID
    )
    SELECT 
        MONTH(first_ever_transaction) as month,
        COUNT(DISTINCT CustomerID) as new_customers,
        DATENAME(month, first_ever_transaction) as month_name
    FROM CustomerFirstEver
    WHERE first_ever_transaction >= '{start_date_str}'
        AND first_ever_transaction <= '{end_date_str}'
    GROUP BY 
        MONTH(first_ever_transaction),
        DATENAME(month, first_ever_transaction)
    ORDER BY 
        MONTH(first_ever_transaction)
    """
    
    # Get weekly breakdown for better insight
    weekly_query = f"""
    WITH CustomerFirstEver AS (
        SELECT 
            CustomerID,
            MIN([Time]) as first_ever_transaction
        FROM [Transaction]
        WHERE CustomerID IS NOT NULL
            AND CustomerID > 0
        GROUP BY CustomerID
    )
    SELECT 
        DATEPART(week, first_ever_transaction) as week_num,
        MIN(CONVERT(date, first_ever_transaction)) as week_start,
        MAX(CONVERT(date, first_ever_transaction)) as week_end,
        COUNT(DISTINCT CustomerID) as new_customers
    FROM CustomerFirstEver
    WHERE first_ever_transaction >= '{start_date_str}'
        AND first_ever_transaction <= '{end_date_str}'
    GROUP BY 
        DATEPART(week, first_ever_transaction)
    ORDER BY 
        DATEPART(week, first_ever_transaction)
    """
    
    try:
        with SQLServerConnection() as db:
            # Get total
            df_total = db.execute_query(query, description="Total new customers 2025")
            
            # Get monthly breakdown
            df_monthly = db.execute_query(monthly_query, description="Monthly breakdown 2025")
            
            # Get weekly breakdown
            df_weekly = db.execute_query(weekly_query, description="Weekly breakdown 2025")
            
            if not df_total.empty:
                total = df_total['total_new_customers'].iloc[0]
                earliest = df_total['earliest_new_customer'].iloc[0]
                latest = df_total['latest_new_customer'].iloc[0]
                
                print("\n" + "="*70)
                print("NEW CUSTOMERS - 2025 YEAR TO DATE")
                print("="*70)
                print(f"Period: January 1, 2025 to {end_date_str}")
                print(f"\n🎯 TOTAL NEW CUSTOMERS IN 2025: {total if total else 0}")
                
                if total and total > 0:
                    print(f"\n📅 First new customer of 2025: {earliest}")
                    print(f"📅 Most recent new customer: {latest}")
                
                if not df_monthly.empty:
                    print("\n📊 MONTHLY BREAKDOWN FOR 2025:")
                    print("-" * 40)
                    cumulative = 0
                    for _, row in df_monthly.iterrows():
                        cumulative += row['new_customers']
                        bar = "█" * int(row['new_customers'] / 2)  # Visual bar chart
                        print(f"  {row['month_name']:12}: {row['new_customers']:3} customers {bar}")
                    
                    # Calculate statistics
                    months_elapsed = df_monthly['month'].max()
                    avg_per_month = total / months_elapsed if months_elapsed > 0 else 0
                    
                    print("\n📈 STATISTICS:")
                    print(f"  Months elapsed in 2025: {months_elapsed}")
                    print(f"  Average per month: {avg_per_month:.1f} customers")
                    print(f"  Best month: {df_monthly.loc[df_monthly['new_customers'].idxmax(), 'month_name']} ({df_monthly['new_customers'].max()} customers)")
                    print(f"  Slowest month: {df_monthly.loc[df_monthly['new_customers'].idxmin(), 'month_name']} ({df_monthly['new_customers'].min()} customers)")
                    
                    # Projection for full year
                    if months_elapsed > 0:
                        projected_total = (total / months_elapsed) * 12
                        print(f"\n🔮 PROJECTED FOR FULL YEAR 2025:")
                        print(f"  At current rate: {projected_total:.0f} new customers")
                        print(f"  Compared to 2024 total (164): {((projected_total/164)-1)*100:+.1f}%")
                
                # Show recent weeks trend
                if not df_weekly.empty and len(df_weekly) > 4:
                    print("\n📅 LAST 4 WEEKS TREND:")
                    for _, row in df_weekly.tail(4).iterrows():
                        print(f"  Week {row['week_num']}: {row['new_customers']} customers ({row['week_start']} to {row['week_end']})")
                
                return total
            else:
                print("\n❌ No data returned")
                return 0
                
    except Exception as e:
        logger.error(f"Error checking 2025 customers: {e}")
        return None

if __name__ == "__main__":
    total = check_2025_customers()
    
    if total is not None:
        print("\n✅ Analysis completed!")
    else:
        print("\n❌ Analysis failed!")