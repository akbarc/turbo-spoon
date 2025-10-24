"""
AI-Powered FBA Analysis Fixer
Uses multiple parallel AI agents to:
1. Fix pack sizes
2. Verify item matches
3. Correct counts and accuracy
4. Fetch JungleScout data using Product Database endpoint
"""

import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
import requests

load_dotenv('.env')

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

# JungleScout credentials
JS_API_NAME = os.getenv("JS_API_NAME")
JS_API_KEY = os.getenv("JS_API_KEY")


def ai_analyze_product_match(your_desc, amazon_title, your_cost, amazon_price, asin):
    """Use AI to verify if products actually match"""

    prompt = f"""Analyze if these two products are the SAME product:

YOUR PRODUCT: "{your_desc}"
Your cost: ${your_cost}

AMAZON PRODUCT: "{amazon_title}"
Amazon price: ${amazon_price}
ASIN: {asin}

Task: Determine if this is a correct match or a false positive (wrong product).

Consider:
- Brand names should match
- Product type should match
- Pack sizes (if different, explain the ratio)
- Price reasonableness (is Amazon price plausible given your cost?)

Return JSON:
{{
  "is_match": true/false,
  "confidence": "HIGH/MEDIUM/LOW",
  "your_pack_size": <number>,
  "amazon_pack_size": <number>,
  "pack_ratio": <amazon_pack / your_pack>,
  "match_quality": "PERFECT/GOOD/QUESTIONABLE/WRONG_PRODUCT",
  "reason": "brief explanation",
  "normalized_your_cost": <your_cost * pack_ratio>
}}

Examples:
- "TIDE 25OZ" vs "Tide Liquid Detergent 25oz" = PERFECT match
- "VIENNA SAUSAGE 1CT" vs "Armour Vienna Sausage 4.6oz (Pack of 24)" = GOOD match, ratio 24
- "CAMEL FILTERS" vs "Praise Classics Gospel Music CD" = WRONG_PRODUCT
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at matching product descriptions. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "is_match": True,
            "confidence": "LOW",
            "your_pack_size": 1,
            "amazon_pack_size": 1,
            "pack_ratio": 1,
            "match_quality": "QUESTIONABLE",
            "reason": f"AI Error: {str(e)[:100]}",
            "normalized_your_cost": your_cost
        }


def fetch_junglescout_data(asin, marketplace="us"):
    """Fetch data from JungleScout Product Database endpoint"""

    if not JS_API_NAME or not JS_API_KEY:
        return None

    url = f"https://developer.junglescout.com/api/product_database_query?marketplace={marketplace}"

    headers = {
        "Authorization": f"{JS_API_NAME}:{JS_API_KEY}",
        "X-API-Type": "junglescout",
        "Accept": "application/vnd.junglescout.v1+json",
        "Content-Type": "application/vnd.api+json"
    }

    # Query by ASIN
    body = {
        "data": {
            "type": "product_database_query",
            "attributes": {
                "asins": [asin],
                "marketplace": marketplace
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract first product if available
        if data.get('data') and len(data['data']) > 0:
            product = data['data'][0]['attributes']
            return {
                'js_monthly_sales': product.get('estimated_30_day_sales', ''),
                'js_monthly_revenue': product.get('estimated_30_day_revenue', ''),
                'js_price': product.get('price', ''),
                'js_bsr': product.get('rank', ''),
                'js_rating': product.get('rating', ''),
                'js_reviews': product.get('reviews', ''),
                'js_sellers_count': product.get('sellers', ''),
                'js_fba_available': product.get('fba_available', False)
            }
        return None
    except Exception as e:
        print(f"    JS Error for ASIN {asin}: {str(e)[:80]}")
        return None


def process_item_with_ai(row, idx, total):
    """Process single item with AI analysis and JungleScout data"""

    # Skip items not on Amazon
    if not row.get('asin'):
        return row

    desc = row.get('description', '')
    amazon_title = row.get('amazon_title', '')
    your_cost = float(row.get('your_cost', 0))
    amazon_price = float(row.get('projected_amazon_price', 0))
    fba_fee_total = float(row.get('fba_fee_total', 0))
    asin = row.get('asin', '')

    if not desc or not amazon_title or your_cost == 0:
        return row

    print(f"[{idx}/{total}] {desc[:50]}")

    # AI analysis
    analysis = ai_analyze_product_match(desc, amazon_title, your_cost, amazon_price, asin)

    # Add AI analysis to row
    row['ai_is_match'] = 'YES' if analysis.get('is_match') else 'NO'
    row['ai_confidence'] = analysis.get('confidence', 'LOW')
    row['ai_match_quality'] = analysis.get('match_quality', 'QUESTIONABLE')
    row['ai_your_pack'] = analysis.get('your_pack_size', 1)
    row['ai_amazon_pack'] = analysis.get('amazon_pack_size', 1)
    row['ai_pack_ratio'] = analysis.get('pack_ratio', 1)
    row['ai_normalized_cost'] = analysis.get('normalized_your_cost', your_cost)
    row['ai_reason'] = analysis.get('reason', '')

    # Fetch JungleScout data
    js_data = fetch_junglescout_data(asin)
    if js_data:
        for key, value in js_data.items():
            row[key] = value
        print(f"    ✓ Got JS data: {js_data.get('js_monthly_sales', 'N/A')} sales/mo")

    # Recalculate profit with AI-corrected costs
    if analysis.get('is_match') and analysis.get('match_quality') in ['PERFECT', 'GOOD']:
        normalized_cost = float(analysis.get('normalized_your_cost', your_cost))

        # Recalculate profit
        corrected_profit = amazon_price - fba_fee_total - normalized_cost
        corrected_roi = (corrected_profit / normalized_cost * 100) if normalized_cost > 0 else 0

        row['ai_corrected_profit'] = round(corrected_profit, 2)
        row['ai_corrected_roi'] = round(corrected_roi, 1)

        # Show significant changes
        if abs(analysis.get('pack_ratio', 1) - 1.0) > 0.1:
            print(f"    Pack: {analysis['your_pack_size']} → {analysis['amazon_pack_size']} (ratio: {analysis['pack_ratio']}x)")
            print(f"    Cost: ${your_cost:.2f} → ${normalized_cost:.2f}")
            print(f"    Profit: ${corrected_profit:.2f} ({corrected_roi:.0f}% ROI)")
    else:
        # Mark as questionable
        row['ai_corrected_profit'] = 0
        row['ai_corrected_roi'] = 0
        print(f"    ⚠️  {analysis.get('match_quality', 'QUESTIONABLE')}: {analysis.get('reason', '')[:60]}")

    return row


def main():
    input_file = 'fba_profit_analysis_FULL_RUN.csv'
    output_file = 'fba_profit_analysis_AI_FIXED.csv'

    print("=" * 100)
    print("AI-POWERED FBA ANALYSIS FIXER")
    print("=" * 100)
    print("Using GPT-4o-mini for product matching, pack size analysis, and verification")
    print("Using JungleScout Product Database API for sales estimates")
    print()

    # Read CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter to items on Amazon
    items_to_process = [r for r in rows if r.get('asin')]
    items_not_found = [r for r in rows if not r.get('asin')]

    print(f"Total items: {len(rows)}")
    print(f"Items on Amazon: {len(items_to_process)}")
    print(f"Processing with AI agents...")
    print()

    # Process with parallel AI agents (20 concurrent)
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(process_item_with_ai, row, idx+1, len(items_to_process)): row
            for idx, row in enumerate(items_to_process)
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Combine with items not found
    all_results = results + items_not_found

    # Write results
    print()
    print("=" * 100)
    print(f"Writing AI-corrected results to: {output_file}")

    if all_results:
        fieldnames = list(all_results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)

    # Statistics
    verified_matches = [r for r in results if r.get('ai_match_quality') in ['PERFECT', 'GOOD']]
    questionable = [r for r in results if r.get('ai_match_quality') == 'QUESTIONABLE']
    wrong_products = [r for r in results if r.get('ai_match_quality') == 'WRONG_PRODUCT']

    profitable_ai = [r for r in verified_matches if float(r.get('ai_corrected_profit', 0)) > 0]
    profitable_ai.sort(key=lambda x: float(x.get('ai_corrected_profit', 0)), reverse=True)

    with_js_data = [r for r in results if r.get('js_monthly_sales')]

    print()
    print("✓ AI Analysis complete!")
    print(f"  Perfect/Good matches: {len(verified_matches)}")
    print(f"  Questionable matches: {len(questionable)}")
    print(f"  Wrong products detected: {len(wrong_products)}")
    print(f"  Items with JungleScout data: {len(with_js_data)}")
    print(f"  Profitable after AI correction: {len(profitable_ai)}")
    print()

    # Show top profitable
    print("=" * 100)
    print("TOP 20 MOST PROFITABLE (AI-VERIFIED)")
    print("=" * 100)
    print(f"{'Description':<45} {'Profit':<10} {'ROI':<8} {'Match':<12} {'JS Sales':<12}")
    print("-" * 100)

    for item in profitable_ai[:20]:
        desc = item.get('description', '')[:43]
        profit = float(item.get('ai_corrected_profit', 0))
        roi = float(item.get('ai_corrected_roi', 0))
        match = item.get('ai_match_quality', 'N/A')
        js_sales = item.get('js_monthly_sales', 'N/A')

        print(f"{desc:<45} ${profit:>8.2f} {roi:>6.0f}% {match:<12} {js_sales:<12}")

    print()
    print(f"✅ Results saved to: {output_file}")

    # Save verified profitable list
    verified_output = 'fba_AI_VERIFIED_profitable.csv'
    if profitable_ai:
        with open(verified_output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=profitable_ai[0].keys())
            writer.writeheader()
            writer.writerows(profitable_ai)
        print(f"✅ Verified profitable items: {verified_output}")


if __name__ == '__main__':
    main()
