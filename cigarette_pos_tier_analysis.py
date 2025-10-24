"""
Simplified Cigarette POS Tier Analysis
Complete pricing and sales data organized by brand tiers
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def analyze_cigarette_pos_tiers():
    """Analyze cigarettes by brand and price tiers"""

    db = SQLServerConnection()

    # Step 1: Get basic item data first
    print("Step 1: Fetching cigarette items from POS...")

    items_query = """
    SELECT
        i.ID as ItemID,
        i.Description as ProductName,
        i.ItemLookupCode as SKU,
        i.Cost as CurrentCost,
        i.LastCost,
        i.Price as CurrentPrice,
        i.PriceA,
        i.PriceB,
        i.PriceC,
        i.SalePrice,
        i.Quantity as OnHand,
        i.ReorderPoint,
        i.LastSold,
        i.LastReceived,
        c.Name as Category,
        -- Extract brand
        CASE
            WHEN i.Description LIKE 'NEWPORT%' THEN 'NEWPORT'
            WHEN i.Description LIKE 'MARL%' THEN 'MARLBORO'
            WHEN i.Description LIKE 'CAMEL%' THEN 'CAMEL'
            WHEN i.Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
            WHEN i.Description LIKE 'WINST%' THEN 'WINSTON'
            WHEN i.Description LIKE 'PALL MALL%' THEN 'PALL MALL'
            WHEN i.Description LIKE 'VIRG SL%' OR i.Description LIKE 'VIRGINIA%' THEN 'VIRGINIA SLIMS'
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
            WHEN i.Description LIKE 'L&M%' OR i.Description LIKE 'L & M%' THEN 'L&M'
            WHEN i.Description LIKE '24/7%' THEN '24/7'
            WHEN i.Description LIKE 'BASIC%' THEN 'BASIC'
            WHEN i.Description LIKE 'CAPRI%' THEN 'CAPRI'
            WHEN i.Description LIKE 'CROWN%' THEN 'CROWNS'
            WHEN i.Description LIKE 'LD%' THEN 'LD'
            WHEN i.Description LIKE 'SHIELD%' THEN 'SHIELD'
            WHEN i.Description LIKE 'TETON%' THEN 'TETON'
            WHEN i.Description LIKE 'WILDHORSE%' THEN 'WILDHORSE'
            WHEN i.Description LIKE 'B&H%' THEN 'B&H'
            WHEN i.Description LIKE 'FORTUNA%' THEN 'FORTUNA'
            WHEN i.Description LIKE 'RAVE%' THEN 'RAVE'
            WHEN i.Description LIKE 'EDGEFIELD%' THEN 'EDGEFIELD'
            WHEN i.Description LIKE 'VANTAGE%' THEN 'VANTAGE'
            WHEN i.Description LIKE 'CARLTON%' THEN 'CARLTON'
            WHEN i.Description LIKE 'TAJMAHAL%' THEN 'TAJMAHAL'
            ELSE LEFT(i.Description, CHARINDEX(' ', i.Description + ' ') - 1)
        END as Brand,
        CASE
            WHEN i.Description LIKE '%MENTHOL%' THEN 'MENTHOL'
            WHEN i.Description LIKE '%CRUSH%' THEN 'CRUSH'
            ELSE 'NON-MENTHOL'
        END as Type,
        CASE
            WHEN i.Description LIKE '%100%' THEN '100s'
            WHEN i.Description LIKE '%120%' THEN '120s'
            WHEN i.Description LIKE '%72%' THEN '72s'
            WHEN i.Description LIKE '%KING%' THEN 'KING'
            ELSE 'REG'
        END as Size
    FROM dbo.Item i
    LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
    WHERE (
        UPPER(ISNULL(c.Name, '')) LIKE '%CIGARETTE%'
        OR UPPER(ISNULL(c.Name, '')) = 'CIGARETTES'
        OR UPPER(ISNULL(c.Name, '')) = 'TOBACCO'
        OR i.Description LIKE '%NEWPORT%'
        OR i.Description LIKE '%MARL%'
        OR i.Description LIKE '%CAMEL%'
        OR i.Description LIKE '%WINSTON%'
        OR i.Description LIKE '%KOOL%'
        OR i.Description LIKE '%AMERICAN SPIRIT%'
        OR i.Description LIKE '%PALL MALL%'
        OR i.Description LIKE '%SALEM%'
        OR i.Description LIKE '%LUCKY%'
        OR i.Description LIKE '%MAVERICK%'
        OR i.Description LIKE '%24/7%'
        OR i.Description LIKE '%305%'
        OR i.Description LIKE '%BASIC%'
        OR i.Description LIKE '%L&M%'
        OR i.Description LIKE '%DORAL%'
        OR i.Description LIKE '%PYRAMID%'
        OR i.Description LIKE '%SENECA%'
    )
    """

    items_df = db.execute_query(items_query)

    if items_df is None or items_df.empty:
        print("No cigarette items found")
        return None

    print(f"Found {len(items_df)} cigarette items")

    # Convert decimal columns
    for col in ['CurrentCost', 'LastCost', 'CurrentPrice', 'PriceA', 'PriceB', 'PriceC', 'SalePrice', 'OnHand', 'ReorderPoint']:
        if col in items_df.columns:
            items_df[col] = pd.to_numeric(items_df[col], errors='coerce')

    # Step 2: Get sales data separately for each time period
    print("\nStep 2: Fetching sales history...")

    # Get item IDs for query
    item_ids = items_df['ItemID'].tolist()
    item_ids_str = ','.join([str(id) for id in item_ids])

    # 1 Month sales
    sales_1mo_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_1Month,
        MAX(te.Price) as MaxPrice_1Month,
        MIN(te.Price) as MinPrice_1Month,
        AVG(te.Price) as AvgPrice_1Month
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(MONTH, -1, GETDATE())
    GROUP BY te.ItemID
    """

    # 3 Month sales
    sales_3mo_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_3Month
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY te.ItemID
    """

    # YTD sales
    sales_ytd_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_YTD
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()), 0)
    GROUP BY te.ItemID
    """

    # 2024 sales
    sales_2024_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_2024
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND YEAR(t.Time) = 2024
    GROUP BY te.ItemID
    """

    # Most recent sale info
    last_sale_query = f"""
    SELECT
        te.ItemID,
        te.Price as LastSalePrice,
        t.Time as LastSaleDate
    FROM (
        SELECT
            te.ItemID,
            MAX(t.Time) as MaxTime
        FROM dbo.TransactionEntry te
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE te.ItemID IN ({item_ids_str})
        GROUP BY te.ItemID
    ) latest
    JOIN [dbo].[Transaction] t ON t.Time = latest.MaxTime
    JOIN dbo.TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        AND te.ItemID = latest.ItemID
    """

    # Execute sales queries
    sales_1mo = db.execute_query(sales_1mo_query)
    sales_3mo = db.execute_query(sales_3mo_query)
    sales_ytd = db.execute_query(sales_ytd_query)
    sales_2024 = db.execute_query(sales_2024_query)
    last_sale = db.execute_query(last_sale_query)

    # Merge all data
    if sales_1mo is not None:
        items_df = items_df.merge(sales_1mo, on='ItemID', how='left')
    if sales_3mo is not None:
        items_df = items_df.merge(sales_3mo, on='ItemID', how='left')
    if sales_ytd is not None:
        items_df = items_df.merge(sales_ytd, on='ItemID', how='left')
    if sales_2024 is not None:
        items_df = items_df.merge(sales_2024, on='ItemID', how='left')
    if last_sale is not None:
        items_df = items_df.merge(last_sale, on='ItemID', how='left')

    # Fill NaN values
    sales_cols = ['Units_1Month', 'Units_3Month', 'Units_YTD', 'Units_2024']
    for col in sales_cols:
        if col in items_df.columns:
            items_df[col] = items_df[col].fillna(0).astype(int)

    # Convert price columns
    price_cols = ['MaxPrice_1Month', 'MinPrice_1Month', 'AvgPrice_1Month', 'LastSalePrice']
    for col in price_cols:
        if col in items_df.columns:
            items_df[col] = pd.to_numeric(items_df[col], errors='coerce')

    # Calculate margins
    items_df['CurrentMargin%'] = ((items_df['CurrentPrice'] - items_df['CurrentCost']) / items_df['CurrentPrice'] * 100).round(1)

    # Define price tiers
    def assign_tier(price):
        if pd.isna(price) or price == 0:
            return 'NO PRICE'
        elif price < 30:
            return '1. DEEP DISCOUNT (<$30)'
        elif price < 50:
            return '2. DISCOUNT ($30-50)'
        elif price < 65:
            return '3. VALUE ($50-65)'
        elif price < 75:
            return '4. MID-TIER ($65-75)'
        elif price < 85:
            return '5. PREMIUM ($75-85)'
        elif price < 95:
            return '6. SUPER PREMIUM ($85-95)'
        else:
            return '7. ULTRA PREMIUM ($95+)'

    items_df['PriceTier'] = items_df['CurrentPrice'].apply(assign_tier)

    # Define sub-brands for Marlboro
    def get_marlboro_tier(desc):
        desc_upper = desc.upper()
        if any(x in desc_upper for x in ['BLACK', 'MIDNIGHT', 'NXT', 'SLATE']):
            return 'MARLBORO BLACK/SPECIAL'
        elif 'MENTHOL' in desc_upper:
            return 'MARLBORO MENTHOL'
        elif '72' in desc_upper:
            return 'MARLBORO 72s'
        elif any(x in desc_upper for x in ['RED', 'GOLD', 'SILVER', 'BLUE']):
            return 'MARLBORO CORE'
        else:
            return 'MARLBORO OTHER'

    # Apply sub-brand logic
    items_df['SubBrand'] = items_df.apply(
        lambda x: get_marlboro_tier(x['ProductName']) if x['Brand'] == 'MARLBORO' else x['Brand'],
        axis=1
    )

    # Sort by brand and price
    items_df = items_df.sort_values(['Brand', 'CurrentPrice', 'ProductName'])

    # Save complete analysis
    filename = f'cigarette_pos_tier_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    items_df.to_csv(filename, index=False)
    print(f"\n✅ Complete analysis saved to {filename}")

    # Create brand tier summary
    print("\nCreating brand tier summaries...")

    brand_summary = items_df.groupby(['Brand', 'PriceTier']).agg({
        'ProductName': 'count',
        'CurrentCost': ['mean', 'min', 'max'],
        'CurrentPrice': ['mean', 'min', 'max'],
        'Units_1Month': 'sum',
        'Units_3Month': 'sum',
        'Units_YTD': 'sum',
        'Units_2024': 'sum',
        'OnHand': 'sum',
        'CurrentMargin%': 'mean'
    }).round(2)

    brand_summary.columns = ['SKUs', 'Avg_Cost', 'Min_Cost', 'Max_Cost',
                             'Avg_Price', 'Min_Price', 'Max_Price',
                             'Units_1Mo', 'Units_3Mo', 'Units_YTD', 'Units_2024',
                             'OnHand', 'Avg_Margin%']

    summary_filename = f'cigarette_brand_tier_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    brand_summary.to_csv(summary_filename)
    print(f"✅ Brand tier summary saved to {summary_filename}")

    # Print top brands
    print("\n" + "="*120)
    print("TOP BRANDS BY UNITS SOLD")
    print("="*120)
    print(f"{'Brand':20} | {'1 Month':>8} | {'3 Month':>8} | {'YTD':>8} | {'2024':>8} | {'Avg Price':>10} | {'Margin%':>8} | {'SKUs':>5}")
    print("-"*120)

    brand_totals = items_df.groupby('Brand').agg({
        'Units_1Month': 'sum',
        'Units_3Month': 'sum',
        'Units_YTD': 'sum',
        'Units_2024': 'sum',
        'CurrentPrice': 'mean',
        'CurrentMargin%': 'mean',
        'ProductName': 'count'
    }).sort_values('Units_1Month', ascending=False).head(20)

    for brand, row in brand_totals.iterrows():
        print(f"{brand:20} | {int(row['Units_1Month']):8,} | {int(row['Units_3Month']):8,} | "
              f"{int(row['Units_YTD']):8,} | {int(row['Units_2024']):8,} | "
              f"${row['CurrentPrice']:9.2f} | {row['CurrentMargin%']:7.1f}% | {int(row['ProductName']):5}")

    # Print Marlboro tiers specifically
    print("\n" + "="*120)
    print("MARLBORO TIER BREAKDOWN")
    print("="*120)

    marl_data = items_df[items_df['Brand'] == 'MARLBORO'].copy()
    if not marl_data.empty:
        marl_summary = marl_data.groupby('SubBrand').agg({
            'Units_1Month': 'sum',
            'CurrentCost': 'mean',
            'CurrentPrice': 'mean',
            'CurrentMargin%': 'mean',
            'ProductName': 'count'
        }).sort_values('Units_1Month', ascending=False)

        print(f"{'Sub-Brand':25} | {'Units 1Mo':>8} | {'Avg Cost':>10} | {'Avg Price':>10} | {'Margin%':>8} | {'SKUs':>5}")
        print("-"*120)
        for sub, row in marl_summary.iterrows():
            print(f"{sub:25} | {int(row['Units_1Month']):8,} | ${row['CurrentCost']:9.2f} | "
                  f"${row['CurrentPrice']:9.2f} | {row['CurrentMargin%']:7.1f}% | {int(row['ProductName']):5}")

    return items_df, brand_summary

if __name__ == "__main__":
    analyze_cigarette_pos_tiers()