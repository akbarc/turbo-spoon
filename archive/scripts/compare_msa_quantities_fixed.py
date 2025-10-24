#!/usr/bin/env python3
"""
Compare total quantities between real MSA files and generated MSA files - FIXED
"""

def calculate_msa_totals(filepath):
    """Calculate total inventory from MSA file"""
    total_quantity = 0
    product_count = 0
    products_with_inventory = 0
    
    # Debug: Check different possible inventory positions
    inventory_positions = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if line.startswith('BID'):
                    product_count += 1
                    
                    # Try to find inventory field
                    # Based on the real MSA sample, inventory appears at the end
                    # Format: 00300000000XXX where XXX is the inventory
                    
                    # Look for pattern "003" followed by numbers
                    if '003' in line:
                        # Find all occurrences of 003
                        idx = line.rfind('003')  # Get the last occurrence
                        if idx > 0 and idx < len(line) - 10:
                            inv_str = line[idx:idx+13].strip()
                            
                            # Parse the inventory value
                            if inv_str.startswith('003-'):
                                # Negative inventory
                                try:
                                    inv_value = -int(inv_str[4:])
                                except:
                                    inv_value = 0
                            elif inv_str.startswith('003'):
                                # Positive inventory
                                try:
                                    # Remove '003' prefix and any leading zeros
                                    inv_part = inv_str[3:].lstrip('0')
                                    inv_value = int(inv_part) if inv_part else 0
                                except:
                                    inv_value = 0
                            else:
                                inv_value = 0
                            
                            total_quantity += inv_value
                            if inv_value > 0:
                                products_with_inventory += 1
                            
                            # Debug first few products
                            if line_num <= 5:
                                upc = line[3:16].strip()
                                name = line[29:89].strip() if len(line) > 89 else line[29:].strip()
                                inventory_positions.append(f"  Line {line_num}: {name[:30]} -> '{inv_str}' = {inv_value}")
                    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    
    # Print debug info for first file
    if inventory_positions and 'Real' in filepath:
        print(f"\nDebug - Sample inventory parsing from {filepath}:")
        for pos in inventory_positions:
            print(pos)
    
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
    
    # First, let's check one file in detail
    print("\nAnalyzing inventory field location...")
    test_file = 'MSA Data Fr/08082025'
    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if line.startswith('BID') and i < 5:
                print(f"\nLine {i+1} length: {len(line)}")
                print(f"Line content (last 50 chars): ...{line[-50:]}")
                
                # Find '003' pattern
                idx = line.rfind('003')
                if idx > 0:
                    print(f"Found '003' at position {idx}")
                    print(f"Inventory string: '{line[idx:idx+13]}'")
    
    print("\n" + "-" * 80)
    print(f"{'Week':<12} {'Source':<10} {'Products':>10} {'With Inv':>10} {'Total Qty':>12} {'Difference':>12}")
    print("-" * 76)
    
    total_real = 0
    total_gen = 0
    week_details = []
    
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
            
            accuracy = 100.0 if real_stats['total_quantity'] == gen_stats['total_quantity'] else (gen_stats['total_quantity']/real_stats['total_quantity']*100 if real_stats['total_quantity'] else 0)
            print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {accuracy:>11.1f}%")
            print("-" * 76)
            
            total_real += real_stats['total_quantity']
            total_gen += gen_stats['total_quantity']
            
            week_details.append({
                'week': week,
                'real': real_stats,
                'gen': gen_stats,
                'diff': diff
            })
    
    # Overall summary
    print(f"\n{'TOTAL':<12} {'Real':<10} {'':<10} {'':<10} {total_real:>12,}")
    print(f"{'':<12} {'Generated':<10} {'':<10} {'':<10} {total_gen:>12,} {total_gen - total_real:>+12,}")
    
    if total_real > 0:
        print(f"{'':<12} {'Match %':<10} {'':<10} {'':<10} {(total_gen/total_real*100):>11.1f}%")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    if total_real == total_gen:
        print("✅ PERFECT MATCH: Total quantities are identical across all weeks!")
    else:
        print(f"Total Real MSA Quantity:      {total_real:,} units")
        print(f"Total Generated MSA Quantity: {total_gen:,} units")
        print(f"Overall Difference:           {total_gen - total_real:+,} units")
        print(f"Overall Accuracy:             {(total_gen/total_real*100 if total_real else 0):.2f}%")

if __name__ == '__main__':
    main()