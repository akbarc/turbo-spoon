#!/usr/bin/env python3
"""
Compare total quantities between real MSA files and generated MSA files
"""

def calculate_msa_totals(filepath):
    """Calculate total inventory from MSA file"""
    total_quantity = 0
    product_count = 0
    products_with_inventory = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('BID'):
                    product_count += 1
                    # Extract inventory from position 303-316
                    if len(line) >= 316:
                        inv_str = line[303:316].strip()
                        
                        # Parse inventory value
                        if inv_str.startswith('003-'):
                            # Negative inventory
                            inv_value = -int(inv_str[4:]) if inv_str[4:] else 0
                        elif inv_str.startswith('003'):
                            # Positive inventory
                            inv_value = int(inv_str[3:]) if inv_str[3:] else 0
                        else:
                            inv_value = 0
                        
                        total_quantity += inv_value
                        if inv_value > 0:
                            products_with_inventory += 1
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    
    return {
        'total_quantity': total_quantity,
        'product_count': product_count,
        'products_with_inventory': products_with_inventory
    }

def main():
    """Compare all MSA weeks"""
    
    weeks = ['08082025', '08012025', '07252025', '07182025', '07112025', '07042025', '06272025']
    
    print("=" * 80)
    print("MSA TOTAL QUANTITY COMPARISON - REAL vs GENERATED")
    print("=" * 80)
    
    print(f"\n{'Week':<12} {'Source':<10} {'Products':>10} {'With Inv':>10} {'Total Qty':>12} {'Difference':>12}")
    print("-" * 76)
    
    total_real = 0
    total_gen = 0
    
    for week in weeks:
        real_file = f'MSA Data Fr/{week}'
        gen_file = f'generated_msa_{week}_100_final.txt'
        
        # Calculate totals for real file
        real_stats = calculate_msa_totals(real_file)
        gen_stats = calculate_msa_totals(gen_file)
        
        if real_stats and gen_stats:
            diff = gen_stats['total_quantity'] - real_stats['total_quantity']
            
            print(f"{week:<12} {'Real':<10} {real_stats['product_count']:>10,} {real_stats['products_with_inventory']:>10,} {real_stats['total_quantity']:>12,}")
            print(f"{'':<12} {'Generated':<10} {gen_stats['product_count']:>10,} {gen_stats['products_with_inventory']:>10,} {gen_stats['total_quantity']:>12,} {diff:>+12,}")
            print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {(gen_stats['total_quantity']/real_stats['total_quantity']*100 if real_stats['total_quantity'] else 0):>11.1f}%")
            print("-" * 76)
            
            total_real += real_stats['total_quantity']
            total_gen += gen_stats['total_quantity']
    
    # Overall summary
    print(f"\n{'TOTAL':<12} {'Real':<10} {'':<10} {'':<10} {total_real:>12,}")
    print(f"{'':<12} {'Generated':<10} {'':<10} {'':<10} {total_gen:>12,} {total_gen - total_real:>+12,}")
    print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {(total_gen/total_real*100 if total_real else 0):>11.1f}%")
    
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS FOR LATEST WEEK (08/08/2025):")
    print("=" * 80)
    
    # Analyze products with largest differences
    real_file = 'MSA Data Fr/08082025'
    gen_file = 'generated_msa_08082025_100_final.txt'
    
    # Extract all products and their inventories
    real_products = {}
    gen_products = {}
    
    with open(real_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:16].strip()
                name = line[29:89].strip()
                if len(line) >= 316:
                    inv_str = line[303:316].strip()
                    if inv_str.startswith('003-'):
                        inv_value = -int(inv_str[4:]) if inv_str[4:] else 0
                    elif inv_str.startswith('003'):
                        inv_value = int(inv_str[3:]) if inv_str[3:] else 0
                    else:
                        inv_value = 0
                    key = f"{upc}|{name}"
                    real_products[key] = inv_value
    
    with open(gen_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:16].strip()
                name = line[29:89].strip()
                if len(line) >= 316:
                    inv_str = line[303:316].strip()
                    if inv_str.startswith('003-'):
                        inv_value = -int(inv_str[4:]) if inv_str[4:] else 0
                    elif inv_str.startswith('003'):
                        inv_value = int(inv_str[3:]) if inv_str[3:] else 0
                    else:
                        inv_value = 0
                    key = f"{upc}|{name}"
                    gen_products[key] = inv_value
    
    # Find products with inventory differences
    differences = []
    for key in real_products:
        if key in gen_products:
            if real_products[key] != gen_products[key]:
                upc, name = key.split('|')
                diff = gen_products[key] - real_products[key]
                differences.append((name, real_products[key], gen_products[key], diff))
    
    if differences:
        # Sort by absolute difference
        differences.sort(key=lambda x: abs(x[3]), reverse=True)
        
        print(f"\nProducts with inventory differences (Top 10):")
        print(f"{'Product':<40} {'Real':>8} {'Gen':>8} {'Diff':>8}")
        print("-" * 64)
        for name, real_inv, gen_inv, diff in differences[:10]:
            print(f"{name[:40]:<40} {real_inv:>8} {gen_inv:>8} {diff:>+8}")
        
        print(f"\nTotal products with differences: {len(differences)}")
    else:
        print("\n✅ All product inventories match perfectly!")
    
    # Summary statistics
    print(f"\n08/08/2025 Week Statistics:")
    print(f"  Real MSA total quantity:      {real_stats['total_quantity']:,} units")
    print(f"  Generated MSA total quantity: {gen_stats['total_quantity']:,} units")
    print(f"  Difference:                   {gen_stats['total_quantity'] - real_stats['total_quantity']:+,} units")
    print(f"  Accuracy:                     {(gen_stats['total_quantity']/real_stats['total_quantity']*100):.2f}%")

if __name__ == '__main__':
    main()