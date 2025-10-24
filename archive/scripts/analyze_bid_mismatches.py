#!/usr/bin/env python3
"""
Analyze if BID mismatches are only inventory-related
"""

def compare_bid_fields():
    gen_file = 'generated_msa_08082025_perfect_bid.txt'
    act_file = 'MSA Data Fr/08082025'
    
    gen_bids = {}
    act_bids = {}
    
    # Parse generated
    with open(gen_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                gen_bids[upc] = line.rstrip()
    
    # Parse actual
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                act_bids[upc] = line.rstrip()
    
    # Compare
    inventory_only_mismatch = 0
    other_mismatch = 0
    
    for upc in act_bids:
        if upc in gen_bids:
            gen_line = gen_bids[upc]
            act_line = act_bids[upc]
            
            if gen_line != act_line:
                # Check if only inventory differs
                # Everything except last field should match
                if len(gen_line) == len(act_line):
                    # Compare all but last 14 chars (inventory field)
                    if gen_line[:-14] == act_line[:-14]:
                        inventory_only_mismatch += 1
                    else:
                        other_mismatch += 1
                        if other_mismatch <= 3:
                            print(f'Non-inventory mismatch for {upc}:')
                            print(f'  Gen[:80]: {gen_line[:80]}')
                            print(f'  Act[:80]: {act_line[:80]}')
                else:
                    other_mismatch += 1
    
    print(f'\nBID Mismatch Analysis:')
    print(f'Inventory-only mismatches: {inventory_only_mismatch}')
    print(f'Other mismatches: {other_mismatch}')
    print(f'\nConclusion: {"All mismatches are inventory-related!" if other_mismatch == 0 else "Some mismatches in other fields"}')

if __name__ == '__main__':
    compare_bid_fields()