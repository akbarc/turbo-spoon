#!/usr/bin/env python3
"""
Quick Cigarette Tiers Summary
Shows price and cost for each tier of major cigarette brands
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

# Major cigarette brands to focus on
MAJOR_BRANDS = [
    'MARLBORO', 'NEWPORT', 'CAMEL', 'AMERICAN SPIRIT',
    'PALL MALL', 'WINSTON', 'KOOL', 'SALEM',
    'MAVERICK', 'L&M', 'BASIC', 'PARLIAMENT'
]

def get_brand_tiers():
    """Get cigarette products grouped by brand and price tier"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        query = """
        SELECT
            CASE
                WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                WHEN UPPER(i.Description) LIKE '%BASIC%' THEN 'BASIC'
                WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                ELSE NULL
            END as Brand,
            i.Price as CurrentPrice,
            i.Cost,
            COUNT(*) OVER (PARTITION BY
                CASE
                    WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                    WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                    WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                    WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                    WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                    WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                    WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                    WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                    WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                    WHEN UPPER(i.Description) LIKE '%BASIC%' THEN 'BASIC'
                    WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                END, i.Price
            ) as ProductsAtPrice
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE
            c.Name LIKE '%CIGARETTE%'
            AND i.Inactive = 0
            AND i.Price > 0
            AND i.Description NOT LIKE '%CIGAR%'
            AND i.Description NOT LIKE '%LIGHTER%'
            AND i.Description NOT LIKE '%TORCH%'
        """

        df = conn.execute_query(query, description="Get cigarette products by brand")
        return df

    finally:
        conn.close()

def main():
    print("="*80)
    print("CIGARETTE BRAND PRICE TIERS - SUMMARY")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    df = get_brand_tiers()

    if df is None or len(df) == 0:
        print("No data found")
        return

    # Filter to major brands only
    df = df[df['Brand'].isin(MAJOR_BRANDS)]

    # Convert to float for calculations
    df['CurrentPrice'] = df['CurrentPrice'].astype(float)
    df['Cost'] = df['Cost'].astype(float)

    # Group by brand and price to identify tiers
    summary_data = []

    for brand in MAJOR_BRANDS:
        brand_df = df[df['Brand'] == brand]

        if len(brand_df) == 0:
            continue

        # Get unique prices sorted
        unique_prices = sorted(brand_df['CurrentPrice'].unique())

        print(f"\n{brand}")
        print("-" * 60)

        if len(unique_prices) == 1:
            # Single price point
            avg_cost = brand_df['Cost'].mean()
            price = unique_prices[0]
            margin = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

            print(f"  Single Tier:")
            print(f"    Price: ${price:.2f}")
            print(f"    Cost:  ${avg_cost:.2f}")
            print(f"    Margin: {margin:.1f}%")
            print(f"    Products: {len(brand_df)}")

            summary_data.append({
                'Brand': brand,
                'Tier': 'Single',
                'Price': price,
                'Cost': avg_cost,
                'Margin%': margin,
                'Product_Count': len(brand_df)
            })

        elif len(unique_prices) == 2:
            # Two tiers
            for idx, price in enumerate(unique_prices):
                tier_name = "Regular" if idx == 0 else "Premium"
                tier_df = brand_df[brand_df['CurrentPrice'] == price]
                avg_cost = tier_df['Cost'].mean()
                margin = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

                print(f"  {tier_name}:")
                print(f"    Price: ${price:.2f}")
                print(f"    Cost:  ${avg_cost:.2f}")
                print(f"    Margin: {margin:.1f}%")
                print(f"    Products: {len(tier_df)}")

                summary_data.append({
                    'Brand': brand,
                    'Tier': tier_name,
                    'Price': price,
                    'Cost': avg_cost,
                    'Margin%': margin,
                    'Product_Count': len(tier_df)
                })

        else:
            # Three or more price points - group into 3 tiers
            # Find natural breaks
            price_range = unique_prices[-1] - unique_prices[0]

            if price_range < 5:  # If range is small, group all as single tier
                avg_price = brand_df['CurrentPrice'].mean()
                avg_cost = brand_df['Cost'].mean()
                margin = ((avg_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

                print(f"  All Products (minimal price variation):")
                print(f"    Avg Price: ${avg_price:.2f}")
                print(f"    Avg Cost:  ${avg_cost:.2f}")
                print(f"    Margin: {margin:.1f}%")
                print(f"    Products: {len(brand_df)}")

            else:
                # Divide into thirds
                tier_boundaries = [
                    unique_prices[0],
                    unique_prices[0] + price_range/3,
                    unique_prices[0] + 2*price_range/3,
                    unique_prices[-1] + 0.01
                ]

                tier_names = ["Value Tier", "Mid Tier", "Premium Tier"]

                for i in range(3):
                    tier_df = brand_df[
                        (brand_df['CurrentPrice'] >= tier_boundaries[i]) &
                        (brand_df['CurrentPrice'] < tier_boundaries[i+1])
                    ]

                    if len(tier_df) > 0:
                        avg_price = tier_df['CurrentPrice'].mean()
                        avg_cost = tier_df['Cost'].mean()
                        margin = ((avg_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

                        print(f"  {tier_names[i]}:")
                        print(f"    Avg Price: ${avg_price:.2f} (${tier_df['CurrentPrice'].min():.2f}-${tier_df['CurrentPrice'].max():.2f})")
                        print(f"    Avg Cost:  ${avg_cost:.2f}")
                        print(f"    Margin: {margin:.1f}%")
                        print(f"    Products: {len(tier_df)}")

                        summary_data.append({
                            'Brand': brand,
                            'Tier': tier_names[i],
                            'Price': avg_price,
                            'Cost': avg_cost,
                            'Margin%': margin,
                            'Product_Count': len(tier_df)
                        })

    # Save summary to CSV
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv('cigarette_tiers_summary.csv', index=False)
        print(f"\n✅ Summary saved to: cigarette_tiers_summary.csv")

    print("\n" + "="*80)
    print("QUICK REFERENCE - TOP BRANDS")
    print("="*80)

    for brand in ['MARLBORO', 'NEWPORT', 'CAMEL']:
        brand_items = [s for s in summary_data if s['Brand'] == brand]
        if brand_items:
            print(f"\n{brand}:")
            for item in brand_items:
                print(f"  {item['Tier']:12} -> Price: ${item['Price']:6.2f}, Cost: ${item['Cost']:6.2f}, Margin: {item['Margin%']:5.1f}%")

if __name__ == "__main__":
    main()