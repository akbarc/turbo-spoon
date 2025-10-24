#!/usr/bin/env python3
"""
Cigarette Pricing Analysis Script
Extracts pricing, volume, and sales data for cigarette products
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'  # Force office server

import database_pymssql as db
import pandas as pd
from datetime import datetime, timedelta
import json

def get_cigarette_products():
    """Get all cigarette products with current pricing"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Query for all cigarette products with pricing tiers
        query = """
        SELECT
            i.ID,
            i.ItemLookupCode as SKU,
            i.Description,
            i.Price as CurrentPrice,
            i.PriceA as TierA_Price,
            i.PriceB as TierB_Price,
            i.PriceC as TierC_Price,
            i.Cost,
            i.LastCost,
            i.Quantity as OnHand,
            i.LastSold,
            i.LastReceived,
            d.Name as Department,
            c.Name as Category,
            s.SupplierName as Supplier,
            CASE
                WHEN i.Description LIKE '%MARL%' THEN 'MARLBORO'
                WHEN i.Description LIKE '%CAMEL%' THEN 'CAMEL'
                WHEN i.Description LIKE '%NEWPORT%' THEN 'NEWPORT'
                WHEN i.Description LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN i.Description LIKE '%WINSTON%' THEN 'WINSTON'
                WHEN i.Description LIKE '%KOOL%' THEN 'KOOL'
                WHEN i.Description LIKE '%SALEM%' THEN 'SALEM'
                WHEN i.Description LIKE '%VIRGINIA%' THEN 'VIRGINIA SLIMS'
                WHEN i.Description LIKE '%PALL MALL%' THEN 'PALL MALL'
                WHEN i.Description LIKE '%LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                WHEN i.Description LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                WHEN i.Description LIKE '%MAVERICK%' THEN 'MAVERICK'
                WHEN i.Description LIKE '%L&M%' THEN 'L&M'
                WHEN i.Description LIKE '%KENT%' THEN 'KENT'
                WHEN i.Description LIKE '%EAGLE%' THEN 'EAGLE'
                WHEN i.Description LIKE '%PYRAMID%' THEN 'PYRAMID'
                WHEN i.Description LIKE '%SENECA%' THEN 'SENECA'
                WHEN i.Description LIKE '%MISTY%' THEN 'MISTY'
                WHEN i.Description LIKE '%DORAL%' THEN 'DORAL'
                WHEN i.Description LIKE '%BASIC%' THEN 'BASIC'
                ELSE 'OTHER'
            END as Brand
        FROM Item i
        LEFT JOIN Department d ON i.DepartmentID = d.ID
        LEFT JOIN Category c ON i.CategoryID = c.ID
        LEFT JOIN Supplier s ON i.SupplierID = s.ID
        WHERE
            (i.Description LIKE '%CIGARETTE%'
            OR i.Description LIKE '%CIG %'
            OR i.Description LIKE '% CIG%'
            OR i.Description LIKE '%MARL%'
            OR i.Description LIKE '%CAMEL%'
            OR i.Description LIKE '%NEWPORT%'
            OR i.Description LIKE '%AMERICAN SPIRIT%'
            OR i.Description LIKE '%WINSTON%'
            OR i.Description LIKE '%KOOL%'
            OR i.Description LIKE '%SALEM%'
            OR i.Description LIKE '%VIRGINIA%'
            OR i.Description LIKE '%PALL MALL%'
            OR i.Description LIKE '%LUCKY STRIKE%'
            OR i.Description LIKE '%PARLIAMENT%'
            OR i.Description LIKE '%MAVERICK%'
            OR i.Description LIKE '%L&M%'
            OR i.Description LIKE '%KENT%'
            OR i.Description LIKE '%EAGLE%'
            OR i.Description LIKE '%PYRAMID%'
            OR i.Description LIKE '%SENECA%'
            OR i.Description LIKE '%MISTY%'
            OR i.Description LIKE '%DORAL%'
            OR i.Description LIKE '%BASIC%')
            AND i.Inactive = 0  -- Only active items
        ORDER BY Brand, i.Description
        """

        products_df = conn.execute_query(query, description="Get all cigarette products")
        return products_df

    finally:
        conn.close()


def get_sales_data(start_date, end_date):
    """Get sales transaction data for cigarettes in date range"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Check if TransactionEntry table exists
        check_tables = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME IN ('TransactionEntry', 'Transaction', 'TransactionDetail', 'Invoice', 'InvoiceDetail')
        """

        tables_df = conn.execute_query(check_tables, description="Check transaction tables")
        print(f"Available transaction tables: {tables_df['TABLE_NAME'].tolist()}")

        # Try to get sales volume data - adjust based on available tables
        if 'TransactionEntry' in tables_df['TABLE_NAME'].tolist():
            sales_query = f"""
            SELECT
                te.ItemID,
                i.ItemLookupCode as SKU,
                i.Description,
                SUM(te.Quantity) as TotalQuantitySold,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                COUNT(DISTINCT te.TransactionNumber) as TransactionCount,
                AVG(te.Price) as AvgSellingPrice,
                MIN(te.Price) as MinPrice,
                MAX(te.Price) as MaxPrice
            FROM TransactionEntry te
            INNER JOIN Item i ON te.ItemID = i.ID
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{start_date}'
                AND t.Time <= '{end_date}'
                AND (i.Description LIKE '%CIGARETTE%'
                    OR i.Description LIKE '%CIG %'
                    OR i.Description LIKE '% CIG%'
                    OR i.Description LIKE '%MARL%'
                    OR i.Description LIKE '%CAMEL%'
                    OR i.Description LIKE '%NEWPORT%'
                    OR i.Description LIKE '%AMERICAN SPIRIT%')
            GROUP BY te.ItemID, i.ItemLookupCode, i.Description
            ORDER BY TotalQuantitySold DESC
            """
        else:
            # Fallback query if TransactionEntry doesn't exist
            sales_query = f"""
            SELECT
                'No transaction data available' as Message
            """

        sales_df = conn.execute_query(sales_query, description="Get sales volume data")
        return sales_df

    finally:
        conn.close()


def main():
    """Main execution function"""

    print("=" * 80)
    print("CIGARETTE PRICING AND VOLUME ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Get all cigarette products with current pricing
    print("Fetching cigarette products and current pricing...")
    products_df = get_cigarette_products()

    if products_df is not None and len(products_df) > 0:
        print(f"Found {len(products_df)} cigarette products")

        # Save to Excel for detailed analysis
        excel_file = "cigarette_pricing_report.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:

            # Sheet 1: All Products with Pricing
            products_df.to_excel(writer, sheet_name='All_Products', index=False)

            # Sheet 2: Summary by Brand with Tier Pricing
            brand_summary = products_df.groupby('Brand').agg({
                'SKU': 'count',
                'CurrentPrice': ['mean', 'min', 'max'],
                'TierA_Price': 'mean',
                'TierB_Price': 'mean',
                'TierC_Price': 'mean',
                'Cost': 'mean',
                'OnHand': 'sum'
            }).round(2)
            brand_summary.columns = ['Product_Count', 'Avg_Price', 'Min_Price', 'Max_Price',
                                     'Avg_TierA', 'Avg_TierB', 'Avg_TierC', 'Avg_Cost', 'Total_OnHand']
            brand_summary.to_excel(writer, sheet_name='Brand_Summary')

            # Sheet 3: Products with Tier Pricing Only
            tier_products = products_df[
                (products_df['TierA_Price'].notna() & (products_df['TierA_Price'] > 0)) |
                (products_df['TierB_Price'].notna() & (products_df['TierB_Price'] > 0)) |
                (products_df['TierC_Price'].notna() & (products_df['TierC_Price'] > 0))
            ][['SKU', 'Description', 'Brand', 'CurrentPrice', 'TierA_Price', 'TierB_Price', 'TierC_Price']]

            if len(tier_products) > 0:
                tier_products.to_excel(writer, sheet_name='Tier_Pricing', index=False)

            # Try to get 3-month sales data
            print("\nFetching 3-month sales volume data...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)

            sales_df = get_sales_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            if sales_df is not None and len(sales_df) > 0 and 'SKU' in sales_df.columns:
                sales_df.to_excel(writer, sheet_name='Sales_Volume_3Months', index=False)
                print(f"Found sales data for {len(sales_df)} products")

        print(f"\n✅ Report saved to: {excel_file}")

        # Print summary to console
        print("\n" + "=" * 80)
        print("SUMMARY BY BRAND")
        print("=" * 80)
        print(brand_summary.to_string())

        # Print products with tier pricing
        print("\n" + "=" * 80)
        print("PRODUCTS WITH TIER PRICING (A/B/C)")
        print("=" * 80)
        if len(tier_products) > 0:
            for _, row in tier_products.head(20).iterrows():
                print(f"\n{row['Brand']} - {row['Description'][:50]}")
                print(f"  SKU: {row['SKU']}")
                print(f"  Current: ${row['CurrentPrice']:.2f}")
                if pd.notna(row['TierA_Price']) and row['TierA_Price'] > 0:
                    print(f"  Tier A:  ${row['TierA_Price']:.2f}")
                if pd.notna(row['TierB_Price']) and row['TierB_Price'] > 0:
                    print(f"  Tier B:  ${row['TierB_Price']:.2f}")
                if pd.notna(row['TierC_Price']) and row['TierC_Price'] > 0:
                    print(f"  Tier C:  ${row['TierC_Price']:.2f}")
        else:
            print("No products found with tier pricing")

        # Save summary as JSON for easy access
        summary_data = {
            'analysis_date': datetime.now().isoformat(),
            'total_products': len(products_df),
            'brands': brand_summary.to_dict(),
            'products_with_tier_pricing': len(tier_products) if len(tier_products) > 0 else 0
        }

        with open('cigarette_pricing_summary.json', 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)

        print(f"\n✅ Summary saved to: cigarette_pricing_summary.json")

    else:
        print("No cigarette products found in database")


if __name__ == "__main__":
    main()