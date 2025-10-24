"""
Retry FBA fee calculations for items that returned $0 fees
"""

import csv
import os
import time
from dotenv import load_dotenv
from fba_profit_analyzer import AmazonSPAPI

load_dotenv('.env')

def main():
    # Load credentials
    SP_REFRESH_TOKEN = os.getenv("SP_REFRESH_TOKEN")
    SP_CLIENT_ID = os.getenv("SP_CLIENT_ID")
    SP_CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
    SP_REGION = os.getenv("SP_REGION", "us-east-1")

    if not all([SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET]):
        print("ERROR: Amazon SP-API credentials not found in .env")
        return

    sp_api = AmazonSPAPI(SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_REGION)

    # Read corrected CSV
    with open('fba_profit_analysis_CORRECTED.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find items with $0 FBA fees
    zero_fee_items = [r for r in rows if r.get('asin') and float(r.get('fba_fee_total', 0)) == 0]

    print("=" * 100)
    print("RETRY FBA FEE CALCULATION")
    print("=" * 100)
    print(f"Items with $0 fees: {len(zero_fee_items)}")
    print()

    updated_count = 0
    results = []

    for idx, item in enumerate(zero_fee_items, 1):
        asin = item.get('asin')
        price = float(item.get('projected_amazon_price', 0))
        desc = item.get('description', '')[:50]

        if not asin or price == 0:
            results.append(item)
            continue

        print(f"[{idx}/{len(zero_fee_items)}] {desc}")

        try:
            # Retry FBA fee calculation
            fees = sp_api.get_fba_fees(asin, price)

            if fees and fees.get('total_fee', 0) > 0:
                # Update fees
                item['fba_fee_total'] = fees.get('total_fee', 0)
                item['fba_referral_fee'] = fees.get('referral_fee', 0)
                item['fba_fulfillment_fee'] = fees.get('fulfillment_fee', 0)
                item['fba_storage_fee'] = fees.get('storage_fee', 0)

                # Recalculate profit
                fba_fee_total = fees.get('total_fee', 0)
                normalized_cost = float(item.get('normalized_cost', item.get('your_cost', 0)))
                corrected_profit = price - fba_fee_total - normalized_cost
                corrected_roi = (corrected_profit / normalized_cost * 100) if normalized_cost > 0 else 0

                item['corrected_fba_profit'] = round(corrected_profit, 2)
                item['corrected_fba_roi'] = round(corrected_roi, 1)

                print(f"    ✓ Got fees: ${fba_fee_total:.2f} | Profit: ${corrected_profit:.2f}")
                updated_count += 1
            else:
                print(f"    ✗ Still no fees")

            results.append(item)
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"    ERROR: {str(e)[:60]}")
            results.append(item)

    # Merge with items that already had fees
    items_with_fees = [r for r in rows if r.get('asin') and float(r.get('fba_fee_total', 0)) > 0]
    items_no_asin = [r for r in rows if not r.get('asin')]

    all_results = results + items_with_fees + items_no_asin

    # Write updated CSV
    output_file = 'fba_profit_analysis_UPDATED.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)

    print()
    print("=" * 100)
    print(f"✓ Updated {updated_count} items with FBA fees")
    print(f"✅ Results saved to: {output_file}")
    print()

if __name__ == '__main__':
    main()
