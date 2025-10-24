"""
Fix FBA Analysis Pack Size Mismatches
Uses AI to extract pack sizes and normalize costs for accurate profit calculations
"""

import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_pack_sizes(your_description, amazon_title, your_cost, amazon_price):
    """Use AI to extract pack sizes and calculate normalized profit"""

    prompt = f"""Analyze these product descriptions and extract pack size information:

YOUR PRODUCT: "{your_description}"
Your cost: ${your_cost}

AMAZON PRODUCT: "{amazon_title}"
Amazon price: ${amazon_price}

Extract:
1. Your pack quantity (how many units in YOUR product)
2. Amazon pack quantity (how many units in AMAZON product)
3. Calculate pack size ratio
4. Normalize your cost to match Amazon's pack size

Examples:
- "VIENNA SAUSAGE 1CT" vs "Vienna Sausage (Pack of 24)" = your:1, amazon:24, ratio:24
- "CHEEZ-IT 3OZ 6CT" vs "Cheez-It 3oz (Pack of 36)" = your:6, amazon:36, ratio:6
- "M&M PEANUT 24CT" vs "M&M Peanut 24 Pack" = your:24, amazon:24, ratio:1 (MATCH!)

Return JSON:
{{
  "your_pack_size": <number>,
  "amazon_pack_size": <number>,
  "pack_ratio": <number>,
  "normalized_your_cost": <your_cost * pack_ratio>,
  "pack_sizes_match": <true if ratio is 1>,
  "confidence": "HIGH/MEDIUM/LOW",
  "notes": "brief explanation"
}}

Be careful with:
- "8/12FL" means 8 fl oz size, not 8 count
- "1CT" often means single unit
- "KS" = King Size (not a pack indicator)
- Look for "Pack of", "CT", "BX", "Case of", etc.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at parsing product descriptions and pack sizes. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        return {
            "your_pack_size": 1,
            "amazon_pack_size": 1,
            "pack_ratio": 1,
            "normalized_your_cost": your_cost,
            "pack_sizes_match": True,
            "confidence": "LOW",
            "notes": f"Error: {str(e)[:100]}"
        }


def process_item(row, idx, total):
    """Process single item with AI pack size extraction"""

    # Skip items not found on Amazon
    if not row.get('asin'):
        return row

    desc = row.get('description', '')
    amazon_title = row.get('amazon_title', '')
    your_cost = float(row.get('your_cost', 0))
    amazon_price = float(row.get('projected_amazon_price', 0))
    fba_fee_total = float(row.get('fba_fee_total', 0))

    # Skip if no data
    if not desc or not amazon_title or your_cost == 0 or amazon_price == 0:
        return row

    print(f"[{idx}/{total}] {desc[:50]}")

    # Get AI analysis
    pack_info = extract_pack_sizes(desc, amazon_title, your_cost, amazon_price)

    # Add pack info to row
    row['ai_your_pack_size'] = pack_info.get('your_pack_size', 1)
    row['ai_amazon_pack_size'] = pack_info.get('amazon_pack_size', 1)
    row['ai_pack_ratio'] = pack_info.get('pack_ratio', 1)
    row['ai_normalized_cost'] = pack_info.get('normalized_your_cost', your_cost)
    row['ai_pack_match'] = 'YES' if pack_info.get('pack_sizes_match') else 'NO'
    row['ai_confidence'] = pack_info.get('confidence', 'LOW')
    row['ai_notes'] = pack_info.get('notes', '')

    # Recalculate profit with normalized cost
    normalized_cost = float(pack_info.get('normalized_your_cost', your_cost))
    corrected_profit = amazon_price - fba_fee_total - normalized_cost
    corrected_roi = (corrected_profit / normalized_cost * 100) if normalized_cost > 0 else 0

    row['corrected_fba_profit'] = round(corrected_profit, 2)
    row['corrected_fba_roi'] = round(corrected_roi, 1)

    # Show result
    if pack_info.get('pack_ratio', 1) > 1:
        print(f"    Pack ratio: {pack_info['pack_ratio']}x (your:{pack_info['your_pack_size']} → amazon:{pack_info['amazon_pack_size']})")
        print(f"    Cost: ${your_cost:.2f} → ${normalized_cost:.2f}")
        print(f"    Profit: ${float(row.get('projected_fba_profit', 0)):.2f} → ${corrected_profit:.2f}")

    return row


def main():
    input_file = 'fba_profit_analysis_FULL_RUN.csv'
    output_file = 'fba_profit_analysis_CORRECTED.csv'

    print("=" * 100)
    print("FBA PACK SIZE CORRECTION - AI Analysis")
    print("=" * 100)
    print()

    # Read CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter items found on Amazon
    items_to_process = [r for r in rows if r.get('asin')]

    print(f"Total items: {len(rows)}")
    print(f"Found on Amazon: {len(items_to_process)}")
    print(f"Processing with AI pack size analysis...")
    print()

    # Process with parallel AI calls
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_item, row, idx+1, len(items_to_process)): row
            for idx, row in enumerate(items_to_process)
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Add back items not found on Amazon (unchanged)
    items_not_found = [r for r in rows if not r.get('asin')]
    all_results = results + items_not_found

    # Write corrected CSV
    print()
    print("=" * 100)
    print(f"Writing corrected results to: {output_file}")

    if all_results:
        fieldnames = list(all_results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)

    # Summary
    corrected_items = [r for r in results if r.get('ai_pack_ratio') and float(r.get('ai_pack_ratio', 1)) > 1]

    print()
    print("✓ Correction complete!")
    print(f"  Items corrected: {len(corrected_items)}")
    print(f"  Results saved: {output_file}")
    print()

    # Show top items with corrected profits
    profitable = [r for r in results if r.get('corrected_fba_profit') and float(r.get('corrected_fba_profit', 0)) > 0]
    profitable.sort(key=lambda x: float(x.get('corrected_fba_profit', 0)), reverse=True)

    print("=" * 100)
    print("TOP 15 MOST PROFITABLE (CORRECTED)")
    print("=" * 100)
    print(f"{'Description':<45} {'Profit':<10} {'ROI':<8} {'Pack Fix':<10}")
    print("-" * 100)

    for item in profitable[:15]:
        desc = item.get('description', '')[:43]
        profit = float(item.get('corrected_fba_profit', 0))
        roi = float(item.get('corrected_fba_roi', 0))
        pack_match = item.get('ai_pack_match', 'UNKNOWN')
        print(f"{desc:<45} ${profit:>8.2f} {roi:>6.0f}% {pack_match:<10}")

    print()


if __name__ == '__main__':
    main()
