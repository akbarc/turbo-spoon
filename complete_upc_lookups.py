#!/usr/bin/env python3
"""
Complete UPC lookups for cigarette inventory
Processes remaining barcodes that hit rate limits
"""

import pandas as pd
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

# UPC API Configuration
UPC_API_KEY = 'abb286e1762c2760f56d08bdb9c96b2d7128e61f10113cbc7693d37e473eb6f0'
UPC_API_URL = 'https://go-upc.com/api/v1/code/'

def fetch_upc_data(barcode):
    """Fetch UPC data from go-upc API for a single barcode"""
    try:
        headers = {
            'Authorization': f'Bearer {UPC_API_KEY}'
        }
        url = f'{UPC_API_URL}{barcode}'
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                'barcode': barcode,
                'success': True,
                'data': json.dumps(data, ensure_ascii=False)
            }
        else:
            return {
                'barcode': barcode,
                'success': False,
                'data': json.dumps({'error': f'HTTP {response.status_code}'})
            }
    except Exception as e:
        return {
            'barcode': barcode,
            'success': False,
            'data': json.dumps({'error': str(e)})
        }

def fetch_batch_with_delay(barcodes, batch_size=50, delay_seconds=2):
    """Fetch UPC data in batches with delays to avoid rate limiting"""
    results = {}
    total = len(barcodes)
    completed = 0
    successful = 0

    print(f"\n🔍 Fetching UPC data for {total} barcodes...")
    print(f"   Processing in batches of {batch_size} with {delay_seconds}s delays")

    start_time = time.time()

    # Split into batches
    for i in range(0, total, batch_size):
        batch = barcodes[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} barcodes)...")

        # Process this batch in parallel
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_barcode = {
                executor.submit(fetch_upc_data, barcode): barcode
                for barcode in batch
            }

            batch_success = 0
            for future in as_completed(future_to_barcode):
                result = future.result()
                results[result['barcode']] = result['data']
                completed += 1

                if result['success']:
                    successful += 1
                    batch_success += 1

        elapsed = time.time() - start_time
        rate = completed / elapsed if elapsed > 0 else 0
        print(f"   ✅ Batch complete: {batch_success}/{len(batch)} successful")
        print(f"   📊 Overall progress: {completed}/{total} ({completed/total*100:.1f}%) - Success: {successful}/{completed}")
        print(f"   ⚡ Rate: {rate:.1f} requests/sec")

        # Delay between batches (except for last batch)
        if i + batch_size < total:
            print(f"   ⏸️  Waiting {delay_seconds} seconds before next batch...")
            time.sleep(delay_seconds)

    elapsed = time.time() - start_time
    print(f"\n✅ All batches complete in {elapsed:.1f} seconds")
    print(f"   Final success rate: {successful}/{total} ({successful/total*100:.1f}%)")

    return results

def main():
    print("="*100)
    print("COMPLETE REMAINING UPC LOOKUPS")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Find the most recent export file
    import glob
    export_files = glob.glob('cigarette_inventory_export_*.xlsx')
    if not export_files:
        print("❌ No export files found!")
        return

    latest_file = max(export_files, key=lambda x: x)
    print(f"📂 Reading: {latest_file}")

    # Read the Excel file
    df = pd.read_excel(latest_file, sheet_name='Cigarette_Inventory')
    print(f"✅ Loaded {len(df)} products")

    # Find barcodes with rate limit errors
    df['needs_lookup'] = df['UPC_RawData_Primary'].fillna('').str.contains('HTTP 429|^$', regex=True)
    failed_items = df[df['needs_lookup']].copy()

    print(f"\n🔍 Found {len(failed_items)} items needing UPC lookup:")
    print(f"   - Rate limited (HTTP 429): {df['UPC_RawData_Primary'].fillna('').str.contains('HTTP 429').sum()}")
    print(f"   - Empty/missing: {df['UPC_RawData_Primary'].fillna('').str.len().eq(0).sum()}")

    if len(failed_items) == 0:
        print("\n✅ All items already have UPC data!")
        return

    # Extract barcodes to lookup
    barcodes_to_lookup = failed_items['Barcode'].dropna().unique().tolist()
    print(f"\n📋 Unique barcodes to lookup: {len(barcodes_to_lookup)}")

    # Fetch UPC data with batching and delays (maximum delays to avoid rate limiting)
    upc_results = fetch_batch_with_delay(barcodes_to_lookup, batch_size=15, delay_seconds=10)

    # Update the dataframe
    print(f"\n📝 Updating dataframe with new UPC data...")
    df.loc[df['needs_lookup'], 'UPC_RawData_Primary'] = df.loc[df['needs_lookup'], 'Barcode'].map(
        lambda x: upc_results.get(x, df.loc[df['Barcode'] == x, 'UPC_RawData_Primary'].iloc[0] if not pd.isna(x) else '')
    )

    # Count final results
    successful_lookups = sum(1 for v in upc_results.values() if 'error' not in v)
    still_failed = df['UPC_RawData_Primary'].fillna('').str.contains('HTTP 429|error').sum()
    total_success = df['UPC_RawData_Primary'].fillna('').apply(
        lambda x: 'error' not in x and len(x) > 0
    ).sum()

    print(f"\n📊 Results:")
    print(f"   ✅ New successful lookups: {successful_lookups}")
    print(f"   ❌ Still failed/rate limited: {still_failed}")
    print(f"   🎯 Total products with UPC data: {total_success}/{len(df)} ({total_success/len(df)*100:.1f}%)")

    # Save updated file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'cigarette_inventory_export_{timestamp}.xlsx'

    print(f"\n💾 Saving updated file: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main export sheet
        df_export = df.drop(columns=['needs_lookup'])
        df_export.to_excel(writer, sheet_name='Cigarette_Inventory', index=False)

        # Negative inventory items
        negative_stock = df_export[df_export['CurrentStock'] < 0].copy()
        if len(negative_stock) > 0:
            negative_stock = negative_stock.sort_values('CurrentStock')
            negative_stock.to_excel(writer, sheet_name='Negative_Inventory', index=False)

        # Top movers (last 30 days)
        top_movers = df_export.nlargest(50, 'TotalSold30D')
        top_movers.to_excel(writer, sheet_name='Top_50_Movers', index=False)

        # Items with UPC data
        items_with_upc = df_export[
            df_export['UPC_RawData_Primary'].fillna('').apply(lambda x: 'error' not in x and len(x) > 0)
        ].copy()
        if len(items_with_upc) > 0:
            items_with_upc.to_excel(writer, sheet_name='Items_With_UPC', index=False)

    print(f"\n✅ Export complete!")
    print(f"\nFile: {output_file}")
    print(f"Sheets: Cigarette_Inventory, Negative_Inventory, Top_50_Movers, Items_With_UPC")

    # Summary stats
    print("\n" + "="*100)
    print("FINAL SUMMARY")
    print("="*100)
    print(f"Total products: {len(df)}")
    print(f"Products with UPC data: {total_success} ({total_success/len(df)*100:.1f}%)")
    print(f"Products without UPC data: {len(df) - total_success} ({(len(df) - total_success)/len(df)*100:.1f}%)")

if __name__ == "__main__":
    main()
