"""
Cigarette POS Analysis - Items Sold in Past 60 Days Only
Complete pricing tiers and sales metrics for active inventory
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def analyze_active_cigarettes():
    """Analyze only cigarettes sold in the past 60 days"""

    db = SQLServerConnection()

    # Step 1: Get items sold in past 60 days
    print("Step 1: Fetching cigarettes sold in past 60 days...")

    active_items_query = """
    WITH ActiveItems AS (
        SELECT DISTINCT te.ItemID
        FROM dbo.TransactionEntry te
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= DATEADD(DAY, -60, GETDATE())
    )
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
        i.MSRP,
        i.Quantity as OnHand,
        i.ReorderPoint,
        i.RestockLevel,
        i.LastSold,
        i.LastReceived,
        c.Name as Category,
        s.SupplierName as Supplier,
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
            WHEN i.Description LIKE 'B&H%' OR i.Description LIKE 'BENSON%' THEN 'BENSON & HEDGES'
            WHEN i.Description LIKE 'FORTUNA%' THEN 'FORTUNA'
            WHEN i.Description LIKE 'RAVE%' THEN 'RAVE'
            WHEN i.Description LIKE 'EDGEFIELD%' THEN 'EDGEFIELD'
            WHEN i.Description LIKE 'VANTAGE%' THEN 'VANTAGE'
            WHEN i.Description LIKE 'CARLTON%' THEN 'CARLTON'
            WHEN i.Description LIKE 'TAJMAHAL%' THEN 'TAJMAHAL'
            WHEN i.Description LIKE 'BERKLEY%' THEN 'BERKLEY'
            WHEN i.Description LIKE 'GPC%' THEN 'GPC'
            WHEN i.Description LIKE 'KENT%' THEN 'KENT'
            WHEN i.Description LIKE 'TRUE%' THEN 'TRUE'
            WHEN i.Description LIKE 'EVE%' THEN 'EVE'
            WHEN i.Description LIKE 'MORE%' THEN 'MORE'
            ELSE LEFT(i.Description, CHARINDEX(' ', i.Description + ' ') - 1)
        END as Brand,
        CASE
            WHEN i.Description LIKE '%MENTHOL%' OR i.Description LIKE '%MENTH%' THEN 'MENTHOL'
            WHEN i.Description LIKE '%CRUSH%' THEN 'CRUSH'
            WHEN i.Description LIKE '%ICE%' OR i.Description LIKE '%COOL%' THEN 'MENTHOL'
            WHEN i.Description LIKE '%JADE%' THEN 'MENTHOL'
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
    INNER JOIN ActiveItems ai ON i.ID = ai.ItemID
    LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
    LEFT JOIN dbo.Supplier s ON i.SupplierID = s.ID
    WHERE (
        UPPER(ISNULL(c.Name, '')) LIKE '%CIGARETTE%'
        OR UPPER(ISNULL(c.Name, '')) = 'CIGARETTES'
        OR UPPER(ISNULL(c.Name, '')) = 'TOBACCO'
        OR i.Description LIKE '%NEWPORT%'
        OR i.Description LIKE '%MARL%'
        OR i.Description LIKE '%CAMEL%'
        OR i.Description LIKE '%WINSTON%'
        OR i.Description LIKE '%AMERICAN SPIRIT%'
        OR i.Description LIKE '%PALL MALL%'
        OR i.Description LIKE '%KOOL%'
        OR i.Description LIKE '%SALEM%'
    )
    """

    items_df = db.execute_query(active_items_query)

    if items_df is None or items_df.empty:
        print("No active cigarette items found")
        return None

    print(f"Found {len(items_df)} active cigarette items (sold in past 60 days)")

    # Convert decimal columns
    numeric_cols = ['CurrentCost', 'LastCost', 'CurrentPrice', 'PriceA', 'PriceB',
                   'PriceC', 'SalePrice', 'MSRP', 'OnHand', 'ReorderPoint', 'RestockLevel']
    for col in numeric_cols:
        if col in items_df.columns:
            items_df[col] = pd.to_numeric(items_df[col], errors='coerce')

    # Get item IDs
    item_ids = items_df['ItemID'].tolist()
    item_ids_str = ','.join([str(id) for id in item_ids])

    # Step 2: Get last PO data (skip if PO tables don't have required columns)
    print("\nStep 2: Checking purchase order data...")

    po_df = None
    try:
        # Try simplified PO query first
        po_query = f"""
        SELECT TOP 1000
            poe.ItemID,
            poe.Price as LastPOCost,
            poe.QuantityOrdered as LastPOQty
        FROM dbo.PurchaseOrderEntry poe
        WHERE poe.ItemID IN ({item_ids_str})
        ORDER BY poe.ID DESC
        """
        po_df = db.execute_query(po_query)

        if po_df is not None and not po_df.empty:
            # Get the most recent PO cost per item
            po_df = po_df.sort_values('ItemID').drop_duplicates(subset=['ItemID'], keep='first')
            print(f"Found PO data for {len(po_df)} items")
    except:
        print("Purchase order data not available, continuing without it")
        po_df = None

    # Step 3: Get comprehensive sales data
    print("\nStep 3: Fetching sales history...")

    # 7 days
    sales_7d_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_7Days,
        AVG(te.Price) as AvgPrice_7Days
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(DAY, -7, GETDATE())
    GROUP BY te.ItemID
    """

    # 30 days
    sales_30d_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_30Days,
        AVG(te.Price) as AvgPrice_30Days,
        MIN(te.Price) as MinPrice_30Days,
        MAX(te.Price) as MaxPrice_30Days,
        SUM(te.Quantity * te.Price) as Revenue_30Days
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(DAY, -30, GETDATE())
    GROUP BY te.ItemID
    """

    # 60 days (entire period)
    sales_60d_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_60Days,
        AVG(te.Price) as AvgPrice_60Days,
        SUM(te.Quantity * te.Price) as Revenue_60Days
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= DATEADD(DAY, -60, GETDATE())
    GROUP BY te.ItemID
    """

    # YTD 2025
    sales_ytd_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_YTD,
        SUM(te.Quantity * te.Price) as Revenue_YTD
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= '2025-01-01'
    GROUP BY te.ItemID
    """

    # 2024 total
    sales_2024_query = f"""
    SELECT
        te.ItemID,
        SUM(te.Quantity) as Units_2024,
        SUM(te.Quantity * te.Price) as Revenue_2024
    FROM dbo.TransactionEntry te
    JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    WHERE te.ItemID IN ({item_ids_str})
      AND t.Time >= '2024-01-01' AND t.Time < '2025-01-01'
    GROUP BY te.ItemID
    """

    # Last sale info
    last_sale_query = f"""
    SELECT
        te.ItemID,
        te.Price as LastSalePrice,
        t.Time as LastSaleDate
    FROM (
        SELECT te.ItemID, MAX(t.Time) as MaxTime
        FROM dbo.TransactionEntry te
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE te.ItemID IN ({item_ids_str})
        GROUP BY te.ItemID
    ) latest
    JOIN [dbo].[Transaction] t ON t.Time = latest.MaxTime
    JOIN dbo.TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
        AND te.ItemID = latest.ItemID
    """

    # Execute all queries
    print("Executing sales queries...")
    sales_7d = db.execute_query(sales_7d_query)
    sales_30d = db.execute_query(sales_30d_query)
    sales_60d = db.execute_query(sales_60d_query)
    sales_ytd = db.execute_query(sales_ytd_query)
    sales_2024 = db.execute_query(sales_2024_query)
    last_sale = db.execute_query(last_sale_query)

    # Merge all data
    print("\nMerging data...")
    if po_df is not None and not po_df.empty:
        items_df = items_df.merge(po_df, on='ItemID', how='left')
    if sales_7d is not None:
        items_df = items_df.merge(sales_7d, on='ItemID', how='left')
    if sales_30d is not None:
        items_df = items_df.merge(sales_30d, on='ItemID', how='left')
    if sales_60d is not None:
        items_df = items_df.merge(sales_60d, on='ItemID', how='left')
    if sales_ytd is not None:
        items_df = items_df.merge(sales_ytd, on='ItemID', how='left')
    if sales_2024 is not None:
        items_df = items_df.merge(sales_2024, on='ItemID', how='left')
    if last_sale is not None:
        items_df = items_df.merge(last_sale, on='ItemID', how='left')

    # Fill NaN values
    sales_cols = ['Units_7Days', 'Units_30Days', 'Units_60Days', 'Units_YTD', 'Units_2024']
    for col in sales_cols:
        if col in items_df.columns:
            items_df[col] = items_df[col].fillna(0).astype(int)

    revenue_cols = ['Revenue_30Days', 'Revenue_60Days', 'Revenue_YTD', 'Revenue_2024']
    for col in revenue_cols:
        if col in items_df.columns:
            items_df[col] = items_df[col].fillna(0)

    # Calculate margins (convert decimal to float first)
    items_df['CurrentMargin%'] = ((items_df['CurrentPrice'] - items_df['CurrentCost']) / items_df['CurrentPrice'] * 100).round(1)
    if 'LastPOCost' in items_df.columns:
        items_df['LastPOCost'] = pd.to_numeric(items_df['LastPOCost'], errors='coerce')
        items_df['POMargin%'] = ((items_df['CurrentPrice'] - items_df['LastPOCost']) / items_df['CurrentPrice'] * 100).round(1)

    # Price tier assignment
    def assign_tier(row):
        price = row['CurrentPrice']
        brand = row['Brand']

        if pd.isna(price) or price == 0:
            return 'NO PRICE'

        premium_brands = ['MARLBORO', 'NEWPORT', 'AMERICAN SPIRIT', 'CAMEL', 'PARLIAMENT']
        value_brands = ['305', 'EAGLE', 'PYRAMID', 'SENECA', 'MONTEGO', 'CROWNS']

        if brand in premium_brands:
            if price < 70:
                return '3. VALUE PREMIUM ($50-70)'
            elif price < 80:
                return '4. MID PREMIUM ($70-80)'
            elif price < 90:
                return '5. PREMIUM ($80-90)'
            else:
                return '6. SUPER PREMIUM ($90+)'
        elif brand in value_brands:
            if price < 40:
                return '1. DEEP DISCOUNT (<$40)'
            elif price < 60:
                return '2. DISCOUNT ($40-60)'
            else:
                return '3. VALUE ($60+)'
        else:
            if price < 40:
                return '1. DEEP DISCOUNT (<$40)'
            elif price < 55:
                return '2. DISCOUNT ($40-55)'
            elif price < 70:
                return '3. VALUE ($55-70)'
            elif price < 80:
                return '4. MID-TIER ($70-80)'
            elif price < 90:
                return '5. PREMIUM ($80-90)'
            else:
                return '6. SUPER PREMIUM ($90+)'

    items_df['PriceTier'] = items_df.apply(assign_tier, axis=1)

    # Brand categorization
    def categorize_brand(brand):
        premium = ['MARLBORO', 'NEWPORT', 'AMERICAN SPIRIT', 'CAMEL', 'PARLIAMENT', 'VIRGINIA SLIMS']
        mid = ['WINSTON', 'KOOL', 'SALEM', 'PALL MALL', 'LUCKY STRIKE', 'L&M']
        value = ['MAVERICK', 'BASIC', 'DORAL', 'GPC', 'MISTY']
        deep = ['305', 'EAGLE', 'PYRAMID', 'SENECA', 'MONTEGO', 'CROWNS', '24/7']

        if brand in premium:
            return 'PREMIUM'
        elif brand in mid:
            return 'MID-TIER'
        elif brand in value:
            return 'VALUE'
        elif brand in deep:
            return 'DEEP DISCOUNT'
        else:
            return 'OTHER'

    items_df['BrandCategory'] = items_df['Brand'].apply(categorize_brand)

    # Marlboro sub-brands
    def get_marlboro_line(desc):
        desc_upper = desc.upper()
        if any(x in desc_upper for x in ['BLACK', 'MIDNIGHT', 'NXT', 'SLATE']):
            return 'BLACK LINE'
        elif '72' in desc_upper:
            return '72s LINE'
        elif any(x in desc_upper for x in ['RED', 'GOLD', 'SILVER', 'BLUE']):
            if 'MENTHOL' in desc_upper:
                return 'CORE MENTHOL'
            else:
                return 'CORE REGULAR'
        else:
            return 'OTHER'

    items_df['ProductLine'] = items_df.apply(
        lambda x: get_marlboro_line(x['ProductName']) if x['Brand'] == 'MARLBORO' else '',
        axis=1
    )

    # ABC Analysis
    if 'Revenue_60Days' in items_df.columns:
        total_revenue = items_df['Revenue_60Days'].sum()
        items_df_sorted = items_df.sort_values('Revenue_60Days', ascending=False).copy()
        items_df_sorted['Revenue_Cumulative'] = items_df_sorted['Revenue_60Days'].cumsum()
        items_df_sorted['Revenue_Cumulative%'] = (items_df_sorted['Revenue_Cumulative'] / total_revenue * 100)

        def assign_abc(row):
            if row['Revenue_Cumulative%'] <= 80:
                return 'A'
            elif row['Revenue_Cumulative%'] <= 95:
                return 'B'
            else:
                return 'C'

        items_df_sorted['ABC_Class'] = items_df_sorted.apply(assign_abc, axis=1)
        items_df = items_df.merge(items_df_sorted[['ItemID', 'ABC_Class']], on='ItemID', how='left')

    # Sort by brand and sales
    items_df = items_df.sort_values(['BrandCategory', 'Brand', 'Units_30Days'], ascending=[True, True, False])

    # Save main analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'cigarette_60day_active_analysis_{timestamp}.csv'
    items_df.to_csv(filename, index=False)
    print(f"\n✅ Active items analysis saved to {filename}")

    # Brand performance summary
    brand_summary = items_df.groupby(['BrandCategory', 'Brand']).agg({
        'ProductName': 'count',
        'CurrentCost': 'mean',
        'CurrentPrice': 'mean',
        'Units_7Days': 'sum',
        'Units_30Days': 'sum',
        'Units_60Days': 'sum',
        'Units_YTD': 'sum',
        'Units_2024': 'sum',
        'Revenue_60Days': 'sum',
        'OnHand': 'sum',
        'CurrentMargin%': 'mean'
    }).round(2)

    brand_filename = f'cigarette_brand_summary_60day_{timestamp}.csv'
    brand_summary.to_csv(brand_filename)
    print(f"✅ Brand summary saved to {brand_filename}")

    # Price tier analysis
    tier_summary = items_df.groupby(['PriceTier', 'Type']).agg({
        'ProductName': 'count',
        'CurrentPrice': 'mean',
        'Units_30Days': 'sum',
        'Units_60Days': 'sum',
        'Revenue_60Days': 'sum',
        'CurrentMargin%': 'mean'
    }).round(2)

    tier_filename = f'cigarette_tier_summary_60day_{timestamp}.csv'
    tier_summary.to_csv(tier_filename)
    print(f"✅ Tier summary saved to {tier_filename}")

    # Executive summary
    print("\n" + "="*120)
    print("EXECUTIVE SUMMARY - ACTIVE CIGARETTE ANALYSIS (60-DAY ACTIVITY)")
    print("="*120)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Active SKUs: {len(items_df):,}")
    print(f"Active Brands: {items_df['Brand'].nunique()}")
    print(f"Total On Hand: {items_df['OnHand'].sum():,.0f} units")
    print(f"Inventory Value: ${(items_df['OnHand'] * items_df['CurrentCost']).sum():,.2f}")

    print("\n" + "-"*120)
    print("SALES PERFORMANCE")
    print("-"*120)
    print(f"Last 7 Days:    {items_df['Units_7Days'].sum():,} units")
    print(f"Last 30 Days:   {items_df['Units_30Days'].sum():,} units")
    print(f"Last 60 Days:   {items_df['Units_60Days'].sum():,} units | ${items_df['Revenue_60Days'].sum():,.2f}")
    print(f"YTD 2025:       {items_df['Units_YTD'].sum():,} units | ${items_df['Revenue_YTD'].sum():,.2f}")
    print(f"Total 2024:     {items_df['Units_2024'].sum():,} units | ${items_df['Revenue_2024'].sum():,.2f}")

    print("\n" + "-"*120)
    print("TOP 15 BRANDS BY 30-DAY SALES")
    print("-"*120)
    print(f"{'Rank':<5} {'Brand':<20} {'Category':<15} {'Units 30D':<12} {'Units 60D':<12} {'Avg Price':<10} {'Margin%':<8} {'SKUs':<5}")
    print("-"*120)

    top_brands = items_df.groupby(['Brand', 'BrandCategory']).agg({
        'Units_30Days': 'sum',
        'Units_60Days': 'sum',
        'CurrentPrice': 'mean',
        'CurrentMargin%': 'mean',
        'ProductName': 'count'
    }).sort_values('Units_30Days', ascending=False).head(15)

    for i, (idx, row) in enumerate(top_brands.iterrows(), 1):
        brand, category = idx
        print(f"{i:<5} {brand:<20} {category:<15} {int(row['Units_30Days']):<12,} "
              f"{int(row['Units_60Days']):<12,} ${row['CurrentPrice']:<9.2f} "
              f"{row['CurrentMargin%']:<7.1f}% {int(row['ProductName']):<5}")

    # Marlboro breakdown
    print("\n" + "="*120)
    print("MARLBORO PRODUCT LINE BREAKDOWN")
    print("="*120)

    marl_data = items_df[items_df['Brand'] == 'MARLBORO'].copy()
    if not marl_data.empty:
        marl_lines = marl_data.groupby('ProductLine').agg({
            'Units_30Days': 'sum',
            'Units_60Days': 'sum',
            'CurrentCost': 'mean',
            'CurrentPrice': 'mean',
            'CurrentMargin%': 'mean',
            'ProductName': 'count'
        }).sort_values('Units_30Days', ascending=False)

        print(f"{'Product Line':<20} {'30-Day':<10} {'60-Day':<10} {'Avg Cost':<10} {'Avg Price':<10} {'Margin%':<8} {'SKUs':<5}")
        print("-"*120)
        for line, row in marl_lines.iterrows():
            if line:
                print(f"{line:<20} {int(row['Units_30Days']):<10,} {int(row['Units_60Days']):<10,} "
                      f"${row['CurrentCost']:<9.2f} ${row['CurrentPrice']:<9.2f} "
                      f"{row['CurrentMargin%']:<7.1f}% {int(row['ProductName']):<5}")

    # ABC Classification
    if 'ABC_Class' in items_df.columns:
        print("\n" + "="*120)
        print("ABC CLASSIFICATION BY REVENUE")
        print("="*120)

        abc_summary = items_df.groupby('ABC_Class').agg({
            'ProductName': 'count',
            'Units_60Days': 'sum',
            'Revenue_60Days': 'sum'
        })

        for cls in ['A', 'B', 'C']:
            if cls in abc_summary.index:
                row = abc_summary.loc[cls]
                revenue_pct = (row['Revenue_60Days'] / items_df['Revenue_60Days'].sum()) * 100
                print(f"Class {cls}: {int(row['ProductName'])} SKUs | "
                      f"{int(row['Units_60Days']):,} units | "
                      f"${row['Revenue_60Days']:,.2f} ({revenue_pct:.1f}% of revenue)")

    return items_df

if __name__ == "__main__":
    analyze_active_cigarettes()