#!/usr/bin/env python3
"""
Compare total quantities between real MSA files and generated MSA files - FINAL VERSION
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
                    
                    # Two possible formats:
                    # Real MSA: inventory at position 247-260 (00300000000125)
                    # Generated: inventory at end of line (just the number after 003)
                    
                    inv_value = 0
                    
                    if len(line) >= 260:
                        # Real MSA format - inventory at fixed position
                        inv_str = line[247:260].strip()
                        if inv_str.startswith('003-'):
                            inv_value = -int(inv_str[4:])
                        elif inv_str.startswith('003'):
                            inv_part = inv_str[3:].lstrip('0')
                            inv_value = int(inv_part) if inv_part else 0
                    else:
                        # Generated format - inventory at end after '003'
                        # Find the last occurrence of a number after whitespace
                        parts = line.strip().split()
                        if parts:
                            last_part = parts[-1]
                            # Check if it ends with '003' pattern
                            if '003' in last_part:
                                # Extract number before '003'
                                idx = last_part.find('003')
                                if idx > 0:
                                    try:
                                        inv_value = int(last_part[:idx])
                                    except:
                                        inv_value = 0
                            else:
                                # Try to parse as plain number
                                try:
                                    inv_value = int(last_part)
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
        
        if abs(accuracy - 100) < 0.1:
            print("\n✅ PERFECT MATCH: Total quantities are identical!")
        elif accuracy >= 99:
            print("\n✅ EXCELLENT: 99%+ quantity accuracy achieved!")
        elif accuracy >= 95:
            print("\n✅ GOOD: 95%+ quantity accuracy achieved!")
    
    # Detailed breakdown for latest week
    print("\n" + "=" * 80)
    print("WEEK 08/08/2025 DETAILED BREAKDOWN:")
    print("=" * 80)
    
    if real_stats and gen_stats:
        print(f"Real MSA:")
        print(f"  Total products:             {real_stats['product_count']:,}")
        print(f"  Products with inventory:    {real_stats['products_with_inventory']:,}")
        print(f"  Total quantity:             {real_stats['total_quantity']:,} units")
        
        print(f"\nGenerated MSA:")
        print(f"  Total products:             {gen_stats['product_count']:,}")
        print(f"  Products with inventory:    {gen_stats['products_with_inventory']:,}")
        print(f"  Total quantity:             {gen_stats['total_quantity']:,} units")
        
        print(f"\nComparison:")
        print(f"  Product difference:         {gen_stats['product_count'] - real_stats['product_count']:+,}")
        print(f"  Quantity difference:        {gen_stats['total_quantity'] - real_stats['total_quantity']:+,} units")
        
        if real_stats['total_quantity'] > 0:
            print(f"  Quantity accuracy:          {(gen_stats['total_quantity']/real_stats['total_quantity']*100):.2f}%")

if __name__ == '__main__':
    main()