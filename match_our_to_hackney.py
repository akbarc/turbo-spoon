#!/usr/bin/env python3
"""
Match OUR cigarette inventory to Hackney's catalog
Go through each of OUR products and find the matching Hackney SKU
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import re

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

def extract_brand_from_name(name):
    """Extract brand from product name"""
    name_upper = str(name).upper()

    brands = [
        'MARLBORO', 'NEWPORT', 'CAMEL', 'PALL MALL', 'WINSTON', 'SALEM', 'KOOL',
        'L&M', 'L & M', 'BASIC', 'AMERICAN SPIRIT', 'VIRGINIA SLIMS', 'PARLIAMENT',
        'MERIT', 'DORAL', 'MISTY', 'CAPRI', 'CARLTON', 'EAGLE 20', 'PYRAMID',
        'MONTEGO', 'SONOMA', 'USA GOLD', 'CROWN', 'FORTUNA', 'MAVERICK', 'RAVE',
        'LD', 'L.D', 'EVE', 'SENECA', '305', 'EDGEFIELD', 'RED KAMEL', 'LUCKY STRIKE',
        'BENSON', 'B&H', '24/7', 'CHESTERFIELD', 'DUNHILL', 'KENT', 'KAMEL RED',
        'MORE', 'NAT AM SPIRIT', 'VANTAGE', 'MONTCLAIR'
    ]

    for brand in brands:
        if brand in name_upper:
            # Normalize some brands
            if brand in ['L&M', 'L & M']:
                return 'L&M'
            elif brand in ['BENSON', 'B&H']:
                return 'BENSON & HEDGES'
            elif brand in ['LD', 'L.D']:
                return 'LD'
            elif brand == 'LUCKY STRIKE':
                return 'LUCKY STRIKE'
            elif brand == 'AMERICAN SPIRIT':
                return 'AMERICAN SPIRIT'
            elif brand == 'NAT AM SPIRIT':
                return 'AMERICAN SPIRIT'
            elif brand == 'RED KAMEL':
                return 'KAMEL RED'
            elif brand == 'EAGLE 20':
                return 'EAGLE 20S'
            elif brand == '305':
                return '305S'
            else:
                return brand

    return 'UNKNOWN'

def find_hackney_match_ai(our_product, hackney_products_same_brand):
    """Use AI to find the best Hackney match for our product"""

    if len(hackney_products_same_brand) == 0:
        return {'matched': False, 'reason': 'No Hackney products in same brand'}

    try:
        # Create list of Hackney products
        hackney_list = "\n".join([
            f"{i+1}. {p['description']} (Item: {p['item']})"
            for i, p in enumerate(hackney_products_same_brand[:30])
        ])

        prompt = f"""Match our cigarette product to the correct Hackney product.

OUR PRODUCT: {our_product['name']}
OUR UPC: {our_product['barcode']}

HACKNEY PRODUCTS (same brand):
{hackney_list}

Return JSON with:
- "match_number": number (1-{min(30, len(hackney_products_same_brand))}) of the matching product, or null if no match
- "confidence": "exact" (perfect match), "high" (very confident), "medium" (likely match), "low" (uncertain), or "none" (no match)
- "reason": brief explanation

Only return JSON, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a cigarette product matching expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')
        confidence = result.get('confidence', 'none')

        if match_num and 1 <= match_num <= len(hackney_products_same_brand):
            matched_product = hackney_products_same_brand[match_num - 1]
            return {
                'matched': True,
                'hackney_product': matched_product,
                'confidence': confidence,
                'reason': result.get('reason', '')
            }
        else:
            return {
                'matched': False,
                'confidence': 'none',
                'reason': result.get('reason', 'No good match found')
            }

    except Exception as e:
        return {
            'matched': False,
            'confidence': 'error',
            'reason': f'Error: {str(e)}'
        }

def main():
    print("="*100)
    print("MATCH OUR INVENTORY TO HACKNEY CATALOG")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    print("📂 Loading files...")
    df_our = pd.read_excel('cigarette_inventory_export_20251022_171837.xlsx', sheet_name='Cigarette_Inventory')
    df_hackney = pd.read_excel('/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx', sheet_name='HACKNEY')

    print(f"✅ Our inventory: {len(df_our)} products")
    print(f"✅ Hackney catalog: {len(df_hackney)} products")

    # Extract brands
    print("\n🏷️  Extracting brands...")
    df_our['Brand'] = df_our['Name'].apply(extract_brand_from_name)
    df_hackney['Brand'] = df_hackney['Description'].apply(extract_brand_from_name)

    our_brands = df_our['Brand'].value_counts()
    hackney_brands = df_hackney['Brand'].value_counts()

    print(f"   Our brands: {len(our_brands)}")
    print(f"   Hackney brands: {len(hackney_brands)}")

    # Show brand breakdown
    print(f"\n   Top 10 brands in our inventory:")
    for brand, count in our_brands.head(10).items():
        hackney_count = hackney_brands.get(brand, 0)
        print(f"      {brand:20s}: {count:3d} ours | {hackney_count:3d} Hackney")

    # Prepare Hackney products by brand
    hackney_by_brand = {}
    for idx, row in df_hackney.iterrows():
        brand = row['Brand']
        if brand not in hackney_by_brand:
            hackney_by_brand[brand] = []
        hackney_by_brand[brand].append({
            'item': row['Item'],
            'description': row['Description'],
            'upc': row['Retail UPC'],
            'price': row['Price'],
            'qty_on_hand': row[' Quantity on Hand']
        })

    # Match each of our products
    print(f"\n🤖 Matching each of our {len(df_our)} products to Hackney catalog...")
    print(f"   Using AI with brand segmentation for accuracy")
    print()

    matches = []
    completed = 0
    start_time = time.time()

    def match_one_product(row):
        our_product = {
            'name': row['Name'],
            'barcode': row['Barcode'],
            'brand': row['Brand'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D']
        }

        # Get Hackney products for same brand
        hackney_same_brand = hackney_by_brand.get(our_product['brand'], [])

        # Try to find match
        result = find_hackney_match_ai(our_product, hackney_same_brand)

        if result['matched']:
            hackney = result['hackney_product']
            return {
                'Our_Name': our_product['name'],
                'Our_Barcode': our_product['barcode'],
                'Our_Brand': our_product['brand'],
                'Our_Cost': our_product['cost'],
                'Our_CurrentPrice': our_product['price'],
                'Our_CurrentStock': our_product['stock'],
                'Our_TotalSold30D': our_product['sold_30d'],
                'Hackney_Item': hackney['item'],
                'Hackney_Description': hackney['description'],
                'Hackney_UPC': hackney['upc'],
                'Hackney_Price': hackney['price'],
                'Hackney_QtyOnHand': hackney['qty_on_hand'],
                'Match_Confidence': result['confidence'],
                'Match_Reason': result['reason']
            }
        else:
            return {
                'Our_Name': our_product['name'],
                'Our_Barcode': our_product['barcode'],
                'Our_Brand': our_product['brand'],
                'Our_Cost': our_product['cost'],
                'Our_CurrentPrice': our_product['price'],
                'Our_CurrentStock': our_product['stock'],
                'Our_TotalSold30D': our_product['sold_30d'],
                'Hackney_Item': None,
                'Hackney_Description': None,
                'Hackney_UPC': None,
                'Hackney_Price': None,
                'Hackney_QtyOnHand': None,
                'Match_Confidence': result.get('confidence', 'none'),
                'Match_Reason': result.get('reason', '')
            }

    # Process with parallel workers
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(match_one_product, row): idx for idx, row in df_our.iterrows()}

        for future in as_completed(futures):
            result = future.result()
            matches.append(result)
            completed += 1

            if completed % 25 == 0 or completed == len(df_our):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                matched_count = sum(1 for m in matches if m['Hackney_Item'] is not None)
                print(f"   Progress: {completed}/{len(df_our)} ({completed/len(df_our)*100:.1f}%) | Matched: {matched_count} | Rate: {rate:.1f}/sec")

    # Create dataframe
    df_results = pd.DataFrame(matches)

    # Analyze results
    matched = df_results['Hackney_Item'].notna()
    total_matched = matched.sum()

    print(f"\n📊 FINAL RESULTS:")
    print(f"   Our products: {len(df_our)}")
    print(f"   Matched to Hackney: {total_matched} ({total_matched/len(df_our)*100:.1f}%)")
    print(f"   Not matched: {len(df_our) - total_matched} ({(len(df_our) - total_matched)/len(df_our)*100:.1f}%)")

    # Confidence breakdown
    if total_matched > 0:
        print(f"\n   Match confidence breakdown:")
        conf_counts = df_results[matched]['Match_Confidence'].value_counts()
        for conf, count in conf_counts.items():
            print(f"      {conf}: {count}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'our_to_hackney_mapping_{timestamp}.xlsx'

    print(f"\n💾 Saving results: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # All products
        df_results.to_excel(writer, sheet_name='All_Our_Products', index=False)

        # Matched only
        df_matched = df_results[matched].copy()
        if len(df_matched) > 0:
            df_matched.to_excel(writer, sheet_name='Matched', index=False)

        # High confidence matches
        high_conf = df_results[matched & (df_results['Match_Confidence'].isin(['exact', 'high']))].copy()
        if len(high_conf) > 0:
            high_conf.to_excel(writer, sheet_name='High_Confidence', index=False)

        # Not matched
        df_unmatched = df_results[~matched].copy()
        if len(df_unmatched) > 0:
            df_unmatched.to_excel(writer, sheet_name='Not_Matched', index=False)

        # By brand summary
        brand_summary = df_results.groupby('Our_Brand').agg({
            'Our_Name': 'count',
            'Hackney_Item': lambda x: x.notna().sum()
        })
        brand_summary.columns = ['Total_Products', 'Matched']
        brand_summary['Match_Rate'] = (brand_summary['Matched'] / brand_summary['Total_Products'] * 100).round(1)
        brand_summary = brand_summary.sort_values('Total_Products', ascending=False)
        brand_summary.to_excel(writer, sheet_name='By_Brand_Summary')

    print(f"\n✅ Export complete!")
    print(f"\nFile: {output_file}")

    # Show samples
    if total_matched > 0:
        print(f"\n📋 Sample matches (first 15):")
        for idx, row in df_matched.head(15).iterrows():
            conf = row['Match_Confidence']
            print(f"\n  {row['Our_Name'][:50]:50s}")
            print(f"  -> {row['Hackney_Description'][:50]:50s} (Hackney #{row['Hackney_Item']}) [{conf}]")

    # Show brand summary
    print(f"\n📊 By Brand Summary:")
    for brand, data in brand_summary.head(15).iterrows():
        print(f"   {brand:20s}: {int(data['Matched'])}/{int(data['Total_Products'])} matched ({data['Match_Rate']:.1f}%)")

if __name__ == "__main__":
    main()
