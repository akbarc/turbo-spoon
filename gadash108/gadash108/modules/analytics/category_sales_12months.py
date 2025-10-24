#!/usr/bin/env python3
"""
Sales by Category - Trailing 12 Months Analysis
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json

def analyze_category_sales_12months():
    """Analyze sales by category for the trailing 12 months."""
    
    with SQLServerConnection() as db:
        print("=" * 80)
        print("SALES BY CATEGORY - TRAILING 12 MONTHS")
        print("=" * 80)
        
        # Main query for category sales
        query_category_sales = """
        SELECT 
            ISNULL(cat.Name, 'UNCATEGORIZED') as Category,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
            SUM(te.Quantity) as TotalUnits,
            SUM(te.Price * te.Quantity) as TotalSales,
            SUM(te.Price * te.Quantity - te.Cost * te.Quantity) as GrossProfit,
            CASE 
                WHEN SUM(te.Price * te.Quantity) > 0 
                THEN (SUM(te.Price * te.Quantity - te.Cost * te.Quantity) / SUM(te.Price * te.Quantity)) * 100
                ELSE 0 
            END as GrossProfitMargin
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
        GROUP BY cat.Name
        ORDER BY TotalSales DESC
        """
        
        df_categories = db.execute_query(query_category_sales, description="Get category sales")
        
        # Calculate totals
        total_sales = df_categories['TotalSales'].sum()
        total_profit = df_categories['GrossProfit'].sum()
        
        print(f"\nPeriod: {(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Total Sales: ${total_sales:,.2f}")
        print(f"Total Gross Profit: ${total_profit:,.2f}")
        print(f"Overall GP Margin: {(total_profit/total_sales*100):.1f}%\n")
        
        # Display top categories
        print("=" * 80)
        print(f"{'Category':<25} {'Sales':>15} {'% of Total':>10} {'GP%':>8} {'Units':>12} {'Customers':>10}")
        print("-" * 80)
        
        for idx, row in df_categories.head(20).iterrows():
            pct_of_total = (row['TotalSales'] / total_sales) * 100
            print(f"{row['Category'][:25]:<25} ${row['TotalSales']:>14,.2f} {pct_of_total:>9.1f}% {row['GrossProfitMargin']:>7.1f}% {row['TotalUnits']:>12,.0f} {row['UniqueCustomers']:>10,}")
        
        # Monthly trend for top 5 categories
        print("\n" + "=" * 80)
        print("MONTHLY TREND - TOP 5 CATEGORIES")
        print("=" * 80)
        
        top_5_categories = df_categories.head(5)['Category'].tolist()
        
        query_monthly_trend = """
        SELECT 
            CONVERT(varchar(7), t.Time, 120) as Month,
            ISNULL(cat.Name, 'UNCATEGORIZED') as Category,
            SUM(te.Price * te.Quantity) as MonthlySales
        FROM [dbo].[Transaction] t
        JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
            AND ISNULL(cat.Name, 'UNCATEGORIZED') IN ({})
        GROUP BY CONVERT(varchar(7), t.Time, 120), cat.Name
        ORDER BY Month, MonthlySales DESC
        """.format(','.join([f"'{cat}'" for cat in top_5_categories]))
        
        df_monthly = db.execute_query(query_monthly_trend, description="Get monthly trend")
        
        # Pivot for display
        pivot_df = df_monthly.pivot(index='Month', columns='Category', values='MonthlySales').fillna(0)
        
        print("\nMonthly Sales by Top 5 Categories:")
        print("-" * 80)
        print(f"{'Month':<10}", end='')
        for cat in pivot_df.columns[:5]:
            print(f"{cat[:15]:>15}", end='')
        print()
        print("-" * 80)
        
        for month, row in pivot_df.iterrows():
            print(f"{month:<10}", end='')
            for cat in pivot_df.columns[:5]:
                print(f"${row[cat]:>14,.0f}", end='')
            print()
        
        # Category performance metrics
        print("\n" + "=" * 80)
        print("CATEGORY PERFORMANCE METRICS")
        print("=" * 80)
        
        # Add performance calculations
        df_categories['SalesPerCustomer'] = df_categories['TotalSales'] / df_categories['UniqueCustomers']
        df_categories['UnitsPerTransaction'] = df_categories['TotalUnits'] / df_categories['TransactionCount']
        df_categories['AvgUnitPrice'] = df_categories['TotalSales'] / df_categories['TotalUnits']
        
        print(f"\n{'Category':<25} {'$/Customer':>12} {'Units/Trans':>12} {'Avg Price':>10}")
        print("-" * 60)
        
        for idx, row in df_categories.head(15).iterrows():
            print(f"{row['Category'][:25]:<25} ${row['SalesPerCustomer']:>11,.2f} {row['UnitsPerTransaction']:>11.1f} ${row['AvgUnitPrice']:>9.2f}")
        
        # Tobacco categories analysis
        print("\n" + "=" * 80)
        print("TOBACCO CATEGORIES ANALYSIS")
        print("=" * 80)
        
        tobacco_categories = df_categories[df_categories['Category'].str.contains('CIGARETTE|CIGAR|TOBACCO|CHEW|SNUFF|LT-TAX', case=False, na=False)]
        
        if not tobacco_categories.empty:
            tobacco_total = tobacco_categories['TotalSales'].sum()
            print(f"\nTotal Tobacco Sales: ${tobacco_total:,.2f}")
            print(f"Tobacco % of Total Sales: {(tobacco_total/total_sales*100):.1f}%\n")
            
            print(f"{'Tobacco Category':<30} {'Sales':>15} {'GP%':>8}")
            print("-" * 55)
            for idx, row in tobacco_categories.iterrows():
                print(f"{row['Category'][:30]:<30} ${row['TotalSales']:>14,.2f} {row['GrossProfitMargin']:>7.1f}%")
        
        # Export results
        results = {
            'analysis_date': datetime.now().isoformat(),
            'period_start': (datetime.now() - timedelta(days=365)).isoformat(),
            'period_end': datetime.now().isoformat(),
            'total_sales': float(total_sales),
            'total_gross_profit': float(total_profit),
            'overall_gp_margin': float(total_profit/total_sales*100) if total_sales > 0 else 0,
            'categories': df_categories.to_dict('records'),
            'top_5_monthly_trend': df_monthly.to_dict('records') if not df_monthly.empty else [],
            'tobacco_total_sales': float(tobacco_categories['TotalSales'].sum()) if not tobacco_categories.empty else 0,
            'tobacco_pct_of_total': float((tobacco_categories['TotalSales'].sum()/total_sales*100)) if not tobacco_categories.empty and total_sales > 0 else 0
        }
        
        # Save to JSON
        with open('category_sales_12months.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save to Excel for easy sharing
        with pd.ExcelWriter('category_sales_12months.xlsx', engine='openpyxl') as writer:
            df_categories.to_excel(writer, sheet_name='Category Sales', index=False)
            if not df_monthly.empty:
                pivot_df.to_excel(writer, sheet_name='Monthly Trend')
            if not tobacco_categories.empty:
                tobacco_categories.to_excel(writer, sheet_name='Tobacco Categories', index=False)
        
        print(f"\n✅ Analysis complete!")
        print(f"📊 Results saved to:")
        print(f"   - category_sales_12months.json")
        print(f"   - category_sales_12months.xlsx")
        print("=" * 80)

if __name__ == "__main__":
    analyze_category_sales_12months()