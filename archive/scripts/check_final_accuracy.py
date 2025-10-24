#!/usr/bin/env python3
"""Check final accuracy of generated MSA"""

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

# Find patterns in mismatches
zero_in_gen = []
zero_in_act = []
both_nonzero = []

for upc in act_inv:
    if upc in gen_inv:
        gen_val = gen_inv[upc]
        act_val = act_inv[upc]
        if gen_val != act_val:
            if gen_val == 0:
                zero_in_gen.append((upc, act_val))
            elif act_val == 0:
                zero_in_act.append((upc, gen_val))
            else:
                both_nonzero.append((upc, gen_val, act_val))

print('MISMATCH PATTERNS:')
print(f'Generated=0, Actual>0: {len(zero_in_gen)} products')
print(f'Generated>0, Actual=0: {len(zero_in_act)} products')
print(f'Both non-zero but different: {len(both_nonzero)} products')

print('\nChecking specific products:')
problem_upcs = ['701375112120', '261008057340', '701370051860']
for upc in problem_upcs:
    if upc in gen_inv and upc in act_inv:
        status = "✓ FIXED!" if gen_inv[upc] == act_inv[upc] else "✗ Still wrong"
        print(f'{upc}: Gen={gen_inv[upc]}, Act={act_inv[upc]} {status}')

# Overall accuracy
exact_matches = sum(1 for upc in act_inv if upc in gen_inv and gen_inv[upc] == act_inv[upc])
total = len(act_inv)
accuracy = exact_matches / total * 100

print(f'\n{"="*70}')
print('FINAL ACCURACY:')
print(f'Exact inventory matches: {exact_matches}/{total} = {accuracy:.1f}%')
print(f'{"="*70}')

if accuracy >= 99:
    print('✓✓✓ ACHIEVED 99%+ ACCURACY! ✓✓✓')
elif accuracy >= 95:
    print('✓ Very close! 95%+ accuracy achieved')
else:
    print(f'Still need work: {100-accuracy:.1f}% to go')