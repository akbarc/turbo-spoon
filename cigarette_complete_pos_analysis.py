"""
Complete Cigarette POS Analysis with Tiers
Includes: Current prices, costs, sales history (1mo, 3mo, YTD, 2024),
last PO, price tiers, and comprehensive brand grouping
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def analyze_cigarette_pos_complete():
    """Complete analysis of all cigarettes in POS system"""

    db = SQLServerConnection()

    # Get all cigarette items with complete POS data and sales history
    query = """
    WITH CigaretteItems AS (
        SELECT
            i.ID as ItemID,
            i.Description as ProductName,
            i.ItemLookupCode as SKU,
            i.Cost as CurrentCost,
            i.LastCost,
            i.ReplacementCost,
            i.Price as CurrentPrice,
            i.PriceA,
            i.PriceB,
            i.PriceC,
            i.SalePrice,
            i.LastUpdated,
            i.LastSold,
            i.LastReceived,
            i.Quantity as OnHand,
            i.ReorderPoint,
            c.Name as Category,
            NULL as SupplierName,
            -- Brand extraction
            CASE
                WHEN i.Description LIKE 'NEWPORT%' THEN 'NEWPORT'
                WHEN i.Description LIKE 'MARL%' THEN 'MARLBORO'
                WHEN i.Description LIKE 'CAMEL%' THEN 'CAMEL'
                WHEN i.Description LIKE 'AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                WHEN i.Description LIKE 'WINSTON%' OR i.Description LIKE 'WINST%' THEN 'WINSTON'
                WHEN i.Description LIKE 'PALL MALL%' THEN 'PALL MALL'
                WHEN i.Description LIKE 'VIRGINIA SLIM%' OR i.Description LIKE 'VIRG SL%' THEN 'VIRGINIA SLIMS'
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
                WHEN i.Description LIKE 'BASIC%' THEN 'BASIC'
                WHEN i.Description LIKE 'CAPRI%' THEN 'CAPRI'
                WHEN i.Description LIKE 'CARLTON%' THEN 'CARLTON'
                WHEN i.Description LIKE 'CROWNS%' THEN 'CROWNS'
                WHEN i.Description LIKE 'LD%' THEN 'LD'
                WHEN i.Description LIKE 'SHIELD%' THEN 'SHIELD'
                WHEN i.Description LIKE 'TAJMAHAL%' THEN 'TAJMAHAL'
                WHEN i.Description LIKE 'TETON%' THEN 'TETON'
                WHEN i.Description LIKE 'VANTAGE%' THEN 'VANTAGE'
                WHEN i.Description LIKE 'WILDHORSE%' THEN 'WILDHORSE'
                WHEN i.Description LIKE 'B&H%' THEN 'B&H'
                WHEN i.Description LIKE 'FORTUNA%' THEN 'FORTUNA'
                WHEN i.Description LIKE 'RAVE%' THEN 'RAVE'
                ELSE SUBSTRING(i.Description, 1, CHARINDEX(' ', i.Description + ' ') - 1)
            END as Brand,
            -- Product type
            CASE
                WHEN i.Description LIKE '%MENTHOL%' THEN 'MENTHOL'
                WHEN i.Description LIKE '%CRUSH%' THEN 'CRUSH/CAPSULE'
                ELSE 'NON-MENTHOL'
            END as MentholType,
            CASE
                WHEN i.Description LIKE '%100%' THEN '100s'
                WHEN i.Description LIKE '%120%' THEN '120s'
                WHEN i.Description LIKE '%72%' THEN '72s'
                WHEN i.Description LIKE '%KING%' THEN 'KINGS'
                ELSE 'KINGS'
            END as Size
        FROM dbo.Item i
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE (
            UPPER(ISNULL(c.Name, '')) LIKE '%CIGARETTE%'
            OR UPPER(ISNULL(c.Name, '')) = 'CIGARETTES'
            OR UPPER(ISNULL(c.Name, '')) = 'TOBACCO'
            OR UPPER(i.Description) LIKE '%MARLBORO%'
            OR UPPER(i.Description) LIKE '%NEWPORT%'
            OR UPPER(i.Description) LIKE '%CAMEL%'
            OR UPPER(i.Description) LIKE '%WINSTON%'
            OR UPPER(i.Description) LIKE '%KOOL%'
            OR UPPER(i.Description) LIKE '%SALEM%'
            OR UPPER(i.Description) LIKE '%PALL MALL%'
            OR UPPER(i.Description) LIKE '%MAVERICK%'
            OR UPPER(i.Description) LIKE '%AMERICAN SPIRIT%'
            OR UPPER(i.Description) LIKE '%24/7%'
            OR UPPER(i.Description) LIKE '%305%'
            OR UPPER(i.Description) LIKE '%LUCKY STRIKE%'
        )
    ),
    SalesHistory AS (
        SELECT
            ci.ItemID,
            ci.ProductName,
            ci.SKU,
            ci.Brand,
            ci.MentholType,
            ci.Size,
            ci.Category,
            ci.SupplierName,
            ci.CurrentCost,
            ci.LastCost,
            ci.ReplacementCost,
            ci.CurrentPrice,
            ci.PriceA,
            ci.PriceB,
            ci.PriceC,
            ci.SalePrice,
            ci.OnHand,
            ci.ReorderPoint,
            ci.LastUpdated,
            ci.LastSold,
            ci.LastReceived,
            -- 1 Month Sales
            (SELECT SUM(te.Quantity) FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
               AND t.Time >= DATEADD(MONTH, -1, GETDATE())) as Units_1Month,
            -- 3 Month Sales
            (SELECT SUM(te.Quantity) FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
               AND t.Time >= DATEADD(MONTH, -3, GETDATE())) as Units_3Month,
            -- YTD Sales
            (SELECT SUM(te.Quantity) FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
               AND t.Time >= DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()), 0)) as Units_YTD,
            -- 2024 Total Sales
            (SELECT SUM(te.Quantity) FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
               AND YEAR(t.Time) = 2024) as Units_2024,
            -- Most recent selling price
            (SELECT TOP 1 te.Price FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
             ORDER BY t.Time DESC) as LastSellingPrice,
            -- Most recent sale date
            (SELECT TOP 1 t.Time FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
             ORDER BY t.Time DESC) as LastSaleDate,
            -- Average selling price (30 days)
            (SELECT AVG(te.Price) FROM dbo.TransactionEntry te
             JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
             WHERE te.ItemID = ci.ItemID
               AND t.Time >= DATEADD(DAY, -30, GETDATE())) as AvgPrice30Days,
            -- Last PO Info
            (SELECT TOP 1 po.PONumber FROM dbo.PurchaseOrder po
             JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
             WHERE poe.ItemID = ci.ItemID
             ORDER BY po.DateCreated DESC) as LastPONumber,
            (SELECT TOP 1 po.DateCreated FROM dbo.PurchaseOrder po
             JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
             WHERE poe.ItemID = ci.ItemID
             ORDER BY po.DateCreated DESC) as LastPODate,
            (SELECT TOP 1 poe.Price FROM dbo.PurchaseOrderEntry poe
             JOIN dbo.PurchaseOrder po ON po.ID = poe.PurchaseOrderID
             WHERE poe.ItemID = ci.ItemID
             ORDER BY po.DateCreated DESC) as LastPOCost
        FROM CigaretteItems ci
    )
    SELECT * FROM SalesHistory
    WHERE Units_1Month > 0 OR Units_3Month > 0 OR Units_YTD > 0 OR Units_2024 > 0 OR OnHand > 0
    ORDER BY Brand, CurrentPrice DESC, ProductName
    """

    print("Fetching complete cigarette POS data...")
    result = db.execute_query(query)

    if result is None or result.empty:
        print("No data found")
        return None

    # Convert decimal types to float
    numeric_columns = ['CurrentCost', 'LastCost', 'ReplacementCost', 'CurrentPrice', 'PriceA', 'PriceB', 'PriceC',
                       'SalePrice', 'OnHand', 'ReorderPoint', 'LastSellingPrice', 'AvgPrice30Days', 'LastPOCost']

    for col in numeric_columns:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce')

    # Handle integer columns
    int_columns = ['Units_1Month', 'Units_3Month', 'Units_YTD', 'Units_2024']
    for col in int_columns:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0).astype(int)

    # Calculate margins
    result['CurrentMargin%'] = ((result['CurrentPrice'] - result['CurrentCost']) / result['CurrentPrice'] * 100).round(1)
    result['LastSaleMargin%'] = ((result['LastSellingPrice'] - result['CurrentCost']) / result['LastSellingPrice'] * 100).round(1)

    # Define price tiers
    def assign_tier(price):
        if pd.isna(price):
            return 'NO PRICE'
        elif price < 30:
            return 'DEEP DISCOUNT (<$30)'
        elif price < 50:
            return 'DISCOUNT ($30-50)'
        elif price < 65:
            return 'VALUE ($50-65)'
        elif price < 75:
            return 'MID-TIER ($65-75)'
        elif price < 85:
            return 'PREMIUM ($75-85)'
        elif price < 95:
            return 'SUPER PREMIUM ($85-95)'
        else:
            return 'ULTRA PREMIUM ($95+)'

    result['PriceTier'] = result['CurrentPrice'].apply(assign_tier)

    # Identify sub-brands within major brands (like Marlboro)
    def get_sub_brand(desc, brand):
        if brand == 'MARLBORO':
            if 'BLACK' in desc or 'MIDNIGHT' in desc or 'NXT' in desc:
                return 'MARLBORO BLACK/SPECIAL'
            elif 'MENTHOL' in desc:
                return 'MARLBORO MENTHOL'
            elif '72' in desc:
                return 'MARLBORO 72s'
            else:
                return 'MARLBORO REGULAR'
        elif brand == 'NEWPORT':
            if 'NON' in desc and 'MENTHOL' in desc:
                return 'NEWPORT NON-MENTHOL'
            elif 'SOFT' in desc:
                return 'NEWPORT SOFT'
            else:
                return 'NEWPORT MENTHOL'
        elif brand == 'CAMEL':
            if 'CRUSH' in desc:
                return 'CAMEL CRUSH'
            elif 'TURKISH' in desc:
                return 'CAMEL TURKISH'
            else:
                return 'CAMEL REGULAR'
        else:
            return brand

    result['SubBrand'] = result.apply(lambda x: get_sub_brand(x['ProductName'], x['Brand']), axis=1)

    # Create tier groupings
    print("\nCreating brand tier analysis...")

    # Group by brand and sub-brand for summary
    brand_tiers = result.groupby(['Brand', 'SubBrand', 'PriceTier']).agg({
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

    # Flatten column names
    brand_tiers.columns = ['SKU_Count', 'Avg_Cost', 'Min_Cost', 'Max_Cost',
                           'Avg_Price', 'Min_Price', 'Max_Price',
                           'Units_1Mo', 'Units_3Mo', 'Units_YTD', 'Units_2024',
                           'Total_OnHand', 'Avg_Margin']

    # Save detailed data
    filename = f'cigarette_complete_pos_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    result.to_csv(filename, index=False)
    print(f"✅ Complete analysis saved to {filename}")

    # Save brand tier summary
    summary_filename = f'cigarette_brand_tier_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    brand_tiers.to_csv(summary_filename)
    print(f"✅ Brand tier summary saved to {summary_filename}")

    # Print top brands by volume
    print("\n" + "="*100)
    print("TOP BRANDS BY UNITS SOLD (1 MONTH)")
    print("="*100)

    brand_totals = result.groupby('Brand').agg({
        'Units_1Month': 'sum',
        'Units_3Month': 'sum',
        'Units_YTD': 'sum',
        'CurrentPrice': 'mean',
        'CurrentMargin%': 'mean'
    }).sort_values('Units_1Month', ascending=False).head(15)

    for brand, row in brand_totals.iterrows():
        print(f"{brand:20} | 1Mo: {int(row['Units_1Month']):7,} | 3Mo: {int(row['Units_3Month']):7,} | YTD: {int(row['Units_YTD']):7,} | Avg Price: ${row['CurrentPrice']:.2f} | Margin: {row['CurrentMargin%']:.1f}%")

    # Print price tier distribution
    print("\n" + "="*100)
    print("PRICE TIER DISTRIBUTION (BY UNITS - 1 MONTH)")
    print("="*100)

    tier_dist = result.groupby('PriceTier').agg({
        'Units_1Month': 'sum',
        'ProductName': 'count',
        'Brand': 'nunique'
    }).sort_values('Units_1Month', ascending=False)

    for tier, row in tier_dist.iterrows():
        print(f"{tier:25} | Units: {int(row['Units_1Month']):7,} | SKUs: {int(row['ProductName']):4} | Brands: {int(row['Brand']):3}")

    # Create detailed brand sheets
    print("\n" + "="*100)
    print("CREATING BRAND-SPECIFIC ANALYSIS FILES")
    print("="*100)

    for brand in result['Brand'].unique():
        if pd.notna(brand) and result[result['Brand'] == brand]['Units_1Month'].sum() > 100:
            brand_data = result[result['Brand'] == brand].copy()
            brand_data = brand_data.sort_values(['SubBrand', 'CurrentPrice', 'ProductName'])

            # Select relevant columns for brand sheet
            brand_sheet = brand_data[['ProductName', 'SKU', 'SubBrand', 'MentholType', 'Size',
                                      'CurrentCost', 'LastCost', 'CurrentPrice', 'PriceA', 'PriceB', 'PriceC',
                                      'LastSellingPrice', 'AvgPrice30Days',
                                      'Units_1Month', 'Units_3Month', 'Units_YTD', 'Units_2024',
                                      'OnHand', 'ReorderPoint', 'CurrentMargin%', 'PriceTier',
                                      'LastPONumber', 'LastPODate', 'LastPOCost',
                                      'LastSaleDate', 'LastReceived']].copy()

            brand_filename = f'{brand.replace("/", "_").replace(" ", "_")}_analysis_{datetime.now().strftime("%Y%m%d")}.csv'
            brand_sheet.to_csv(brand_filename, index=False)
            print(f"  ✅ {brand}: {len(brand_sheet)} SKUs saved to {brand_filename}")

    # Create pricing optimization report
    print("\n" + "="*100)
    print("PRICING ANOMALIES & OPPORTUNITIES")
    print("="*100)

    # Find items where last sale price differs significantly from current price
    price_changes = result[(abs(result['LastSellingPrice'] - result['CurrentPrice']) > 0.50) &
                           (result['Units_1Month'] > 0)].copy()

    if not price_changes.empty:
        print("\nItems with significant price differences:")
        for _, item in price_changes.head(10).iterrows():
            diff = item['LastSellingPrice'] - item['CurrentPrice']
            print(f"  {item['ProductName'][:40]:40} | Current: ${item['CurrentPrice']:.2f} | Last Sold: ${item['LastSellingPrice']:.2f} | Diff: ${diff:+.2f}")

    # Find low margin items with high volume
    low_margin_high_volume = result[(result['CurrentMargin%'] < 5) &
                                    (result['Units_1Month'] > 50)].copy()

    if not low_margin_high_volume.empty:
        print("\nHigh volume items with margins under 5%:")
        for _, item in low_margin_high_volume.head(10).iterrows():
            print(f"  {item['ProductName'][:40]:40} | Units: {item['Units_1Month']:5} | Margin: {item['CurrentMargin%']:.1f}% | Price: ${item['CurrentPrice']:.2f}")

    return result, brand_tiers

if __name__ == "__main__":
    analyze_cigarette_pos_complete()