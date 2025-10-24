"""
FBA Profit Analyzer - Enhanced Version
Uses MASTER_CONSOLIDATED_ALL_DATA with alternate barcodes
"""

import csv
from fba_profit_analyzer import (
    AmazonSPAPI, JungleScoutAPI, FBAProfitAnalyzer,
    is_tobacco_or_vapor_product, is_active_product
)
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize APIs
sp_api = AmazonSPAPI(
    os.getenv("SP_REFRESH_TOKEN"),
    os.getenv("SP_CLIENT_ID"),
    os.getenv("SP_CLIENT_SECRET"),
    "us-east-1"
)

js_api = JungleScoutAPI(
    os.getenv("JS_API_NAME"),
    os.getenv("JS_API_KEY")
)

analyzer = FBAProfitAnalyzer(sp_api, js_api)

print("=" * 80)
print("FBA PROFIT ANALYZER - WITH ALTERNATE BARCODES")
print("=" * 80)
print()

# Read master consolidated data
with open('MASTER_CONSOLIDATED_ALL_DATA.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    products = list(reader)

# Filter for active products only
print(f"Total products: {len(products)}")
active_products = [p for p in products if is_active_product(p, 12)]
print(f"Active products (last 12 months): {len(active_products)}")

# Filter out tobacco
non_tobacco = [p for p in active_products if not is_tobacco_or_vapor_product(p)]
print(f"Active non-tobacco: {len(non_tobacco)}")
print()

# Test first 10
test_products = non_tobacco[:10]

print(f"Testing first {len(test_products)} products:")
print("=" * 80)
print()

for idx, product in enumerate(test_products, 1):
    desc = product.get('Description', '')
    primary_upc = product.get('ItemLookupCode', '')
    alternates = product.get('AlternateBarcodes', '')

    print(f"[{idx}] {desc[:60]}")
    print(f"  Primary UPC: {primary_upc}")

    # Try primary UPC first
    result = sp_api.lookup_product_by_upc(primary_upc)

    if result:
        asin = result.get('asin')
        print(f"  ✓ FOUND via primary UPC!")
        print(f"    ASIN: {asin}")
    elif alternates and alternates.strip():
        # Try alternate barcodes
        alt_list = [a.strip() for a in alternates.split('|') if a.strip()]
        print(f"  ✗ Primary failed. Trying {len(alt_list)} alternates...")

        asin = None
        for alt_upc in alt_list[:5]:  # Try first 5 alternates
            result = sp_api.lookup_product_by_upc(alt_upc)
            if result:
                asin = result.get('asin')
                print(f"  ✓ FOUND via alternate: {alt_upc}")
                print(f"    ASIN: {asin}")
                break

        if not asin:
            print(f"  ✗ None of the alternates found either")
    else:
        print(f"  ✗ Not found, no alternates available")

    print()

print("=" * 80)
print("SUMMARY:")
print("=" * 80)
print()
print("Next steps:")
print("1. If alternates help → Update main script to use them")
print("2. If still not found → Try keyword search with UPC_ProductName")
print("3. Or accept that wholesale UPCs don't match Amazon retail")
