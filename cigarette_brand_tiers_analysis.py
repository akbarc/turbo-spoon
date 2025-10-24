#!/usr/bin/env python3
"""
Cigarette Brand Price Tiers Analysis
Groups cigarette products by brand and identifies natural price tiers
Shows current price and cost for each tier
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime
import numpy as np

def get_cigarette_products():
    """Get only cigarette products (not accessories)"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        query = """
        SELECT
            i.ID,
            i.ItemLookupCode as SKU,
            i.Description,
            i.Price as CurrentPrice,
            i.Cost,
            i.LastCost,
            i.Quantity as OnHand,
            c.Name as Category,
            CASE
                WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                WHEN UPPER(i.Description) LIKE '%VIRGINIA SLIM%' THEN 'VIRGINIA SLIMS'
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
                ELSE NULL
            END as Brand,
            CASE
                WHEN UPPER(i.Description) LIKE '%100%' OR UPPER(i.Description) LIKE '%100S%' THEN '100s'
                WHEN UPPER(i.Description) LIKE '%KING%' OR UPPER(i.Description) LIKE '% KG %' THEN 'King'
                WHEN UPPER(i.Description) LIKE '%SHORT%' THEN 'Shorts'
                ELSE 'Regular'
            END as Size,
            CASE
                WHEN UPPER(i.Description) LIKE '%MENTHOL%' OR UPPER(i.Description) LIKE '% MENTH%' THEN 'Menthol'
                WHEN UPPER(i.Description) LIKE '%LIGHT%' OR UPPER(i.Description) LIKE '% LT %' THEN 'Lights'
                WHEN UPPER(i.Description) LIKE '%ULTRA%' THEN 'Ultra Lights'
                ELSE 'Regular'
            END as Style
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE
            c.Name LIKE '%CIGARETTE%'
            AND i.Inactive = 0
            AND i.Price > 0
            AND i.Description NOT LIKE '%CIGAR%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
            AND i.Description NOT LIKE '%PAPER%'
            AND i.Description NOT LIKE '%TUBE%'
            AND i.Description NOT LIKE '%MACHINE%'
            AND i.Description NOT LIKE '%CASE%'
        ORDER BY Brand, CurrentPrice DESC
        """

        df = conn.execute_query(query, description="Get cigarette products")
        return df

    finally:
        conn.close()

def identify_price_tiers(brand_df):
    """Identify natural price tiers within a brand using clustering"""

    prices = brand_df['CurrentPrice'].astype(float).values

    # Remove outliers using IQR method
    Q1 = np.percentile(prices, 25)
    Q3 = np.percentile(prices, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Filter out outliers
    filtered_prices = prices[(prices >= lower_bound) & (prices <= upper_bound)]

    if len(filtered_prices) == 0:
        filtered_prices = prices

    # Identify natural breaks in pricing
    unique_prices = sorted(set(filtered_prices))

    # Convert costs to float to avoid decimal issues
    brand_df['Cost'] = brand_df['Cost'].astype(float)

    if len(unique_prices) <= 3:
        # If 3 or fewer unique prices, each is its own tier
        tiers = []
        tier_names = ['Value/Low Tier', 'Mid Tier', 'Premium/High Tier']
        for idx, price in enumerate(unique_prices):
            mask = brand_df['CurrentPrice'].astype(float) == price
            if mask.any():
                tier_data = brand_df[mask]
                tiers.append({
                    'tier_name': tier_names[min(idx, len(tier_names)-1)],
                    'avg_price': float(price),
                    'min_price': float(price),
                    'max_price': float(price),
                    'avg_cost': float(tier_data['Cost'].mean()),
                    'min_cost': float(tier_data['Cost'].min()),
                    'max_cost': float(tier_data['Cost'].max()),
                    'markup_pct': ((float(price) - float(tier_data['Cost'].mean())) / float(tier_data['Cost'].mean()) * 100) if float(tier_data['Cost'].mean()) > 0 else 0,
                    'product_count': mask.sum(),
                    'total_inventory': tier_data['OnHand'].sum(),
                    'sample_products': tier_data['Description'].tolist()[:3]
                })
    else:
        # Group into max 3 tiers based on price gaps
        price_gaps = np.diff(unique_prices)

        # Find the 2 largest gaps to create 3 tiers
        if len(price_gaps) >= 2:
            gap_indices = np.argsort(price_gaps)[-2:]
            tier_boundaries = sorted([0] + [i+1 for i in sorted(gap_indices)] + [len(unique_prices)])
        else:
            tier_boundaries = [0, len(unique_prices)]

        tiers = []
        tier_names = ['Value/Low Tier', 'Mid Tier', 'Premium/High Tier']

        for i in range(len(tier_boundaries)-1):
            start_idx = tier_boundaries[i]
            end_idx = tier_boundaries[i+1]
            tier_prices = unique_prices[start_idx:end_idx]

            mask = brand_df['CurrentPrice'].isin(tier_prices)
            if mask.any():
                tier_data = brand_df[mask]
                tier_name = tier_names[min(i, len(tier_names)-1)]

                tiers.append({
                    'tier_name': tier_name,
                    'avg_price': float(tier_data['CurrentPrice'].mean()),
                    'min_price': float(tier_data['CurrentPrice'].min()),
                    'max_price': float(tier_data['CurrentPrice'].max()),
                    'avg_cost': float(tier_data['Cost'].mean()),
                    'min_cost': float(tier_data['Cost'].min()),
                    'max_cost': float(tier_data['Cost'].max()),
                    'markup_pct': ((float(tier_data['CurrentPrice'].mean()) - float(tier_data['Cost'].mean())) / float(tier_data['Cost'].mean()) * 100) if float(tier_data['Cost'].mean()) > 0 else 0,
                    'product_count': len(tier_data),
                    'total_inventory': tier_data['OnHand'].sum(),
                    'sample_products': tier_data.nsmallest(3, 'CurrentPrice')['Description'].tolist()
                })

    return tiers

def main():
    print("="*80)
    print("CIGARETTE BRAND PRICE TIERS ANALYSIS")
    print("="*80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get cigarette products
    print("Fetching cigarette products...")
    products_df = get_cigarette_products()

    if products_df is None or len(products_df) == 0:
        print("No cigarette products found")
        return

    # Filter to only branded cigarettes
    branded_df = products_df[products_df['Brand'].notna()]

    print(f"Found {len(branded_df)} branded cigarette products\n")

    # Analyze each brand
    brands = branded_df['Brand'].unique()

    all_tiers_data = []

    for brand in sorted(brands):
        brand_df = branded_df[branded_df['Brand'] == brand]

        if len(brand_df) < 2:
            continue

        print(f"\n{'='*60}")
        print(f"BRAND: {brand}")
        print(f"Total Products: {len(brand_df)}")
        print(f"Price Range: ${brand_df['CurrentPrice'].min():.2f} - ${brand_df['CurrentPrice'].max():.2f}")
        print("-"*60)

        # Identify price tiers
        tiers = identify_price_tiers(brand_df)

        for i, tier in enumerate(tiers, 1):
            if 'tier_name' in tier:
                print(f"\n{tier['tier_name']}:")
                print(f"  Products: {tier['product_count']}")
                print(f"  Price: ${tier['avg_price']:.2f} (${tier['min_price']:.2f} - ${tier['max_price']:.2f})")
                print(f"  Cost:  ${tier['avg_cost']:.2f} (${tier['min_cost']:.2f} - ${tier['max_cost']:.2f})")
                print(f"  Markup: {tier['markup_pct']:.1f}%")
                print(f"  Inventory: {tier['total_inventory']:.0f} units")

                # Store for Excel export
                tier['brand'] = brand
                all_tiers_data.append(tier)

                if tier['sample_products']:
                    print(f"  Examples:")
                    for prod in tier['sample_products'][:2]:
                        print(f"    - {prod[:50]}")

    # Create Excel report
    if all_tiers_data:
        tiers_df = pd.DataFrame(all_tiers_data)

        # Create summary by brand
        brand_summary = branded_df.groupby('Brand').agg({
            'SKU': 'count',
            'CurrentPrice': ['mean', 'min', 'max'],
            'Cost': ['mean', 'min', 'max'],
            'OnHand': 'sum'
        }).round(2)

        # Save to Excel
        with pd.ExcelWriter('cigarette_brand_tiers.xlsx', engine='openpyxl') as writer:
            # Sheet 1: Tier Analysis
            tiers_df.to_excel(writer, sheet_name='Price_Tiers', index=False)

            # Sheet 2: Brand Summary
            brand_summary.to_excel(writer, sheet_name='Brand_Summary')

            # Sheet 3: All Products
            branded_df[['Brand', 'SKU', 'Description', 'CurrentPrice', 'Cost', 'OnHand']].to_excel(
                writer, sheet_name='All_Products', index=False
            )

        print("\n" + "="*80)
        print("✅ Report saved to: cigarette_brand_tiers.xlsx")

        # Create simplified summary for major brands
        print("\n" + "="*80)
        print("MAJOR BRANDS TIER SUMMARY")
        print("="*80)

        major_brands = ['MARLBORO', 'NEWPORT', 'CAMEL', 'AMERICAN SPIRIT', 'PALL MALL', 'WINSTON', 'KOOL']

        for brand in major_brands:
            brand_tiers = [t for t in all_tiers_data if t['brand'] == brand]
            if brand_tiers:
                print(f"\n{brand}:")
                for tier in brand_tiers:
                    print(f"  {tier.get('tier_name', 'Tier')}: Price ${tier['avg_price']:.2f}, Cost ${tier['avg_cost']:.2f}, Markup {tier['markup_pct']:.0f}%")

if __name__ == "__main__":
    main()