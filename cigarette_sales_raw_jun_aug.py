#!/usr/bin/env python3
"""
Raw Cigarette Sales Data - June 1 to August 31
Exact transaction data with brand identification
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

def get_raw_sales_data():
    """Get all cigarette sales transactions from June 1 to August 31"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Query for exact sales data with brand identification
        query = """
        SELECT
            t.TransactionNumber,
            t.Time as TransactionDate,
            i.ItemLookupCode as SKU,
            i.Description as ProductDescription,
            te.Quantity as QuantitySold,
            te.Price as SellingPrice,
            i.Cost as ItemCost,
            (te.Price * te.Quantity) as TotalRevenue,
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
                WHEN UPPER(i.Description) LIKE '%LUCKY STRIKE%' OR UPPER(i.Description) LIKE '%LUCKY STR%' THEN 'LUCKY STRIKE'
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
                WHEN UPPER(i.Description) LIKE '%USA GOLD%' OR UPPER(i.Description) LIKE '%USA GLD%' THEN 'USA GOLD'
                WHEN UPPER(i.Description) LIKE '%SONOMA%' THEN 'SONOMA'
                WHEN UPPER(i.Description) LIKE '%B&H%' OR UPPER(i.Description) LIKE '%BENSON%' THEN 'BENSON & HEDGES'
                WHEN UPPER(i.Description) LIKE '%CAPRI%' THEN 'CAPRI'
                WHEN UPPER(i.Description) LIKE '%CARLTON%' THEN 'CARLTON'
                WHEN UPPER(i.Description) LIKE '%CROWN%' THEN 'CROWN'
                WHEN UPPER(i.Description) LIKE '%FORTUNA%' THEN 'FORTUNA'
                WHEN UPPER(i.Description) LIKE '%RAVE%' THEN 'RAVE'
                WHEN UPPER(i.Description) LIKE '%EVE%' THEN 'EVE'
                WHEN UPPER(i.Description) LIKE '%MONTEGO%' THEN 'MONTEGO'
                WHEN UPPER(i.Description) LIKE '%MERIT%' THEN 'MERIT'
                WHEN UPPER(i.Description) LIKE '%RED KAMEL%' OR UPPER(i.Description) LIKE '%KAMEL RED%' THEN 'RED KAMEL'
                WHEN UPPER(i.Description) LIKE '%VANTAGE%' THEN 'VANTAGE'
                WHEN UPPER(i.Description) LIKE '%EDGEFIELD%' THEN 'EDGEFIELD'
                WHEN UPPER(i.Description) LIKE '%TIMELESS%' THEN 'TIMELESS TIME'
                WHEN UPPER(i.Description) LIKE '%THIS%' THEN 'THIS'
                WHEN UPPER(i.Description) LIKE '%TOURING%' THEN 'TOURING'
                WHEN UPPER(i.Description) LIKE '%TRAFFIC%' THEN 'TRAFFIC'
                ELSE 'OTHER/UNIDENTIFIED'
            END as Brand
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE t.Time >= '2025-06-01'
            AND t.Time <= '2025-08-31 23:59:59'
            AND c.Name LIKE '%CIGARETTE%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
            AND i.Description NOT LIKE '%PAPER%'
            AND i.Description NOT LIKE '%TUBE%'
            AND i.Description NOT LIKE '%MACHINE%'
            AND i.Description NOT LIKE '%CASE%'
        ORDER BY t.Time, t.TransactionNumber
        """

        df = conn.execute_query(query, description="Get June-August cigarette sales")

        return df

    finally:
        conn.close()

def main():
    print("="*100)
    print("RAW CIGARETTE SALES DATA - JUNE 1 TO AUGUST 31, 2025")
    print("="*100)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get sales data
    sales_df = get_raw_sales_data()

    if sales_df is None or len(sales_df) == 0:
        print("No sales data found for the period")
        return

    # Convert numeric columns
    numeric_cols = ['QuantitySold', 'SellingPrice', 'ItemCost', 'TotalRevenue']
    for col in numeric_cols:
        if col in sales_df.columns:
            sales_df[col] = pd.to_numeric(sales_df[col], errors='coerce')

    # Calculate profit per transaction
    sales_df['GrossProfit'] = (sales_df['SellingPrice'] - sales_df['ItemCost']) * sales_df['QuantitySold']

    print(f"Total Transactions: {len(sales_df):,}")
    print(f"Date Range: {sales_df['TransactionDate'].min()} to {sales_df['TransactionDate'].max()}")
    print(f"Total Units Sold: {sales_df['QuantitySold'].sum():,.0f}")
    print(f"Total Revenue: ${sales_df['TotalRevenue'].sum():,.2f}\n")

    # Show summary by brand
    print("SUMMARY BY BRAND")
    print("="*80)

    brand_summary = sales_df.groupby('Brand').agg({
        'TransactionNumber': 'count',
        'QuantitySold': 'sum',
        'TotalRevenue': 'sum',
        'GrossProfit': 'sum'
    }).round(2)

    brand_summary.columns = ['Transactions', 'Units_Sold', 'Revenue', 'Gross_Profit']
    brand_summary = brand_summary.sort_values('Revenue', ascending=False)

    print(f"{'Brand':<20} {'Transactions':>12} {'Units Sold':>12} {'Revenue':>15} {'Gross Profit':>15}")
    print("-"*80)

    for brand, row in brand_summary.head(20).iterrows():
        print(f"{brand:<20} {row['Transactions']:12.0f} {row['Units_Sold']:12.0f} ${row['Revenue']:14,.2f} ${row['Gross_Profit']:14,.2f}")

    # Show sample of raw data
    print("\n" + "="*100)
    print("SAMPLE OF RAW TRANSACTION DATA (First 20 records)")
    print("="*100)

    sample_cols = ['TransactionDate', 'Brand', 'SKU', 'ProductDescription', 'QuantitySold', 'SellingPrice', 'ItemCost']

    print("\nFirst 10 transactions:")
    for idx, row in sales_df.head(10).iterrows():
        print(f"\nTransaction #{row['TransactionNumber']}")
        print(f"  Date: {row['TransactionDate']}")
        print(f"  Brand: {row['Brand']}")
        print(f"  Product: {row['ProductDescription'][:60]}")
        print(f"  SKU: {row['SKU']}")
        print(f"  Quantity: {row['QuantitySold']:.0f}")
        print(f"  Selling Price: ${row['SellingPrice']:.2f}")
        print(f"  Cost: ${row['ItemCost']:.2f}")
        print(f"  Revenue: ${row['TotalRevenue']:.2f}")

    # Save to Excel with all raw data
    with pd.ExcelWriter('cigarette_sales_raw_june_august.xlsx', engine='openpyxl') as writer:
        # All raw transactions
        sales_df.to_excel(writer, sheet_name='Raw_Transactions', index=False)

        # Summary by brand
        brand_summary.to_excel(writer, sheet_name='Brand_Summary')

        # Monthly summary
        sales_df['Month'] = pd.to_datetime(sales_df['TransactionDate']).dt.strftime('%Y-%m')
        monthly_summary = sales_df.groupby(['Month', 'Brand']).agg({
            'QuantitySold': 'sum',
            'TotalRevenue': 'sum',
            'GrossProfit': 'sum'
        }).round(2)
        monthly_summary.to_excel(writer, sheet_name='Monthly_by_Brand')

        # Daily summary
        sales_df['Date'] = pd.to_datetime(sales_df['TransactionDate']).dt.date
        daily_summary = sales_df.groupby('Date').agg({
            'TransactionNumber': 'count',
            'QuantitySold': 'sum',
            'TotalRevenue': 'sum'
        }).round(2)
        daily_summary.columns = ['Transactions', 'Units_Sold', 'Revenue']
        daily_summary.to_excel(writer, sheet_name='Daily_Summary')

    print(f"\n✅ Complete raw data saved to: cigarette_sales_raw_june_august.xlsx")
    print(f"   - Raw_Transactions sheet: All {len(sales_df):,} transactions")
    print(f"   - Brand_Summary sheet: Summary by brand")
    print(f"   - Monthly_by_Brand sheet: Monthly breakdown by brand")
    print(f"   - Daily_Summary sheet: Daily sales totals")

    # Print date range confirmation
    print(f"\n📅 Date Range Confirmation:")
    print(f"   Start: June 1, 2025")
    print(f"   End: August 31, 2025")
    print(f"   Actual data range: {sales_df['TransactionDate'].min()} to {sales_df['TransactionDate'].max()}")

if __name__ == "__main__":
    main()