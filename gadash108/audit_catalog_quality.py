import os
import pandas as pd
import json
import random
from openai import OpenAI

print('╔════════════════════════════════════════════════════════════════╗')
print('║       MANUAL CATALOG QUALITY AUDIT - AI DEEP REVIEW          ║')
print('╚════════════════════════════════════════════════════════════════╝')
print()

# Initialize OpenAI
client = OpenAI(api_key='YOUR_OPENAI_API_KEY_HERE')

# Load consolidated catalog
df = pd.read_csv('MASTER_CONSOLIDATED_ALL_DATA.csv')

print(f'Loaded {len(df):,} products for quality audit')
print()

# Sample strategy: Get diverse samples
print('Sampling strategy:')
print('  - 10 random from each main category (120 total)')
print('  - 20 with UPC data (check UPC match quality)')
print('  - 20 without UPC data (check our categorization)')
print('  - 10 FAIR/POOR quality items')
print('  - 10 EXCELLENT quality items')
print('  Total: ~180 products to manually review')
print()

samples = []

# Sample from each category
for category in df['MainCategory'].unique():
    cat_items = df[df['MainCategory'] == category]
    sample_size = min(10, len(cat_items))
    samples.extend(cat_items.sample(n=sample_size).to_dict('records'))

# Add UPC data samples
with_upc = df[df['UPC_DataAvailable'] == 'Yes'].sample(n=min(20, len(df[df['UPC_DataAvailable'] == 'Yes'])))
samples.extend(with_upc.to_dict('records'))

# Add without UPC samples
without_upc = df[df['UPC_DataAvailable'] == 'No'].sample(n=min(20, len(df[df['UPC_DataAvailable'] == 'No'])))
samples.extend(without_upc.to_dict('records'))

# Add quality extremes
fair_poor = df[df['AI_DataQuality'].isin(['FAIR', 'POOR'])].sample(n=min(10, len(df[df['AI_DataQuality'].isin(['FAIR', 'POOR'])])))
samples.extend(fair_poor.to_dict('records'))

excellent = df[df['AI_DataQuality'] == 'EXCELLENT'].sample(n=min(10, len(df[df['AI_DataQuality'] == 'EXCELLENT'])))
samples.extend(excellent.to_dict('records'))

# Remove duplicates
seen_ids = set()
unique_samples = []
for item in samples:
    if item['ItemID'] not in seen_ids:
        seen_ids.add(item['ItemID'])
        unique_samples.append(item)

print(f'Selected {len(unique_samples)} unique products for deep review')
print()

# Process in chunks of 5 (smaller to avoid timeouts)
chunk_size = 5
audit_results = []

for chunk_idx in range(0, len(unique_samples), chunk_size):
    chunk = unique_samples[chunk_idx:chunk_idx + chunk_size]
    chunk_num = chunk_idx // chunk_size + 1
    total_chunks = (len(unique_samples) + chunk_size - 1) // chunk_size

    print(f'Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} products)...')

    # Prepare data for AI review
    products_for_review = []
    for item in chunk:
        products_for_review.append({
            'ItemID': item['ItemID'],
            'Description': item['Description'],
            'Brand': item['Brand'],
            'MainCategory': item['MainCategory'],
            'Subcategory': item['Subcategory'],
            'Size': item['Size'],
            'UPC_Available': item['UPC_DataAvailable'],
            'UPC_ProductName': item.get('UPC_ProductName', ''),
            'UPC_Brand': item.get('UPC_Brand', ''),
            'UPC_Category': item.get('UPC_Category', ''),
            'UPC_Size': item.get('UPC_Size', ''),
            'UPC_ImageURL': item.get('UPC_ImageURL', ''),
            'AI_VerifiedBrand': item.get('AI_VerifiedBrand', ''),
            'AI_VerifiedCategory': item.get('AI_VerifiedCategory', ''),
            'AI_DataQuality': item.get('AI_DataQuality', ''),
            'Price': item.get('Price', '')
        })

    # AI Manual Review
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a product data quality auditor. Review each product and assess:

1. BRAND ACCURACY: Is the extracted brand correct based on the description?
2. CATEGORY ACCURACY: Is the category/subcategory appropriate?
3. PACK SIZE ACCURACY: Does the extracted size match what's in the description?
4. UPC MATCH QUALITY: If UPC data exists, does it actually match our product? Or is it a different product?
5. IMAGE AVAILABILITY: Is there a UPC image URL?
6. OVERALL ACCURACY: How well organized is this product?

For each product, return JSON:
{
  "ItemID": "the ID",
  "brand_correct": true/false,
  "brand_issue": "explanation if incorrect",
  "category_correct": true/false,
  "category_issue": "explanation if incorrect",
  "size_correct": true/false,
  "size_issue": "explanation if incorrect",
  "upc_match_quality": "PERFECT/GOOD/PARTIAL/MISMATCH/NO_UPC",
  "upc_match_explanation": "how well UPC data matches",
  "has_image": true/false,
  "overall_score": 1-10,
  "issues_found": "list of any problems",
  "recommendations": "suggestions for improvement"
}

Return array of objects, one per product."""},
                {"role": "user", "content": f"Review these {len(products_for_review)} products:\n\n{json.dumps(products_for_review, indent=2)}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=120
        )

        result = json.loads(response.choices[0].message.content)

        # Extract results (handle both array and object with products key)
        if isinstance(result, dict) and 'products' in result:
            audit_results.extend(result['products'])
        elif isinstance(result, dict) and 'reviews' in result:
            audit_results.extend(result['reviews'])
        elif isinstance(result, list):
            audit_results.extend(result)
        else:
            # Single object wrapped - try to extract list
            for key in result:
                if isinstance(result[key], list):
                    audit_results.extend(result[key])
                    break
            # If still no results, treat each key-value as a review if it's a dict
            if not audit_results or len(audit_results) == 0:
                for key, value in result.items():
                    if isinstance(value, dict) and 'ItemID' in value:
                        audit_results.append(value)

        print(f'  ✅ Chunk {chunk_num} reviewed ({len(audit_results)} total so far)')

    except Exception as e:
        print(f'  ❌ Error on chunk {chunk_num}: {e}')

    print()

print()
print('═' * 80)
print('AUDIT COMPLETE - ANALYZING RESULTS')
print('═' * 80)
print()

# Analyze results
if audit_results:
    # Calculate statistics
    total_reviewed = len(audit_results)

    brand_correct = sum(1 for r in audit_results if r.get('brand_correct', False))
    category_correct = sum(1 for r in audit_results if r.get('category_correct', False))
    size_correct = sum(1 for r in audit_results if r.get('size_correct', False))

    has_image = sum(1 for r in audit_results if r.get('has_image', False))

    upc_quality = {}
    for r in audit_results:
        quality = r.get('upc_match_quality', 'UNKNOWN')
        upc_quality[quality] = upc_quality.get(quality, 0) + 1

    avg_score = sum(r.get('overall_score', 0) for r in audit_results) / total_reviewed if total_reviewed > 0 else 0

    print(f'📊 QUALITY AUDIT RESULTS ({total_reviewed} products manually reviewed)')
    print('─' * 80)
    print()
    print('✅ ACCURACY RATES:')
    print(f'   Brand Extraction:     {brand_correct}/{total_reviewed} correct ({brand_correct/total_reviewed*100:.1f}%)')
    print(f'   Category Assignment:  {category_correct}/{total_reviewed} correct ({category_correct/total_reviewed*100:.1f}%)')
    print(f'   Pack Size Extraction: {size_correct}/{total_reviewed} correct ({size_correct/total_reviewed*100:.1f}%)')
    print()
    print('🌐 UPC ENRICHMENT QUALITY:')
    for quality, count in sorted(upc_quality.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_reviewed * 100
        print(f'   {quality:<15} {count:>4} ({pct:>5.1f}%)')
    print()
    print(f'📸 IMAGE AVAILABILITY: {has_image}/{total_reviewed} products ({has_image/total_reviewed*100:.1f}%)')
    print()
    print(f'⭐ AVERAGE QUALITY SCORE: {avg_score:.1f}/10')
    print()

    # Show examples of issues found
    print('🔍 TOP ISSUES DISCOVERED:')
    print('─' * 80)

    issues_by_product = {}
    for r in audit_results:
        item_id = r.get('ItemID', 'Unknown')
        issues = r.get('issues_found', '')
        if issues and issues != 'None' and issues != '':
            issues_by_product[item_id] = {
                'issues': issues,
                'score': r.get('overall_score', 0),
                'brand_issue': r.get('brand_issue', ''),
                'category_issue': r.get('category_issue', ''),
                'size_issue': r.get('size_issue', ''),
                'upc_match': r.get('upc_match_explanation', '')
            }

    # Show worst 10
    worst = sorted(issues_by_product.items(), key=lambda x: x[1]['score'])[:10]
    for item_id, data in worst:
        # Find product in df
        product = df[df['ItemID'] == item_id]
        if not product.empty:
            product = product.iloc[0]
            print(f"\nItemID {item_id}: {product['Description'][:60]}")
            print(f"  Score: {data['score']}/10")
            if data['brand_issue']:
                print(f"  Brand Issue: {data['brand_issue']}")
            if data['category_issue']:
                print(f"  Category Issue: {data['category_issue']}")
            if data['size_issue']:
                print(f"  Size Issue: {data['size_issue']}")
            if data['upc_match']:
                print(f"  UPC Match: {data['upc_match']}")

    print()
    print('═' * 80)
    print('RECOMMENDATIONS FOR IMPROVEMENT')
    print('═' * 80)

    # Collect all recommendations
    all_recommendations = []
    for r in audit_results:
        recs = r.get('recommendations', '')
        if recs and recs != 'None' and recs != '':
            all_recommendations.append(recs)

    # Show unique recommendations
    unique_recs = list(set(all_recommendations))[:15]
    for i, rec in enumerate(unique_recs, 1):
        print(f"{i}. {rec}")

    # Save full audit results
    with open('catalog_quality_audit_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_reviewed': total_reviewed,
            'accuracy_rates': {
                'brand': f'{brand_correct}/{total_reviewed} ({brand_correct/total_reviewed*100:.1f}%)',
                'category': f'{category_correct}/{total_reviewed} ({category_correct/total_reviewed*100:.1f}%)',
                'size': f'{size_correct}/{total_reviewed} ({size_correct/total_reviewed*100:.1f}%)',
            },
            'upc_quality': upc_quality,
            'image_availability': f'{has_image}/{total_reviewed} ({has_image/total_reviewed*100:.1f}%)',
            'average_score': avg_score,
            'detailed_results': audit_results
        }, f, indent=2)

    print()
    print(f'✅ Full audit results saved to: catalog_quality_audit_results.json')
    print()

    # Generate summary
    print('═' * 80)
    print('FINAL ASSESSMENT')
    print('═' * 80)
    print()

    if avg_score >= 8.5:
        grade = 'EXCELLENT'
        assessment = 'Catalog is very well organized with high accuracy'
    elif avg_score >= 7.0:
        grade = 'GOOD'
        assessment = 'Catalog is well organized with minor issues'
    elif avg_score >= 5.5:
        grade = 'FAIR'
        assessment = 'Catalog needs improvement in several areas'
    else:
        grade = 'NEEDS WORK'
        assessment = 'Significant issues found, manual review recommended'

    print(f'📈 OVERALL GRADE: {grade} ({avg_score:.1f}/10)')
    print(f'📝 ASSESSMENT: {assessment}')
    print()
    print(f'✅ Brand Accuracy: {brand_correct/total_reviewed*100:.1f}%')
    print(f'✅ Category Accuracy: {category_correct/total_reviewed*100:.1f}%')
    print(f'✅ Size Accuracy: {size_correct/total_reviewed*100:.1f}%')
    print()

else:
    print('❌ No audit results generated')
