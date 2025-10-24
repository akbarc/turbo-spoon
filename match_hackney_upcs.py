#!/usr/bin/env python3
"""
Match Hackney UPCs to our UPCs using multiple strategies
"""

import pandas as pd
from datetime import datetime

def try_upc_matching_strategies(hackney_upc, our_upcs_dict):
    """Try different UPC matching strategies"""

    # Strategy 1: Exact match
    if hackney_upc in our_upcs_dict:
        return our_upcs_dict[hackney_upc], 'exact'

    # Strategy 2: Add leading zero to Hackney UPC (11 -> 12 digits)
    padded = '0' + hackney_upc
    if padded in our_upcs_dict:
        return our_upcs_dict[padded], 'padded'

    # Strategy 3: Match first 11 digits of our 12-digit UPCs
    for our_upc, data in our_upcs_dict.items():
        if len(our_upc) == 12 and len(hackney_upc) == 11:
            if our_upc[:11] == hackney_upc:
                return data, 'first_11'

    # Strategy 4: Match last 11 digits of our 12-digit UPCs
    for our_upc, data in our_upcs_dict.items():
        if len(our_upc) == 12 and len(hackney_upc) == 11:
            if our_upc[1:] == hackney_upc:
                return data, 'last_11'

    # Strategy 5: Match first 10 digits (fuzzy - check digit might differ)
    for our_upc, data in our_upcs_dict.items():
        if len(our_upc) >= 10 and len(hackney_upc) >= 10:
            if our_upc[:10] == hackney_upc[:10]:
                return data, 'first_10_fuzzy'

    return None, 'no_match'

def main():
    print("="*100)
    print("HACKNEY UPC MATCHING - MULTIPLE STRATEGIES")
    print("="*100)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load files
    hackney_file = '/Users/akbarchranya/Downloads/priceinquiry_NEW-2025102213495720563 (1).xlsx'
    our_file = 'cigarette_inventory_export_20251022_171837.xlsx'

    print(f"📂 Loading files...")
    df_hackney = pd.read_excel(hackney_file, sheet_name='HACKNEY')
    df_our = pd.read_excel(our_file, sheet_name='Cigarette_Inventory')

    print(f"✅ Hackney: {len(df_hackney)} products")
    print(f"✅ Our inventory: {len(df_our)} products")

    # Clean UPCs
    df_hackney['UPC_Clean'] = df_hackney['Retail UPC'].astype(str).str.strip()
    df_our['UPC_Clean'] = df_our['Barcode'].astype(str).str.strip()

    # Create dictionary of our UPCs -> product data
    our_upcs_dict = {}
    for idx, row in df_our.iterrows():
        upc = row['UPC_Clean']
        if pd.notna(upc) and upc not in ['nan', '', 'None']:
            our_upcs_dict[upc] = {
                'Name': row['Name'],
                'Barcode': row['Barcode'],
                'Cost': row['Cost'],
                'CurrentPrice': row['CurrentPrice'],
                'CurrentStock': row['CurrentStock'],
                'TotalSold30D': row['TotalSold30D'],
                'LastSupplier': row['LastSupplier'],
                'LastPurchasePrice': row['LastPurchasePrice'],
                'UPC_RawData_Primary': row['UPC_RawData_Primary']
            }

    print(f"\n🔍 Attempting to match {len(df_hackney)} Hackney products...")

    # Track matching statistics
    match_stats = {
        'exact': 0,
        'padded': 0,
        'first_11': 0,
        'last_11': 0,
        'first_10_fuzzy': 0,
        'no_match': 0
    }

    # Match each Hackney product
    matches = []
    for idx, row in df_hackney.iterrows():
        hackney_upc = row['UPC_Clean']

        if pd.notna(hackney_upc) and hackney_upc not in ['nan', '', 'None']:
            match_data, strategy = try_upc_matching_strategies(hackney_upc, our_upcs_dict)
            match_stats[strategy] += 1

            if match_data:
                matches.append({
                    'Hackney_Item': row['Item'],
                    'Hackney_Description': row['Description'],
                    'Hackney_UPC': hackney_upc,
                    'Hackney_Price': row['Price'],
                    'Hackney_QtyOnHand': row[' Quantity on Hand'],
                    'Match_Strategy': strategy,
                    'Our_Name': match_data['Name'],
                    'Our_Barcode': match_data['Barcode'],
                    'Our_Cost': match_data['Cost'],
                    'Our_CurrentPrice': match_data['CurrentPrice'],
                    'Our_CurrentStock': match_data['CurrentStock'],
                    'Our_TotalSold30D': match_data['TotalSold30D'],
                    'Our_LastSupplier': match_data['LastSupplier'],
                    'Our_LastPurchasePrice': match_data['LastPurchasePrice'],
                    'UPC_RawData': match_data['UPC_RawData_Primary']
                })

    # Create results dataframe
    df_matches = pd.DataFrame(matches)

    # Print statistics
    print(f"\n📊 MATCHING RESULTS:")
    print(f"   Total Hackney products: {len(df_hackney)}")
    print(f"   Successfully matched: {len(df_matches)} ({len(df_matches)/len(df_hackney)*100:.1f}%)")
    print(f"\n   Match strategies used:")
    for strategy, count in match_stats.items():
        if count > 0:
            print(f"      {strategy}: {count}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'hackney_matched_{timestamp}.xlsx'

    print(f"\n💾 Saving results: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # All matches
        df_matches.to_excel(writer, sheet_name='Matched_Products', index=False)

        # Unmatched Hackney items
        matched_hackney_items = set(df_matches['Hackney_Item'].astype(str))
        df_unmatched = df_hackney[~df_hackney['Item'].astype(str).isin(matched_hackney_items)]
        if len(df_unmatched) > 0:
            df_unmatched.to_excel(writer, sheet_name='Unmatched_Hackney', index=False)

    print(f"\n✅ Export complete!")
    print(f"\nFile: {output_file}")
    print(f"Matched products: {len(df_matches)}")
    print(f"Unmatched products: {len(df_hackney) - len(df_matches)}")

    # Show sample matches
    if len(df_matches) > 0:
        print(f"\n📋 Sample matches (first 10):")
        print()
        for idx, row in df_matches.head(10).iterrows():
            print(f"  {row['Hackney_Description'][:35]:35s} -> {row['Our_Name'][:35]:35s} ({row['Match_Strategy']})")

    # Show unmatched samples
    if len(df_hackney) - len(df_matches) > 0:
        print(f"\n❌ Sample unmatched (first 10):")
        unmatched_items = df_hackney[~df_hackney['Item'].astype(str).isin(matched_hackney_items)]
        for idx, row in unmatched_items.head(10).iterrows():
            print(f"  {row['Item']:10s} | {row['Description'][:40]:40s} | UPC: {row['Retail UPC']}")

if __name__ == "__main__":
    main()
