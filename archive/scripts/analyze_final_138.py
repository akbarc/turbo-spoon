#!/usr/bin/env python3
"""Analyze the final 138 mismatches"""

gen_file = 'generated_msa_08082025_100_percent.txt'
act_file = 'MSA Data Fr/08082025'

gen_inv = {}
act_inv = {}

# Parse files
with open(gen_file, 'r') as f:
    for line in f:
        if line.startswith('BID'):
            upc = line[3:18].strip()
            if len(line) >= 261:
                inv_str = line[247:261]
            elif len(line) >= 210:
                inv_str = line[199:210]
            else:
                continue
            inv = int(inv_str.replace('003', '').replace('-', '').strip())
            gen_inv[upc] = inv

with open(act_file, 'r') as f:
    for line in f:
        if line.startswith('BID'):
            upc = line[3:18].strip()
            if len(line) >= 261:
                inv_str = line[247:261]
            elif len(line) >= 210:
                inv_str = line[199:210]
            else:
                continue
            inv = int(inv_str.replace('003', '').replace('-', '').strip())
            act_inv[upc] = inv

# Analyze remaining mismatches
mismatches = []
for upc in act_inv:
    if upc in gen_inv and gen_inv[upc] != act_inv[upc]:
        mismatches.append({
            'upc': upc,
            'gen': gen_inv[upc],
            'act': act_inv[upc],
            'diff': act_inv[upc] - gen_inv[upc]
        })

print(f'Remaining {len(mismatches)} mismatches:')
print('='*70)

# Group by pattern
zero_gen = [m for m in mismatches if m['gen'] == 0]
zero_act = [m for m in mismatches if m['act'] == 0]
small_diff = [m for m in mismatches if 0 < abs(m['diff']) <= 10 and m['gen'] != 0 and m['act'] != 0]
large_diff = [m for m in mismatches if abs(m['diff']) > 10 and m['gen'] != 0 and m['act'] != 0]

print(f'Generated=0, Actual>0: {len(zero_gen)} products')
print(f'Generated>0, Actual=0: {len(zero_act)} products')
print(f'Small differences (1-10): {len(small_diff)} products')
print(f'Large differences (>10): {len(large_diff)} products')

print('\nSample of large differences:')
for m in sorted(large_diff, key=lambda x: abs(x['diff']), reverse=True)[:5]:
    print(f'  {m["upc"]}: Gen={m["gen"]:4}, Act={m["act"]:4}, Diff={m["diff"]:+5}')

print('\n' + '='*70)
print('TO REACH 100%:')
perfect_matches = len(act_inv)
current_matches = sum(1 for upc in act_inv if upc in gen_inv and gen_inv[upc] == act_inv[upc])
needed = perfect_matches - current_matches
print(f'Need to fix {needed} more products out of {perfect_matches} total')
print(f'Current: {current_matches}/{perfect_matches} = {current_matches/perfect_matches*100:.1f}%')
print(f'Target: 100.0%')