#!/usr/bin/env python3
"""
Deep analysis of Distributor SKU patterns to find sustainable mapping logic
"""

from collections import defaultdict
import os
import re
from database_pymssql import connection_pool

def extract_all_distributor_skus():
    """Extract all distributor SKUs from actual MSA files"""
    print("="*70)
    print("EXTRACTING DISTRIBUTOR SKUs FROM ALL MSA FILES")
    print("="*70)
    
    msa_dir = "MSA Data Fr"
    all_dist_skus = set()
    sku_to_products = defaultdict(set)
    
    # Process all MSA files
    for filename in os.listdir(msa_dir):
        filepath = os.path.join(msa_dir, filename)
        if os.path.isfile(filepath):
            print(f"\nProcessing: {filename}")
            
            # Track BID records (products)
            bid_by_upc = {}
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        name = line[18:78].strip() if len(line) > 78 else ''
                        bid_by_upc[upc] = name
                    
                    elif line.startswith('PUR'):
                        # Extract distributor SKU
                        if len(line) > 41:
                            dist_sku = line[27:41].strip()
                            if dist_sku:
                                all_dist_skus.add(dist_sku)
                                
                                # Try to find matching product
                                for upc, name in bid_by_upc.items():
                                    if dist_sku in upc or upc in dist_sku:
                                        sku_to_products[dist_sku].add(name)
                                        break
    
    print(f"\nTotal unique Distributor SKUs found: {len(all_dist_skus)}")
    return all_dist_skus, sku_to_products

def analyze_sku_patterns(dist_skus):
    """Analyze patterns in distributor SKUs"""
    print("\n" + "="*70)
    print("DISTRIBUTOR SKU PATTERN ANALYSIS")
    print("="*70)
    
    # Length distribution
    length_dist = defaultdict(int)
    for sku in dist_skus:
        length_dist[len(sku)] += 1
    
    print("\n### SKU Length Distribution ###")
    for length in sorted(length_dist.keys()):
        print(f"Length {length:2}: {length_dist[length]:4} SKUs ({length_dist[length]*100/len(dist_skus):.1f}%)")
    
    # Prefix patterns
    prefix_patterns = defaultdict(list)
    for sku in dist_skus:
        if len(sku) >= 5:
            prefix = sku[:5]
            prefix_patterns[prefix].append(sku)
    
    print("\n### Common Prefixes (5 digits) ###")
    sorted_prefixes = sorted(prefix_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:15]
    for prefix, skus in sorted_prefixes:
        print(f"Prefix '{prefix}': {len(skus):3} SKUs")
        # Show examples
        for example in skus[:2]:
            print(f"  Example: {example}")
    
    # Check for embedded patterns
    print("\n### SKU Structure Analysis ###")
    
    # Count leading zeros
    leading_zeros = defaultdict(int)
    for sku in dist_skus:
        zeros = len(sku) - len(sku.lstrip('0'))
        leading_zeros[zeros] += 1
    
    print("\nLeading zeros distribution:")
    for zeros in sorted(leading_zeros.keys()):
        print(f"  {zeros} zeros: {leading_zeros[zeros]} SKUs ({leading_zeros[zeros]*100/len(dist_skus):.1f}%)")
    
    # Check if they're UPC-A format (12 digits + check)
    upc_like = sum(1 for sku in dist_skus if len(sku.lstrip('0')) in [11, 12, 13])
    print(f"\nUPC-like format (11-13 significant digits): {upc_like} ({upc_like*100/len(dist_skus):.1f}%)")
    
    return prefix_patterns

def check_pos_correlations(dist_skus):
    """Check correlations with POS fields"""
    print("\n" + "="*70)
    print("CHECKING POS DATABASE CORRELATIONS")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Get tobacco items with all potentially relevant fields
    query = """
    SELECT TOP 100
        ItemLookupCode,
        Description,
        Alias,
        GTIN,
        SubDescription1,
        SubDescription2,
        SubDescription3,
        CategoryID
    FROM Item
    WHERE CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
    ORDER BY ItemLookupCode
    """
    
    cursor.execute(query)
    items = cursor.fetchall()
    
    print(f"\nAnalyzing {len(items)} POS items...")
    
    # Check for barcode field
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Item' AND COLUMN_NAME LIKE '%barcode%'")
    barcode_columns = cursor.fetchall()
    if barcode_columns:
        print(f"Found barcode columns: {[col['COLUMN_NAME'] for col in barcode_columns]}")
    
    # Check for UPC/EAN fields
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Item' AND (COLUMN_NAME LIKE '%UPC%' OR COLUMN_NAME LIKE '%EAN%')")
    upc_columns = cursor.fetchall()
    if upc_columns:
        print(f"Found UPC/EAN columns: {[col['COLUMN_NAME'] for col in upc_columns]}")
    
    # Check ItemBarcode table
    cursor.execute("SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ItemBarcode'")
    if cursor.fetchone()['cnt'] > 0:
        print("\nFound ItemBarcode table!")
        cursor.execute("""
            SELECT TOP 20 
                i.ItemLookupCode,
                ib.Barcode
            FROM Item i
            JOIN ItemBarcode ib ON i.ID = ib.ItemID
            WHERE i.CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
        """)
        barcode_samples = cursor.fetchall()
        
        print("\n### Sample Item Barcodes ###")
        matches_found = 0
        for sample in barcode_samples[:10]:
            print(f"POS: {sample['ItemLookupCode']:15} → Barcode: {sample['Barcode']}")
            # Check if barcode matches any distributor SKU pattern
            barcode_clean = sample['Barcode'].strip().lstrip('0')
            for dist_sku in list(dist_skus)[:100]:  # Check sample
                dist_clean = dist_sku.lstrip('0')
                if barcode_clean in dist_clean or dist_clean in barcode_clean:
                    matches_found += 1
                    print(f"  ✓ Matches Distributor SKU: {dist_sku}")
                    break
        
        if matches_found > 0:
            print(f"\n✓ Found {matches_found} barcode matches! ItemBarcode table is the key!")
    
    # Analyze Alias field patterns
    print("\n### Alias Field Analysis ###")
    alias_patterns = defaultdict(int)
    for item in items:
        if item['Alias']:
            alias = item['Alias'].strip()
            # Check if numeric
            if alias.replace('-', '').isdigit():
                alias_patterns['numeric'] += 1
                # Check if it matches distributor SKU patterns
                alias_clean = alias.replace('-', '').lstrip('0')
                for dist_sku in list(dist_skus)[:50]:
                    if alias_clean in dist_sku.lstrip('0'):
                        alias_patterns['matches_dist_sku'] += 1
                        print(f"Alias match: {item['ItemLookupCode']} alias '{alias}' → Dist SKU {dist_sku}")
                        break
            else:
                alias_patterns['text'] += 1
    
    print(f"Numeric aliases: {alias_patterns['numeric']}")
    print(f"Text aliases: {alias_patterns['text']}")
    print(f"Aliases matching Dist SKUs: {alias_patterns['matches_dist_sku']}")
    
    cursor.close()
    connection_pool.return_connection(conn)

def find_sustainable_mapping():
    """Identify sustainable mapping strategy"""
    print("\n" + "="*70)
    print("SUSTAINABLE MAPPING STRATEGY")
    print("="*70)
    
    print("""
### KEY FINDINGS ###

1. DISTRIBUTOR SKU CHARACTERISTICS:
   - Consistently 14 characters (padded with leading zeros)
   - Appear to be UPC-A or EAN-13 format
   - Common prefixes suggest manufacturer codes
   
2. LIKELY MAPPING SOURCES:
   a) ItemBarcode table (if exists) - Most promising
   b) Alias field (if contains UPC/barcode)
   c) GTIN field (Global Trade Item Number)
   d) SubDescription fields (might contain UPC)
   
3. SUSTAINABLE APPROACH:
   - Build mapping from ItemBarcode → Distributor SKU
   - Use zero-padded 14-character format
   - Fall back to Alias/GTIN if no barcode
   - Learn new mappings from each MSA file
   
4. PATTERN RECOGNITION:
   - Distributor SKUs are zero-padded barcodes
   - Format: 00000000XXXXXX (14 chars total)
   - Core digits are standard UPC/EAN codes
""")

def main():
    # Extract all distributor SKUs
    dist_skus, sku_to_products = extract_all_distributor_skus()
    
    # Analyze patterns
    prefix_patterns = analyze_sku_patterns(dist_skus)
    
    # Check POS correlations
    check_pos_correlations(dist_skus)
    
    # Propose sustainable solution
    find_sustainable_mapping()
    
    print("\n" + "="*70)
    print("RECOMMENDED NEXT STEP")
    print("="*70)
    print("""
Query the ItemBarcode table to build proper SKU mappings:

SELECT 
    i.ItemLookupCode,
    i.Description,
    ib.Barcode,
    RIGHT('00000000000000' + ib.Barcode, 14) as DistributorSKU
FROM Item i
JOIN ItemBarcode ib ON i.ID = ib.ItemID
WHERE i.CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)

This will give us the sustainable mapping we need!
""")

if __name__ == "__main__":
    main()