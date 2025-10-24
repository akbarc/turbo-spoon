#!/usr/bin/env python3
"""
Investigate exact BID differences - inventory and formatting
"""

def investigate_differences():
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
    
    print("="*70)
    print("INVESTIGATING BID DIFFERENCES")
    print("="*70)
    
    # Find formatting errors (non-inventory differences)
    formatting_errors = []
    inventory_diffs = []
    
    for upc in act_bids:
        if upc in gen_bids:
            gen_line = gen_bids[upc]
            act_line = act_bids[upc]
            
            if gen_line != act_line:
                # Check what's different
                if len(gen_line) != len(act_line):
                    formatting_errors.append((upc, gen_line, act_line, 'LENGTH'))
                else:
                    # Same length, check field by field
                    # BID format: 
                    # 0-3: "BID"
                    # 3-18: UPC1 (15 chars)
                    # 18-30: UPC2 or start of description (12 chars)
                    # 18-78: Description (60 chars)
                    # Various other fields...
                    # Last 14 chars: usually inventory
                    
                    if gen_line[:18] != act_line[:18]:
                        formatting_errors.append((upc, gen_line, act_line, 'UPC'))
                    elif gen_line[18:78] != act_line[18:78]:
                        formatting_errors.append((upc, gen_line, act_line, 'DESC'))
                    elif gen_line[78:-14] != act_line[78:-14]:
                        formatting_errors.append((upc, gen_line, act_line, 'MIDDLE'))
                    else:
                        # Only inventory differs
                        gen_inv = gen_line[-14:]
                        act_inv = act_line[-14:]
                        inventory_diffs.append((upc, gen_inv, act_inv))
    
    # Show formatting errors
    print(f"\n1. FORMATTING ERRORS ({len(formatting_errors)} products):")
    print("-" * 50)
    
    for i, (upc, gen_line, act_line, error_type) in enumerate(formatting_errors[:10], 1):
        print(f"\n{i}. UPC: {upc} - Error: {error_type}")
        
        if error_type == 'LENGTH':
            print(f"   Gen length: {len(gen_line)}")
            print(f"   Act length: {len(act_line)}")
        elif error_type == 'DESC':
            print(f"   Gen desc: [{gen_line[18:78]}]")
            print(f"   Act desc: [{act_line[18:78]}]")
        elif error_type == 'UPC':
            print(f"   Gen UPC: [{gen_line[3:30]}]")
            print(f"   Act UPC: [{act_line[3:30]}]")
        elif error_type == 'MIDDLE':
            print(f"   Difference in middle fields")
            print(f"   Gen[78:150]: {gen_line[78:150]}")
            print(f"   Act[78:150]: {act_line[78:150]}")
    
    # Analyze inventory differences
    print(f"\n2. INVENTORY DIFFERENCES ({len(inventory_diffs)} products):")
    print("-" * 50)
    
    # Sample some inventory differences
    print("\nSample inventory differences:")
    for i, (upc, gen_inv, act_inv) in enumerate(inventory_diffs[:10], 1):
        try:
            gen_val = int(gen_inv.strip())
            act_val = int(act_inv.strip())
            diff = act_val - gen_val
            print(f"{i:2}. UPC {upc}: Gen={gen_val:6}, Act={act_val:6}, Diff={diff:+6}")
        except:
            print(f"{i:2}. UPC {upc}: Gen=[{gen_inv}], Act=[{act_inv}]")
    
    # Check if there's a pattern in inventory differences
    print("\n3. INVENTORY PATTERN ANALYSIS:")
    print("-" * 50)
    
    positive_diffs = 0
    negative_diffs = 0
    zero_in_gen = 0
    zero_in_act = 0
    
    for upc, gen_inv, act_inv in inventory_diffs:
        try:
            gen_val = int(gen_inv.strip())
            act_val = int(act_inv.strip())
            if gen_val == 0:
                zero_in_gen += 1
            if act_val == 0:
                zero_in_act += 1
            if act_val > gen_val:
                positive_diffs += 1
            elif act_val < gen_val:
                negative_diffs += 1
        except:
            pass
    
    print(f"Actual > Generated: {positive_diffs} products")
    print(f"Actual < Generated: {negative_diffs} products")
    print(f"Zero inventory in generated: {zero_in_gen}")
    print(f"Zero inventory in actual: {zero_in_act}")
    
    # Look at specific products to understand the pattern
    print("\n4. DETAILED ANALYSIS OF SPECIFIC PRODUCTS:")
    print("-" * 50)
    
    # Check a Grizzly product
    grizzly_upcs = [upc for upc in act_bids if 'GRIZZLY' in act_bids[upc][:78]]
    if grizzly_upcs:
        upc = grizzly_upcs[0]
        if upc in gen_bids:
            print(f"\nGrizzly product: {upc}")
            print(f"Gen: {gen_bids[upc]}")
            print(f"Act: {act_bids[upc]}")

if __name__ == '__main__':
    investigate_differences()