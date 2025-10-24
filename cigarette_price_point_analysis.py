#!/usr/bin/env python3
"""
Cigarette Price Point Analysis
Shows volume sold at each distinct selling price and cost combination by brand
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime, timedelta

def get_price_point_sales():
    """Get sales grouped by distinct price and cost points"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        print(f"Analyzing sales from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")

        # Query to get volume at each price point
        sales_query = f"""
        SELECT
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
            te.Price as SellingPrice,
            i.Cost as ItemCost,
            SUM(te.Quantity) as UnitsSold,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            SUM(te.Price * te.Quantity) as Revenue,
            MIN(i.Description) as SampleProduct
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
            te.Price,
            i.Cost
        ORDER BY Brand, ItemCost DESC, SellingPrice DESC
        """

        sales_df = conn.execute_query(sales_query, description="Get sales by price points")

        return sales_df

    finally:
        conn.close()

def main():
    print("="*100)
    print("CIGARETTE SALES BY PRICE POINT - 3 MONTH ANALYSIS")
    print("="*100)
    print(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get sales data
    sales_df = get_price_point_sales()

    if sales_df is None or len(sales_df) == 0:
        print("No sales data found for the period")
        return

    # Convert numeric columns
    numeric_cols = ['SellingPrice', 'ItemCost', 'UnitsSold', 'Revenue']
    for col in numeric_cols:
        if col in sales_df.columns:
            sales_df[col] = pd.to_numeric(sales_df[col], errors='coerce')

    # Calculate margin for each price point
    sales_df['GrossProfit'] = (sales_df['SellingPrice'] - sales_df['ItemCost']) * sales_df['UnitsSold']
    sales_df['Margin%'] = ((sales_df['SellingPrice'] - sales_df['ItemCost']) / sales_df['SellingPrice'] * 100).round(1)

    # Major brands to focus on
    major_brands = ['NEWPORT', 'MARLBORO', 'CAMEL', 'AMERICAN SPIRIT', 'PALL MALL',
                   'WINSTON', 'KOOL', 'VIRGINIA SLIMS', 'PARLIAMENT', 'BASIC', 'L&M',
                   'MAVERICK', 'SALEM', 'DORAL', 'MISTY']

    # Create separate tables by selling price and by cost
    for brand in major_brands:
        brand_data = sales_df[sales_df['Brand'] == brand]

        if len(brand_data) > 0:
            print(f"\n{'='*80}")
            print(f"BRAND: {brand}")
            print(f"{'='*80}")

            total_units = brand_data['UnitsSold'].sum()
            total_revenue = brand_data['Revenue'].sum()
            unique_prices = len(brand_data['SellingPrice'].unique())
            unique_costs = len(brand_data['ItemCost'].unique())

            print(f"Total Units: {total_units:,.0f} | Revenue: ${total_revenue:,.2f}")
            print(f"Unique Selling Prices: {unique_prices} | Unique Cost Points: {unique_costs}")

            # Group by COST to show volume at each cost level
            print(f"\n--- BY COST TIER ---")
            cost_summary = brand_data.groupby('ItemCost').agg({
                'UnitsSold': 'sum',
                'SellingPrice': ['mean', 'min', 'max'],
                'Revenue': 'sum',
                'SampleProduct': 'first'
            }).round(2)

            cost_summary.columns = ['Units_Sold', 'Avg_Sell_Price', 'Min_Sell_Price', 'Max_Sell_Price', 'Revenue', 'Sample_Product']
            cost_summary = cost_summary.sort_values('ItemCost', ascending=False)

            print(f"{'Cost':>8} {'Units':>10} {'Avg Sell':>10} {'Min Sell':>10} {'Max Sell':>10} {'Revenue':>12}")
            print("-" * 62)

            for cost, row in cost_summary.iterrows():
                print(f"${float(cost):7.2f} {row['Units_Sold']:10.0f} ${row['Avg_Sell_Price']:9.2f} ${row['Min_Sell_Price']:9.2f} ${row['Max_Sell_Price']:9.2f} ${row['Revenue']:11,.2f}")

            # Show detailed price points for each cost
            print(f"\n--- DETAILED PRICE POINTS BY COST ---")

            for cost in sorted(brand_data['ItemCost'].unique(), reverse=True):
                cost_data = brand_data[brand_data['ItemCost'] == cost]
                print(f"\nCost: ${float(cost):.2f}")
                print(f"{'Sell Price':>12} {'Units Sold':>12} {'Revenue':>12} {'Margin%':>10}")
                print("-" * 48)

                for _, row in cost_data.sort_values('SellingPrice', ascending=False).iterrows():
                    print(f"${row['SellingPrice']:11.2f} {row['UnitsSold']:12.0f} ${row['Revenue']:11,.2f} {row['Margin%']:9.1f}%")

    # Create comprehensive Excel report
    with pd.ExcelWriter('cigarette_price_point_analysis.xlsx', engine='openpyxl') as writer:
        # Sheet 1: All price points
        sales_df.to_excel(writer, sheet_name='All_Price_Points', index=False)

        # Sheet 2: Summary by brand and cost
        brand_cost_summary = sales_df.groupby(['Brand', 'ItemCost']).agg({
            'UnitsSold': 'sum',
            'SellingPrice': ['mean', 'min', 'max', 'count'],
            'Revenue': 'sum',
            'GrossProfit': 'sum'
        }).round(2)
        brand_cost_summary.to_excel(writer, sheet_name='By_Brand_Cost')

        # Sheet 3: Summary by brand and selling price
        brand_price_summary = sales_df.groupby(['Brand', 'SellingPrice']).agg({
            'UnitsSold': 'sum',
            'ItemCost': ['mean', 'min', 'max'],
            'Revenue': 'sum',
            'GrossProfit': 'sum'
        }).round(2)
        brand_price_summary.to_excel(writer, sheet_name='By_Brand_SellingPrice')

        # Sheet 4: Top volume price points
        top_volume = sales_df.nlargest(100, 'UnitsSold')[['Brand', 'SellingPrice', 'ItemCost', 'UnitsSold', 'Revenue', 'Margin%', 'SampleProduct']]
        top_volume.to_excel(writer, sheet_name='Top_100_Volume_PricePoints', index=False)

    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)

    # Overall stats
    print(f"Total Unique Price Points: {len(sales_df)}")
    print(f"Total Units Sold: {sales_df['UnitsSold'].sum():,.0f}")
    print(f"Total Revenue: ${sales_df['Revenue'].sum():,.2f}")

    # Top selling price points
    print("\nTOP 10 VOLUME PRICE POINTS:")
    print(f"{'Brand':15} {'Sell Price':>10} {'Cost':>10} {'Units':>10} {'Revenue':>12}")
    print("-" * 60)

    for _, row in sales_df.nlargest(10, 'UnitsSold').iterrows():
        brand = row['Brand'][:14] if len(row['Brand']) > 14 else row['Brand']
        print(f"{brand:15} ${row['SellingPrice']:9.2f} ${row['ItemCost']:9.2f} {row['UnitsSold']:10.0f} ${row['Revenue']:11,.2f}")

    print(f"\n✅ Detailed report saved to: cigarette_price_point_analysis.xlsx")

if __name__ == "__main__":
    main()