"""
Fix FBA Analysis Pack Size Mismatches - Simple Regex Version
Uses pattern matching to extract pack sizes and normalize costs
"""

import csv
import re

def extract_pack_size(text):
    """Extract pack size from text using regex patterns"""

    if not text:
        return 1

    text_upper = text.upper()

    # Pattern 1: "Pack of 12", "Pack of 24"
    match = re.search(r'PACK OF (\d+)', text_upper)
    if match:
        return int(match.group(1))

    # Pattern 2: "24CT", "12 CT", "36 COUNT"
    match = re.search(r'(\d+)\s*CT(?:\s|$|,)', text_upper)
    if match:
        return int(match.group(1))

    match = re.search(r'(\d+)\s*COUNT', text_upper)
    if match:
        return int(match.group(1))

    # Pattern 3: "24-Pack", "12 Pack"
    match = re.search(r'(\d+)[\s-]*PACK', text_upper)
    if match:
        return int(match.group(1))

    # Pattern 4: "(Pack of 12)", "Case of 24"
    match = re.search(r'CASE OF (\d+)', text_upper)
    if match:
        return int(match.group(1))

    # Pattern 5: "x 24", "× 12"
    match = re.search(r'[X×]\s*(\d+)', text_upper)
    if match:
        return int(match.group(1))

    # Default to 1 if no pack size found
    return 1


def analyze_pack_mismatch(your_desc, amazon_title, your_cost, amazon_price):
    """Analyze pack size mismatch and calculate corrections"""

    # Extract pack sizes
    your_pack = extract_pack_size(your_desc)
    amazon_pack = extract_pack_size(amazon_title)

    # Calculate how many of YOUR units needed to match Amazon's pack
    # If you sell 1 and Amazon sells 12, you need 12 of yours (multiply cost by 12)
    # If you sell 24 and Amazon sells 24, you need 1 of yours (multiply cost by 1)
    if your_pack > 0:
        units_needed = amazon_pack / your_pack
        normalized_cost = your_cost * units_needed
        pack_ratio = units_needed
    else:
        pack_ratio = 1
        normalized_cost = your_cost

    # Determine match confidence
    pack_match = "YES" if abs(pack_ratio - 1.0) < 0.01 else "NO"

    # Confidence based on what we found
    if your_pack > 1 and amazon_pack > 1:
        confidence = "HIGH"
    elif your_pack == 1 and amazon_pack == 1:
        confidence = "MEDIUM"
    elif your_pack > 1 or amazon_pack > 1:
        confidence = "HIGH"
    else:
        confidence = "LOW"

    return {
        'your_pack_size': your_pack,
        'amazon_pack_size': amazon_pack,
        'pack_ratio': round(pack_ratio, 2),
        'normalized_cost': round(normalized_cost, 2),
        'pack_match': pack_match,
        'confidence': confidence
    }


def process_csv():
    """Process the FBA analysis CSV and fix pack sizes"""

    input_file = 'fba_profit_analysis_FULL_RUN.csv'
    output_file = 'fba_profit_analysis_CORRECTED.csv'

    print("=" * 100)
    print("FBA PACK SIZE CORRECTION - Pattern Matching")
    print("=" * 100)
    print()

    # Read CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total items: {len(rows)}")

    # Process each row
    corrected_count = 0
    results = []

    for idx, row in enumerate(rows, 1):
        # Skip items not found on Amazon
        if not row.get('asin'):
            results.append(row)
            continue

        desc = row.get('description', '')
        amazon_title = row.get('amazon_title', '')
        your_cost = float(row.get('your_cost', 0))
        amazon_price = float(row.get('projected_amazon_price', 0))
        fba_fee_total = float(row.get('fba_fee_total', 0))

        # Skip if no data
        if not desc or not amazon_title or your_cost == 0:
            results.append(row)
            continue

        # Analyze pack sizes
        analysis = analyze_pack_mismatch(desc, amazon_title, your_cost, amazon_price)

        # Add analysis to row
        row['your_pack_size'] = analysis['your_pack_size']
        row['amazon_pack_size'] = analysis['amazon_pack_size']
        row['pack_ratio'] = analysis['pack_ratio']
        row['normalized_cost'] = analysis['normalized_cost']
        row['pack_match'] = analysis['pack_match']
        row['pack_confidence'] = analysis['confidence']

        # Recalculate profit
        normalized_cost = analysis['normalized_cost']
        corrected_profit = amazon_price - fba_fee_total - normalized_cost
        corrected_roi = (corrected_profit / normalized_cost * 100) if normalized_cost > 0 else 0

        row['corrected_fba_profit'] = round(corrected_profit, 2)
        row['corrected_fba_roi'] = round(corrected_roi, 1)

        # Track corrections
        if analysis['pack_ratio'] > 1.1:  # More than 10% difference
            corrected_count += 1
            if idx <= 20 or corrected_count <= 10:  # Show first few
                print(f"[{idx}/{len(rows)}] {desc[:50]}")
                print(f"    Your pack: {analysis['your_pack_size']} | Amazon pack: {analysis['amazon_pack_size']} | Ratio: {analysis['pack_ratio']}x")
                print(f"    Cost: ${your_cost:.2f} → ${normalized_cost:.2f}")
                orig_profit = float(row.get('projected_fba_profit', 0))
                print(f"    Profit: ${orig_profit:.2f} → ${corrected_profit:.2f}")
                print()

        results.append(row)

    # Write corrected CSV
    print()
    print("=" * 100)
    print(f"Writing corrected results to: {output_file}")

    if results:
        # Get all fieldnames
        fieldnames = list(results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    # Summary statistics
    items_on_amazon = [r for r in results if r.get('asin')]
    pack_mismatches = [r for r in items_on_amazon if r.get('pack_match') == 'NO']
    profitable_corrected = [r for r in items_on_amazon if float(r.get('corrected_fba_profit', 0)) > 0]

    print()
    print("✓ Correction complete!")
    print(f"  Items on Amazon: {len(items_on_amazon)}")
    print(f"  Pack mismatches found: {len(pack_mismatches)}")
    print(f"  Profitable after correction: {len(profitable_corrected)}")
    print()

    # Show corrected top items
    profitable_corrected.sort(key=lambda x: float(x.get('corrected_fba_profit', 0)), reverse=True)

    print("=" * 100)
    print("TOP 20 MOST PROFITABLE (CORRECTED FOR PACK SIZE)")
    print("=" * 100)
    print(f"{'Description':<45} {'Profit':<10} {'ROI':<8} {'Pack Match':<12} {'Cost Fix':<15}")
    print("-" * 100)

    for item in profitable_corrected[:20]:
        desc = item.get('description', '')[:43]
        profit = float(item.get('corrected_fba_profit', 0))
        roi = float(item.get('corrected_fba_roi', 0))
        pack_match = item.get('pack_match', 'UNKNOWN')
        your_pack = item.get('your_pack_size', 1)
        amazon_pack = item.get('amazon_pack_size', 1)
        cost_fix = f"${item.get('your_cost', 0)} → ${item.get('normalized_cost', 0)}"

        print(f"{desc:<45} ${profit:>8.2f} {roi:>6.0f}% {pack_match:<12} {cost_fix:<15}")

    print()
    print("=" * 100)
    print("NOTES:")
    print("=" * 100)
    print("- 'Pack Match: YES' = Your pack size matches Amazon (reliable)")
    print("- 'Pack Match: NO' = Cost was adjusted for different pack sizes")
    print("- 'Cost Fix' shows: your_cost → normalized_cost (to match Amazon pack)")
    print()
    print(f"✅ Results saved to: {output_file}")


if __name__ == '__main__':
    process_csv()
