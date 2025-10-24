"""
FBA Profit Analyzer - SMART PARALLEL VERSION
Respects API rate limits while maximizing throughput

Strategy:
- Process in batches of 5
- Wait 1 second between batches
- = 5 requests/second (within Amazon's 5 req/sec limit)
- 2,226 products in ~8-10 minutes (vs 74 minutes sequential)
"""

import csv
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from dotenv import load_dotenv
import threading

from fba_profit_analyzer import (
    AmazonSPAPI, JungleScoutAPI, FBAProfitAnalyzer,
    is_tobacco_or_vapor_product, is_active_product
)

load_dotenv()

# Global rate limiter
class RateLimiter:
    """Simple rate limiter using token bucket algorithm"""
    def __init__(self, requests_per_second=5):
        self.requests_per_second = requests_per_second
        self.lock = threading.Lock()
        self.last_request_time = 0

    def wait_if_needed(self):
        """Wait if we're going too fast"""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            min_interval = 1.0 / self.requests_per_second

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()


rate_limiter = RateLimiter(requests_per_second=3)  # Conservative: 3 req/sec for max reliability


def analyze_product_safe(product_data, analyzer, idx, total):
    """Analyze product with rate limiting"""

    desc = product_data.get('Description', '')[:60]

    try:
        # Rate limit before making API calls
        rate_limiter.wait_if_needed()

        result = analyzer.analyze_product(product_data)

        # Print result
        if result['data_source'] == 'TOBACCO_VAPOR_EXCLUDED':
            print(f"[{idx}/{total}] ⊘ {desc}")
        elif result['asin']:
            profit = result.get('projected_fba_profit', 0)
            roi = result.get('projected_fba_roi', 0)

            # Show if alternate UPC was used
            source_indicator = ""
            if 'ALTERNATE_UPC' in result.get('data_source', ''):
                source_indicator = " [ALT]"

            print(f"[{idx}/{total}] ✓ {desc[:40]}{source_indicator} | ${profit:.2f} ({roi:.0f}%)")
        else:
            print(f"[{idx}/{total}] ✗ {desc}")

        return result
    except Exception as e:
        print(f"[{idx}/{total}] ERROR: {desc} - {str(e)[:50]}")
        return None


def process_catalog_smart_parallel(
    input_file: str,
    output_file: str,
    sp_api: AmazonSPAPI,
    js_api: JungleScoutAPI,
    batch_size: int = 10,
    filter_active: bool = True,
    max_products: int = None
):
    """
    Process catalog in smart parallel batches

    Args:
        batch_size: Products per batch (10 = process 10, wait 1 sec, next 10)
    """

    analyzer = FBAProfitAnalyzer(sp_api, js_api)

    print("=" * 80)
    print("FBA PROFIT ANALYZER - SMART PARALLEL MODE")
    print("=" * 80)
    print(f"Batch size: {batch_size} products")
    print(f"Rate limit: 3 requests/second (with retry logic)")
    print()

    # Read catalog
    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)

    catalog_total = len(products)

    # Filter active
    if filter_active:
        products = [p for p in products if is_active_product(p, 12)]

    # Filter tobacco
    products = [p for p in products if not is_tobacco_or_vapor_product(p)]

    # Limit for testing
    if max_products:
        products = products[:max_products]

    total = len(products)

    print(f"Total catalog: {catalog_total}")
    print(f"Active non-tobacco: {len([p for p in products if not is_tobacco_or_vapor_product(p)])}")
    print(f"Processing: {total} products")
    print()
    print("=" * 80)
    print()

    start_time = time.time()
    results = []

    # Process in batches
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = products[batch_start:batch_end]

        print(f"\nBatch {batch_start//batch_size + 1}: Processing products {batch_start+1}-{batch_end}")

        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [
                executor.submit(
                    analyze_product_safe,
                    product,
                    analyzer,
                    batch_start + idx + 1,
                    total
                )
                for idx, product in enumerate(batch)
            ]

            # Wait for batch to complete
            batch_results = [f.result() for f in futures if f.result()]
            results.extend(batch_results)

    elapsed = time.time() - start_time

    # Write results
    print()
    print("=" * 80)
    print(f"Writing results to: {output_file}")

    if results:
        # Get all possible fieldnames from all results
        all_fields = set()
        for r in results:
            all_fields.update(r.keys())
        fieldnames = sorted(all_fields)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        # Statistics
        found = sum(1 for r in results if r.get('asin'))
        profitable = sum(1 for r in results if r.get('projected_fba_profit', 0) > 0)
        total_profit = sum(r.get('projected_fba_profit', 0) for r in results if r.get('projected_fba_profit', 0) > 0)

        print()
        print("✓ Analysis complete!")
        print(f"  Products processed: {len(results)}")
        print(f"  Found on Amazon: {found} ({found/len(results)*100:.1f}%)")
        print(f"  Potentially profitable: {profitable}")
        print(f"  Total potential profit: ${total_profit:.2f}")
        print()
        print(f"⚡ Processing time: {elapsed/60:.1f} minutes")
        print(f"   Average: {elapsed/len(results):.2f} sec/product")
        print()

        # Estimated full run time
        if max_products and max_products < 2226:
            full_estimate = (elapsed / len(results)) * 2226 / 60
            sequential_time = 2226 * 2 / 60  # Old sequential time
            speedup = sequential_time / full_estimate
            print(f"📊 Full run estimate (2,226 products):")
            print(f"   Smart Parallel: {full_estimate:.1f} minutes")
            print(f"   Old Sequential: {sequential_time:.0f} minutes")
            print(f"   Speedup: {speedup:.1f}x faster!")

        print(f"\n✅ Results saved to: {output_file}")
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
    OUTPUT_CSV = os.getenv("OUTPUT_CSV", "fba_profit_analysis_SMART.csv")
    MAX_PRODUCTS = os.getenv("MAX_PRODUCTS")
    FILTER_ACTIVE_ONLY = os.getenv("FILTER_ACTIVE_ONLY", "true").lower() == "true"
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

    # Validate
    if not all([SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET, JS_API_NAME, JS_API_KEY]):
        print("ERROR: API credentials not configured!")
        return

    # Initialize APIs
    sp_api = AmazonSPAPI(SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_REGION)
    js_api = JungleScoutAPI(JS_API_NAME, JS_API_KEY)

    # Process
    max_prod = int(MAX_PRODUCTS) if MAX_PRODUCTS else None
    process_catalog_smart_parallel(
        INPUT_CSV,
        OUTPUT_CSV,
        sp_api,
        js_api,
        batch_size=BATCH_SIZE,
        filter_active=FILTER_ACTIVE_ONLY,
        max_products=max_prod
    )


if __name__ == "__main__":
    main()
