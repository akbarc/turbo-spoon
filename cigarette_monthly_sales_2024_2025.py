#!/usr/bin/env python3
"""
Cigarette Sales by Month - Total Units Sold
2024-2025 Period
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime
import calendar

def get_monthly_cigarette_sales():
    """Get cigarette sales by month for 2024-2025"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Query for monthly cigarette sales
        query = """
        SELECT
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            DATENAME(MONTH, t.Time) as MonthName,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            COUNT(DISTINCT te.ItemID) as UniqueProducts,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            AVG(te.Price) as AvgPrice
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.Time >= '2024-01-01'
            AND t.Time < '2026-01-01'
            AND c.Name LIKE '%CIGARETTE%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
            AND i.Description NOT LIKE '%PAPER%'
            AND i.Description NOT LIKE '%TUBE%'
            AND i.Description NOT LIKE '%MACHINE%'
            AND i.Description NOT LIKE '%CASE%'
        GROUP BY
            YEAR(t.Time),
            MONTH(t.Time),
            DATENAME(MONTH, t.Time)
        ORDER BY
            YEAR(t.Time),
            MONTH(t.Time)
        """

        df = conn.execute_query(query, description="Get monthly cigarette sales 2024-2025")

        return df

    finally:
        conn.close()

def main():
    print("="*80)
    print("CIGARETTE SALES BY MONTH - TOTAL UNITS SOLD")
    print("2024-2025 PERIOD")
    print("="*80)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get monthly sales data
    df = get_monthly_cigarette_sales()

    if df is None or len(df) == 0:
        print("No sales data found for 2024-2025")
        return

    # Convert numeric columns
    numeric_cols = ['UnitsSold', 'TotalRevenue', 'AvgPrice', 'Transactions']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Create month-year column for display
    df['Month-Year'] = df.apply(lambda x: f"{x['MonthName'][:3]} {int(x['Year'])}", axis=1)

    # Separate 2024 and 2025 data
    df_2024 = df[df['Year'] == 2024].copy()
    df_2025 = df[df['Year'] == 2025].copy()

    # Print 2024 Summary
    print("2024 MONTHLY SALES")
    print("-"*80)

    if len(df_2024) > 0:
        print(f"{'Month':<15} {'Units Sold':>12} {'Transactions':>12} {'Revenue':>15} {'Avg Price':>10}")
        print("-"*80)

        total_2024_units = 0
        total_2024_revenue = 0
        total_2024_trans = 0

        for _, row in df_2024.iterrows():
            print(f"{row['MonthName']:<15} {row['UnitsSold']:12,.0f} {row['Transactions']:12,.0f} ${row['TotalRevenue']:14,.2f} ${row['AvgPrice']:9.2f}")
            total_2024_units += row['UnitsSold']
            total_2024_revenue += row['TotalRevenue']
            total_2024_trans += row['Transactions']

        print("-"*80)
        print(f"{'2024 TOTAL':<15} {total_2024_units:12,.0f} {total_2024_trans:12,.0f} ${total_2024_revenue:14,.2f}")

        # Calculate monthly average
        months_2024 = len(df_2024)
        print(f"{'2024 AVG/MONTH':<15} {total_2024_units/months_2024:12,.0f} {total_2024_trans/months_2024:12,.0f} ${total_2024_revenue/months_2024:14,.2f}")
    else:
        print("No data available for 2024")

    # Print 2025 Summary
    print("\n" + "="*80)
    print("2025 MONTHLY SALES (Year to Date)")
    print("-"*80)

    if len(df_2025) > 0:
        print(f"{'Month':<15} {'Units Sold':>12} {'Transactions':>12} {'Revenue':>15} {'Avg Price':>10}")
        print("-"*80)

        total_2025_units = 0
        total_2025_revenue = 0
        total_2025_trans = 0

        for _, row in df_2025.iterrows():
            print(f"{row['MonthName']:<15} {row['UnitsSold']:12,.0f} {row['Transactions']:12,.0f} ${row['TotalRevenue']:14,.2f} ${row['AvgPrice']:9.2f}")
            total_2025_units += row['UnitsSold']
            total_2025_revenue += row['TotalRevenue']
            total_2025_trans += row['Transactions']

        print("-"*80)
        print(f"{'2025 YTD TOTAL':<15} {total_2025_units:12,.0f} {total_2025_trans:12,.0f} ${total_2025_revenue:14,.2f}")

        # Calculate monthly average
        months_2025 = len(df_2025)
        print(f"{'2025 AVG/MONTH':<15} {total_2025_units/months_2025:12,.0f} {total_2025_trans/months_2025:12,.0f} ${total_2025_revenue/months_2025:14,.2f}")
    else:
        print("No data available for 2025")

    # Year-over-Year Comparison if both years have data
    if len(df_2024) > 0 and len(df_2025) > 0:
        print("\n" + "="*80)
        print("YEAR-OVER-YEAR COMPARISON (Same months only)")
        print("-"*80)

        # Get months that exist in both years
        months_2024_set = set(df_2024['Month'].values)
        months_2025_set = set(df_2025['Month'].values)
        common_months = months_2024_set.intersection(months_2025_set)

        if common_months:
            print(f"{'Month':<15} {'2024 Units':>12} {'2025 Units':>12} {'Change':>12} {'% Change':>10}")
            print("-"*80)

            for month in sorted(common_months):
                units_2024 = df_2024[df_2024['Month'] == month]['UnitsSold'].values[0]
                units_2025 = df_2025[df_2025['Month'] == month]['UnitsSold'].values[0]
                change = units_2025 - units_2024
                pct_change = (change / units_2024 * 100) if units_2024 > 0 else 0

                month_name = calendar.month_name[int(month)]
                print(f"{month_name:<15} {units_2024:12,.0f} {units_2025:12,.0f} {change:+12,.0f} {pct_change:+9.1f}%")

    # Create visualization data
    print("\n" + "="*80)
    print("MONTHLY TREND VISUALIZATION")
    print("="*80)

    # Combine all data for chart
    all_months = []
    for _, row in df.iterrows():
        all_months.append({
            'Period': f"{int(row['Year'])}-{int(row['Month']):02d}",
            'Month': row['Month-Year'],
            'Units': row['UnitsSold'],
            'Revenue': row['TotalRevenue']
        })

    # Print bar chart representation
    if all_months:
        max_units = max([m['Units'] for m in all_months])
        scale = 50 / max_units if max_units > 0 else 1

        print("\nUnits Sold (Each █ = ~{:.0f} units)".format(max_units/50))
        print("-"*80)

        for month in all_months:
            bar_length = int(month['Units'] * scale)
            bar = '█' * bar_length
            print(f"{month['Month']:10} {month['Units']:8,.0f} |{bar}")

    # Save to Excel
    with pd.ExcelWriter('cigarette_monthly_sales_2024_2025.xlsx', engine='openpyxl') as writer:
        # All monthly data
        df.to_excel(writer, sheet_name='Monthly_Sales', index=False)

        # 2024 data
        if len(df_2024) > 0:
            df_2024.to_excel(writer, sheet_name='2024_Monthly', index=False)

        # 2025 data
        if len(df_2025) > 0:
            df_2025.to_excel(writer, sheet_name='2025_Monthly', index=False)

        # Summary statistics
        summary_data = []

        if len(df_2024) > 0:
            summary_data.append({
                'Year': '2024',
                'Total_Units': df_2024['UnitsSold'].sum(),
                'Total_Revenue': df_2024['TotalRevenue'].sum(),
                'Total_Transactions': df_2024['Transactions'].sum(),
                'Avg_Units_Per_Month': df_2024['UnitsSold'].mean(),
                'Months_Count': len(df_2024)
            })

        if len(df_2025) > 0:
            summary_data.append({
                'Year': '2025',
                'Total_Units': df_2025['UnitsSold'].sum(),
                'Total_Revenue': df_2025['TotalRevenue'].sum(),
                'Total_Transactions': df_2025['Transactions'].sum(),
                'Avg_Units_Per_Month': df_2025['UnitsSold'].mean(),
                'Months_Count': len(df_2025)
            })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Annual_Summary', index=False)

    print(f"\n✅ Detailed report saved to: cigarette_monthly_sales_2024_2025.xlsx")

    # Print grand totals
    print("\n" + "="*80)
    print("GRAND TOTALS (2024-2025)")
    print("="*80)

    total_units_all = df['UnitsSold'].sum()
    total_revenue_all = df['TotalRevenue'].sum()
    total_trans_all = df['Transactions'].sum()

    print(f"Total Units Sold: {total_units_all:,.0f}")
    print(f"Total Revenue: ${total_revenue_all:,.2f}")
    print(f"Total Transactions: {total_trans_all:,.0f}")
    print(f"Average Price per Unit: ${total_revenue_all/total_units_all:.2f}" if total_units_all > 0 else "N/A")

if __name__ == "__main__":
    main()