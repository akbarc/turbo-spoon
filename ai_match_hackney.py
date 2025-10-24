#!/usr/bin/env python3
"""
AI-based product name matching for Hackney products
Uses OpenAI to intelligently match product descriptions
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

def match_product_with_ai(hackney_product, our_products_list):
    """Use OpenAI to match a Hackney product to our inventory"""

    try:
        # Create a list of our products for matching
        products_str = "\n".join([f"{i+1}. {p['name']} (UPC: {p['upc']})" for i, p in enumerate(our_products_list[:50])])

        prompt = f"""You are a cigarette product matching expert. Match the Hackney product to the most similar product from our inventory.

Hackney Product: {hackney_product['description']}
Hackney UPC: {hackney_product['upc']}

Our Products:
{products_str}

Return a JSON object with:
- "match_index": the number (1-{min(50, len(our_products_list))}) of the best matching product, or null if no good match
- "confidence": "high", "medium", or "low"
- "reason": brief explanation of why they match (or why no match)

Only return the JSON, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a product matching expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content.strip())

        if result.get('match_index') is not None:
            match_idx = result['match_index'] - 1  # Convert to 0-based index
            if 0 <= match_idx < len(our_products_list):
                matched_product = our_products_list[match_idx]
                return {
                    'matched': True,
                    'our_product': matched_product,
                    'confidence': result.get('confidence', 'unknown'),
                    'reason': result.get('reason', ''),
                    'method': 'ai'
                }

        return {
            'matched': False,
            'confidence': result.get('confidence', 'none'),
            'reason': result.get('reason', 'No good match found'),
            'method': 'ai'
        }

    except Exception as e:
        print(f"Error matching {hackney_product['description']}: {e}")
        return {
            'matched': False,
            'confidence': 'error',
            'reason': str(e),
            'method': 'ai_error'
        }

def match_batch_parallel(hackney_products, our_products_list, max_workers=10):
    """Match products in parallel batches"""
    results = []
    total = len(hackney_products)
    completed = 0

    print(f"\n🤖 AI matching {total} products...")
    print(f"   Using {max_workers} parallel workers")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_product = {
            executor.submit(match_product_with_ai, product, our_products_list): product
            for product in hackney_products
        }

        # Process completed tasks
        for future in as_completed(future_to_product):
            product = future_to_product[future]
            result = future.result()

            results.append({
                'hackney_product': product,
                'match_result': result
            })

            completed += 1
            if completed % 10 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                matched_so_far = sum(1 for r in results if r['match_result']['matched'])
                print(f"   Progress: {completed}/{total} ({completed/total*100:.1f}%) | Matched: {matched_so_far} | Rate: {rate:.1f}/sec")

    elapsed = time.time() - start_time
    total_matched = sum(1 for r in results if r['match_result']['matched'])
    print(f"\n✅ AI matching complete in {elapsed:.1f}s")
    print(f"   Total matched: {total_matched}/{total} ({total_matched/total*100:.1f}%)")

    return results

def main():
    print("="*100)
    print("HACKNEY AI PRODUCT NAME MATCHING")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    hackney_file = '/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx'
    our_file = 'cigarette_inventory_export_20251022_171837.xlsx'
    already_matched_file = 'hackney_matched_20251022_173601.xlsx'

    print(f"📂 Loading files...")
    df_hackney = pd.read_excel(hackney_file, sheet_name='HACKNEY')
    df_our = pd.read_excel(our_file, sheet_name='Cigarette_Inventory')
    df_already_matched = pd.read_excel(already_matched_file, sheet_name='Matched_Products')

    print(f"✅ Hackney: {len(df_hackney)} products")
    print(f"✅ Our inventory: {len(df_our)} products")
    print(f"✅ Already matched (UPC): {len(df_already_matched)} products")

    # Get unmatched Hackney products
    already_matched_items = set(df_already_matched['Hackney_Item'].astype(str))
    df_unmatched = df_hackney[~df_hackney['Item'].astype(str).isin(already_matched_items)].copy()

    print(f"\n🔍 Unmatched products to process: {len(df_unmatched)}")

    # Prepare our products list for AI matching
    our_products_list = []
    for idx, row in df_our.iterrows():
        our_products_list.append({
            'name': row['Name'],
            'upc': row['Barcode'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D'],
            'supplier': row['LastSupplier'],
            'last_purchase_price': row['LastPurchasePrice']
        })

    # Prepare Hackney products for matching
    hackney_products = []
    for idx, row in df_unmatched.iterrows():
        hackney_products.append({
            'item': row['Item'],
            'description': row['Description'],
            'upc': row['Retail UPC'],
            'price': row['Price'],
            'qty_on_hand': row[' Quantity on Hand']
        })

    # Match products with AI
    match_results = match_batch_parallel(hackney_products, our_products_list, max_workers=10)

    # Process results
    ai_matches = []
    for result in match_results:
        if result['match_result']['matched']:
            hackney = result['hackney_product']
            our = result['match_result']['our_product']

            ai_matches.append({
                'Hackney_Item': hackney['item'],
                'Hackney_Description': hackney['description'],
                'Hackney_UPC': hackney['upc'],
                'Hackney_Price': hackney['price'],
                'Hackney_QtyOnHand': hackney['qty_on_hand'],
                'Match_Strategy': 'ai',
                'Match_Confidence': result['match_result']['confidence'],
                'Match_Reason': result['match_result']['reason'],
                'Our_Name': our['name'],
                'Our_Barcode': our['upc'],
                'Our_Cost': our['cost'],
                'Our_CurrentPrice': our['price'],
                'Our_CurrentStock': our['stock'],
                'Our_TotalSold30D': our['sold_30d'],
                'Our_LastSupplier': our['supplier'],
                'Our_LastPurchasePrice': our['last_purchase_price']
            })

    df_ai_matches = pd.DataFrame(ai_matches)

    # Combine with UPC matches
    print(f"\n🔗 Combining AI matches with UPC matches...")
    df_combined = pd.concat([df_already_matched, df_ai_matches], ignore_index=True)

    print(f"\n📊 FINAL RESULTS:")
    print(f"   UPC matches: {len(df_already_matched)}")
    print(f"   AI matches: {len(df_ai_matches)}")
    print(f"   Total matched: {len(df_combined)}/{len(df_hackney)} ({len(df_combined)/len(df_hackney)*100:.1f}%)")

    # Break down AI matches by confidence
    if len(df_ai_matches) > 0:
        print(f"\n   AI match confidence breakdown:")
        confidence_counts = df_ai_matches['Match_Confidence'].value_counts()
        for conf, count in confidence_counts.items():
            print(f"      {conf}: {count}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'hackney_matched_complete_{timestamp}.xlsx'

    print(f"\n💾 Saving results: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # All matches
        df_combined.to_excel(writer, sheet_name='All_Matches', index=False)

        # UPC matches only
        df_already_matched.to_excel(writer, sheet_name='UPC_Matches', index=False)

        # AI matches only
        if len(df_ai_matches) > 0:
            df_ai_matches.to_excel(writer, sheet_name='AI_Matches', index=False)

        # High confidence AI matches
        if len(df_ai_matches) > 0:
            high_conf = df_ai_matches[df_ai_matches['Match_Confidence'] == 'high']
            if len(high_conf) > 0:
                high_conf.to_excel(writer, sheet_name='AI_High_Confidence', index=False)

        # Unmatched
        still_unmatched_items = set(df_combined['Hackney_Item'].astype(str))
        df_still_unmatched = df_hackney[~df_hackney['Item'].astype(str).isin(still_unmatched_items)]
        if len(df_still_unmatched) > 0:
            df_still_unmatched.to_excel(writer, sheet_name='Still_Unmatched', index=False)

    print(f"\n✅ Export complete!")
    print(f"\nFile: {output_file}")
    print(f"Total matches: {len(df_combined)}/{len(df_hackney)} ({len(df_combined)/len(df_hackney)*100:.1f}%)")
    print(f"Unmatched: {len(df_hackney) - len(df_combined)}")

    # Show sample AI matches
    if len(df_ai_matches) > 0:
        print(f"\n📋 Sample AI matches (first 10):")
        for idx, row in df_ai_matches.head(10).iterrows():
            print(f"\n  {row['Hackney_Description']}")
            print(f"  -> {row['Our_Name']}")
            print(f"  Confidence: {row['Match_Confidence']} | {row['Match_Reason']}")

if __name__ == "__main__":
    main()
