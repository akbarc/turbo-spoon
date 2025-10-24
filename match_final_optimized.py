#!/usr/bin/env python3
"""
FINAL OPTIMIZED MATCHING:
- AI brand extraction
- UPC prefix as scoring hint (not filter)
- Keyword matching
- AI with relaxed cigarette-specific rules
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_brand(name):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Extract cigarette brand. Return JSON with 'brand'."},
                {"role": "user", "content": f"Brand: {name}"}
            ]
        )
        return json.loads(response.choices[0].message.content).get('brand', 'UNKNOWN').upper()
    except:
        return 'UNKNOWN'

def extract_keywords(name):
    name_upper = name.upper()
    keywords = []

    for kw in ['GOLD', 'SILVER', 'RED', 'BLUE', 'GREEN', 'BLACK', 'MENTHOL', 'MEN',
               'SMOOTH', 'BOLD', 'NXT', 'ICE', 'CRUSH', 'LABEL', 'SELECT']:
        if kw in name_upper:
            keywords.append(kw)

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

def score_candidate(our_product, hackney_product):
    """Score Hackney candidate by UPC + keyword match"""
    score = 0

    # UPC prefix matching (bonus points)
    our_upc = str(our_product['barcode']).strip()
    hackney_upc = str(hackney_product['upc']).strip()

    if len(our_upc) >= 5 and len(hackney_upc) >= 5:
        if our_upc[:5] == hackney_upc[:5]:
            score += 10  # Same 5-digit prefix
        if len(our_upc) >= 6 and len(hackney_upc) >= 6:
            if our_upc[:6] == hackney_upc[:6]:
                score += 5  # Same 6-digit prefix

    # Keyword matching
    our_kw = extract_keywords(our_product['name'])
    hackney_kw = extract_keywords(hackney_product['description'])

    matches = sum(1 for kw in our_kw if kw in hackney_product['description'].upper())
    score += matches * 2

    # Penalize mismatched keywords
    extra = sum(1 for kw in hackney_kw if kw not in our_kw)
    score -= extra * 0.5

    return score

def find_match(our_product, hackney_by_brand):
    brand = our_product['brand']
    all_hackney = hackney_by_brand.get(brand, [])

    if not all_hackney:
        return {'matched': False, 'reason': f'No Hackney for brand {brand}'}

    # Score all candidates
    scored = [(score_candidate(our_product, h), h) for h in all_hackney]
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top 25
    top_candidates = [h for score, h in scored[:25]]

    try:
        candidates_list = "\n".join([f"{i+1}. {h['description']}" for i, h in enumerate(top_candidates)])

        prompt = f"""Match cigarette products.

OUR: {our_product['name']}
UPC: {our_product['barcode']}

HACKNEY (scored by UPC + keywords):
{candidates_list}

CIGARETTE MATCHING RULES:
✅ ALLOW:
- "MARL" = "MARLBORO" (abbreviation)
- "MEN" = "MENTHOL" (abbreviation)
- "KING BOX" = "BOX" = "LABEL BX" (packaging variations)
- "RED KING" = "RED LABEL" (Marlboro naming variation)
- Ignore "10CT" (our pack size)
- UPC prefixes 282000/282001/282003 are all Marlboro (different product lines)

❌ REJECT:
- "GOLD" ≠ "BLACK GOLD" (different flavors)
- "MENTHOL" ≠ "NON-MENTHOL" (different types)
- "100" ≠ "KING" ≠ "72" (different sizes)

Return JSON:
- "match_number": 1-{len(top_candidates)} or null
- "confidence": "exact"/"high"/"medium"/"none"
- "reason": brief

BE FLEXIBLE on naming. If brand + variant + size match, that's a match!"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Cigarette matcher. Be flexible on naming, strict on variants."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')
        confidence = result.get('confidence', 'none')

        if match_num and 1 <= match_num <= len(top_candidates) and confidence in ['exact', 'high']:
            return {
                'matched': True,
                'hackney_product': top_candidates[match_num - 1],
                'confidence': confidence,
                'reason': result.get('reason', '')
            }
        else:
            return {
                'matched': False,
                'confidence': confidence,
                'reason': result.get('reason', 'No confident match')
            }

    except Exception as e:
        return {'matched': False, 'reason': f'Error: {str(e)}'}

def main():
    print("="*100)
    print("FINAL OPTIMIZED MATCHING")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    df_our = pd.read_excel('cigarette_inventory_export_20251022_171837.xlsx', sheet_name='Cigarette_Inventory')
    df_hackney = pd.read_excel('/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx', sheet_name='HACKNEY')

    print(f"✅ Our: {len(df_our)} | Hackney: {len(df_hackney)}")

    # Extract brands
    print(f"\n🤖 Extracting brands...")

    our_brands = {}
    hackney_brands = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _, row in df_our.iterrows():
            futures.append((executor.submit(extract_brand, row['Name']), 'our', row['Name']))
        for _, row in df_hackney.iterrows():
            futures.append((executor.submit(extract_brand, row['Description']), 'hackney', row['Description']))

        completed = 0
        for future, source, name in futures:
            brand = future.result()
            if source == 'our':
                our_brands[name] = brand
            else:
                hackney_brands[name] = brand
            completed += 1
            if completed % 200 == 0:
                print(f"   {completed}/{len(futures)}")

    df_our['Brand'] = df_our['Name'].map(our_brands)
    df_hackney['Brand'] = df_hackney['Description'].map(hackney_brands)

    print(f"✅ Brands extracted")

    # Organize Hackney
    hackney_by_brand = {}
    for _, row in df_hackney.iterrows():
        brand = row['Brand']
        if brand not in hackney_by_brand:
            hackney_by_brand[brand] = []
        hackney_by_brand[brand].append({
            'item': row['Item'],
            'description': row['Description'],
            'upc': row['Retail UPC'],
            'price': row['Price'],
            'qty': row[' Quantity on Hand']
        })

    # Match
    print(f"\n🤖 Matching with flexible rules...")

    matches = []
    completed = 0
    start_time = time.time()

    def match_one(row):
        our = {
            'name': row['Name'],
            'barcode': row['Barcode'],
            'brand': row['Brand'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D']
        }

        result = find_match(our, hackney_by_brand)

        if result['matched']:
            h = result['hackney_product']
            return {
                'Our_Name': our['name'],
                'Our_Barcode': our['barcode'],
                'Our_Brand': our['brand'],
                'Our_Cost': our['cost'],
                'Our_Price': our['price'],
                'Our_Stock': our['stock'],
                'Our_Sold30D': our['sold_30d'],
                'Hackney_Item': h['item'],
                'Hackney_Desc': h['description'],
                'Hackney_UPC': h['upc'],
                'Hackney_Price': h['price'],
                'Hackney_Qty': h['qty'],
                'Confidence': result['confidence'],
                'Reason': result['reason']
            }
        else:
            return {
                'Our_Name': our['name'],
                'Our_Barcode': our['barcode'],
                'Our_Brand': our['brand'],
                'Our_Cost': our['cost'],
                'Our_Price': our['price'],
                'Our_Stock': our['stock'],
                'Our_Sold30D': our['sold_30d'],
                'Hackney_Item': None,
                'Hackney_Desc': None,
                'Hackney_UPC': None,
                'Hackney_Price': None,
                'Hackney_Qty': None,
                'Confidence': result.get('confidence', 'none'),
                'Reason': result.get('reason', '')
            }

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(match_one, row): i for i, row in df_our.iterrows()}

        for future in as_completed(futures):
            matches.append(future.result())
            completed += 1

            if completed % 25 == 0 or completed == len(df_our):
                elapsed = time.time() - start_time
                matched_count = sum(1 for m in matches if m['Hackney_Item'] is not None)
                print(f"   {completed}/{len(df_our)} ({completed/len(df_our)*100:.1f}%) | Matched: {matched_count} | {completed/elapsed:.1f}/sec")

    df_results = pd.DataFrame(matches)
    matched = df_results['Hackney_Item'].notna()
    total_matched = matched.sum()

    print(f"\n📊 RESULTS:")
    print(f"   Matched: {total_matched}/{len(df_our)} ({total_matched/len(df_our)*100:.1f}%)")

    if total_matched > 0:
        print(f"\n   Confidence:")
        for conf, count in df_results[matched]['Confidence'].value_counts().items():
            print(f"      {conf}: {count}")

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output = f'FINAL_MATCH_{timestamp}.xlsx'

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='All', index=False)
        if total_matched > 0:
            df_results[matched].to_excel(writer, sheet_name='Matched', index=False)
        if len(df_results[~matched]) > 0:
            df_results[~matched].to_excel(writer, sheet_name='Not_Matched', index=False)

    print(f"\n✅ Saved: {output}")

    # Top sellers
    print(f"\n📋 Top 10 Sellers:")
    for _, row in df_results.nlargest(10, 'Our_Sold30D').iterrows():
        icon = "✅" if pd.notna(row['Hackney_Item']) else "❌"
        print(f"{icon} {row['Our_Name'][:50]:50s} | {row['Our_Sold30D']:5.0f}")

if __name__ == "__main__":
    main()
