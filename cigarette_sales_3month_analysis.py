#!/usr/bin/env python3
"""
3-Month Cigarette Sales Analysis by Brand
Shows quantity sold, selling price, and cost by brand and month
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime, timedelta
import calendar

def get_cigarette_sales():
    """Get cigarette sales data for last 3 months"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        print(f"Analyzing sales from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")

        # Query sales data with brand identification
        sales_query = f"""
        SELECT
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            CASE
                WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                WHEN UPPER(i.Description) LIKE '%VIRGINIA SLIM%' OR UPPER(i.Description) LIKE '%VIRG SL%' THEN 'VIRGINIA SLIMS'
                WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                WHEN UPPER(i.Description) LIKE '%LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                WHEN UPPER(i.Description) LIKE '%KENT%' THEN 'KENT'
                WHEN UPPER(i.Description) LIKE '%BASIC%' THEN 'BASIC'
                WHEN UPPER(i.Description) LIKE '%DORAL%' THEN 'DORAL'
                WHEN UPPER(i.Description) LIKE '%PYRAMID%' THEN 'PYRAMID'
                WHEN UPPER(i.Description) LIKE '%SENECA%' THEN 'SENECA'
                WHEN UPPER(i.Description) LIKE '%MISTY%' THEN 'MISTY'
                WHEN UPPER(i.Description) LIKE '%EAGLE 20%' THEN 'EAGLE 20S'
                WHEN UPPER(i.Description) LIKE '%LIGGETT%' THEN 'LIGGETT SELECT'
                WHEN UPPER(i.Description) LIKE '%305%' THEN '305S'
                WHEN UPPER(i.Description) LIKE '%WAVE%' THEN 'WAVE'
                WHEN UPPER(i.Description) LIKE '%USA GOLD%' THEN 'USA GOLD'
                WHEN UPPER(i.Description) LIKE '%SONOMA%' THEN 'SONOMA'
                WHEN UPPER(i.Description) LIKE '%B&H%' OR UPPER(i.Description) LIKE '%BENSON%' THEN 'BENSON & HEDGES'
                WHEN UPPER(i.Description) LIKE '%CAPRI%' THEN 'CAPRI'
                ELSE 'OTHER'
            END as Brand,
            i.ItemLookupCode as SKU,
            i.Description,
            SUM(te.Quantity) as QuantitySold,
            AVG(te.Price) as AvgSellingPrice,
            MIN(te.Price) as MinPrice,
            MAX(te.Price) as MaxPrice,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            AVG(i.Cost) as ItemCost,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.Time >= '{start_date.strftime('%Y-%m-%d')}'
            AND t.Time <= '{end_date.strftime('%Y-%m-%d')}'
            AND c.Name LIKE '%CIGARETTE%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
            AND i.Description NOT LIKE '%CASE%'
        GROUP BY
            YEAR(t.Time),
            MONTH(t.Time),
            CASE
                WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                WHEN UPPER(i.Description) LIKE '%VIRGINIA SLIM%' OR UPPER(i.Description) LIKE '%VIRG SL%' THEN 'VIRGINIA SLIMS'
                WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                WHEN UPPER(i.Description) LIKE '%LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                WHEN UPPER(i.Description) LIKE '%KENT%' THEN 'KENT'
                WHEN UPPER(i.Description) LIKE '%BASIC%' THEN 'BASIC'
                WHEN UPPER(i.Description) LIKE '%DORAL%' THEN 'DORAL'
                WHEN UPPER(i.Description) LIKE '%PYRAMID%' THEN 'PYRAMID'
                WHEN UPPER(i.Description) LIKE '%SENECA%' THEN 'SENECA'
                WHEN UPPER(i.Description) LIKE '%MISTY%' THEN 'MISTY'
                WHEN UPPER(i.Description) LIKE '%EAGLE 20%' THEN 'EAGLE 20S'
                WHEN UPPER(i.Description) LIKE '%LIGGETT%' THEN 'LIGGETT SELECT'
                WHEN UPPER(i.Description) LIKE '%305%' THEN '305S'
                WHEN UPPER(i.Description) LIKE '%WAVE%' THEN 'WAVE'
                WHEN UPPER(i.Description) LIKE '%USA GOLD%' THEN 'USA GOLD'
                WHEN UPPER(i.Description) LIKE '%SONOMA%' THEN 'SONOMA'
                WHEN UPPER(i.Description) LIKE '%B&H%' OR UPPER(i.Description) LIKE '%BENSON%' THEN 'BENSON & HEDGES'
                WHEN UPPER(i.Description) LIKE '%CAPRI%' THEN 'CAPRI'
                ELSE 'OTHER'
            END,
            i.ItemLookupCode,
            i.Description,
            i.Cost
        ORDER BY Brand, Year, Month
        """

        sales_df = conn.execute_query(sales_query, description="Get 3-month cigarette sales")

        return sales_df

    finally:
        conn.close()

def main():
    print("="*80)
    print("3-MONTH CIGARETTE SALES ANALYSIS BY BRAND")
    print("="*80)
    print(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get sales data
    sales_df = get_cigarette_sales()

    if sales_df is None or len(sales_df) == 0:
        print("No sales data found for the period")
        return

    # Convert numeric columns to float
    numeric_cols = ['QuantitySold', 'AvgSellingPrice', 'TotalRevenue', 'ItemCost']
    for col in numeric_cols:
        if col in sales_df.columns:
            sales_df[col] = pd.to_numeric(sales_df[col], errors='coerce')

    # Create month names for display
    sales_df['MonthName'] = sales_df.apply(lambda x: f"{calendar.month_abbr[int(x['Month'])]} {int(x['Year'])}", axis=1)

    # Calculate profit margin
    sales_df['GrossProfit'] = sales_df['TotalRevenue'] - (sales_df['QuantitySold'] * sales_df['ItemCost'])
    sales_df['ProfitMargin%'] = (sales_df['GrossProfit'] / sales_df['TotalRevenue'] * 100).fillna(0)

    # Group by Brand and Month for summary
    brand_month_summary = sales_df.groupby(['Brand', 'MonthName', 'Year', 'Month']).agg({
        'QuantitySold': 'sum',
        'TotalRevenue': 'sum',
        'AvgSellingPrice': 'mean',
        'ItemCost': 'mean',
        'GrossProfit': 'sum',
        'TransactionCount': 'sum'
    }).round(2)

    # Sort by year and month properly
    brand_month_summary = brand_month_summary.reset_index()
    brand_month_summary = brand_month_summary.sort_values(['Brand', 'Year', 'Month'])

    # Print summary by major brands
    major_brands = ['MARLBORO', 'NEWPORT', 'CAMEL', 'AMERICAN SPIRIT', 'PALL MALL',
                   'WINSTON', 'KOOL', 'VIRGINIA SLIMS', 'PARLIAMENT', 'BASIC']

    for brand in major_brands:
        brand_data = brand_month_summary[brand_month_summary['Brand'] == brand]
        if len(brand_data) > 0:
            print(f"\n{'='*60}")
            print(f"BRAND: {brand}")
            print(f"{'='*60}")

            total_qty = brand_data['QuantitySold'].sum()
            total_revenue = brand_data['TotalRevenue'].sum()
            avg_price = brand_data['AvgSellingPrice'].mean()
            avg_cost = brand_data['ItemCost'].mean()
            total_profit = brand_data['GrossProfit'].sum()

            print(f"3-Month Totals: {total_qty:.0f} units | Revenue: ${total_revenue:,.2f} | Profit: ${total_profit:,.2f}")
            print(f"Average Price: ${avg_price:.2f} | Average Cost: ${avg_cost:.2f} | Margin: {(total_profit/total_revenue*100):.1f}%\n")

            print(f"{'Month':<12} {'Qty Sold':>10} {'Avg Price':>10} {'Avg Cost':>10} {'Revenue':>12} {'Profit':>12} {'Margin%':>8}")
            print("-" * 82)

            for _, row in brand_data.iterrows():
                margin = (row['GrossProfit']/row['TotalRevenue']*100) if row['TotalRevenue'] > 0 else 0
                print(f"{row['MonthName']:<12} {row['QuantitySold']:10.0f} ${row['AvgSellingPrice']:9.2f} ${row['ItemCost']:9.2f} ${row['TotalRevenue']:11,.2f} ${row['GrossProfit']:11,.2f} {margin:7.1f}%")

    # Create Excel report with multiple sheets
    with pd.ExcelWriter('cigarette_sales_3month_analysis.xlsx', engine='openpyxl') as writer:
        # Sheet 1: Summary by Brand and Month
        brand_month_summary.to_excel(writer, sheet_name='Brand_Monthly_Summary', index=False)

        # Sheet 2: Detailed sales data
        sales_df.to_excel(writer, sheet_name='Detailed_Sales', index=False)

        # Sheet 3: Brand Totals
        brand_totals = sales_df.groupby('Brand').agg({
            'QuantitySold': 'sum',
            'TotalRevenue': 'sum',
            'AvgSellingPrice': 'mean',
            'ItemCost': 'mean',
            'GrossProfit': 'sum',
            'TransactionCount': 'sum'
        }).round(2)
        brand_totals['ProfitMargin%'] = (brand_totals['GrossProfit'] / brand_totals['TotalRevenue'] * 100).round(1)
        brand_totals = brand_totals.sort_values('TotalRevenue', ascending=False)
        brand_totals.to_excel(writer, sheet_name='Brand_3Month_Totals')

        # Sheet 4: Top Products
        top_products = sales_df.groupby(['Brand', 'Description']).agg({
            'QuantitySold': 'sum',
            'TotalRevenue': 'sum',
            'AvgSellingPrice': 'mean',
            'ItemCost': 'mean'
        }).round(2)
        top_products = top_products.sort_values('QuantitySold', ascending=False).head(50)
        top_products.to_excel(writer, sheet_name='Top_50_Products')

    print("\n" + "="*80)
    print("OVERALL 3-MONTH SUMMARY")
    print("="*80)

    total_units = sales_df['QuantitySold'].sum()
    total_revenue = sales_df['TotalRevenue'].sum()
    total_profit = sales_df['GrossProfit'].sum()

    print(f"Total Units Sold: {total_units:,.0f}")
    print(f"Total Revenue: ${total_revenue:,.2f}")
    print(f"Total Gross Profit: ${total_profit:,.2f}")
    print(f"Overall Profit Margin: {(total_profit/total_revenue*100):.1f}%")

    print(f"\n✅ Detailed report saved to: cigarette_sales_3month_analysis.xlsx")

if __name__ == "__main__":
    main()