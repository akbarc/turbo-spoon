"""
Cigarette Brand Price Comparison Analysis
Matches actual sales data with HT new pricing
"""

from database_pymssql import SQLServerConnection
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# HT New Pricing structure provided
HT_PRICING = {
    '24-7': 28.94,
    'AMERICAN SPIRIT': 89.96,
    'AMERICAN SPIRIT ORG': 94.76,
    'B&H': 106.65,
    'BASIC': 60.81,
    'CAMEL': 83.58,
    'CAMEL NO RETAIL SUPPORT': 94.41,
    'CAMEL REG': 120.60,
    'CAPRI': 120.60,
    'CARLTON': 120.60,
    'CROWN': 33.20,
    'DORAL': 103.56,
    'EAGLE 20S': 58.15,
    'EDGEFIELD': 37.30,
    'FORTUNA': 79.56,
    'KOOL': 81.52,
    'L&M': 78.47,
    'LD': 34.97,
    'LUCKYSTRIKE': 58.49,
    'MARLBORO': 79.48,  # Will need to handle multiple Marlboro prices
    'MARLBORO_PREMIUM': 82.91,
    'MARLBORO_VALUE': 75.07,
    'MAVERICK': 63.00,
    'MISTY': 100.50,
    'MONTEGO': 39.50,
    'NEWPORT': 88.53,
    'NEWPORT SOFT': 83.53,
    'NEWPORT NON MENTHOL': 78.93,
    'PALL MALL': 77.56,
    'PARLIAMENT': 94.93,
    'PYRAMID': 66.73,
    'RAVE': 79.56,
    'SALEM': 94.36,
    'SENECA': 31.19,
    'VA SLIM': 94.83,
    'VANTAGE': 120.60,
    'WINSTON': 80.83
}

def normalize_brand_name(product_name):
    """Extract and normalize brand name from product description"""

    product_upper = product_name.upper()

    # Special handling for specific brands
    if 'NEWPORT' in product_upper:
        if 'SOFT' in product_upper:
            return 'NEWPORT SOFT'
        elif 'NON' in product_upper and 'MENTHOL' in product_upper:
            return 'NEWPORT NON MENTHOL'
        else:
            return 'NEWPORT'

    elif 'MARL' in product_upper:
        # Determine Marlboro tier based on product name and cost
        if any(x in product_upper for x in ['BLACK', 'NXT', 'SMOOTH', 'SLATE']):
            return 'MARLBORO_VALUE'
        elif any(x in product_upper for x in ['RED', 'GOLD', 'SILVER', 'MENTHOL', 'GREEN']):
            return 'MARLBORO'
        else:
            return 'MARLBORO_PREMIUM'

    elif 'AMERICAN SPIRIT' in product_upper:
        if 'ORG' in product_upper or 'ORGANIC' in product_upper:
            return 'AMERICAN SPIRIT ORG'
        else:
            return 'AMERICAN SPIRIT'

    elif 'CAMEL' in product_upper:
        if 'NO RETAIL' in product_upper:
            return 'CAMEL NO RETAIL SUPPORT'
        elif 'REG' in product_upper:
            return 'CAMEL REG'
        else:
            return 'CAMEL'

    elif 'EAGLE' in product_upper:
        return 'EAGLE 20S'

    elif '24/7' in product_upper or '24-7' in product_upper:
        return '24-7'

    elif 'VIRGINIA SLIM' in product_upper or 'VA SLIM' in product_upper:
        return 'VA SLIM'

    elif 'LUCKY' in product_upper and 'STRIKE' in product_upper:
        return 'LUCKYSTRIKE'

    elif 'PALL MALL' in product_upper:
        return 'PALL MALL'

    elif 'L&M' in product_upper or 'L & M' in product_upper:
        return 'L&M'

    elif 'B&H' in product_upper or 'BENSON' in product_upper:
        return 'B&H'

    elif 'CROWN' in product_upper and 'CROWN' not in ['CROWNS']:
        return 'CROWN'

    # Standard brand mappings
    brand_checks = [
        'BASIC', 'CAPRI', 'CARLTON', 'DORAL', 'EDGEFIELD', 'FORTUNA',
        'KOOL', 'LD', 'MAVERICK', 'MISTY', 'MONTEGO', 'PARLIAMENT',
        'PYRAMID', 'RAVE', 'SALEM', 'SENECA', 'VANTAGE', 'WINSTON'
    ]

    for brand in brand_checks:
        if brand in product_upper:
            return brand

    return 'OTHER'

def get_brand_comparison_data():
    """Get sales data and compare with HT pricing"""

    db = SQLServerConnection()

    # Comprehensive query for all cigarette sales
    query = """
    WITH CigaretteSales AS (
        SELECT
            i.Description as ProductName,
            i.ItemLookupCode as SKU,
            i.Cost as CurrentCost,
            i.SalePrice as ListPrice,
            COUNT(DISTINCT te.TransactionNumber) as Transactions,
            SUM(te.Quantity) as UnitsSold,
            AVG(te.Price) as AvgSellingPrice,
            MIN(te.Price) as MinPrice,
            MAX(te.Price) as MaxPrice,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM dbo.Item i
        JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
        JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
            AND (
                UPPER(i.Description) LIKE '%CIGARETTE%'
                OR UPPER(i.Description) LIKE '%MARLBORO%'
                OR UPPER(i.Description) LIKE '%MARL %'
                OR UPPER(i.Description) LIKE '%NEWPORT%'
                OR UPPER(i.Description) LIKE '%CAMEL%'
                OR UPPER(i.Description) LIKE '%AMERICAN SPIRIT%'
                OR UPPER(i.Description) LIKE '%WINSTON%'
                OR UPPER(i.Description) LIKE '%PALL MALL%'
                OR UPPER(i.Description) LIKE '%VIRGINIA SLIM%'
                OR UPPER(i.Description) LIKE '%KOOL%'
                OR UPPER(i.Description) LIKE '%SALEM%'
                OR UPPER(i.Description) LIKE '%PARLIAMENT%'
                OR UPPER(i.Description) LIKE '%LUCKY%'
                OR UPPER(i.Description) LIKE '%MAVERICK%'
                OR UPPER(i.Description) LIKE '%EAGLE%'
                OR UPPER(i.Description) LIKE '%PYRAMID%'
                OR UPPER(i.Description) LIKE '%SENECA%'
                OR UPPER(i.Description) LIKE '%DORAL%'
                OR UPPER(i.Description) LIKE '%MISTY%'
                OR UPPER(i.Description) LIKE '%MONTEGO%'
                OR UPPER(i.Description) LIKE '%305%'
                OR UPPER(i.Description) LIKE '%LIGGETT%'
                OR UPPER(i.Description) LIKE '%24/7%'
                OR UPPER(i.Description) LIKE '%24-7%'
                OR UPPER(i.Description) LIKE '%L&M%'
                OR UPPER(i.Description) LIKE '%L & M%'
                OR UPPER(i.Description) LIKE '%BASIC%'
                OR UPPER(i.Description) LIKE '%USA GOLD%'
                OR UPPER(i.Description) LIKE '%SONOMA%'
                OR UPPER(i.Description) LIKE '%WAVE%'
                OR UPPER(i.Description) LIKE '%TIMELESS%'
                OR UPPER(i.Description) LIKE '%CROWN%'
                OR UPPER(i.Description) LIKE '%CAPRI%'
                OR UPPER(i.Description) LIKE '%CARLTON%'
                OR UPPER(i.Description) LIKE '%EDGEFIELD%'
                OR UPPER(i.Description) LIKE '%FORTUNA%'
                OR UPPER(i.Description) LIKE '%LD%'
                OR UPPER(i.Description) LIKE '%RAVE%'
                OR UPPER(i.Description) LIKE '%VANTAGE%'
                OR UPPER(i.Description) LIKE '%B&H%'
                OR UPPER(i.Description) LIKE '%BENSON%'
                OR UPPER(c.Name) LIKE '%CIGARETTE%'
                OR UPPER(c.Name) LIKE '%TOBACCO%'
            )
        GROUP BY i.Description, i.ItemLookupCode, i.Cost, i.SalePrice
    )
    SELECT * FROM CigaretteSales
    WHERE UnitsSold > 0
    ORDER BY UnitsSold DESC
    """

    print("Fetching cigarette sales data...")
    result = db.execute_query(query)

    if result is None or result.empty:
        print("No data found")
        return None

    # Convert Decimal types
    for col in ['CurrentCost', 'ListPrice', 'AvgSellingPrice', 'MinPrice', 'MaxPrice',
                'TotalRevenue', 'GrossProfit']:
        if col in result.columns:
            result[col] = result[col].astype(float)

    # Normalize brand names
    result['Brand_Normalized'] = result['ProductName'].apply(normalize_brand_name)

    # Map HT prices
    result['HT_New_Price'] = result['Brand_Normalized'].map(HT_PRICING)

    # Calculate price differences
    result['Price_Diff_From_HT'] = result['AvgSellingPrice'] - result['HT_New_Price']
    result['Price_Diff_Pct'] = ((result['AvgSellingPrice'] - result['HT_New_Price']) /
                                 result['HT_New_Price'] * 100).round(1)

    # Group by brand for summary
    brand_summary = result.groupby('Brand_Normalized').agg({
        'SKU': 'count',
        'UnitsSold': 'sum',
        'CurrentCost': 'mean',
        'AvgSellingPrice': 'mean',
        'MinPrice': 'min',
        'MaxPrice': 'max',
        'TotalRevenue': 'sum',
        'GrossProfit': 'sum',
        'HT_New_Price': 'first'
    }).round(2)

    brand_summary['Margin_%'] = (brand_summary['GrossProfit'] /
                                 brand_summary['TotalRevenue'] * 100).round(1)

    # Calculate difference from HT pricing
    brand_summary['Current_vs_HT_Price'] = (brand_summary['AvgSellingPrice'] -
                                           brand_summary['HT_New_Price']).round(2)
    brand_summary['Current_vs_HT_%'] = ((brand_summary['AvgSellingPrice'] -
                                        brand_summary['HT_New_Price']) /
                                        brand_summary['HT_New_Price'] * 100).round(1)

    # Sort by units sold
    brand_summary = brand_summary.sort_values('UnitsSold', ascending=False)

    # Create output in requested format
    output_data = []

    # Process each brand in HT pricing list
    for ht_brand in sorted(set(HT_PRICING.keys())):
        if ht_brand in ['MARLBORO_PREMIUM', 'MARLBORO_VALUE']:
            continue  # Skip duplicate Marlboro entries

        ht_price = HT_PRICING[ht_brand]

        if ht_brand in brand_summary.index:
            row = brand_summary.loc[ht_brand]
            output_data.append({
                'BRAND': ht_brand,
                'HT_NEW_PRICE': ht_price,
                'CURRENT_AVG_SELLING': row['AvgSellingPrice'],
                'CURRENT_COST': row['CurrentCost'],
                'UNITS_SOLD_30D': int(row['UnitsSold']),
                'NUM_SKUS': int(row['SKU']),
                'MIN_PRICE': row['MinPrice'],
                'MAX_PRICE': row['MaxPrice'],
                'PRICE_DIFF': row['Current_vs_HT_Price'],
                'DIFF_%': row['Current_vs_HT_%'],
                'MARGIN_%': row['Margin_%'],
                'TOTAL_REVENUE': row['TotalRevenue']
            })
        else:
            # Brand in HT list but no sales
            output_data.append({
                'BRAND': ht_brand,
                'HT_NEW_PRICE': ht_price,
                'CURRENT_AVG_SELLING': 0,
                'CURRENT_COST': 0,
                'UNITS_SOLD_30D': 0,
                'NUM_SKUS': 0,
                'MIN_PRICE': 0,
                'MAX_PRICE': 0,
                'PRICE_DIFF': 0,
                'DIFF_%': 0,
                'MARGIN_%': 0,
                'TOTAL_REVENUE': 0
            })

    # Create DataFrame
    output_df = pd.DataFrame(output_data)

    # Sort by units sold
    output_df = output_df.sort_values('UNITS_SOLD_30D', ascending=False)

    # Save files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Main comparison file
    filename1 = f'cigarette_brand_ht_price_comparison_{timestamp}.csv'
    output_df.to_csv(filename1, index=False)
    print(f"\n✅ Brand price comparison saved to {filename1}")

    # Detailed SKU-level comparison
    detail_df = result[['ProductName', 'Brand_Normalized', 'SKU', 'UnitsSold',
                        'CurrentCost', 'AvgSellingPrice', 'HT_New_Price',
                        'Price_Diff_From_HT', 'Price_Diff_Pct', 'TotalRevenue']].copy()
    detail_df = detail_df.sort_values(['Brand_Normalized', 'UnitsSold'], ascending=[True, False])

    filename2 = f'cigarette_sku_ht_comparison_{timestamp}.csv'
    detail_df.to_csv(filename2, index=False)
    print(f"✅ SKU-level comparison saved to {filename2}")

    # Print summary
    print("\n" + "="*80)
    print("CIGARETTE BRAND PRICE COMPARISON - HT NEW PRICING")
    print("="*80)

    print("\n📊 BRANDS WITH SIGNIFICANT VOLUME (>1000 units):")
    print("-"*80)
    print(f"{'BRAND':<25} {'HT PRICE':>10} {'CURRENT':>10} {'DIFF':>8} {'UNITS':>10} {'MARGIN%':>8}")
    print("-"*80)

    for _, row in output_df[output_df['UNITS_SOLD_30D'] > 1000].iterrows():
        diff_indicator = '↑' if row['PRICE_DIFF'] > 0 else '↓' if row['PRICE_DIFF'] < 0 else '='
        print(f"{row['BRAND']:<25} ${row['HT_NEW_PRICE']:>9.2f} ${row['CURRENT_AVG_SELLING']:>9.2f} "
              f"{diff_indicator}{abs(row['PRICE_DIFF']):>6.2f} {row['UNITS_SOLD_30D']:>10,} {row['MARGIN_%']:>7.1f}%")

    print("\n🔴 BRANDS WITH NO CURRENT SALES:")
    print("-"*80)
    no_sales = output_df[output_df['UNITS_SOLD_30D'] == 0]['BRAND'].tolist()
    if no_sales:
        for brand in no_sales:
            print(f"  • {brand} (HT Price: ${HT_PRICING.get(brand, 0):.2f})")
    else:
        print("  All brands have sales activity")

    print("\n💡 KEY INSIGHTS:")
    print("-"*80)

    # Brands selling above HT price
    above_ht = output_df[(output_df['PRICE_DIFF'] > 0) & (output_df['UNITS_SOLD_30D'] > 0)]
    if not above_ht.empty:
        print(f"• {len(above_ht)} brands selling ABOVE HT pricing")
        top_over = above_ht.nlargest(3, 'PRICE_DIFF')
        for _, row in top_over.iterrows():
            print(f"    - {row['BRAND']}: +${row['PRICE_DIFF']:.2f} ({row['DIFF_%']:+.1f}%)")

    # Brands selling below HT price
    below_ht = output_df[(output_df['PRICE_DIFF'] < 0) & (output_df['UNITS_SOLD_30D'] > 0)]
    if not below_ht.empty:
        print(f"\n• {len(below_ht)} brands selling BELOW HT pricing")
        top_under = below_ht.nsmallest(3, 'PRICE_DIFF')
        for _, row in top_under.iterrows():
            print(f"    - {row['BRAND']}: ${row['PRICE_DIFF']:.2f} ({row['DIFF_%']:.1f}%)")

    print("\n✅ Analysis complete!")

    return output_df

if __name__ == "__main__":
    get_brand_comparison_data()