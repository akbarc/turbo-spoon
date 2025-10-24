#!/usr/bin/env python3
"""
Complete Petrey Purchase Analysis
Shows all purchases by SKU, price point, and brand
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

def get_all_petrey_purchases():
    """Get complete purchase history from Petrey"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Get all Petrey purchases with item details
        query = """
        WITH BrandedItems AS (
            SELECT
                poe.PurchaseOrderID,
                po.PONumber,
                po.DateCreated as PurchaseDate,
                poe.ItemID,
                i.ItemLookupCode as SKU,
                i.Description,
                poe.QuantityOrdered,
                poe.QuantityReceived,
                poe.Price as UnitCost,
                (poe.Price * poe.QuantityOrdered) as ExtendedCost,
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
                    WHEN UPPER(i.Description) LIKE '%305%' THEN '305S'
                    WHEN UPPER(i.Description) LIKE '%B&H%' OR UPPER(i.Description) LIKE '%BENSON%' THEN 'BENSON & HEDGES'
                    WHEN UPPER(i.Description) LIKE '%CAPRI%' THEN 'CAPRI'
                    WHEN UPPER(i.Description) LIKE '%CARLTON%' THEN 'CARLTON'
                    WHEN UPPER(i.Description) LIKE '%CROWN%' THEN 'CROWN'
                    WHEN UPPER(i.Description) LIKE '%FORTUNA%' THEN 'FORTUNA'
                    WHEN UPPER(i.Description) LIKE '%RAVE%' THEN 'RAVE'
                    WHEN UPPER(i.Description) LIKE '%MONTEGO%' THEN 'MONTEGO'
                    WHEN UPPER(i.Description) LIKE '%MERIT%' THEN 'MERIT'
                    WHEN UPPER(i.Description) LIKE '%VANTAGE%' THEN 'VANTAGE'
                    WHEN UPPER(i.Description) LIKE '%EDGEFIELD%' THEN 'EDGEFIELD'
                    WHEN UPPER(i.Description) LIKE '%USA GOLD%' THEN 'USA GOLD'
                    WHEN UPPER(i.Description) LIKE '%SONOMA%' THEN 'SONOMA'
                    WHEN UPPER(i.Description) LIKE '%EVE%' THEN 'EVE'
                    WHEN UPPER(i.Description) LIKE '%LD%' OR UPPER(i.Description) LIKE '%L.D%' THEN 'LD'
                    WHEN UPPER(i.Description) LIKE '%WAVE%' THEN 'WAVE'
                    WHEN UPPER(i.Description) LIKE '%TIMELESS%' THEN 'TIMELESS TIME'
                    ELSE 'OTHER/UNIDENTIFIED'
                END as Brand
            FROM PurchaseOrderEntry poe
            INNER JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
            INNER JOIN Item i ON poe.ItemID = i.ID
            WHERE po.SupplierID = 1330  -- Petrey ID
        )
        SELECT * FROM BrandedItems
        ORDER BY Brand, UnitCost DESC, PurchaseDate DESC
        """

        df = conn.execute_query(query, description="Get all Petrey purchases")

        return df

    finally:
        conn.close()

def main():
    print("="*120)
    print("COMPLETE PETREY WHOLESALE PURCHASE ANALYSIS")
    print("="*120)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get purchase data
    df = get_all_petrey_purchases()

    if df is None or len(df) == 0:
        print("No Petrey purchase data found")
        return

    # Convert numeric columns
    numeric_cols = ['QuantityOrdered', 'QuantityReceived', 'UnitCost', 'ExtendedCost']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Overall summary
    total_cost = df['ExtendedCost'].sum()
    total_units = df['QuantityOrdered'].sum()
    unique_skus = df['SKU'].nunique()
    unique_brands = df['Brand'].nunique()

    print("OVERALL SUMMARY")
    print("-"*120)
    print(f"Total Purchased from Petrey: ${total_cost:,.2f}")
    print(f"Total Units Ordered: {total_units:,.0f}")
    print(f"Unique SKUs: {unique_skus}")
    print(f"Unique Brands: {unique_brands}")
    print(f"Date Range: {df['PurchaseDate'].min()} to {df['PurchaseDate'].max()}\n")

    # Summary by Brand and Price Point
    print("="*120)
    print("PURCHASES BY BRAND AND PRICE POINT")
    print("="*120)

    brand_price_summary = df.groupby(['Brand', 'UnitCost']).agg({
        'QuantityOrdered': 'sum',
        'ExtendedCost': 'sum',
        'SKU': 'nunique',
        'Description': 'first'
    }).round(2)

    for brand in sorted(df['Brand'].unique()):
        brand_data = brand_price_summary.loc[brand]
        brand_total = df[df['Brand'] == brand]['ExtendedCost'].sum()
        brand_units = df[df['Brand'] == brand]['QuantityOrdered'].sum()

        print(f"\n{brand}")
        print("-"*80)
        print(f"Brand Total: ${brand_total:,.2f} | Total Units: {brand_units:,.0f}")
        print(f"{'Unit Cost':>12} {'Units':>10} {'Total Cost':>15} {'SKUs':>6}  Sample Product")
        print("-"*80)

        if isinstance(brand_data, pd.Series):
            # Single price point
            print(f"${brand_data.name:11.2f} {brand_data['QuantityOrdered']:10.0f} ${brand_data['ExtendedCost']:14,.2f} {brand_data['SKU']:6.0f}  {brand_data['Description'][:40]}")
        else:
            # Multiple price points
            for cost, row in brand_data.iterrows():
                print(f"${cost:11.2f} {row['QuantityOrdered']:10.0f} ${row['ExtendedCost']:14,.2f} {row['SKU']:6.0f}  {row['Description'][:40]}")

    # Detailed SKU analysis
    print("\n" + "="*120)
    print("DETAILED ANALYSIS BY SKU AND PRICE")
    print("="*120)

    sku_price_summary = df.groupby(['SKU', 'Description', 'UnitCost', 'Brand']).agg({
        'QuantityOrdered': 'sum',
        'ExtendedCost': 'sum',
        'PurchaseDate': ['min', 'max', 'count']
    }).round(2)

    sku_price_summary.columns = ['Units', 'Total_Cost', 'First_Purchase', 'Last_Purchase', 'PO_Count']
    sku_price_summary = sku_price_summary.sort_values('Total_Cost', ascending=False)

    print("\nTOP 50 SKUs BY TOTAL PURCHASE VALUE")
    print("-"*120)
    print(f"{'SKU':15} {'Description':40} {'Brand':15} {'Cost':>8} {'Units':>8} {'Total':>12} {'POs':>5}")
    print("-"*120)

    for (sku, desc, cost, brand), row in sku_price_summary.head(50).iterrows():
        desc_short = desc[:38] if len(desc) > 38 else desc
        brand_short = brand[:14] if len(brand) > 14 else brand
        print(f"{sku:15} {desc_short:40} {brand_short:15} ${cost:7.2f} {row['Units']:8.0f} ${row['Total_Cost']:11,.2f} {row['PO_Count']:5.0f}")

    # Create detailed Excel report
    with pd.ExcelWriter('petrey_complete_purchase_analysis.xlsx', engine='openpyxl') as writer:
        # Sheet 1: All raw purchase data
        df.to_excel(writer, sheet_name='All_Purchases', index=False)

        # Sheet 2: Summary by Brand and Price
        brand_price_full = df.groupby(['Brand', 'UnitCost']).agg({
            'QuantityOrdered': 'sum',
            'QuantityReceived': 'sum',
            'ExtendedCost': 'sum',
            'SKU': 'nunique',
            'PurchaseDate': ['min', 'max', 'count']
        }).round(2)
        brand_price_full.to_excel(writer, sheet_name='By_Brand_Price')

        # Sheet 3: Summary by SKU and Price
        sku_price_summary.to_excel(writer, sheet_name='By_SKU_Price')

        # Sheet 4: Brand totals
        brand_totals = df.groupby('Brand').agg({
            'QuantityOrdered': 'sum',
            'ExtendedCost': 'sum',
            'SKU': 'nunique',
            'UnitCost': ['mean', 'min', 'max']
        }).round(2)
        brand_totals.columns = ['Total_Units', 'Total_Cost', 'Unique_SKUs', 'Avg_Cost', 'Min_Cost', 'Max_Cost']
        brand_totals = brand_totals.sort_values('Total_Cost', ascending=False)
        brand_totals.to_excel(writer, sheet_name='Brand_Totals')

        # Sheet 5: Purchase Orders summary
        po_summary = df.groupby(['PONumber', 'PurchaseDate']).agg({
            'ExtendedCost': 'sum',
            'QuantityOrdered': 'sum',
            'SKU': 'nunique'
        }).round(2)
        po_summary.columns = ['PO_Total', 'Total_Units', 'Unique_SKUs']
        po_summary = po_summary.sort_values('PurchaseDate', ascending=False)
        po_summary.to_excel(writer, sheet_name='PO_Summary')

    print(f"\n✅ Complete analysis saved to: petrey_complete_purchase_analysis.xlsx")

    # Print top brands summary
    print("\n" + "="*120)
    print("TOP 10 BRANDS BY PURCHASE VALUE")
    print("="*120)

    top_brands = df.groupby('Brand').agg({
        'ExtendedCost': 'sum',
        'QuantityOrdered': 'sum',
        'UnitCost': 'mean',
        'SKU': 'nunique'
    }).round(2)
    top_brands.columns = ['Total_Cost', 'Total_Units', 'Avg_Unit_Cost', 'Unique_SKUs']
    top_brands = top_brands.sort_values('Total_Cost', ascending=False).head(10)

    print(f"{'Brand':20} {'Total Cost':>15} {'Units':>10} {'Avg Cost':>10} {'SKUs':>8}")
    print("-"*65)

    for brand, row in top_brands.iterrows():
        print(f"{brand[:19]:20} ${row['Total_Cost']:14,.2f} {row['Total_Units']:10.0f} ${row['Avg_Unit_Cost']:9.2f} {row['Unique_SKUs']:8.0f}")

    print(f"\n📊 Total Investment with Petrey Wholesale: ${total_cost:,.2f}")

if __name__ == "__main__":
    main()