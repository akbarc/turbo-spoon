#!/usr/bin/env python3
"""
Compare exact BID and SID record content between generated and actual MSA
"""

def parse_bid_records(filepath):
    bids = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('BID'):
                # Parse BID fields
                upc1 = line[3:18].strip()
                # The full line is the value
                bids[upc1] = line.rstrip('\r\n')
    return bids

def parse_sid_records(filepath):
    sids = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('SID'):
                customer_id = line[3:11].strip()
                if customer_id:
                    sids[customer_id] = line.rstrip('\r\n')
    return sids

def main():
    # Parse both files
    gen_bids = parse_bid_records('generated_msa_08082025_perfect_bid.txt')
    act_bids = parse_bid_records('MSA Data Fr/08082025')
    
    gen_sids = parse_sid_records('generated_msa_08082025_perfect_bid.txt')
    act_sids = parse_sid_records('MSA Data Fr/08082025')
    
    print('='*70)
    print('BID RECORD CONTENT COMPARISON')
    print('='*70)
    
    # Check BID matches
    exact_bid_matches = 0
    bid_mismatches = []
    
    for upc in act_bids:
        if upc in gen_bids:
            if gen_bids[upc] == act_bids[upc]:
                exact_bid_matches += 1
            else:
                bid_mismatches.append((upc, gen_bids[upc], act_bids[upc]))
    
    print(f'Total actual BIDs: {len(act_bids)}')
    print(f'Found in generated: {len([u for u in act_bids if u in gen_bids])}')
    print(f'Exact content matches: {exact_bid_matches}')
    print(f'Content mismatches: {len(bid_mismatches)}')
    
    if bid_mismatches:
        print('\nFirst 10 BID mismatches:')
        for i, (upc, gen_line, act_line) in enumerate(bid_mismatches[:10], 1):
            print(f'\n{i}. UPC: {upc}')
            # Show character-by-character comparison for inventory field
            if len(gen_line) >= 210 and len(act_line) >= 210:
                gen_inv = gen_line[199:210]
                act_inv = act_line[199:210]
                if gen_inv != act_inv:
                    print(f'   Inventory: Gen={gen_inv}, Act={act_inv}')
            # Check other differences
            if gen_line[:199] != act_line[:199]:
                print(f'   Description/format differs')
                print(f'   Gen[:80]: {gen_line[:80]}')
                print(f'   Act[:80]: {act_line[:80]}')
    
    print('\n' + '='*70)
    print('SID RECORD CONTENT COMPARISON')
    print('='*70)
    
    # Check SID matches
    exact_sid_matches = 0
    sid_mismatches = []
    
    for cust_id in act_sids:
        if cust_id in gen_sids:
            if gen_sids[cust_id] == act_sids[cust_id]:
                exact_sid_matches += 1
            else:
                sid_mismatches.append((cust_id, gen_sids[cust_id], act_sids[cust_id]))
    
    print(f'Total actual SIDs: {len(act_sids)}')
    print(f'Found in generated: {len([c for c in act_sids if c in gen_sids])}')
    print(f'Exact content matches: {exact_sid_matches}')
    print(f'Content mismatches: {len(sid_mismatches)}')
    
    if sid_mismatches:
        print('\nFirst 5 SID mismatches:')
        for i, (cust_id, gen_line, act_line) in enumerate(sid_mismatches[:5], 1):
            print(f'\n{i}. Customer: {cust_id}')
            print(f'   Gen: {repr(gen_line)}')
            print(f'   Act: {repr(act_line)}')
            if len(gen_line) != len(act_line):
                print(f'   Length: Gen={len(gen_line)}, Act={len(act_line)}')
    
    # Summary
    print('\n' + '='*70)
    print('SUMMARY')
    print('='*70)
    
    bid_accuracy = (exact_bid_matches / len(act_bids)) * 100 if act_bids else 0
    sid_accuracy = (exact_sid_matches / len(act_sids)) * 100 if act_sids else 0
    
    print(f'BID exact match rate: {bid_accuracy:.1f}%')
    print(f'SID exact match rate: {sid_accuracy:.1f}%')
    
    if bid_accuracy < 100:
        print('\nBID mismatches are likely due to inventory differences')
    if sid_accuracy < 100:
        print('\nSID mismatches may be due to formatting differences')

if __name__ == '__main__':
    main()