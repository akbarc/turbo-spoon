#!/usr/bin/env python3
"""
Improved AI-based product matching with better error handling
"""

import pandas as pd
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

def find_best_match_ai(hackney_name, our_products_list):
    """Use OpenAI to find the best matching product"""

    try:
        # Limit to 20 most relevant products for faster/cleaner responses
        products_str = "\n".join([f"{i+1}. {p['name']}" for i, p in enumerate(our_products_list[:20])])

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You match cigarette products. Return JSON with: match_number (1-20 or null), confidence (high/medium/low), reason (brief)."
                },
                {
                    "role": "user",
                    "content": f"Match '{hackney_name}' to:\n{products_str}"
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)
        match_num = result.get('match_number')

        if match_num and 1 <= match_num <= len(our_products_list):
            return {
                'matched': True,
                'product': our_products_list[match_num - 1],
                'confidence': result.get('confidence', 'unknown'),
                'reason': result.get('reason', '')
            }

    except Exception as e:
        pass

    return {'matched': False}

def main():
    print("="*100)
    print("HACKNEY AI MATCHING - IMPROVED VERSION")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    df_hackney = pd.read_excel('/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx', sheet_name='HACKNEY')
    df_our = pd.read_excel('cigarette_inventory_export_20251022_171837.xlsx', sheet_name='Cigarette_Inventory')
    df_already_matched = pd.read_excel('hackney_matched_20251022_173601.xlsx', sheet_name='Matched_Products')

    print(f"✅ Loaded {len(df_hackney)} Hackney products")
    print(f"✅ Loaded {len(df_our)} our products")
    print(f"✅ Already matched (UPC): {len(df_already_matched)}")

    # Get unmatched
    matched_items = set(df_already_matched['Hackney_Item'].astype(str))
    df_unmatched = df_hackney[~df_hackney['Item'].astype(str).isin(matched_items)]

    print(f"\n🔍 Processing {len(df_unmatched)} unmatched products")

    # Prepare our products
    our_products = [
        {
            'name': row['Name'],
            'upc': row['Barcode'],
            'cost': row['Cost'],
            'price': row['CurrentPrice'],
            'stock': row['CurrentStock'],
            'sold_30d': row['TotalSold30D']
        }
        for _, row in df_our.iterrows()
    ]

    # Match with AI
    print(f"\n🤖 Starting AI matching (parallel=5)...\n")

    matches = []
    completed = 0
    start_time = time.time()

    def match_one(row):
        result = find_best_match_ai(row['Description'], our_products)
        if result['matched']:
            return {
                'Hackney_Item': row['Item'],
                'Hackney_Description': row['Description'],
                'Hackney_UPC': row['Retail UPC'],
                'Hackney_Price': row['Price'],
                'Match_Strategy': 'ai',
                'Match_Confidence': result['confidence'],
                'Match_Reason': result['reason'],
                'Our_Name': result['product']['name'],
                'Our_Barcode': result['product']['upc'],
                'Our_Cost': result['product']['cost'],
                'Our_CurrentPrice': result['product']['price'],
                'Our_CurrentStock': result['product']['stock'],
                'Our_TotalSold30D': result['product']['sold_30d']
            }
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(match_one, row): idx for idx, row in df_unmatched.iterrows()}

        for future in as_completed(futures):
            result = future.result()
            if result:
                matches.append(result)

            completed += 1
            if completed % 25 == 0:
                elapsed = time.time() - start_time
                print(f"   Progress: {completed}/{len(df_unmatched)} | Matched: {len(matches)} | Rate: {completed/elapsed:.1f}/sec")

    df_ai_matches = pd.DataFrame(matches)

    # Combine all matches
    df_combined = pd.concat([df_already_matched, df_ai_matches], ignore_index=True)

    print(f"\n📊 FINAL RESULTS:")
    print(f"   UPC matches: {len(df_already_matched)}")
    print(f"   AI matches: {len(df_ai_matches)}")
    print(f"   Total: {len(df_combined)}/{len(df_hackney)} ({len(df_combined)/len(df_hackney)*100:.1f}%)")

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'hackney_complete_{timestamp}.xlsx'

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_combined.to_excel(writer, sheet_name='All_Matches', index=False)
        df_already_matched.to_excel(writer, sheet_name='UPC_Matches', index=False)
        if len(df_ai_matches) > 0:
            df_ai_matches.to_excel(writer, sheet_name='AI_Matches', index=False)

    print(f"\n✅ Saved: {output_file}")

    # Show samples
    if len(df_ai_matches) > 0:
        print(f"\n📋 AI matches sample:")
        for idx, row in df_ai_matches.head(10).iterrows():
            print(f"\n  {row['Hackney_Description']}")
            print(f"  -> {row['Our_Name']} ({row['Match_Confidence']})")

if __name__ == "__main__":
    main()
