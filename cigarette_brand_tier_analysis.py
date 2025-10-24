"""
Cigarette Brand Tier Analysis
Groups cigarettes by brand and price tier with comprehensive metrics
Only includes items from the Cigarette category
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def analyze_cigarette_tiers():
    """Analyze cigarette sales by brand and price tier"""

    db = SQLServerConnection()

    # First, get all cigarette sales data from Cigarette category only
    query = """
    WITH CigaretteSales AS (
        SELECT
            i.Description as ProductName,
            i.ItemLookupCode as SKU,
            i.Cost as UnitCost,
            i.SalePrice as ListPrice,
            c.Name as Category,
            -- Extract brand name (usually first word or two)
            CASE
                WHEN i.Description LIKE 'NEWPORT%' THEN 'NEWPORT'
                WHEN i.Description LIKE 'MARL%' THEN 'MARLBORO'
                WHEN i.Description LIKE 'CAMEL%' THEN 'CAMEL'
                WHEN i.Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN i.Description LIKE 'WINSTON%' THEN 'WINSTON'
                WHEN i.Description LIKE 'PALL MALL%' THEN 'PALL MALL'
                WHEN i.Description LIKE 'VIRGINIA SLIM%' THEN 'VIRGINIA SLIMS'
                WHEN i.Description LIKE 'KOOL%' THEN 'KOOL'
                WHEN i.Description LIKE 'SALEM%' THEN 'SALEM'
                WHEN i.Description LIKE 'PARLIAMENT%' THEN 'PARLIAMENT'
                WHEN i.Description LIKE 'LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                WHEN i.Description LIKE 'MAVERICK%' THEN 'MAVERICK'
                WHEN i.Description LIKE 'EAGLE%' THEN 'EAGLE'
                WHEN i.Description LIKE 'PYRAMID%' THEN 'PYRAMID'
                WHEN i.Description LIKE 'SENECA%' THEN 'SENECA'
                WHEN i.Description LIKE 'DORAL%' THEN 'DORAL'
                WHEN i.Description LIKE 'MISTY%' THEN 'MISTY'
                WHEN i.Description LIKE 'MONTEGO%' THEN 'MONTEGO'
                WHEN i.Description LIKE '305%' THEN '305'
                WHEN i.Description LIKE 'LIGGETT%' THEN 'LIGGETT'
                WHEN i.Description LIKE 'L&M%' THEN 'L&M'
                WHEN i.Description LIKE '24/7%' THEN '24/7'
                WHEN i.Description LIKE 'EDGEFIELD%' THEN 'EDGEFIELD'
                WHEN i.Description LIKE 'COUTURE%' THEN 'COUTURE'
                WHEN i.Description LIKE 'BERLEY%' THEN 'BERLEY'
                WHEN i.Description LIKE 'WAVE%' THEN 'WAVE'
                ELSE SUBSTRING(i.Description, 1, CHARINDEX(' ', i.Description + ' ') - 1)
            END as BrandName,
            -- Product attributes
            CASE
                WHEN i.Description LIKE '%MENTHOL%' THEN 'MENTHOL'
                WHEN i.Description LIKE '%CRUSH%' THEN 'CRUSH/CAPSULE'
                ELSE 'NON-MENTHOL'
            END as MentholType,
            CASE
                WHEN i.Description LIKE '%100%' OR i.Description LIKE '%100S%' THEN '100s'
                WHEN i.Description LIKE '%KING%' OR i.Description LIKE '%KINGS%' THEN 'KINGS'
                WHEN i.Description LIKE '%72%' THEN '72s'
                ELSE 'KINGS'
            END as SizeType,
            CASE
                WHEN i.Description LIKE '%SOFT%' THEN 'SOFT PACK'
                ELSE 'BOX'
            END as PackType,
            COUNT(DISTINCT te.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            AVG(te.Price) as AvgSellingPrice,
            MIN(te.Price) as MinSellingPrice,
            MAX(te.Price) as MaxSellingPrice,
            STDEV(te.Price) as PriceStdDev,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
            AVG(te.Cost) as AvgCost
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            AND (
                UPPER(c.Name) LIKE '%CIGARETTE%'
                OR UPPER(c.Name) = 'CIGARETTES'
                OR UPPER(c.Name) = 'TOBACCO'
            )
        GROUP BY i.Description, i.ItemLookupCode, i.Cost, i.SalePrice, c.Name
    )
    SELECT * FROM CigaretteSales
    WHERE UnitsSold > 0 AND Category IS NOT NULL
    ORDER BY BrandName, AvgSellingPrice DESC, UnitsSold DESC
    """

    print("Fetching cigarette sales data from Cigarette category...")
    result = db.execute_query(query)

    if result is None or result.empty:
        print("No data found")
        return None

    # Convert Decimal types to float
    for col in ['UnitCost', 'ListPrice', 'AvgSellingPrice', 'MinSellingPrice',
                'MaxSellingPrice', 'TotalRevenue', 'GrossProfit', 'AvgCost', 'PriceStdDev']:
        if col in result.columns:
            result[col] = result[col].astype(float)

    # Define price tiers based on selling price
    def assign_tier(price):
        if price < 30:
            return 'DEEP DISCOUNT'
        elif price < 50:
            return 'DISCOUNT'
        elif price < 65:
            return 'VALUE'
        elif price < 75:
            return 'MID-TIER'
        elif price < 85:
            return 'PREMIUM'
        else:
            return 'SUPER PREMIUM'

    result['PriceTier'] = result['AvgSellingPrice'].apply(assign_tier)

    # Group similar products by brand, tier, and attributes
    brand_tier_groups = []

    for brand in result['BrandName'].unique():
        brand_data = result[result['BrandName'] == brand].copy()

        # Group by price clusters (within $0.50 of each other)
        brand_data['PriceCluster'] = pd.cut(brand_data['AvgSellingPrice'],
                                            bins=np.arange(0, 150, 0.5),
                                            labels=False)

        for cluster in brand_data['PriceCluster'].unique():
            if pd.isna(cluster):
                continue

            cluster_data = brand_data[brand_data['PriceCluster'] == cluster]

            # Further group by menthol type and size
            for menthol in cluster_data['MentholType'].unique():
                menthol_data = cluster_data[cluster_data['MentholType'] == menthol]

                for size in menthol_data['SizeType'].unique():
                    size_data = menthol_data[menthol_data['SizeType'] == size]

                    if len(size_data) > 0:
                        # Calculate tier metrics
                        min_cost = size_data['UnitCost'].min()
                        max_cost = size_data['UnitCost'].max()
                        avg_cost = size_data['AvgCost'].mean()

                        min_price = size_data['MinSellingPrice'].min()
                        max_price = size_data['MaxSellingPrice'].max()
                        avg_price = size_data['AvgSellingPrice'].mean()

                        total_units = size_data['UnitsSold'].sum()
                        total_revenue = size_data['TotalRevenue'].sum()
                        total_profit = size_data['GrossProfit'].sum()

                        # Note any cost variations
                        cost_variation = max_cost - min_cost
                        cost_note = ""
                        if cost_variation > 0.10:
                            cost_note = f"Cost varies ${min_cost:.2f}-${max_cost:.2f}"

                        # Note any price variations within tier
                        price_variation = size_data['AvgSellingPrice'].max() - size_data['AvgSellingPrice'].min()
                        price_note = ""
                        if price_variation > 0.10:
                            price_note = f"Price varies within tier by ${price_variation:.2f}"

                        # List all SKUs in this tier
                        skus = size_data['SKU'].tolist()
                        products = size_data['ProductName'].tolist()

                        tier_info = {
                            'Brand': brand,
                            'Tier': size_data['PriceTier'].iloc[0],
                            'Type': f"{menthol} {size}",
                            'Pack Types': ', '.join(size_data['PackType'].unique()),
                            'Num SKUs': len(size_data),
                            'Units Sold': int(total_units),
                            'Avg Cost': round(avg_cost, 2),
                            'Min Cost': round(min_cost, 2),
                            'Max Cost': round(max_cost, 2),
                            'Avg Selling Price': round(avg_price, 2),
                            'Min Selling Price': round(min_price, 2),
                            'Max Selling Price': round(max_price, 2),
                            'Total Revenue': round(total_revenue, 2),
                            'Total Profit': round(total_profit, 2),
                            'Margin %': round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 1),
                            'Cost Note': cost_note,
                            'Price Note': price_note,
                            'SKUs': '; '.join(skus[:3]) + ('...' if len(skus) > 3 else ''),
                            'Products': '; '.join([p[:30] for p in products[:2]]) + ('...' if len(products) > 2 else '')
                        }

                        brand_tier_groups.append(tier_info)

    # Create DataFrame from tier groups
    tier_df = pd.DataFrame(brand_tier_groups)

    # Sort by brand and units sold
    tier_df = tier_df.sort_values(['Brand', 'Units Sold'], ascending=[True, False])

    # Save main tier analysis
    filename = f'cigarette_brand_tiers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    tier_df.to_csv(filename, index=False)

    print(f"\n✅ Brand tier analysis saved to {filename}")
    print(f"Total brand-tier combinations: {len(tier_df)}")
    print(f"Total brands analyzed: {tier_df['Brand'].nunique()}")

    # Create brand summary
    brand_summary = tier_df.groupby('Brand').agg({
        'Units Sold': 'sum',
        'Total Revenue': 'sum',
        'Total Profit': 'sum',
        'Num SKUs': 'sum',
        'Avg Selling Price': 'mean'
    }).round(2)

    brand_summary['Margin %'] = (brand_summary['Total Profit'] / brand_summary['Total Revenue'] * 100).round(1)
    brand_summary = brand_summary.sort_values('Units Sold', ascending=False)

    # Save brand summary
    summary_filename = f'cigarette_brand_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    brand_summary.to_csv(summary_filename)

    print(f"✅ Brand summary saved to {summary_filename}")

    # Print top brands
    print("\n" + "="*80)
    print("TOP BRANDS BY UNITS SOLD (30 DAYS)")
    print("="*80)
    for brand, row in brand_summary.head(10).iterrows():
        print(f"{brand:20} | Units: {int(row['Units Sold']):8,} | Revenue: ${row['Total Revenue']:12,.2f} | Margin: {row['Margin %']:5.1f}%")

    # Print tier distribution
    print("\n" + "="*80)
    print("TIER DISTRIBUTION")
    print("="*80)
    tier_dist = tier_df.groupby('Tier').agg({
        'Units Sold': 'sum',
        'Total Revenue': 'sum',
        'Brand': 'nunique'
    })
    tier_dist = tier_dist.sort_values('Units Sold', ascending=False)

    for tier, row in tier_dist.iterrows():
        print(f"{tier:15} | Units: {int(row['Units Sold']):8,} | Revenue: ${row['Total Revenue']:12,.2f} | Brands: {int(row['Brand']):3}")

    # Print menthol vs non-menthol
    print("\n" + "="*80)
    print("MENTHOL VS NON-MENTHOL")
    print("="*80)

    menthol_analysis = []
    for _, row in tier_df.iterrows():
        if 'MENTHOL' in row['Type']:
            category = 'MENTHOL'
        elif 'CRUSH' in row['Type']:
            category = 'CRUSH/CAPSULE'
        else:
            category = 'NON-MENTHOL'
        menthol_analysis.append({
            'Category': category,
            'Units': row['Units Sold'],
            'Revenue': row['Total Revenue']
        })

    menthol_df = pd.DataFrame(menthol_analysis)
    menthol_summary = menthol_df.groupby('Category').agg({
        'Units': 'sum',
        'Revenue': 'sum'
    })

    for cat, row in menthol_summary.iterrows():
        pct = (row['Units'] / menthol_summary['Units'].sum() * 100)
        print(f"{cat:15} | Units: {int(row['Units']):8,} ({pct:5.1f}%) | Revenue: ${row['Revenue']:12,.2f}")

    return filename, summary_filename

if __name__ == "__main__":
    analyze_cigarette_tiers()