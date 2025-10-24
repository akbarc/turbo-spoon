#!/usr/bin/env python3
"""
UPC-verified matching:
1. Extract brand with AI
2. Filter Hackney by UPC prefix (first 5-8 digits = manufacturer)
3. Use AI for final matching within UPC-verified candidates
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
from collections import defaultdict

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

def get_upc_prefix(upc, length=5):
    """Extract UPC prefix (manufacturer code)"""
    upc_str = str(upc).strip()
    if len(upc_str) >= length:
        return upc_str[:length]
    return None

def extract_brand_with_ai(product_name):
    """Use AI to extract brand"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Extract cigarette brand. Return JSON with 'brand' (MARLBORO, NEWPORT, CAMEL, etc.)."
                },
                {"role": "user", "content": f"Brand from: {product_name}"}
            ]
        )
        result = json.loads(response.choices[0].message.content)
        return result.get('brand', 'UNKNOWN').upper()
    except:
        return 'UNKNOWN'

def filter_by_upc_prefix(our_upc, hackney_products, prefix_lengths=[5, 6, 7, 8]):
    """Filter Hackney products by matching UPC prefix"""
    if not our_upc or str(our_upc) == 'nan':
        return hackney_products

    our_upc_str = str(our_upc).strip()
    if len(our_upc_str) < 5:
        return hackney_products

    # Try different prefix lengths (5, 6, 7, 8 digits)
    for prefix_len in prefix_lengths:
        our_prefix = get_upc_prefix(our_upc, prefix_len)
        if not our_prefix:
            continue

        matches = []
        for product in hackney_products:
            hackney_upc = str(product['upc']).strip()
            if len(hackney_upc) >= prefix_len:
                hackney_prefix = hackney_upc[:prefix_len]
                if our_prefix == hackney_prefix:
                    matches.append(product)

        # If we found matches with this prefix length, use them
        if matches:
            return matches

    # No UPC matches - return all products in brand (fallback)
    return hackney_products

def extract_keywords(product_name):
    """Extract variant keywords"""
    name_upper = product_name.upper()
    keywords = []

    variants = ['GOLD', 'SILVER', 'RED', 'BLUE', 'GREEN', 'BLACK', 'ORANGE',
                'MENTHOL', 'MEN', 'SMOOTH', 'BOLD', 'NXT', 'ICE', 'CRUSH',
                'EDGE', 'LABEL', 'SELECT', 'SLATE', 'MIDNIGHT', 'SPECIAL']

    for variant in variants:
        if variant in name_upper:
            keywords.append(variant)

    if '100' in name_upper:
        keywords.append('100')
    elif '72' in name_upper:
        keywords.append('72')
    elif 'KING' in name_upper:
        keywords.append('KING')

    if 'BOX' in name_upper:
        keywords.append('BOX')
    elif 'SOFT' in name_upper:
        keywords.append('SOFT')

    return keywords

def score_keyword_match(our_keywords, hackney_desc):
    """Score how well Hackney product matches our keywords"""
    hackney_upper = hackney_desc.upper()
    hackney_keywords = extract_keywords(hackney_desc)

    # Count matching keywords
    matches = sum(1 for kw in our_keywords if kw in hackney_upper)

    # Penalize extra keywords Hackney has that we don't
    extra = sum(1 for kw in hackney_keywords if kw not in our_keywords)

    return matches - (extra * 0.5)

def find_match_with_upc_and_ai(our_product, hackney_by_brand):
    """Match using UPC prefix + keyword filtering + AI"""

    brand = our_product['brand']
    hackney_all = hackney_by_brand.get(brand, [])

    if not hackney_all:
        return {
            'matched': False,
            'reason': f'No Hackney products for brand {brand}',
            'method': 'no_brand'
        }

    # Step 1: Filter by UPC prefix
    hackney_upc_filtered = filter_by_upc_prefix(our_product['barcode'], hackney_all)

    upc_filter_used = len(hackney_upc_filtered) < len(hackney_all)

    # Step 2: Score by keyword match
    our_keywords = extract_keywords(our_product['name'])

    scored = []
    for product in hackney_upc_filtered:
        score = score_keyword_match(our_keywords, product['description'])
        scored.append((score, product))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top 20 candidates
    top_candidates = [p for score, p in scored[:20]]

    if not top_candidates:
        return {
            'matched': False,
            'reason': 'No candidates after UPC and keyword filtering',
            'method': 'no_candidates'
        }

    # Step 3: Use AI for final matching
    try:
        candidates_list = "\n".join([
            f"{i+1}. {p['description']}"
            for i, p in enumerate(top_candidates)
        ])

        prompt = f"""Match cigarette products. UPC prefixes already verified to be same manufacturer.

OUR PRODUCT: {our_product['name']}
OUR UPC: {our_product['barcode']}

HACKNEY CANDIDATES (same manufacturer by UPC prefix):
{candidates_list}

RULES:
- UPC prefix match means SAME MANUFACTURER
- "MARL" = "MARLBORO" (abbreviation OK)
- "MEN" = "MENTHOL" (abbreviation OK)
- Ignore "10CT" (our pack size)
- "GOLD" ≠ "BLACK GOLD" (different products)
- "100" ≠ "KING" (different sizes)

Return JSON:
- "match_number": 1-{len(top_candidates)} or null
- "confidence": "exact"/"high"/"medium"/"none"
- "reason": brief explanation

Be confident if UPC prefix matches AND product description matches."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Cigarette matcher. UPC prefix = same manufacturer. Return JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')
        confidence = result.get('confidence', 'none')

        if match_num and 1 <= match_num <= len(top_candidates) and confidence in ['exact', 'high']:
            matched = top_candidates[match_num - 1]

            method = 'upc_ai' if upc_filter_used else 'keyword_ai'

            return {
                'matched': True,
                'hackney_product': matched,
                'confidence': confidence,
                'reason': result.get('reason', ''),
                'method': method
            }
        else:
            return {
                'matched': False,
                'confidence': confidence,
                'reason': result.get('reason', 'No confident match'),
                'method': 'ai_rejected'
            }

    except Exception as e:
        return {
            'matched': False,
            'confidence': 'error',
            'reason': f'Error: {str(e)}',
            'method': 'error'
        }

def main():
    print("="*100)
    print("UPC-VERIFIED MATCHING")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    print("📂 Loading files...")
    df_our = pd.read_excel('cigarette_inventory_export_20251022_171837.xlsx', sheet_name='Cigarette_Inventory')
    df_hackney = pd.read_excel('/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx', sheet_name='HACKNEY')

    print(f"✅ Our inventory: {len(df_our)} products")
    print(f"✅ Hackney catalog: {len(df_hackney)} products")

    # Extract brands
    print(f"\n🤖 Extracting brands...")

    our_brands = {}
    hackney_brands = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for idx, row in df_our.iterrows():
            futures.append((executor.submit(extract_brand_with_ai, row['Name']), 'our', row['Name']))

        for idx, row in df_hackney.iterrows():
            futures.append((executor.submit(extract_brand_with_ai, row['Description']), 'hackney', row['Description']))

        for future, source, name in futures:
            brand = future.result()
            if source == 'our':
                our_brands[name] = brand
            else:
                hackney_brands[name] = brand

            completed += 1
            if completed % 200 == 0:
                print(f"   Progress: {completed}/{len(futures)}")

    df_our['AI_Brand'] = df_our['Name'].map(our_brands)
    df_hackney['AI_Brand'] = df_hackney['Description'].map(hackney_brands)

    print(f"✅ Brand extraction complete")

    # Analyze UPC prefixes
    print(f"\n📊 Analyzing UPC prefixes...")

    # Group by brand and show UPC prefixes
    brand_upcs = defaultdict(set)
    for idx, row in df_our.iterrows():
        brand = row['AI_Brand']
        upc_prefix = get_upc_prefix(row['Barcode'], 5)
        if upc_prefix:
            brand_upcs[brand].add(upc_prefix)

    print(f"   Top brands and their UPC prefixes:")
    for brand in ['MARLBORO', 'NEWPORT', 'CAMEL', 'PALL MALL', 'WINSTON']:
        if brand in brand_upcs:
            prefixes = sorted(brand_upcs[brand])
            print(f"      {brand:20s}: {', '.join(prefixes)}")

    # Organize Hackney by brand
    hackney_by_brand = {}
    for idx, row in df_hackney.iterrows():
        brand = row['AI_Brand']
        if brand not in hackney_by_brand:
            hackney_by_brand[brand] = []
        hackney_by_brand[brand].append({
            'item': row['Item'],
            'description': row['Description'],
            'upc': row['Retail UPC'],
            'price': row['Price'],
            'qty_on_hand': row[' Quantity on Hand']
        })

    # Match with UPC verification
    print(f"\n🤖 Matching with UPC prefix verification...")
    print()

    matches = []
    completed = 0
    start_time = time.time()

    def match_one(row):
        our_product = {
            'name': row['Name'],
            'barcode': row['Barcode'],
            'brand': row['AI_Brand'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D']
        }

        result = find_match_with_upc_and_ai(our_product, hackney_by_brand)

        if result['matched']:
            hackney = result['hackney_product']
            return {
                'Our_Name': our_product['name'],
                'Our_Barcode': our_product['barcode'],
                'Our_AI_Brand': our_product['brand'],
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
                'Match_Method': result['method'],
                'Match_Reason': result['reason']
            }
        else:
            return {
                'Our_Name': our_product['name'],
                'Our_Barcode': our_product['barcode'],
                'Our_AI_Brand': our_product['brand'],
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
                'Match_Method': result.get('method', 'none'),
                'Match_Reason': result.get('reason', '')
            }

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(match_one, row): idx for idx, row in df_our.iterrows()}

        for future in as_completed(futures):
            result = future.result()
            matches.append(result)
            completed += 1

            if completed % 25 == 0 or completed == len(df_our):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                matched_count = sum(1 for m in matches if m['Hackney_Item'] is not None)
                print(f"   Progress: {completed}/{len(df_our)} ({completed/len(df_our)*100:.1f}%) | Matched: {matched_count} | Rate: {rate:.1f}/sec")

    # Results
    df_results = pd.DataFrame(matches)
    matched = df_results['Hackney_Item'].notna()
    total_matched = matched.sum()

    print(f"\n📊 FINAL RESULTS:")
    print(f"   Our products: {len(df_our)}")
    print(f"   Matched: {total_matched} ({total_matched/len(df_our)*100:.1f}%)")
    print(f"   Not matched: {len(df_our) - total_matched}")

    if total_matched > 0:
        print(f"\n   Confidence breakdown:")
        conf_counts = df_results[matched]['Match_Confidence'].value_counts()
        for conf, count in conf_counts.items():
            print(f"      {conf}: {count}")

        print(f"\n   Method breakdown:")
        method_counts = df_results[matched]['Match_Method'].value_counts()
        for method, count in method_counts.items():
            print(f"      {method}: {count}")

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'our_to_hackney_UPC_VERIFIED_{timestamp}.xlsx'

    print(f"\n💾 Saving: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='All_Our_Products', index=False)

        if total_matched > 0:
            df_results[matched].to_excel(writer, sheet_name='Matched', index=False)

            # UPC-verified matches only
            upc_verified = df_results[matched & (df_results['Match_Method'] == 'upc_ai')]
            if len(upc_verified) > 0:
                upc_verified.to_excel(writer, sheet_name='UPC_Verified', index=False)

        if len(df_results[~matched]) > 0:
            df_results[~matched].to_excel(writer, sheet_name='Not_Matched', index=False)

        brand_summary = df_results.groupby('Our_AI_Brand').agg({
            'Our_Name': 'count',
            'Hackney_Item': lambda x: x.notna().sum()
        })
        brand_summary.columns = ['Total', 'Matched']
        brand_summary['Match_Rate'] = (brand_summary['Matched'] / brand_summary['Total'] * 100).round(1)
        brand_summary = brand_summary.sort_values('Total', ascending=False)
        brand_summary.to_excel(writer, sheet_name='By_Brand_Summary')

    print(f"\n✅ Complete! File: {output_file}")

    # Show top sellers status
    print(f"\n📋 Top Sellers Status:")
    top_sellers = df_results.nlargest(10, 'Our_TotalSold30D')
    for idx, row in top_sellers.iterrows():
        matched_icon = "✅" if pd.notna(row['Hackney_Item']) else "❌"
        print(f"{matched_icon} {row['Our_Name'][:45]:45s} | Sold: {row['Our_TotalSold30D']:5.0f} | {row['Match_Method']}")

if __name__ == "__main__":
    main()
