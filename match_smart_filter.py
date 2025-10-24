#!/usr/bin/env python3
"""
Smart filtering + AI matching:
1. Use AI to extract brand
2. Filter Hackney by brand
3. Filter Hackney by keywords from our product (GOLD, RED, MENTHOL, etc.)
4. Send only relevant candidates to AI for final matching
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

def extract_brand_with_ai(product_name):
    """Use AI to extract cigarette brand from product name"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a cigarette brand expert. Extract the brand name from cigarette product names. Return JSON with 'brand' (normalized full brand name like MARLBORO, NEWPORT, CAMEL, etc.)."
                },
                {
                    "role": "user",
                    "content": f"Extract brand from: {product_name}"
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)
        return result.get('brand', 'UNKNOWN').upper()

    except Exception as e:
        return 'UNKNOWN'

def extract_keywords(product_name):
    """Extract key variant/flavor keywords from product name"""
    name_upper = product_name.upper()

    keywords = []

    # Variant keywords
    variants = ['GOLD', 'SILVER', 'RED', 'BLUE', 'GREEN', 'BLACK', 'ORANGE',
                'YELLOW', 'MENTHOL', 'MEN', 'SMOOTH', 'BOLD', 'NXT', 'ICE',
                'CRUSH', 'EDGE', 'LABEL', 'SELECT', 'SPECIAL', 'SLATE', 'MIDNIGHT']

    for variant in variants:
        if variant in name_upper:
            keywords.append(variant)

    # Size keywords
    if '100' in name_upper:
        keywords.append('100')
    elif '72' in name_upper:
        keywords.append('72')
    elif 'KING' in name_upper:
        keywords.append('KING')

    # Pack type
    if 'BOX' in name_upper:
        keywords.append('BOX')
    elif 'SOFT' in name_upper:
        keywords.append('SOFT')

    return keywords

def filter_hackney_candidates(our_product_name, hackney_products, brand):
    """Filter Hackney products to most relevant candidates"""

    # Get keywords from our product
    our_keywords = extract_keywords(our_product_name)

    if not our_keywords:
        # No keywords - return all products in brand
        return hackney_products[:50]

    # Score each Hackney product by keyword overlap
    scored_products = []
    for product in hackney_products:
        hackney_name = product['description'].upper()

        # Count matching keywords
        matches = sum(1 for kw in our_keywords if kw in hackney_name)

        # Penalize if Hackney has keywords we don't have
        hackney_keywords = extract_keywords(product['description'])
        extra_keywords = [kw for kw in hackney_keywords if kw not in our_keywords]
        penalty = len(extra_keywords)

        score = matches - (penalty * 0.5)

        scored_products.append((score, product))

    # Sort by score descending
    scored_products.sort(key=lambda x: x[0], reverse=True)

    # Return top 30 candidates
    return [p for score, p in scored_products[:30]]

def find_exact_match_ai(our_product, filtered_candidates):
    """Use AI to find exact match from pre-filtered candidates"""

    if len(filtered_candidates) == 0:
        return {'matched': False, 'reason': 'No candidates after filtering'}

    try:
        # Create list of filtered candidates
        hackney_list = "\n".join([
            f"{i+1}. {p['description']}"
            for i, p in enumerate(filtered_candidates)
        ])

        prompt = f"""Match our cigarette product to the correct Hackney product.

OUR PRODUCT: {our_product['name']}

HACKNEY CANDIDATES (pre-filtered by relevance):
{hackney_list}

MATCHING RULES:
- "MARL" = "MARLBORO" (abbreviation OK)
- "MEN" = "MENTHOL" (abbreviation OK)
- "10CT" is our pack size - ignore it
- "GOLD" ≠ "BLACK GOLD" (different variants)
- "RED" ≠ "RED LABEL" might be different (be careful)
- "100" ≠ "KING" (different sizes)
- "BOX" ≠ "SOFT" (different packaging)

Return JSON:
- "match_number": 1-{len(filtered_candidates)} or null
- "confidence": "exact" / "high" / "medium" / "none"
- "reason": brief explanation

If not confident, return null."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a cigarette product matcher. Handle abbreviations but be strict about variants. Return JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')
        confidence = result.get('confidence', 'none')

        # Accept exact or high confidence
        if match_num and 1 <= match_num <= len(filtered_candidates) and confidence in ['exact', 'high']:
            matched_product = filtered_candidates[match_num - 1]
            return {
                'matched': True,
                'hackney_product': matched_product,
                'confidence': confidence,
                'reason': result.get('reason', '')
            }
        else:
            return {
                'matched': False,
                'confidence': confidence,
                'reason': result.get('reason', 'No confident match found')
            }

    except Exception as e:
        return {
            'matched': False,
            'confidence': 'error',
            'reason': f'Error: {str(e)}'
        }

def main():
    print("="*100)
    print("SMART FILTERED AI MATCHING")
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
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        # Our products
        for idx, row in df_our.iterrows():
            futures.append((executor.submit(extract_brand_with_ai, row['Name']), 'our', row['Name']))

        # Hackney products
        for idx, row in df_hackney.iterrows():
            futures.append((executor.submit(extract_brand_with_ai, row['Description']), 'hackney', row['Description']))

        for future, source, name in futures:
            brand = future.result()
            if source == 'our':
                our_brands[name] = brand
            else:
                hackney_brands[name] = brand

            completed += 1
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{len(futures)}")

    df_our['AI_Brand'] = df_our['Name'].map(our_brands)
    df_hackney['AI_Brand'] = df_hackney['Description'].map(hackney_brands)

    elapsed = time.time() - start_time
    print(f"✅ Brand extraction complete in {elapsed:.1f}s")

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

    # Match with smart filtering
    print(f"\n🤖 Matching with smart keyword filtering...")
    print()

    matches = []
    completed = 0
    start_time = time.time()

    def match_one_product(row):
        our_product = {
            'name': row['Name'],
            'barcode': row['Barcode'],
            'brand': row['AI_Brand'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D']
        }

        # Get Hackney products for brand
        hackney_same_brand = hackney_by_brand.get(our_product['brand'], [])

        # Filter to most relevant candidates
        filtered = filter_hackney_candidates(our_product['name'], hackney_same_brand, our_product['brand'])

        # Match with AI
        result = find_exact_match_ai(our_product, filtered)

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
                'Match_Reason': result.get('reason', '')
            }

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

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'our_to_hackney_SMART_{timestamp}.xlsx'

    print(f"\n💾 Saving: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='All_Our_Products', index=False)

        if total_matched > 0:
            df_results[matched].to_excel(writer, sheet_name='Matched', index=False)

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

    # Show top unmatched by sales
    if len(df_results[~matched]) > 0:
        print(f"\n❌ Top 10 Unmatched by Sales:")
        top_unmatched = df_results[~matched].nlargest(10, 'Our_TotalSold30D')
        for idx, row in top_unmatched.iterrows():
            print(f"   {row['Our_Name'][:50]:50s} | Sold: {row['Our_TotalSold30D']:5.0f}")

if __name__ == "__main__":
    main()
