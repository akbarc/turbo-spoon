#!/usr/bin/env python3
"""
Current Cigarette Pricing Report
Shows most recent cost/price by brand with supplier and sales data
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime, timedelta

def get_current_pricing_and_sales():
    """Get current pricing with supplier and recent sales data"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Calculate date range for sales data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        # Query to get current item pricing with supplier and recent sales
        query = f"""
        WITH BrandedItems AS (
            SELECT
                i.ID,
                i.ItemLookupCode as SKU,
                i.Description,
                i.Price as CurrentPrice,
                i.Cost as CurrentCost,
                i.LastCost,
                i.Quantity as OnHand,
                s.SupplierName,
                s.Code as SupplierCode,
                CASE
                    WHEN UPPER(i.Description) LIKE '%CROWN%' THEN 'CROWN'
                    WHEN UPPER(i.Description) LIKE '%FORTUNA%' THEN 'FORTUNA'
                    WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                    WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                    WHEN UPPER(i.Description) LIKE '%RAVE%' THEN 'RAVE'
                    WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                    WHEN UPPER(i.Description) LIKE '%SONOMA%' THEN 'SONOMA'
                    WHEN UPPER(i.Description) LIKE '%USA GOLD%' OR UPPER(i.Description) LIKE '%USA GLD%' THEN 'USA GOLD'
                    WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                    WHEN UPPER(i.Description) LIKE '%L.D%' OR UPPER(i.Description) LIKE '% LD %' THEN 'LD'
                    WHEN UPPER(i.Description) LIKE '%EAGLE 20%' THEN 'EAGLE 20S'
                    WHEN UPPER(i.Description) LIKE '%EVE%' AND UPPER(i.Description) LIKE '%120%' THEN 'EVE'
                    WHEN UPPER(i.Description) LIKE '%MONTEGO%' THEN 'MONTEGO'
                    WHEN UPPER(i.Description) LIKE '%PYRAMID%' THEN 'PYRAMID'
                    WHEN UPPER(i.Description) LIKE '%BENSON%' OR UPPER(i.Description) LIKE '%B&H%' THEN 'BENSON & HEDGES'
                    WHEN UPPER(i.Description) LIKE '%BASIC%' THEN 'BASIC'
                    WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                    WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                    WHEN UPPER(i.Description) LIKE '%MERIT%' THEN 'MERIT'
                    WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                    WHEN UPPER(i.Description) LIKE '%VIRGINIA SLIM%' OR UPPER(i.Description) LIKE '%VIRG SL%' THEN 'VIRGINIA SLIMS'
                    WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                    WHEN UPPER(i.Description) LIKE '%CAPRI%' THEN 'CAPRI'
                    WHEN UPPER(i.Description) LIKE '%CARLTON%' THEN 'CARLTON'
                    WHEN UPPER(i.Description) LIKE '%DORAL%' THEN 'DORAL'
                    WHEN UPPER(i.Description) LIKE '%LUCKY STRIKE%' OR UPPER(i.Description) LIKE '%LUCKY STR%' THEN 'LUCKY STRIKE'
                    WHEN UPPER(i.Description) LIKE '%MISTY%' THEN 'MISTY'
                    WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                    WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                    WHEN UPPER(i.Description) LIKE '%RED KAMEL%' OR UPPER(i.Description) LIKE '%KAMEL RED%' THEN 'RED KAMEL'
                    WHEN UPPER(i.Description) LIKE '%VANTAGE%' THEN 'VANTAGE'
                    WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    WHEN UPPER(i.Description) LIKE '%SENECA%' THEN 'SENECA'
                    WHEN UPPER(i.Description) LIKE '%305%' THEN '305S'
                    WHEN UPPER(i.Description) LIKE '%EDGEFIELD%' THEN 'EDGEFIELD'
                    ELSE NULL
                END as Brand,
                i.LastReceived
            FROM Item i
            LEFT JOIN Supplier s ON i.SupplierID = s.ID
            LEFT JOIN Category c ON i.CategoryID = c.ID
            WHERE c.Name LIKE '%CIGARETTE%'
                AND i.Inactive = 0
                AND i.Price > 0
                AND i.Cost > 0
        ),
        RecentSales AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as UnitsSold3Months,
                AVG(te.Price) as AvgSellingPrice,
                MAX(t.Time) as LastSoldDate
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d')}'
                AND t.Time <= '{end_date.strftime('%Y-%m-%d')}'
            GROUP BY te.ItemID
        )
        SELECT
            b.Brand,
            b.SKU,
            b.Description,
            b.CurrentPrice as SalesPrice,
            b.CurrentCost as Cost,
            b.SupplierName as Supplier,
            b.OnHand as Inventory,
            COALESCE(r.UnitsSold3Months, 0) as UnitsSold,
            b.LastReceived,
            r.LastSoldDate,
            ROW_NUMBER() OVER (PARTITION BY b.Brand ORDER BY b.LastReceived DESC, r.UnitsSold3Months DESC) as rn
        FROM BrandedItems b
        LEFT JOIN RecentSales r ON b.ID = r.ItemID
        WHERE b.Brand IS NOT NULL
        ORDER BY b.Brand, rn
        """

        df = conn.execute_query(query, description="Get current pricing with suppliers")

        return df

    finally:
        conn.close()

def main():
    print("="*100)
    print("CURRENT CIGARETTE PRICING BY BRAND")
    print("="*100)
    print(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get data
    df = get_current_pricing_and_sales()

    if df is None or len(df) == 0:
        print("No data found")
        return

    # Convert numeric columns
    numeric_cols = ['SalesPrice', 'Cost', 'UnitsSold', 'Inventory']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Calculate margin
    df['Margin%'] = ((df['SalesPrice'] - df['Cost']) / df['SalesPrice'] * 100).round(1)
    df['GrossProfit'] = (df['SalesPrice'] - df['Cost']) * df['UnitsSold']

    # Define how many tiers to show for each brand
    brand_tiers = {
        'CROWN': 1, 'FORTUNA': 1, 'KOOL': 1, 'MAVERICK': 1, 'RAVE': 1,
        'SALEM': 1, 'SONOMA': 1, 'USA GOLD': 1, 'WINSTON': 1, 'LD': 1,
        'EAGLE 20S': 1, 'EVE': 1, 'MONTEGO': 1, 'PYRAMID': 1,
        'BENSON & HEDGES': 1, 'BASIC': 1, 'L&M': 1, 'MARLBORO': 3,
        'MERIT': 1, 'PARLIAMENT': 1, 'VIRGINIA SLIMS': 1, 'CAMEL': 3,
        'CAPRI': 1, 'CARLTON': 1, 'DORAL': 1, 'LUCKY STRIKE': 1,
        'MISTY': 1, 'NEWPORT': 3, 'PALL MALL': 1, 'RED KAMEL': 1,
        'VANTAGE': 1, 'AMERICAN SPIRIT': 2, 'SENECA': 1, '305S': 1,
        'EDGEFIELD': 1
    }

    # Print summary table
    print("BRAND PRICING SUMMARY")
    print("="*100)
    print(f"{'Brand':<20} {'Supplier':<25} {'Sales Price':>12} {'Cost':>10} {'Margin%':>8} {'Units Sold':>12}")
    print("-"*100)

    summary_data = []

    for brand, tier_count in brand_tiers.items():
        brand_data = df[df['Brand'] == brand].copy()

        if len(brand_data) == 0:
            continue

        # Get the most recent/highest volume items based on tier count
        brand_data = brand_data.sort_values(['rn']).head(tier_count)

        for idx, row in brand_data.iterrows():
            supplier = row['Supplier'] if row['Supplier'] else 'Unknown'
            supplier = supplier[:23] if len(supplier) > 23 else supplier

            print(f"{brand:<20} {supplier:<25} ${row['SalesPrice']:11.2f} ${row['Cost']:9.2f} {row['Margin%']:7.1f}% {row['UnitsSold']:12.0f}")

            summary_data.append({
                'Brand': brand,
                'SKU': row['SKU'],
                'Description': row['Description'],
                'Supplier': row['Supplier'],
                'SalesPrice': row['SalesPrice'],
                'Cost': row['Cost'],
                'Margin%': row['Margin%'],
                'UnitsSold': row['UnitsSold'],
                'Inventory': row['Inventory'],
                'LastReceived': row['LastReceived'],
                'LastSold': row['LastSoldDate']
            })

    # Group by brand showing details
    print("\n" + "="*100)
    print("DETAILED BREAKDOWN BY BRAND")
    print("="*100)

    for brand, tier_count in brand_tiers.items():
        brand_data = df[df['Brand'] == brand].copy()

        if len(brand_data) == 0:
            continue

        print(f"\n{brand}")
        print("-"*60)

        # Get top items by recency and volume
        brand_data = brand_data.sort_values(['rn']).head(tier_count)

        for idx, row in brand_data.iterrows():
            print(f"  Product: {row['Description'][:50]}")
            print(f"  SKU: {row['SKU']}")
            print(f"  Supplier: {row['Supplier'] if row['Supplier'] else 'Unknown'}")
            print(f"  Sales Price: ${row['SalesPrice']:.2f}")
            print(f"  Cost: ${row['Cost']:.2f}")
            print(f"  Margin: {row['Margin%']:.1f}%")
            print(f"  3-Month Sales: {row['UnitsSold']:.0f} units")
            print(f"  Current Inventory: {row['Inventory']:.0f} units")
            if row['LastReceived']:
                print(f"  Last Received: {row['LastReceived']}")
            print()

    # Save to Excel
    if summary_data:
        summary_df = pd.DataFrame(summary_data)

        with pd.ExcelWriter('cigarette_current_pricing_report.xlsx', engine='openpyxl') as writer:
            # Main summary
            summary_df.to_excel(writer, sheet_name='Current_Pricing', index=False)

            # All data
            df[df['Brand'].notna()].to_excel(writer, sheet_name='All_Products', index=False)

            # Supplier summary
            supplier_summary = summary_df.groupby('Supplier').agg({
                'Brand': 'count',
                'SalesPrice': 'mean',
                'Cost': 'mean',
                'UnitsSold': 'sum'
            }).round(2)
            supplier_summary.columns = ['Brands', 'Avg_Price', 'Avg_Cost', 'Total_Units']
            supplier_summary.to_excel(writer, sheet_name='By_Supplier')

        print(f"\n✅ Report saved to: cigarette_current_pricing_report.xlsx")

    # Print top suppliers
    print("\n" + "="*100)
    print("TOP SUPPLIERS")
    print("="*100)

    if summary_data:
        supplier_df = pd.DataFrame(summary_data)
        top_suppliers = supplier_df.groupby('Supplier')['UnitsSold'].sum().sort_values(ascending=False).head(10)

        for supplier, units in top_suppliers.items():
            if supplier:
                brands = supplier_df[supplier_df['Supplier'] == supplier]['Brand'].unique()
                print(f"{supplier[:30]:<30} {units:8.0f} units | Brands: {', '.join(brands[:5])}")

if __name__ == "__main__":
    main()