#!/usr/bin/env python3
"""
Compare total quantities between real MSA files and generated MSA files - CORRECT PARSING
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
                    
                    inv_value = 0
                    
                    # Real MSA format: inventory at position 247-260 (00300000000125)
                    if len(line) >= 260 and line[247:250] == '003':
                        inv_str = line[247:260].strip()
                        if inv_str.startswith('003-'):
                            inv_value = -int(inv_str[4:])
                        elif inv_str.startswith('003'):
                            inv_part = inv_str[3:].lstrip('0')
                            inv_value = int(inv_part) if inv_part else 0
                    
                    # Generated format: inventory at end (number followed by 003)
                    elif line.strip().endswith('003'):
                        # Get the last part after all spaces
                        line_stripped = line.strip()
                        # Find where the number starts (look backwards from '003')
                        idx = line_stripped.rfind('003')
                        if idx > 0:
                            # Find the start of the number
                            num_start = idx - 1
                            while num_start >= 0 and line_stripped[num_start].isdigit():
                                num_start -= 1
                            num_start += 1
                            
                            # Extract the number
                            num_str = line_stripped[num_start:idx]
                            try:
                                inv_value = int(num_str)
                            except:
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
    
    # Test parsing on a few lines first
    print("\nVerifying parsing logic:")
    print("-" * 40)
    
    # Test real MSA format
    test_real = "BID  60924990342600609249903426ZYN 6MG WINTERGREEN  5CT                                                                            000005N      003231                                                                                                 00300000000125"
    real_val = 0
    if len(test_real) >= 260 and test_real[247:250] == '003':
        inv_str = test_real[247:260].strip()
        inv_part = inv_str[3:].lstrip('0')
        real_val = int(inv_part) if inv_part else 0
    print(f"Real MSA test: extracted {real_val} (expected 125)")
    
    # Test generated format
    test_gen = "BID  6851419131210068514191312124/7 MENT KING BOX                                                                                  000200N      003231                                                                                                            176003"
    gen_val = 0
    if test_gen.strip().endswith('003'):
        line_stripped = test_gen.strip()
        idx = line_stripped.rfind('003')
        if idx > 0:
            num_start = idx - 1
            while num_start >= 0 and line_stripped[num_start].isdigit():
                num_start -= 1
            num_start += 1
            num_str = line_stripped[num_start:idx]
            gen_val = int(num_str)
    print(f"Generated test: extracted {gen_val} (expected 176)")
    
    print("\n" + "-" * 80)
    print(f"{'Week':<12} {'Source':<10} {'Products':>10} {'With Inv':>10} {'Total Qty':>12} {'Difference':>12}")
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
            
            accuracy = 100.0 if real_stats['total_quantity'] == gen_stats['total_quantity'] else (
                (gen_stats['total_quantity']/real_stats['total_quantity']*100) if real_stats['total_quantity'] else 0
            )
            print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {accuracy:>11.1f}%")
            print("-" * 76)
            
            total_real += real_stats['total_quantity']
            total_gen += gen_stats['total_quantity']
    
    # Overall summary
    print(f"\n{'TOTAL':<12} {'Real':<10} {'':<10} {'':<10} {total_real:>12,}")
    print(f"{'':<12} {'Generated':<10} {'':<10} {'':<10} {total_gen:>12,} {total_gen - total_real:>+12,}")
    
    if total_real > 0:
        accuracy = (total_gen/total_real*100)
        print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {accuracy:>11.1f}%")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    print(f"Total Real MSA Quantity:      {total_real:,} units")
    print(f"Total Generated MSA Quantity: {total_gen:,} units")
    print(f"Overall Difference:           {total_gen - total_real:+,} units")
    
    if total_real > 0:
        accuracy = (total_gen/total_real*100)
        print(f"Overall Accuracy:             {accuracy:.2f}%")
        
        if abs(total_real - total_gen) == 0:
            print("\n✅ PERFECT MATCH: Total quantities are IDENTICAL across all weeks!")
        elif accuracy >= 99.9:
            print("\n✅ EXCELLENT: Near-perfect quantity match (99.9%+)!")
        elif accuracy >= 99:
            print("\n✅ VERY GOOD: 99%+ quantity accuracy achieved!")

if __name__ == '__main__':
    main()