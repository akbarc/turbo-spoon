#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_customer_concentration():
    """Analyze top-10 customer concentration by different time periods"""
    
    # Define date ranges
    ytd_start = '2025-01-01'
    year_2024_start = '2024-01-01'
    year_2024_end = '2024-12-31'
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info("Analyzing customer concentration across different periods")
    
    # Query for all-time customer revenue
    all_time_query = """
    SELECT TOP 10
        CustomerID,
        CustomerName,
        AccountNumber,
        TotalRevenue,
        TransactionCount,
        FirstPurchase,
        LastPurchase,
        CustomerLifeDays,
        RevenueSharePercent,
        CumulativeSharePercent
    FROM (
        SELECT 
            c.ID as CustomerID,
            ISNULL(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.AccountNumber,
            SUM(t.Total) as TotalRevenue,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            MIN(t.[Time]) as FirstPurchase,
            MAX(t.[Time]) as LastPurchase,
            DATEDIFF(day, MIN(t.[Time]), MAX(t.[Time])) as CustomerLifeDays,
            SUM(t.Total) * 100.0 / (SELECT SUM(Total) FROM [Transaction] WHERE Total > 0 AND CustomerID > 0) as RevenueSharePercent,
            0 as CumulativeSharePercent
        FROM [Transaction] t
        INNER JOIN Customer c ON t.CustomerID = c.ID
        WHERE t.Total > 0
            AND c.ID > 0
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountNumber
    ) AS CustomerData
    ORDER BY TotalRevenue DESC
    """
    
    # Query for YTD 2025 revenue
    ytd_query = f"""
    SELECT TOP 10
        CustomerID,
        CustomerName,
        AccountNumber,
        TotalRevenue,
        TransactionCount,
        FirstPurchase,
        LastPurchase,
        RevenueSharePercent,
        CumulativeSharePercent
    FROM (
        SELECT 
            c.ID as CustomerID,
            ISNULL(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.AccountNumber,
            SUM(t.Total) as TotalRevenue,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            MIN(t.[Time]) as FirstPurchase,
            MAX(t.[Time]) as LastPurchase,
            SUM(t.Total) * 100.0 / (SELECT SUM(Total) FROM [Transaction] WHERE Total > 0 AND CustomerID > 0 AND [Time] >= '{ytd_start}' AND [Time] <= '{current_date}') as RevenueSharePercent,
            0 as CumulativeSharePercent
        FROM [Transaction] t
        INNER JOIN Customer c ON t.CustomerID = c.ID
        WHERE t.Total > 0
            AND c.ID > 0
            AND t.[Time] >= '{ytd_start}'
            AND t.[Time] <= '{current_date}'
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountNumber
    ) AS CustomerData
    ORDER BY TotalRevenue DESC
    """
    
    # Query for 2024 revenue
    year_2024_query = f"""
    SELECT TOP 10
        CustomerID,
        CustomerName,
        AccountNumber,
        TotalRevenue,
        TransactionCount,
        FirstPurchase,
        LastPurchase,
        RevenueSharePercent,
        CumulativeSharePercent
    FROM (
        SELECT 
            c.ID as CustomerID,
            ISNULL(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
            c.AccountNumber,
            SUM(t.Total) as TotalRevenue,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            MIN(t.[Time]) as FirstPurchase,
            MAX(t.[Time]) as LastPurchase,
            SUM(t.Total) * 100.0 / (SELECT SUM(Total) FROM [Transaction] WHERE Total > 0 AND CustomerID > 0 AND [Time] >= '{year_2024_start}' AND [Time] <= '{year_2024_end}') as RevenueSharePercent,
            0 as CumulativeSharePercent
        FROM [Transaction] t
        INNER JOIN Customer c ON t.CustomerID = c.ID
        WHERE t.Total > 0
            AND c.ID > 0
            AND t.[Time] >= '{year_2024_start}'
            AND t.[Time] <= '{year_2024_end}'
        GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountNumber
    ) AS CustomerData
    ORDER BY TotalRevenue DESC
    """
    
    # Get grand totals for context
    totals_query = f"""
    SELECT 
        'All-Time' as Period,
        COUNT(DISTINCT CustomerID) as TotalCustomers,
        SUM(Total) as TotalRevenue,
        COUNT(*) as TotalTransactions
    FROM [Transaction]
    WHERE Total > 0 AND CustomerID > 0
    
    UNION ALL
    
    SELECT 
        'YTD 2025' as Period,
        COUNT(DISTINCT CustomerID) as TotalCustomers,
        SUM(Total) as TotalRevenue,
        COUNT(*) as TotalTransactions
    FROM [Transaction]
    WHERE Total > 0 AND CustomerID > 0
        AND [Time] >= '{ytd_start}'
        AND [Time] <= '{current_date}'
    
    UNION ALL
    
    SELECT 
        '2024' as Period,
        COUNT(DISTINCT CustomerID) as TotalCustomers,
        SUM(Total) as TotalRevenue,
        COUNT(*) as TotalTransactions
    FROM [Transaction]
    WHERE Total > 0 AND CustomerID > 0
        AND [Time] >= '{year_2024_start}'
        AND [Time] <= '{year_2024_end}'
    """
    
    try:
        with SQLServerConnection() as db:
            # Execute all queries
            df_all_time = db.execute_query(all_time_query, description="All-time top customers")
            df_ytd = db.execute_query(ytd_query, description="YTD 2025 top customers")
            df_2024 = db.execute_query(year_2024_query, description="2024 top customers")
            df_totals = db.execute_query(totals_query, description="Period totals")
            
            # Create output text file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"customer_concentration_report_{timestamp}.txt"
            
            with open(output_file, 'w') as f:
                # Write header
                f.write("="*100 + "\n")
                f.write(" "*30 + "CUSTOMER CONCENTRATION ANALYSIS\n")
                f.write("="*100 + "\n")
                f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*100 + "\n\n")
                
                # Write period summaries
                if not df_totals.empty:
                    f.write("PERIOD SUMMARIES\n")
                    f.write("-"*100 + "\n")
                    f.write(f"{'Period':<15} {'Total Customers':>20} {'Total Revenue':>20} {'Total Transactions':>20}\n")
                    f.write("-"*100 + "\n")
                    for _, row in df_totals.iterrows():
                        f.write(f"{row['Period']:<15} {row['TotalCustomers']:>20,} ${row['TotalRevenue']:>19,.2f} {row['TotalTransactions']:>20,}\n")
                    f.write("\n\n")
                
                # Write all-time top 10
                f.write("="*100 + "\n")
                f.write("TOP 10 CUSTOMERS - ALL TIME\n")
                f.write("="*100 + "\n")
                if not df_all_time.empty:
                    # Calculate cumulative percentages
                    df_all_time['CumulativeSharePercent'] = df_all_time['RevenueSharePercent'].cumsum()
                    
                    all_time_total = df_all_time['TotalRevenue'].sum()
                    f.write(f"Top 10 Revenue Total: ${all_time_total:,.2f}\n")
                    f.write(f"Top 10 Concentration: {df_all_time['CumulativeSharePercent'].iloc[-1]:.1f}%\n\n")
                    
                    f.write(f"{'Rank':<6} {'Customer Name':<35} {'Account':<12} {'Revenue':>15} {'Share':>8} {'Cumulative':>11} {'Transactions':>13} {'Life(Days)':>11}\n")
                    f.write("-"*100 + "\n")
                    
                    for idx, row in df_all_time.iterrows():
                        rank = idx + 1
                        customer_name = str(row['CustomerName'])[:34]
                        account = str(row['AccountNumber'])[:11] if row['AccountNumber'] else 'N/A'
                        f.write(f"{rank:<6} {customer_name:<35} {account:<12} ${row['TotalRevenue']:>14,.2f} {row['RevenueSharePercent']:>7.2f}% {row['CumulativeSharePercent']:>10.1f}% {row['TransactionCount']:>13,} {row['CustomerLifeDays']:>11,}\n")
                    f.write("\n\n")
                
                # Write YTD 2025 top 10
                f.write("="*100 + "\n")
                f.write(f"TOP 10 CUSTOMERS - YTD 2025 (Jan 1 - {current_date})\n")
                f.write("="*100 + "\n")
                if not df_ytd.empty:
                    # Calculate cumulative percentages
                    df_ytd['CumulativeSharePercent'] = df_ytd['RevenueSharePercent'].cumsum()
                    
                    ytd_total = df_ytd['TotalRevenue'].sum()
                    f.write(f"Top 10 Revenue Total: ${ytd_total:,.2f}\n")
                    f.write(f"Top 10 Concentration: {df_ytd['CumulativeSharePercent'].iloc[-1]:.1f}%\n\n")
                    
                    f.write(f"{'Rank':<6} {'Customer Name':<35} {'Account':<12} {'Revenue':>15} {'Share':>8} {'Cumulative':>11} {'Transactions':>13}\n")
                    f.write("-"*100 + "\n")
                    
                    for idx, row in df_ytd.iterrows():
                        rank = idx + 1
                        customer_name = str(row['CustomerName'])[:34]
                        account = str(row['AccountNumber'])[:11] if row['AccountNumber'] else 'N/A'
                        f.write(f"{rank:<6} {customer_name:<35} {account:<12} ${row['TotalRevenue']:>14,.2f} {row['RevenueSharePercent']:>7.2f}% {row['CumulativeSharePercent']:>10.1f}% {row['TransactionCount']:>13,}\n")
                    f.write("\n\n")
                
                # Write 2024 top 10
                f.write("="*100 + "\n")
                f.write("TOP 10 CUSTOMERS - 2024 FULL YEAR\n")
                f.write("="*100 + "\n")
                if not df_2024.empty:
                    # Calculate cumulative percentages
                    df_2024['CumulativeSharePercent'] = df_2024['RevenueSharePercent'].cumsum()
                    
                    year_2024_total = df_2024['TotalRevenue'].sum()
                    f.write(f"Top 10 Revenue Total: ${year_2024_total:,.2f}\n")
                    f.write(f"Top 10 Concentration: {df_2024['CumulativeSharePercent'].iloc[-1]:.1f}%\n\n")
                    
                    f.write(f"{'Rank':<6} {'Customer Name':<35} {'Account':<12} {'Revenue':>15} {'Share':>8} {'Cumulative':>11} {'Transactions':>13}\n")
                    f.write("-"*100 + "\n")
                    
                    for idx, row in df_2024.iterrows():
                        rank = idx + 1
                        customer_name = str(row['CustomerName'])[:34]
                        account = str(row['AccountNumber'])[:11] if row['AccountNumber'] else 'N/A'
                        f.write(f"{rank:<6} {customer_name:<35} {account:<12} ${row['TotalRevenue']:>14,.2f} {row['RevenueSharePercent']:>7.2f}% {row['CumulativeSharePercent']:>10.1f}% {row['TransactionCount']:>13,}\n")
                    f.write("\n\n")
                
                # Write comparison analysis
                f.write("="*100 + "\n")
                f.write("CUSTOMER CONCENTRATION INSIGHTS\n")
                f.write("="*100 + "\n")
                
                if not df_all_time.empty and not df_ytd.empty and not df_2024.empty:
                    f.write("\nKEY METRICS:\n")
                    f.write("-"*50 + "\n")
                    f.write(f"  • Top 10 Concentration All-Time:  {df_all_time['CumulativeSharePercent'].iloc[-1]:.1f}%\n")
                    f.write(f"  • Top 10 Concentration 2024:      {df_2024['CumulativeSharePercent'].iloc[-1]:.1f}%\n")
                    f.write(f"  • Top 10 Concentration YTD 2025:  {df_ytd['CumulativeSharePercent'].iloc[-1]:.1f}%\n")
                    
                    # Check customer retention in top 10
                    all_time_customers = set(df_all_time['CustomerID'].values)
                    ytd_customers = set(df_ytd['CustomerID'].values)
                    year_2024_customers = set(df_2024['CustomerID'].values)
                    
                    retained_2024_to_ytd = year_2024_customers.intersection(ytd_customers)
                    new_in_ytd = ytd_customers - year_2024_customers
                    
                    f.write("\nCUSTOMER RETENTION:\n")
                    f.write("-"*50 + "\n")
                    f.write(f"  • Customers in Top 10 both 2024 and YTD 2025: {len(retained_2024_to_ytd)}\n")
                    f.write(f"  • New customers in YTD 2025 Top 10: {len(new_in_ytd)}\n")
                    
                    # Revenue concentration trend
                    f.write("\nCONCENTRATION TREND:\n")
                    f.write("-"*50 + "\n")
                    concentration_change = df_ytd['CumulativeSharePercent'].iloc[-1] - df_2024['CumulativeSharePercent'].iloc[-1]
                    if concentration_change > 0:
                        f.write(f"  ⚠️  Concentration INCREASING: +{concentration_change:.1f}% points YTD vs 2024\n")
                    else:
                        f.write(f"  ✅ Concentration DECREASING: {concentration_change:.1f}% points YTD vs 2024\n")
                
                f.write("\n" + "="*100 + "\n")
                f.write("END OF REPORT\n")
                f.write("="*100 + "\n")
            
            print(f"\n✅ Customer concentration analysis complete!")
            print(f"📄 Report saved to: {output_file}")
            
            # Also display summary to console
            print("\nQUICK SUMMARY:")
            print("-"*50)
            if not df_all_time.empty:
                df_all_time['CumulativeSharePercent'] = df_all_time['RevenueSharePercent'].cumsum()
                print(f"All-Time Top 10 Concentration: {df_all_time['CumulativeSharePercent'].iloc[-1]:.1f}%")
            if not df_2024.empty:
                df_2024['CumulativeSharePercent'] = df_2024['RevenueSharePercent'].cumsum()
                print(f"2024 Top 10 Concentration: {df_2024['CumulativeSharePercent'].iloc[-1]:.1f}%")
            if not df_ytd.empty:
                df_ytd['CumulativeSharePercent'] = df_ytd['RevenueSharePercent'].cumsum()
                print(f"YTD 2025 Top 10 Concentration: {df_ytd['CumulativeSharePercent'].iloc[-1]:.1f}%")
            
            return output_file
            
    except Exception as e:
        logger.error(f"Error analyzing customer concentration: {e}")
        return None

if __name__ == "__main__":
    output_file = analyze_customer_concentration()
    
    if output_file:
        print(f"\n✅ Analysis completed successfully!")
        print(f"📄 Full report available in: {output_file}")
    else:
        print("\n❌ Analysis failed. Please check the logs.")