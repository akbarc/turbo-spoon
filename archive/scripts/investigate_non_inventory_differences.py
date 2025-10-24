#!/usr/bin/env python3
"""
Investigate the 16 products with non-inventory field differences
"""

def investigate_non_inventory_differences():
    gen_file = 'generated_msa_08082025_perfect_bid.txt'
    act_file = 'MSA Data Fr/08082025'
    
    gen_bids = {}
    act_bids = {}
    
    # Parse files
    with open(gen_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                gen_bids[upc] = line.rstrip()
    
    with open(act_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                act_bids[upc] = line.rstrip()
    
    print("="*70)
    print("INVESTIGATING NON-INVENTORY FIELD DIFFERENCES")
    print("="*70)
    
    # Find non-inventory differences
    non_inventory_diffs = []
    
    for upc in act_bids:
        if upc in gen_bids:
            gen_line = gen_bids[upc]
            act_line = act_bids[upc]
            
            if gen_line != act_line and len(gen_line) == len(act_line):
                # Same length but different content - check if inventory is the same
                gen_inv, act_inv = extract_inventory_values(gen_line, act_line)
                
                if gen_inv == act_inv:
                    # Same inventory, different other fields
                    non_inventory_diffs.append({
                        'upc': upc,
                        'gen_line': gen_line,
                        'act_line': act_line,
                        'name': extract_product_name(act_line)
                    })
    
    print(f"Found {len(non_inventory_diffs)} products with non-inventory differences:")
    
    for i, diff in enumerate(non_inventory_diffs, 1):
        print(f"\n{i}. {diff['name'][:40]} (UPC: {diff['upc']})")
        
        # Compare field by field
        gen_line = diff['gen_line']
        act_line = diff['act_line']
        
        # Check different sections
        if gen_line[:18] != act_line[:18]:
            print(f"   UPC section differs:")
            print(f"     Gen: [{gen_line[:18]}]")
            print(f"     Act: [{act_line[:18]}]")
        
        if len(gen_line) > 78 and len(act_line) > 78:
            if gen_line[18:78] != act_line[18:78]:
                print(f"   Description section differs:")
                print(f"     Gen: [{gen_line[18:78]}]")
                print(f"     Act: [{act_line[18:78]}]")
        
        # Check middle sections for differences
        sections = [
            (78, 120, "Middle section 1"),
            (120, 160, "Middle section 2"), 
            (160, 200, "Middle section 3")
        ]
        
        for start, end, name in sections:
            if len(gen_line) > end and len(act_line) > end:
                if gen_line[start:end] != act_line[start:end]:
                    print(f"   {name} differs:")
                    print(f"     Gen: [{gen_line[start:end]}]")
                    print(f"     Act: [{act_line[start:end]}]")
        
        # Check if it's just trailing spaces/padding
        if gen_line.strip() == act_line.strip():
            print(f"   Only trailing spaces differ")
        
        # Show character-by-character difference for first few
        if i <= 3:
            print(f"   Character-by-character comparison:")
            for j in range(min(len(gen_line), len(act_line))):
                if gen_line[j] != act_line[j]:
                    print(f"     Position {j}: Gen='{gen_line[j]}' vs Act='{act_line[j]}'")
                    break

def extract_inventory_values(gen_line, act_line):
    """Extract inventory values from both lines"""
    try:
        # Check format based on length
        if len(gen_line) >= 261 and len(act_line) >= 261:
            # Extended format
            gen_inv_str = gen_line[247:261]
            act_inv_str = act_line[247:261]
        elif len(gen_line) >= 210 and len(act_line) >= 210:
            # Standard format
            gen_inv_str = gen_line[199:210]
            act_inv_str = act_line[199:210]
        else:
            return None, None
        
        # Parse inventory values
        gen_inv = int(gen_inv_str.replace('003', '').replace('-', '').strip())
        act_inv = int(act_inv_str.replace('003', '').replace('-', '').strip())
        
        return gen_inv, act_inv
    except:
        return None, None

def extract_product_name(line):
    """Extract product name from BID line"""
    if len(line) > 78:
        # Check for double UPC format
        if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
            # Find where name starts after ItemLookupCode
            for i in range(18, min(80, len(line))):
                if line[i].isalpha():
                    return line[i:i+40].strip()
            return line[30:78].strip()
        else:
            return line[18:78].strip()
    return line[18:].strip()

if __name__ == '__main__':
    investigate_non_inventory_differences()