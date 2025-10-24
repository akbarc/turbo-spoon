#!/usr/bin/env python3
"""
Customer Analysis for Last 12 Months
- Total unique customers
- Customer segmentation by sales volume
- Customers with over $1000 balance
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json

def analyze_customers_12months():
    """Analyze customer metrics for the last 12 months."""
    
    with SQLServerConnection() as db:
        # 1. Total unique customers in last 12 months
        print("=" * 60)
        print("CUSTOMER ANALYSIS - LAST 12 MONTHS")
        print("=" * 60)
        
        query_unique_customers = """
        SELECT COUNT(DISTINCT t.CustomerID) as unique_customers,
               COUNT(DISTINCT t.TransactionNumber) as total_transactions,
               SUM(te.Price * te.Quantity) as total_sales
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
        """
        
        df_total = db.execute_query(query_unique_customers, description="Get total unique customers")
        print(f"\nTotal Unique Customers (Last 12 Months): {df_total['unique_customers'].iloc[0]:,}")
        print(f"Total Transactions: {df_total['total_transactions'].iloc[0]:,}")
        print(f"Total Sales: ${df_total['total_sales'].iloc[0]:,.2f}")
        
        # 2. Customer segmentation by sales volume
        print("\n" + "=" * 60)
        print("CUSTOMER SEGMENTATION BY SALES VOLUME")
        print("=" * 60)
        
        query_segmentation = """
        WITH CustomerSales AS (
            SELECT t.CustomerID,
                   c.ID,
                   COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                   SUM(te.Price * te.Quantity) as TotalSales,
                   COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                   MIN(t.Time) as FirstPurchase,
                   MAX(t.Time) as LastPurchase
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN Customer c ON t.CustomerID = c.ID
            WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
            GROUP BY t.CustomerID, c.ID, c.Company, c.FirstName, c.LastName
        )
        SELECT 
            Segment,
            COUNT(*) as CustomerCount,
            SUM(TotalSales) as SegmentTotalSales,
            AVG(TotalSales) as AvgSalesPerCustomer,
            AVG(TransactionCount) as AvgTransactionsPerCustomer,
            MIN(SortOrder) as SortOrder
        FROM (
            SELECT 
                CASE 
                    WHEN TotalSales >= 50000 THEN 'Platinum ($50K+)'
                    WHEN TotalSales >= 25000 THEN 'Gold ($25K-$50K)'
                    WHEN TotalSales >= 10000 THEN 'Silver ($10K-$25K)'
                    WHEN TotalSales >= 5000 THEN 'Bronze ($5K-$10K)'
                    WHEN TotalSales >= 1000 THEN 'Regular ($1K-$5K)'
                    ELSE 'Small (<$1K)'
                END as Segment,
                TotalSales,
                TransactionCount,
                CASE 
                    WHEN TotalSales >= 50000 THEN 1
                    WHEN TotalSales >= 25000 THEN 2
                    WHEN TotalSales >= 10000 THEN 3
                    WHEN TotalSales >= 5000 THEN 4
                    WHEN TotalSales >= 1000 THEN 5
                    ELSE 6
                END as SortOrder
            FROM CustomerSales
        ) AS SegmentedData
        GROUP BY Segment
        ORDER BY MIN(SortOrder)
        """
        
        df_segments = db.execute_query(query_segmentation, description="Get customer segmentation")
        
        print("\nCustomer Segments:")
        print("-" * 80)
        print(f"{'Segment':<20} {'Customers':>12} {'Total Sales':>15} {'Avg Sales':>15} {'Avg Trans':>10}")
        print("-" * 80)
        
        for _, row in df_segments.iterrows():
            print(f"{row['Segment']:<20} {row['CustomerCount']:>12,} ${row['SegmentTotalSales']:>14,.2f} ${row['AvgSalesPerCustomer']:>14,.2f} {row['AvgTransactionsPerCustomer']:>10.1f}")
        
        # 3. Customers with over $1000 balance
        print("\n" + "=" * 60)
        print("CUSTOMERS WITH BALANCE OVER $1,000")
        print("=" * 60)
        
        query_high_balance = """
        WITH CustomerBalances AS (
            SELECT 
                ar.CustomerID,
                c.ID,
                COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                SUM(ar.Balance) as CurrentBalance
            FROM AccountReceivable ar
            LEFT JOIN Customer c ON ar.CustomerID = c.ID
            GROUP BY ar.CustomerID, c.ID, c.Company, c.FirstName, c.LastName
            HAVING SUM(ar.Balance) > 1000
        ),
        CustomerSalesLast12 AS (
            SELECT 
                t.CustomerID,
                SUM(te.Price * te.Quantity) as Sales12Months,
                MAX(t.Time) as LastPurchaseDate
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
            GROUP BY t.CustomerID
        )
        SELECT 
            cb.CustomerID,
            cb.CustomerName,
            cb.CurrentBalance,
            ISNULL(cs.Sales12Months, 0) as Sales12Months,
            cs.LastPurchaseDate,
            DATEDIFF(DAY, cs.LastPurchaseDate, GETDATE()) as DaysSinceLastPurchase
        FROM CustomerBalances cb
        LEFT JOIN CustomerSalesLast12 cs ON cb.CustomerID = cs.CustomerID
        ORDER BY cb.CurrentBalance DESC
        """
        
        df_high_balance = db.execute_query(query_high_balance, description="Get high balance customers")
        
        print(f"\nTotal Customers with Balance > $1,000: {len(df_high_balance):,}")
        print(f"Total Outstanding Balance: ${df_high_balance['CurrentBalance'].sum():,.2f}")
        
        # Balance brackets analysis
        print("\nBalance Brackets:")
        print("-" * 60)
        
        query_balance_brackets = """
        WITH CustomerBalances AS (
            SELECT 
                ar.CustomerID,
                SUM(ar.Balance) as CurrentBalance
            FROM AccountReceivable ar
            GROUP BY ar.CustomerID
        )
        SELECT 
            BalanceBracket,
            COUNT(*) as CustomerCount,
            SUM(CurrentBalance) as TotalBalance,
            MIN(SortOrder) as SortOrder
        FROM (
            SELECT 
                CurrentBalance,
                CASE 
                    WHEN CurrentBalance >= 10000 THEN '$10,000+'
                    WHEN CurrentBalance >= 5000 THEN '$5,000-$10,000'
                    WHEN CurrentBalance >= 2500 THEN '$2,500-$5,000'
                    WHEN CurrentBalance >= 1000 THEN '$1,000-$2,500'
                    WHEN CurrentBalance > 0 THEN 'Under $1,000'
                    ELSE 'Zero Balance'
                END as BalanceBracket,
                CASE 
                    WHEN CurrentBalance >= 10000 THEN 1
                    WHEN CurrentBalance >= 5000 THEN 2
                    WHEN CurrentBalance >= 2500 THEN 3
                    WHEN CurrentBalance >= 1000 THEN 4
                    WHEN CurrentBalance > 0 THEN 5
                    ELSE 6
                END as SortOrder
            FROM CustomerBalances
        ) AS BracketedData
        GROUP BY BalanceBracket
        ORDER BY MIN(SortOrder)
        """
        
        df_brackets = db.execute_query(query_balance_brackets, description="Get balance brackets")
        
        print(f"{'Balance Bracket':<20} {'Customer Count':>15} {'Total Balance':>20}")
        print("-" * 60)
        for _, row in df_brackets.iterrows():
            print(f"{row['BalanceBracket']:<20} {row['CustomerCount']:>15,} ${row['TotalBalance']:>19,.2f}")
        
        # Top 10 customers by balance
        if len(df_high_balance) > 0:
            print("\n" + "=" * 60)
            print("TOP 10 CUSTOMERS BY BALANCE")
            print("=" * 60)
            print(f"{'Customer Name':<30} {'Balance':>12} {'12M Sales':>12} {'Days Since Purchase':>18}")
            print("-" * 80)
            
            for i, row in df_high_balance.head(10).iterrows():
                days_str = f"{row['DaysSinceLastPurchase']:.0f} days" if pd.notna(row['DaysSinceLastPurchase']) else "No recent purchase"
                print(f"{row['CustomerName'][:30]:<30} ${row['CurrentBalance']:>11,.2f} ${row['Sales12Months']:>11,.2f} {days_str:>18}")
        
        # Summary statistics
        print("\n" + "=" * 60)
        print("SUMMARY STATISTICS")
        print("=" * 60)
        
        # Active vs Inactive customers
        query_activity = """
        WITH CustomerActivity AS (
            SELECT 
                c.ID as CustomerID,
                MAX(t.Time) as LastTransactionDate
            FROM Customer c
            LEFT JOIN [dbo].[Transaction] t ON t.CustomerID = c.ID
            GROUP BY c.ID
        )
        SELECT 
            ActivityStatus,
            COUNT(*) as CustomerCount,
            MIN(SortOrder) as SortOrder
        FROM (
            SELECT 
                CASE 
                    WHEN LastTransactionDate >= DATEADD(MONTH, -3, GETDATE()) THEN 'Active (0-3 months)'
                    WHEN LastTransactionDate >= DATEADD(MONTH, -6, GETDATE()) THEN 'Semi-Active (3-6 months)'
                    WHEN LastTransactionDate >= DATEADD(MONTH, -12, GETDATE()) THEN 'Inactive (6-12 months)'
                    WHEN LastTransactionDate IS NOT NULL THEN 'Dormant (>12 months)'
                    ELSE 'Never Purchased'
                END as ActivityStatus,
                CASE 
                    WHEN LastTransactionDate >= DATEADD(MONTH, -3, GETDATE()) THEN 1
                    WHEN LastTransactionDate >= DATEADD(MONTH, -6, GETDATE()) THEN 2
                    WHEN LastTransactionDate >= DATEADD(MONTH, -12, GETDATE()) THEN 3
                    WHEN LastTransactionDate IS NOT NULL THEN 4
                    ELSE 5
                END as SortOrder
            FROM CustomerActivity
        ) AS ActivityData
        GROUP BY ActivityStatus
        ORDER BY MIN(SortOrder)
        """
        
        df_activity = db.execute_query(query_activity, description="Get customer activity status")
        
        print("\nCustomer Activity Status:")
        print("-" * 40)
        for _, row in df_activity.iterrows():
            print(f"{row['ActivityStatus']:<30} {row['CustomerCount']:>10,}")
        
        # Export results to JSON for reference
        results = {
            'analysis_date': datetime.now().isoformat(),
            'total_unique_customers_12m': int(df_total['unique_customers'].iloc[0]),
            'total_sales_12m': float(df_total['total_sales'].iloc[0]),
            'segmentation': df_segments.to_dict('records'),
            'customers_over_1000_balance': len(df_high_balance),
            'total_balance_over_1000': float(df_high_balance['CurrentBalance'].sum()),
            'balance_brackets': df_brackets.to_dict('records'),
            'activity_status': df_activity.to_dict('records')
        }
        
        with open('customer_12month_analysis.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Analysis complete! Results saved to customer_12month_analysis.json")
        print("=" * 60)

if __name__ == "__main__":
    analyze_customers_12months()