#!/usr/bin/env python3

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_recent_customers():
    """Check new customers in the past 3 months"""
    
    # Calculate date range - past 3 months from today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Format dates for SQL query
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Checking new customers from {start_date_str} to {end_date_str}")
    
    # SQL query to get new customers in past 3 months
    query = f"""
    -- First, get all customers who had their FIRST transaction in the past 3 months
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
    NewCustomersLast3Months AS (
        -- Filter to only those whose first transaction was in past 3 months
        SELECT 
            CustomerID,
            first_ever_transaction,
            YEAR(first_ever_transaction) as year,
            MONTH(first_ever_transaction) as month,
            DAY(first_ever_transaction) as day
        FROM CustomerFirstEver
        WHERE first_ever_transaction >= '{start_date_str}'
            AND first_ever_transaction <= '{end_date_str}'
    )
    SELECT 
        COUNT(DISTINCT CustomerID) as total_new_customers,
        MIN(first_ever_transaction) as earliest_new_customer,
        MAX(first_ever_transaction) as latest_new_customer
    FROM NewCustomersLast3Months
    """
    
    # Also get month-by-month breakdown
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
        YEAR(first_ever_transaction) as year,
        MONTH(first_ever_transaction) as month,
        COUNT(DISTINCT CustomerID) as new_customers
    FROM CustomerFirstEver
    WHERE first_ever_transaction >= '{start_date_str}'
        AND first_ever_transaction <= '{end_date_str}'
    GROUP BY 
        YEAR(first_ever_transaction),
        MONTH(first_ever_transaction)
    ORDER BY 
        year, month
    """
    
    try:
        with SQLServerConnection() as db:
            # Get total
            df_total = db.execute_query(query, description="Total new customers past 3 months")
            
            # Get monthly breakdown
            df_monthly = db.execute_query(monthly_query, description="Monthly breakdown past 3 months")
            
            if not df_total.empty:
                total = df_total['total_new_customers'].iloc[0]
                earliest = df_total['earliest_new_customer'].iloc[0]
                latest = df_total['latest_new_customer'].iloc[0]
                
                print("\n" + "="*60)
                print("NEW CUSTOMERS - PAST 3 MONTHS")
                print("="*60)
                print(f"Period: {start_date_str} to {end_date_str}")
                print(f"\n🎯 TOTAL NEW CUSTOMERS: {total if total else 0}")
                
                if total and total > 0:
                    print(f"\n📅 First new customer: {earliest}")
                    print(f"📅 Latest new customer: {latest}")
                
                if not df_monthly.empty:
                    print("\n📊 MONTHLY BREAKDOWN:")
                    for _, row in df_monthly.iterrows():
                        month_name = pd.to_datetime(f"{row['year']}-{row['month']:02d}-01").strftime('%B %Y')
                        print(f"  {month_name}: {row['new_customers']} new customers")
                    
                    # Calculate daily average
                    days_in_period = (end_date - start_date).days
                    daily_avg = total / days_in_period if total else 0
                    print(f"\n📈 Daily Average: {daily_avg:.2f} new customers/day")
                    print(f"📈 Weekly Average: {daily_avg * 7:.1f} new customers/week")
                    print(f"📈 Monthly Average: {total / 3:.1f} new customers/month")
                
                return total
            else:
                print("\n❌ No data returned")
                return 0
                
    except Exception as e:
        logger.error(f"Error checking recent customers: {e}")
        return None

if __name__ == "__main__":
    total = check_recent_customers()
    
    if total is not None:
        print("\n✅ Analysis completed!")
    else:
        print("\n❌ Analysis failed!")