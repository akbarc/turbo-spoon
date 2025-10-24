#!/usr/bin/env python3
"""
Process Hackney price inquiry file:
1. Extract all UPCs and do lookups
2. Map Hackney SKUs to our cigarette SKUs
3. Create comprehensive mapping file
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

def fetch_batch_with_delay(barcodes, batch_size=20, delay_seconds=8):
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

        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} barcodes)...")

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
        print(f"   ✅ {batch_success}/{len(batch)} successful | Overall: {successful}/{completed} ({successful/completed*100:.1f}%)")

        # Delay between batches (except for last batch)
        if i + batch_size < total:
            print(f"   ⏸️  Waiting {delay_seconds}s...")
            time.sleep(delay_seconds)

    elapsed = time.time() - start_time
    print(f"\n✅ Complete in {elapsed:.1f}s | Success: {successful}/{total} ({successful/total*100:.1f}%)")

    return results

def main():
    print("="*100)
    print("HACKNEY PRICE INQUIRY - UPC LOOKUP & SKU MAPPING")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Read Hackney file
    hackney_file = '/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx'
    print(f"📂 Reading Hackney file: {hackney_file}")
    df_hackney = pd.read_excel(hackney_file, sheet_name='HACKNEY')
    print(f"✅ Loaded {len(df_hackney)} Hackney products")

    # Read our cigarette inventory
    our_file = 'cigarette_inventory_export_20251022_171837.xlsx'
    print(f"\n📂 Reading our inventory: {our_file}")
    df_our = pd.read_excel(our_file, sheet_name='Cigarette_Inventory')
    print(f"✅ Loaded {len(df_our)} of our cigarette products")

    # Clean up UPCs
    print("\n🧹 Cleaning UPC data...")
    df_hackney['UPC_Clean'] = df_hackney['Retail UPC'].astype(str).str.strip()
    df_our['UPC_Clean'] = df_our['Barcode'].astype(str).str.strip()

    # Get unique Hackney UPCs
    hackney_upcs = df_hackney['UPC_Clean'].dropna().unique().tolist()
    hackney_upcs = [upc for upc in hackney_upcs if upc not in ['nan', '', 'None']]
    print(f"   Hackney UPCs: {len(hackney_upcs)}")
    print(f"   Our UPCs: {len(df_our['UPC_Clean'].unique())}")

    # Fetch UPC data for Hackney products
    upc_results = fetch_batch_with_delay(hackney_upcs, batch_size=20, delay_seconds=8)

    # Add UPC raw data to Hackney dataframe
    print(f"\n📝 Adding UPC data to Hackney products...")
    df_hackney['UPC_RawData'] = df_hackney['UPC_Clean'].map(lambda x: upc_results.get(x, ''))

    # Map Hackney SKUs to our SKUs by UPC
    print(f"\n🔗 Mapping Hackney SKUs to our SKUs...")

    # Create mapping dictionary: UPC -> our product info
    our_upc_map = {}
    for idx, row in df_our.iterrows():
        upc = row['UPC_Clean']
        if pd.notna(upc) and upc not in ['nan', '', 'None']:
            our_upc_map[upc] = {
                'Our_Name': row['Name'],
                'Our_Barcode': row['Barcode'],
                'Our_Cost': row['Cost'],
                'Our_CurrentPrice': row['CurrentPrice'],
                'Our_CurrentStock': row['CurrentStock'],
                'Our_TotalSold30D': row['TotalSold30D'],
                'Our_LastSupplier': row['LastSupplier'],
                'Our_LastPurchasePrice': row['LastPurchasePrice']
            }

    # Add our product info to Hackney dataframe
    for col in ['Our_Name', 'Our_Barcode', 'Our_Cost', 'Our_CurrentPrice', 'Our_CurrentStock',
                'Our_TotalSold30D', 'Our_LastSupplier', 'Our_LastPurchasePrice']:
        df_hackney[col] = df_hackney['UPC_Clean'].map(lambda x: our_upc_map.get(x, {}).get(col, ''))

    # Calculate mapping statistics
    matched = df_hackney['Our_Name'].notna().sum()
    unmatched = len(df_hackney) - matched

    print(f"   ✅ Matched: {matched}/{len(df_hackney)} ({matched/len(df_hackney)*100:.1f}%)")
    print(f"   ❌ Unmatched: {unmatched}/{len(df_hackney)} ({unmatched/len(df_hackney)*100:.1f}%)")

    # Add price comparison columns
    df_hackney['Price_Difference'] = ''
    df_hackney['Our_Better'] = ''

    for idx, row in df_hackney.iterrows():
        if pd.notna(row['Our_LastPurchasePrice']) and pd.notna(row['Price']):
            try:
                our_price = float(row['Our_LastPurchasePrice'])
                hackney_price = float(row['Price'])
                diff = our_price - hackney_price
                df_hackney.at[idx, 'Price_Difference'] = diff
                df_hackney.at[idx, 'Our_Better'] = 'YES' if diff < 0 else 'NO'
            except:
                pass

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'hackney_mapping_{timestamp}.xlsx'

    print(f"\n💾 Saving results: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Full mapping
        df_hackney.to_excel(writer, sheet_name='Hackney_Full_Mapping', index=False)

        # Matched items only
        df_matched = df_hackney[df_hackney['Our_Name'].notna()].copy()
        if len(df_matched) > 0:
            df_matched.to_excel(writer, sheet_name='Matched_Items', index=False)

        # Unmatched items
        df_unmatched = df_hackney[df_hackney['Our_Name'].isna()].copy()
        if len(df_unmatched) > 0:
            df_unmatched.to_excel(writer, sheet_name='Unmatched_Items', index=False)

        # Price comparison (where we have both prices)
        df_price_compare = df_hackney[
            df_hackney['Price_Difference'].notna() &
            (df_hackney['Price_Difference'] != '')
        ].copy()
        if len(df_price_compare) > 0:
            df_price_compare = df_price_compare.sort_values('Price_Difference')
            df_price_compare.to_excel(writer, sheet_name='Price_Comparison', index=False)

    print(f"\n✅ Export complete!")
    print(f"\nFile: {output_file}")
    print(f"Sheets: Hackney_Full_Mapping, Matched_Items, Unmatched_Items, Price_Comparison")

    # Print summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    print(f"Hackney products: {len(df_hackney)}")
    print(f"UPC lookups: {len(upc_results)} ({sum(1 for v in upc_results.values() if 'error' not in v)} successful)")
    print(f"Matched to our inventory: {matched} ({matched/len(df_hackney)*100:.1f}%)")
    print(f"Unmatched: {unmatched} ({unmatched/len(df_hackney)*100:.1f}%)")

    if len(df_price_compare) > 0:
        better_price = (df_hackney['Our_Better'] == 'YES').sum()
        worse_price = (df_hackney['Our_Better'] == 'NO').sum()
        print(f"\nPrice Comparison:")
        print(f"  Our price better: {better_price}")
        print(f"  Hackney price better: {worse_price}")

    # Show top unmatched items
    if len(df_unmatched) > 0:
        print(f"\n❌ Top 10 Unmatched Items:")
        for idx, row in df_unmatched.head(10).iterrows():
            print(f"   {row['Item']:10s} | {row['Description'][:50]:50s} | UPC: {row['UPC_Clean']}")

if __name__ == "__main__":
    main()
