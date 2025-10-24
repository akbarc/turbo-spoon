"""
FBA Profit Analyzer - PARALLEL VERSION
Processes 5-10 products concurrently to reduce processing time by 80-90%

Original: 74 minutes
Parallel: 8-15 minutes
"""

import csv
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from dotenv import load_dotenv

from fba_profit_analyzer import (
    AmazonSPAPI, JungleScoutAPI, FBAProfitAnalyzer,
    is_tobacco_or_vapor_product, is_active_product
)

load_dotenv()


def analyze_product_wrapper(args):
    """Wrapper for parallel execution"""
    product_data, analyzer, idx, total = args

    desc = product_data.get('Description', '')[:60]

    print(f"[{idx}/{total}] Processing: {desc}")

    try:
        result = analyzer.analyze_product(product_data)

        # Print result
        if result['data_source'] == 'TOBACCO_VAPOR_EXCLUDED':
            print(f"  [{idx}] ⊘ Tobacco/Vapor - Skipped")
        elif result['asin']:
            profit = result.get('projected_fba_profit', 0)
            roi = result.get('projected_fba_roi', 0)
            print(f"  [{idx}] ✓ ASIN: {result['asin']}, Profit: ${profit:.2f} ({roi:.1f}% ROI)")
        else:
            print(f"  [{idx}] ✗ Not found")

        return result
    except Exception as e:
        print(f"  [{idx}] ERROR: {e}")
        return None


def process_catalog_parallel(
    input_file: str,
    output_file: str,
    sp_api: AmazonSPAPI,
    js_api: JungleScoutAPI,
    max_workers: int = 5,
    filter_active: bool = True,
    max_products: int = None
):
    """
    Process catalog in parallel

    Args:
        max_workers: Number of concurrent threads (5-10 recommended)
                    Don't go above 10 to avoid hitting API rate limits
    """

    analyzer = FBAProfitAnalyzer(sp_api, js_api)

    print("=" * 80)
    print("FBA PROFIT ANALYZER - PARALLEL MODE")
    print("=" * 80)
    print(f"Concurrent workers: {max_workers}")
    print()

    # Read catalog
    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)

    catalog_total = len(products)
    print(f"Total products in catalog: {catalog_total}")

    # Filter active
    if filter_active:
        products = [p for p in products if is_active_product(p, 12)]
        print(f"Active products (last 12 months): {len(products)}")

    # Filter tobacco
    products = [p for p in products if not is_tobacco_or_vapor_product(p)]
    print(f"After tobacco filtering: {len(products)}")

    # Limit for testing
    if max_products:
        products = products[:max_products]
        print(f"Test mode - processing first {max_products} products")

    total = len(products)
    print()
    print(f"Processing {total} products with {max_workers} concurrent workers...")
    print("=" * 80)
    print()

    start_time = time.time()
    results = []

    # Create work items
    work_items = [(p, analyzer, idx, total) for idx, p in enumerate(products, 1)]

    # Process in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_product = {
            executor.submit(analyze_product_wrapper, item): item
            for item in work_items
        }

        # Collect results as they complete
        for future in as_completed(future_to_product):
            result = future.result()
            if result:
                results.append(result)

    elapsed = time.time() - start_time

    # Write results
    print()
    print("=" * 80)
    print(f"Writing results to: {output_file}")

    if results:
        fieldnames = list(results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        # Statistics
        tobacco_excluded = sum(1 for r in results if r['data_source'] == 'TOBACCO_VAPOR_EXCLUDED')
        found = sum(1 for r in results if r['asin'])
        variation_matched = sum(1 for r in results if 'VARIATION_MATCHED' in r.get('data_source', ''))
        profitable = sum(1 for r in results if r['projected_fba_profit'] > 0)
        total_potential_profit = sum(r['projected_fba_profit'] for r in results if r['projected_fba_profit'] > 0)

        print()
        print("✓ Analysis complete!")
        print(f"  Products processed: {len(results)}")
        print(f"  Tobacco/Vapor excluded: {tobacco_excluded}")
        print(f"  Found on Amazon: {found}")
        print(f"  Variation matched: {variation_matched}")
        print(f"  Potentially profitable: {profitable}")
        print(f"  Total potential monthly profit: ${total_potential_profit:.2f}")
        print()
        print(f"Processing time: {elapsed/60:.1f} minutes")
        print(f"Average: {elapsed/len(results):.2f} seconds per product")
        print()

        # Estimated full run time
        if max_products and max_products < 2226:
            full_estimate = (elapsed / len(results)) * 2226 / 60
            print(f"Estimated full run time (2,226 products): {full_estimate:.1f} minutes")

        print(f"\nResults saved to: {output_file}")
    else:
        print("No results to write")


def main():
    """Main execution"""

    # Load configuration
    SP_REFRESH_TOKEN = os.getenv("SP_REFRESH_TOKEN")
    SP_CLIENT_ID = os.getenv("SP_CLIENT_ID")
    SP_CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
    SP_REGION = os.getenv("SP_REGION", "us-east-1")

    JS_API_NAME = os.getenv("JS_API_NAME")
    JS_API_KEY = os.getenv("JS_API_KEY")

    INPUT_CSV = os.getenv("INPUT_CSV", "MASTER_CONSOLIDATED_ALL_DATA.csv")
    OUTPUT_CSV = os.getenv("OUTPUT_CSV", "fba_profit_analysis_PARALLEL.csv")
    MAX_PRODUCTS = os.getenv("MAX_PRODUCTS")
    FILTER_ACTIVE_ONLY = os.getenv("FILTER_ACTIVE_ONLY", "true").lower() == "true"

    # Parallel settings
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))  # 5 concurrent threads (safe default)

    # Validate configuration
    if not all([SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET]):
        print("ERROR: Amazon SP-API credentials not configured!")
        return

    if not all([JS_API_NAME, JS_API_KEY]):
        print("ERROR: Jungle Scout API credentials not configured!")
        return

    # Initialize APIs
    sp_api = AmazonSPAPI(SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_REGION)
    js_api = JungleScoutAPI(JS_API_NAME, JS_API_KEY)

    # Process catalog
    max_prod = int(MAX_PRODUCTS) if MAX_PRODUCTS else None
    process_catalog_parallel(
        INPUT_CSV,
        OUTPUT_CSV,
        sp_api,
        js_api,
        max_workers=MAX_WORKERS,
        filter_active=FILTER_ACTIVE_ONLY,
        max_products=max_prod
    )


if __name__ == "__main__":
    main()
