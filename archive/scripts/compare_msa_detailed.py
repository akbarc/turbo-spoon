#!/usr/bin/env python3
"""
Detailed comparison of generated vs real MSA data
"""

def parse_msa_file(filepath):
    """Parse MSA file and extract all records"""
    records = {
        'header': None,
        'bids': [],
        'sids': [],
        'sales': [],
        'trailer': None
    }
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    lines = content.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
            
        if line.startswith('HID'):
            records['header'] = line
        elif line.startswith('BID'):
            records['bids'].append(line)
        elif line.startswith('SID'):
            records['sids'].append(line)
        elif line.startswith('SAL'):
            records['sales'].append(line)
        elif line.startswith('TRL'):
            records['trailer'] = line
            
    return records

def extract_bid_info(bid_line):
    """Extract UPC, name, and inventory from BID line"""
    try:
        upc = bid_line[3:16].strip()
        duplicate_upc = bid_line[16:29].strip()
        product_name = bid_line[29:89].strip()
        inventory = bid_line[303:316].strip()
        
        # Convert inventory, handling special format
        if inventory.startswith('003-'):
            inv_value = -int(inventory[4:])
        else:
            inv_value = int(inventory[3:]) if inventory[3:] else 0
            
        return {
            'upc': upc,
            'dup_upc': duplicate_upc,
            'name': product_name,
            'inventory': inv_value,
            'full_line': bid_line
        }
    except:
        return None

def compare_msa_files():
    """Compare generated vs real MSA files"""
    
    print("=" * 80)
    print("MSA FILE COMPARISON - DETAILED ANALYSIS")
    print("=" * 80)
    
    # Parse both files
    print("\nParsing files...")
    real = parse_msa_file('MSA Data Fr/08082025')
    generated = parse_msa_file('generated_msa_08082025_100_final.txt')
    
    # Compare headers
    print("\n1. HEADER COMPARISON:")
    print("-" * 40)
    if real['header'] == generated['header']:
        print("✓ Headers match perfectly")
    else:
        print("✗ Headers differ:")
        print(f"  Real: {real['header'][:100]}...")
        print(f"  Gen:  {generated['header'][:100]}...")
    
    # Compare BID records
    print("\n2. BID RECORDS (PRODUCTS):")
    print("-" * 40)
    print(f"Real file:      {len(real['bids'])} products")
    print(f"Generated file: {len(generated['bids'])} products")
    print(f"Difference:     {len(real['bids']) - len(generated['bids'])} products")
    
    # Extract and compare product details
    real_products = {}
    gen_products = {}
    
    for bid in real['bids']:
        info = extract_bid_info(bid)
        if info:
            key = f"{info['upc']}_{info['name']}"
            real_products[key] = info
            
    for bid in generated['bids']:
        info = extract_bid_info(bid)
        if info:
            key = f"{info['upc']}_{info['name']}"
            gen_products[key] = info
    
    # Find differences
    only_in_real = set(real_products.keys()) - set(gen_products.keys())
    only_in_gen = set(gen_products.keys()) - set(real_products.keys())
    in_both = set(real_products.keys()) & set(gen_products.keys())
    
    print(f"\nProduct presence:")
    print(f"  Only in real MSA:      {len(only_in_real)} products")
    print(f"  Only in generated:     {len(only_in_gen)} products")
    print(f"  In both files:         {len(in_both)} products")
    
    # Check inventory differences for matching products
    inventory_diffs = []
    for key in in_both:
        real_inv = real_products[key]['inventory']
        gen_inv = gen_products[key]['inventory']
        if real_inv != gen_inv:
            inventory_diffs.append({
                'product': real_products[key]['name'],
                'upc': real_products[key]['upc'],
                'real_inv': real_inv,
                'gen_inv': gen_inv,
                'diff': gen_inv - real_inv
            })
    
    print(f"\nInventory accuracy:")
    print(f"  Matching inventory:    {len(in_both) - len(inventory_diffs)} products")
    print(f"  Different inventory:   {len(inventory_diffs)} products")
    print(f"  Accuracy rate:         {((len(in_both) - len(inventory_diffs)) / len(real_products) * 100):.1f}%")
    
    # Show sample of missing products
    if only_in_real:
        print("\n3. PRODUCTS ONLY IN REAL MSA (first 10):")
        print("-" * 40)
        for i, key in enumerate(sorted(only_in_real)[:10]):
            prod = real_products[key]
            print(f"  {prod['upc']} | {prod['name'][:40]:40} | Inv: {prod['inventory']}")
    
    if only_in_gen:
        print("\n4. PRODUCTS ONLY IN GENERATED (first 10):")
        print("-" * 40)
        for i, key in enumerate(sorted(only_in_gen)[:10]):
            prod = gen_products[key]
            print(f"  {prod['upc']} | {prod['name'][:40]:40} | Inv: {prod['inventory']}")
    
    # Show inventory differences
    if inventory_diffs:
        print("\n5. INVENTORY DIFFERENCES (first 20):")
        print("-" * 40)
        # Sort by absolute difference
        inventory_diffs.sort(key=lambda x: abs(x['diff']), reverse=True)
        for diff in inventory_diffs[:20]:
            print(f"  {diff['upc']} | {diff['product'][:30]:30} | Real: {diff['real_inv']:4} | Gen: {diff['gen_inv']:4} | Diff: {diff['diff']:+4}")
    
    # Compare SID records
    print("\n6. SID RECORDS (CUSTOMERS):")
    print("-" * 40)
    print(f"Real file:      {len(real['sids'])} customers")
    print(f"Generated file: {len(generated['sids'])} customers")
    
    # Compare sales records
    print("\n7. SALES RECORDS:")
    print("-" * 40)
    print(f"Real file:      {len(real['sales'])} sales")
    print(f"Generated file: {len(generated['sales'])} sales")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("-" * 40)
    accuracy = ((len(in_both) - len(inventory_diffs)) / len(real_products) * 100)
    print(f"Overall BID accuracy: {accuracy:.1f}%")
    print(f"Product coverage:     {(len(in_both) / len(real_products) * 100):.1f}%")
    print(f"Customer match:       {(len(generated['sids']) / len(real['sids']) * 100 if real['sids'] else 0):.1f}%")
    print(f"Sales match:          {(len(generated['sales']) / len(real['sales']) * 100 if real['sales'] else 0):.1f}%")
    
    return {
        'accuracy': accuracy,
        'missing_products': only_in_real,
        'extra_products': only_in_gen,
        'inventory_diffs': inventory_diffs
    }

if __name__ == '__main__':
    result = compare_msa_files()