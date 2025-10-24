"""
Test Product Filtering - No API credentials needed
Shows which products would be analyzed based on filters
"""

import csv
from datetime import datetime, timedelta
import re
from typing import Dict, Optional


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from CSV"""
    if not date_str or date_str.strip() == '':
        return None

    date_str = date_str.strip()

    formats = [
        '%m/%d/%y',    # 10/9/25
        '%m/%d/%Y',    # 10/09/2025
        '%Y-%m-%d',    # 2025-10-09
        '%m-%d-%Y',    # 10-09-2025
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if parsed.year < 100:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed
        except ValueError:
            continue

    return None


def is_active_product(product_data: Dict, months_back: int = 12) -> bool:
    """Check if product is active (sold recently AND purchased recently)"""
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)

    # Check LastSold
    last_sold_str = product_data.get('LastSold', '')
    last_sold = parse_date(last_sold_str)

    # Check LastReceived
    last_received_str = product_data.get('LastReceived', '')
    last_received = parse_date(last_received_str)

    has_recent_sale = last_sold and last_sold >= cutoff_date
    has_recent_purchase = last_received and last_received >= cutoff_date

    return has_recent_sale and has_recent_purchase


def is_tobacco_or_vapor_product(product_data: Dict) -> bool:
    """Check if product is tobacco/vapor"""
    tobacco_categories = {
        'CIGARETTE', 'LT-TAX PAID', 'CIGAR', 'VAPE', 'VAPOR', 'E-CIG', 'ECIG',
        'TOBACCO', 'NICOTINE', 'JUUL', 'VUSE'
    }

    tobacco_keywords = {
        'cigarette', 'cigar', 'tobacco', 'vape', 'vapor', 'e-cig', 'ecig',
        'juul', 'vuse', 'nicotine', 'dip', 'chew', 'snus', 'hookah', 'shisha',
        'mod', 'pod system', 'salt nic', 'freebase', 'nic salt'
    }

    allowed_accessories = {
        'rolling paper', 'raw', 'zig zag', 'zigzag', 'blunt wrap', 'cone',
        'lighter', 'match', 'ashtray', 'grinder', 'rolling machine',
        'filter', 'tip', 'hemp wick'
    }

    category = str(product_data.get('CurrentCategory', '')).upper()
    main_category = str(product_data.get('MainCategory', '')).upper()
    description = str(product_data.get('Description', '')).lower()

    # Check category
    if category in tobacco_categories:
        if any(acc in description for acc in allowed_accessories):
            return False
        return True

    # Check main category
    if 'TOBACCO' in main_category or 'NICOTINE' in main_category:
        if any(acc in description for acc in allowed_accessories):
            return False
        return True

    # Check description
    if any(acc in description for acc in allowed_accessories):
        return False

    if any(kw in description for kw in tobacco_keywords):
        return True

    return False


def extract_pack_size(text: str) -> Optional[int]:
    """Extract pack size from description"""
    if not text:
        return None

    text = text.upper()

    # Pattern 1: "12CT", "24 CT"
    match = re.search(r'(\d+)\s*[-]?\s*CT\b', text)
    if match:
        return int(match.group(1))

    # Pattern 2: "12 COUNT"
    match = re.search(r'(\d+)\s*[-]?\s*COUNT\b', text)
    if match:
        return int(match.group(1))

    # Pattern 3: "12 PACK"
    match = re.search(r'(\d+)\s*[-]?\s*(PACK|PK)\b', text)
    if match:
        return int(match.group(1))

    # Pattern 4: "SINGLE", "EACH"
    if any(word in text for word in ['SINGLE', 'EACH', '1CT', '1 CT']):
        return 1

    # Pattern 5: "BOX OF 12"
    match = re.search(r'(?:DISPLAY|BOX|CASE)\s+OF\s+(\d+)', text)
    if match:
        return int(match.group(1))

    return None


def main():
    input_file = "master_product_catalog.csv"

    print("=" * 80)
    print("FBA PRODUCT FILTER TEST")
    print("=" * 80)
    print()

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)

    total_products = len(products)

    # Apply filters
    active_products = [p for p in products if is_active_product(p, 12)]
    non_tobacco = [p for p in active_products if not is_tobacco_or_vapor_product(p)]
    tobacco_filtered = [p for p in active_products if is_tobacco_or_vapor_product(p)]

    print(f"FILTERING RESULTS:")
    print(f"  Total products in catalog: {total_products}")
    print(f"  Active (sold & purchased in last 12 months): {len(active_products)}")
    print(f"  Inactive products: {total_products - len(active_products)}")
    print()
    print(f"AFTER TOBACCO FILTERING:")
    print(f"  Active non-tobacco products: {len(non_tobacco)}")
    print(f"  Active tobacco products (excluded): {len(tobacco_filtered)}")
    print()

    # Show first 10 products that WOULD be analyzed
    print("=" * 80)
    print(f"FIRST 10 PRODUCTS THAT WOULD BE ANALYZED:")
    print("=" * 80)
    print()

    for idx, product in enumerate(non_tobacco[:10], 1):
        desc = product.get('Description', '')
        upc = product.get('ItemLookupCode', '')
        cost = product.get('Cost', '')
        last_sold = product.get('LastSold', '')
        last_received = product.get('LastReceived', '')
        pack_size = extract_pack_size(desc)

        print(f"[{idx}] {desc[:60]}")
        print(f"    UPC: {upc}")
        print(f"    Cost: ${cost}")
        print(f"    Pack Size: {pack_size or 'Unknown'}")
        print(f"    Last Sold: {last_sold}, Last Received: {last_received}")
        print()

    # Show some tobacco products that would be SKIPPED
    print("=" * 80)
    print(f"SAMPLE TOBACCO PRODUCTS THAT WOULD BE SKIPPED:")
    print("=" * 80)
    print()

    for idx, product in enumerate(tobacco_filtered[:5], 1):
        desc = product.get('Description', '')
        category = product.get('CurrentCategory', '')

        print(f"[{idx}] {desc[:60]}")
        print(f"    Category: {category}")
        print(f"    ⊘ TOBACCO/VAPOR - Would be skipped")
        print()

    # Estimate processing time
    print("=" * 80)
    print("ESTIMATED PROCESSING TIME:")
    print("=" * 80)
    print()
    print(f"Products to analyze: {len(non_tobacco)}")
    print(f"Tobacco products skipped: {len(tobacco_filtered)}")
    print()
    print(f"At 2 seconds per product:")
    print(f"  Processing time: ~{len(non_tobacco) * 2 / 60:.1f} minutes")
    print()
    print(f"API calls saved by filtering:")
    print(f"  Tobacco filtered: {len(tobacco_filtered) * 3} calls saved")
    print(f"  Inactive filtered: {(total_products - len(active_products)) * 3} calls saved")
    print(f"  Total saved: {(len(tobacco_filtered) + (total_products - len(active_products))) * 3} API calls!")
    print()


if __name__ == "__main__":
    main()
