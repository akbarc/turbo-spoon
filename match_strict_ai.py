#!/usr/bin/env python3
"""
Strict AI matching: Compare each of our products against ALL Hackney products
Use brand filtering only to reduce API calls, but give AI ALL candidates in that brand
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

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

def find_exact_match_strict(our_product, all_hackney_products):
    """
    Use AI to find EXACT match with STRICT criteria
    AI must compare our product against the ENTIRE Hackney list
    """

    if len(all_hackney_products) == 0:
        return {'matched': False, 'reason': 'No Hackney products available'}

    try:
        # Create list of ALL Hackney products (or limit to first 50 for API)
        hackney_list = "\n".join([
            f"{i+1}. {p['description']}"
            for i, p in enumerate(all_hackney_products[:50])
        ])

        prompt = f"""You are matching cigarette products. Find the EXACT matching product ONLY.

OUR PRODUCT: {our_product['name']}

HACKNEY PRODUCTS (complete list):
{hackney_list}

STRICT MATCHING RULES:
1. "GOLD" and "BLACK GOLD" are DIFFERENT products - do NOT match them
2. "MENTHOL" and "MENTHOL GOLD" are DIFFERENT products
3. "RED" and "RED LABEL" are DIFFERENT products
4. "BLUE" and "MENTHOL BLUE" are DIFFERENT products
5. "100" (100mm) and "KING" (84mm) are DIFFERENT sizes - do NOT match
6. "BOX" and "SOFT PACK" are DIFFERENT packaging - only match if both are same
7. Ignore "10CT" in our product name - that's just our pack quantity
8. Product must have SAME base variant (Red/Gold/Silver/Blue/Menthol/etc.)

Return JSON with:
- "match_number": number (1-{min(50, len(all_hackney_products))}) of the EXACT matching product, or null if NO EXACT match exists
- "confidence": "exact" (perfect match including variant), "high" (very close match), or "none" (no match or only partial match)
- "reason": explain WHY you matched or why no match exists

IMPORTANT: If you're not confident it's the SAME EXACT product variant, return null. Better to have no match than wrong match."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict cigarette product matcher. Only match products that are EXACTLY the same variant. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')
        confidence = result.get('confidence', 'none')

        # Only accept "exact" or "high" confidence matches
        if match_num and 1 <= match_num <= len(all_hackney_products) and confidence in ['exact', 'high']:
            matched_product = all_hackney_products[match_num - 1]
            return {
                'matched': True,
                'hackney_product': matched_product,
                'confidence': confidence,
                'reason': result.get('reason', '')
            }
        else:
            return {
                'matched': False,
                'confidence': confidence if confidence else 'none',
                'reason': result.get('reason', 'No exact match found or confidence too low')
            }

    except Exception as e:
        return {
            'matched': False,
            'confidence': 'error',
            'reason': f'Error: {str(e)}'
        }

def main():
    print("="*100)
    print("STRICT AI MATCHING - ONE PRODUCT vs ENTIRE HACKNEY LIST")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    print("📂 Loading files...")
    df_our = pd.read_excel('cigarette_inventory_export_20251022_171837.xlsx', sheet_name='Cigarette_Inventory')
    df_hackney = pd.read_excel('/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx', sheet_name='HACKNEY')

    print(f"✅ Our inventory: {len(df_our)} products")
    print(f"✅ Hackney catalog: {len(df_hackney)} products")

    # Extract brands with AI for filtering
    print(f"\n🤖 Extracting brands for filtering...")

    start_time = time.time()
    completed = 0

    our_brands = {}
    def extract_our_brand(row):
        name = row['Name']
        brand = extract_brand_with_ai(name)
        return (name, brand)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_our_brand, row): idx for idx, row in df_our.iterrows()}
        for future in as_completed(futures):
            name, brand = future.result()
            our_brands[name] = brand
            completed += 1
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{len(df_our)} our products")

    hackney_brands = {}
    def extract_hackney_brand(row):
        desc = row['Description']
        brand = extract_brand_with_ai(desc)
        return (desc, brand)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_hackney_brand, row): idx for idx, row in df_hackney.iterrows()}
        for future in as_completed(futures):
            desc, brand = future.result()
            hackney_brands[desc] = brand
            completed += 1
            if completed % 100 == 0:
                print(f"   Progress: {completed}/{len(df_our) + len(df_hackney)} total")

    df_our['AI_Brand'] = df_our['Name'].map(our_brands)
    df_hackney['AI_Brand'] = df_hackney['Description'].map(hackney_brands)

    elapsed = time.time() - start_time
    print(f"✅ Brand extraction complete in {elapsed:.1f}s")

    # Organize Hackney products by brand
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

    # STRICT MATCHING: Each of our products vs entire brand list
    print(f"\n🤖 STRICT MATCHING: Each product vs entire Hackney brand list...")
    print(f"   Using STRICT criteria (GOLD ≠ BLACK GOLD, etc.)")
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

        # Get ALL Hackney products for same brand
        hackney_same_brand = hackney_by_brand.get(our_product['brand'], [])

        # Try to find STRICT match
        result = find_exact_match_strict(our_product, hackney_same_brand)

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
    output_file = f'our_to_hackney_STRICT_{timestamp}.xlsx'

    print(f"\n💾 Saving results: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='All_Our_Products', index=False)

        df_matched = df_results[matched].copy()
        if len(df_matched) > 0:
            df_matched.to_excel(writer, sheet_name='Matched', index=False)

        high_conf = df_results[matched & (df_results['Match_Confidence'].isin(['exact', 'high']))].copy()
        if len(high_conf) > 0:
            high_conf.to_excel(writer, sheet_name='High_Confidence', index=False)

        df_unmatched = df_results[~matched].copy()
        if len(df_unmatched) > 0:
            df_unmatched.to_excel(writer, sheet_name='Not_Matched', index=False)

        brand_summary = df_results.groupby('Our_AI_Brand').agg({
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
        print(f"\n📋 Sample STRICT matches (first 15):")
        for idx, row in df_matched.head(15).iterrows():
            print(f"\n  {row['Our_Name'][:50]:50s}")
            print(f"  -> {row['Hackney_Description'][:50]:50s} [{row['Match_Confidence']}]")
            print(f"     Reason: {row['Match_Reason'][:80]}")

    # Show top unmatched by sales
    if len(df_unmatched) > 0:
        print(f"\n❌ Top 10 Unmatched by Sales Volume:")
        top_unmatched = df_unmatched.nlargest(10, 'Our_TotalSold30D')
        for idx, row in top_unmatched.iterrows():
            print(f"   {row['Our_Name'][:45]:45s} | Sold: {row['Our_TotalSold30D']:5.0f}")
            print(f"      Reason: {row['Match_Reason'][:80]}")

if __name__ == "__main__":
    main()
