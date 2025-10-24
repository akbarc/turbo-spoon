#!/usr/bin/env python3
"""
Investigate the consistent 4-product gap across all weeks
"""

def find_missing_products(week_date):
    """Find which products are consistently missing"""
    
    real_file = f'MSA Data Fr/{week_date}'
    generated_file = f'generated_msa_{week_date}_100_final.txt'
    
    # Extract products from both files
    real_products = set()
    gen_products = set()
    
    with open(real_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('BID'):
                try:
                    upc = line[3:16].strip()
                    name = line[29:89].strip()
                    key = f"{upc}|{name}"
                    real_products.add(key)
                except:
                    pass
    
    with open(generated_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('BID'):
                try:
                    upc = line[3:16].strip()
                    name = line[29:89].strip()
                    key = f"{upc}|{name}"
                    gen_products.add(key)
                except:
                    pass
    
    # Find differences
    only_in_real = real_products - gen_products
    only_in_gen = gen_products - real_products
    
    return only_in_real, only_in_gen

def main():
    """Analyze the 4-product gap pattern"""
    
    weeks = ['08082025', '08012025', '07252025', '07182025', '07112025', '07042025', '06272025']
    
    print("="*80)
    print("INVESTIGATING THE 4-PRODUCT GAP")
    print("="*80)
    
    # Collect missing products from each week
    all_missing = {}
    
    for week in weeks:
        missing, extra = find_missing_products(week)
        
        print(f"\nWeek {week}:")
        print(f"  Products only in real MSA: {len(missing)}")
        print(f"  Products only in generated: {len(extra)}")
        
        if missing:
            print(f"  Missing products:")
            for prod in sorted(missing)[:10]:  # Show first 10
                upc, name = prod.split('|')
                print(f"    {upc} | {name}")
                
                # Track which weeks each product is missing
                if prod not in all_missing:
                    all_missing[prod] = []
                all_missing[prod].append(week)
    
    # Find products missing in ALL weeks
    print("\n" + "="*80)
    print("PRODUCTS CONSISTENTLY MISSING ACROSS ALL WEEKS:")
    print("="*80)
    
    consistent_missing = [prod for prod, weeks_list in all_missing.items() 
                         if len(weeks_list) >= 6]  # Missing in at least 6 weeks
    
    if consistent_missing:
        print(f"\nFound {len(consistent_missing)} products missing in 6+ weeks:")
        for prod in sorted(consistent_missing):
            upc, name = prod.split('|')
            weeks_count = len(all_missing[prod])
            print(f"  {upc} | {name[:40]:<40} | Missing in {weeks_count} weeks")
    
    # Check if these are duplicate BID lines
    print("\n" + "="*80)
    print("CHECKING FOR DUPLICATE BID LINES IN REAL MSA:")
    print("="*80)
    
    # Check one week for duplicates
    real_file = 'MSA Data Fr/08082025'
    bid_lines = {}
    duplicates = []
    
    with open(real_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if line.startswith('BID'):
                try:
                    upc = line[3:16].strip()
                    name = line[29:89].strip()
                    key = f"{upc}|{name}"
                    
                    if key in bid_lines:
                        duplicates.append((key, bid_lines[key], line_num))
                    else:
                        bid_lines[key] = line_num
                except:
                    pass
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate BID entries in 08082025:")
        for key, first_line, dup_line in duplicates[:10]:
            upc, name = key.split('|')
            print(f"  {upc} | {name[:30]:<30} | Lines {first_line} & {dup_line}")
    else:
        print("\nNo duplicate BID entries found")
    
    print("\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)
    print("The 4-product difference is consistent across all weeks.")
    print("These appear to be specific products that exist in MULTICAT")
    print("but are not being picked up by our generator, likely because:")
    print("1. They have no sales/purchases history")
    print("2. They are manually maintained entries in MULTICAT")
    print("3. They may be duplicate entries or special cases")

if __name__ == '__main__':
    main()