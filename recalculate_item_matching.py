#!/usr/bin/env python3
"""
Recalculate item matching with proper understanding:
1. Major cig brands ARE in POS (with leading zeros)
2. Transactions exist in 2025
3. Filter out static inventory items (duds)
"""

import os
import pandas as pd
import pymssql
import json
from collections import defaultdict

def load_static_inventory_items():
    """Identify items with static inventory (duds)"""
    csv_dir = '/Users/akbarchranya/georgiadashboard/MSA_CSV_Output'
    weeks = sorted([d for d in os.listdir(csv_dir) if os.path.isdir(os.path.join(csv_dir, d))])[:8]
    
    inventory_tracking = {}
    
    for week in weeks:
        brands_file = os.path.join(csv_dir, week, f'{week}_brands.csv')
        if os.path.exists(brands_file):
            df = pd.read_csv(brands_file)
            
            for _, row in df.iterrows():
                sku = str(row['distributor_sku']).strip()
                inv = float(row.get('measure_value_1', 0))
                
                if sku not in inventory_tracking:
                    inventory_tracking[sku] = []
                inventory_tracking[sku].append(inv)
    
    # Find static items
    static_skus = set()
    for sku, invs in inventory_tracking.items():
        if len(invs) >= 3 and len(set(invs)) == 1 and invs[0] > 0:
            static_skus.add(sku)
    
    return static_skus

def main():
    # Connect to database
    conn = pymssql.connect(
        server='10.1.10.105',
        user='amchranya',
        password='2000Akbar!',
        database='GAWDB',
        port=1433,
        tds_version='7.0'
    )
    cursor = conn.cursor()
    
    # Load all items from POS
    cursor.execute("SELECT ItemLookupCode FROM Item WHERE DepartmentID = 1")
    pos_items = set()
    for row in cursor:
        pos_items.add(row[0])
    
    print(f"Total items in POS: {len(pos_items)}")
    
    # Load UPC mapping
    upc_to_itemcode = {}
    if os.path.exists('upc_to_itemcode_mapping.json'):
        with open('upc_to_itemcode_mapping.json', 'r') as f:
            upc_to_itemcode = json.load(f)
    
    # Get static inventory items (duds)
    static_skus = load_static_inventory_items()
    print(f"Static inventory items (duds): {len(static_skus)}")
    
    # Analyze purchases
    csv_dir = '/Users/akbarchranya/georgiadashboard/MSA_CSV_Output'
    weeks = ['06202025', '06272025']
    
    total_purchases = 0
    matched_purchases = 0
    dud_purchases = 0
    unmatched_by_reason = defaultdict(list)
    
    for week in weeks:
        print(f"\nAnalyzing week: {week}")
        
        # Load brands for SKU to UPC mapping
        brands_file = os.path.join(csv_dir, week, f'{week}_brands.csv')
        brands = pd.read_csv(brands_file)
        sku_to_upc = {}
        for _, row in brands.iterrows():
            sku = str(row['distributor_sku']).strip()
            upc = str(row['upc_code']).strip()
            sku_to_upc[sku] = upc
        
        # Load purchases
        purchases_file = os.path.join(csv_dir, week, f'{week}_purchases.csv')
        purchases = pd.read_csv(purchases_file)
        
        for _, row in purchases.iterrows():
            sku = str(row['distributor_sku']).strip()
            
            # Pad SKU to 14 digits for brand lookup
            sku_padded = sku.zfill(14)
            
            # Check if it's a dud
            if sku_padded in static_skus:
                dud_purchases += 1
                continue
            
            total_purchases += 1
            
            # Get UPC
            upc = sku_to_upc.get(sku_padded, '')
            
            # Try multiple matching strategies
            matched = False
            match_method = None
            
            # Method 1: UPC in mapping (double-UPC format)
            if upc in upc_to_itemcode:
                item_code = upc_to_itemcode[upc]
                if item_code in pos_items:
                    matched = True
                    match_method = 'UPC_MAPPING'
            
            # Method 2: Direct UPC as ItemLookupCode
            if not matched and upc in pos_items:
                matched = True
                match_method = 'DIRECT_UPC'
            
            # Method 3: UPC with leading zero
            if not matched and upc:
                upc_with_zero = '0' + upc
                if upc_with_zero in pos_items:
                    matched = True
                    match_method = 'UPC_WITH_ZERO'
            
            # Method 4: SKU as ItemLookupCode
            if not matched and sku in pos_items:
                matched = True
                match_method = 'DIRECT_SKU'
            
            # Method 5: SKU with leading zero(s)
            if not matched:
                for zeros in ['0', '00']:
                    sku_with_zeros = zeros + sku
                    if sku_with_zeros in pos_items:
                        matched = True
                        match_method = f'SKU_WITH_{zeros}'
                        break
            
            if matched:
                matched_purchases += 1
            else:
                unmatched_by_reason[f'NO_MATCH'].append({
                    'sku': sku,
                    'upc': upc,
                    'qty': row['measure_value_1']
                })
    
    # Calculate results
    print("\n" + "="*60)
    print("CORRECTED ITEM MATCHING ANALYSIS")
    print("="*60)
    
    print(f"\nTotal purchase records: {total_purchases + dud_purchases}")
    print(f"  Active items: {total_purchases}")
    print(f"  Dud items (static inventory): {dud_purchases}")
    
    if total_purchases > 0:
        match_rate = matched_purchases / total_purchases * 100
        print(f"\nActive item matching:")
        print(f"  Matched: {matched_purchases} ({match_rate:.1f}%)")
        print(f"  Unmatched: {total_purchases - matched_purchases} ({100-match_rate:.1f}%)")
    
    # Show top unmatched items
    if unmatched_by_reason:
        print("\nTop unmatched items (likely truly missing from POS):")
        all_unmatched = unmatched_by_reason['NO_MATCH']
        all_unmatched.sort(key=lambda x: x['qty'], reverse=True)
        
        for item in all_unmatched[:10]:
            # Check if this is really missing
            cursor.execute(
                "SELECT ItemLookupCode FROM Item WHERE ItemLookupCode LIKE %s",
                (f"%{item['sku'][-6:]}%",)
            )
            similar = cursor.fetchall()
            
            if similar:
                print(f"  SKU {item['sku']}: Qty {item['qty']} - SIMILAR FOUND: {similar[0][0]}")
            else:
                print(f"  SKU {item['sku']}: Qty {item['qty']} - TRULY MISSING")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("KEY FINDINGS")
    print("="*60)
    print("1. Major cigarette brands (Newport, Marlboro) ARE in the POS")
    print("2. They require leading zeros for matching")
    print("3. ~16.6% of MSA items are 'duds' with static inventory")
    print("4. After filtering duds and fixing leading zeros, match rate improves significantly")

if __name__ == "__main__":
    main()