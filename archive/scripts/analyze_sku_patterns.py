#!/usr/bin/env python3
"""
Analyze SKU patterns in actual MSA files to understand the mapping
between BID UPCs and PUR Distributor SKUs
"""

from collections import defaultdict
import re

def parse_msa_complete(filepath):
    """Parse MSA file extracting all record details"""
    records = {
        'bids': {},  # UPC -> BID record
        'sids': {},  # Customer ID -> SID record
        'purs': []   # List of PUR records
    }
    
    print(f"\nAnalyzing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            record_type = line[:3]
            
            if record_type == 'BID':
                # Extract UPC and SKU from BID record
                upc = line[3:18].strip()  # Full UPC (15 chars max)
                sku = line[18:31].strip() if len(line) > 31 else ''  # Distributor SKU field
                name = line[31:81].strip() if len(line) > 81 else ''
                
                records['bids'][upc] = {
                    'upc': upc,
                    'sku': sku,
                    'name': name,
                    'raw': line.rstrip()
                }
                
            elif record_type == 'SID':
                customer_id = line[3:11].strip() if len(line) > 11 else ''
                records['sids'][customer_id] = {
                    'customer_id': customer_id,
                    'raw': line.rstrip()
                }
                
            elif record_type == 'PUR':
                # Parse PUR record according to MULTICAT spec
                customer_id = line[3:11].strip() if len(line) > 11 else ''
                shipping_num = line[11:19].strip() if len(line) > 19 else ''
                shipping_ext = line[19:27].strip() if len(line) > 27 else ''
                distributor_sku = line[27:41].strip() if len(line) > 41 else ''
                
                # The actual format seems to concatenate fields differently
                # Let's also try to extract what looks like the SKU pattern
                # Based on the actual line structure
                
                # Try to find numeric patterns that look like SKUs
                sku_match = re.search(r'(\d{11,14})', line[20:50])
                extracted_sku = sku_match.group(1) if sku_match else distributor_sku
                
                records['purs'].append({
                    'customer_id': customer_id,
                    'distributor_sku': distributor_sku,
                    'extracted_sku': extracted_sku,
                    'raw': line.rstrip(),
                    'line_length': len(line.rstrip())
                })
    
    return records

def analyze_sku_relationships(records):
    """Analyze the relationship between BID UPCs and PUR SKUs"""
    print("\n=== SKU PATTERN ANALYSIS ===")
    
    # Collect unique SKUs from PUR records
    pur_skus = set()
    for pur in records['purs']:
        if pur['extracted_sku']:
            pur_skus.add(pur['extracted_sku'])
    
    print(f"Unique SKUs in PUR records: {len(pur_skus)}")
    
    # Collect UPCs from BID records
    bid_upcs = set(records['bids'].keys())
    print(f"Unique UPCs in BID records: {len(bid_upcs)}")
    
    # Try to match patterns
    matches = []
    for pur_sku in list(pur_skus)[:20]:  # Sample first 20
        for bid_upc in bid_upcs:
            # Check if PUR SKU is a substring of BID UPC
            if pur_sku in bid_upc:
                matches.append((pur_sku, bid_upc, 'substring'))
            # Check if they share last N digits
            elif len(pur_sku) >= 10 and len(bid_upc) >= 10:
                if pur_sku[-10:] == bid_upc[-10:]:
                    matches.append((pur_sku, bid_upc, 'last_10_digits'))
    
    print(f"\nFound {len(matches)} potential matches")
    
    # Show pattern examples
    if matches:
        print("\nExample SKU patterns:")
        for pur_sku, bid_upc, match_type in matches[:5]:
            print(f"  PUR SKU: {pur_sku}")
            print(f"  BID UPC: {bid_upc}")
            print(f"  Match: {match_type}")
            print()
    
    return pur_skus, bid_upcs

def analyze_pur_format(records):
    """Analyze the exact format of PUR records"""
    print("\n=== PUR RECORD FORMAT ANALYSIS ===")
    
    # Analyze line lengths
    line_lengths = defaultdict(int)
    for pur in records['purs']:
        line_lengths[pur['line_length']] += 1
    
    print("PUR record line lengths:")
    for length, count in sorted(line_lengths.items()):
        print(f"  Length {length}: {count} records")
    
    # Show sample PUR records with field breakdown
    print("\nSample PUR records:")
    for pur in records['purs'][:3]:
        line = pur['raw']
        print(f"\nRaw: {line[:80]}...")
        print(f"  Length: {len(line)}")
        print(f"  Customer (3-11): '{line[3:11] if len(line) > 11 else ''}'")
        print(f"  Field (11-27): '{line[11:27] if len(line) > 27 else ''}'")
        print(f"  SKU area (27-41): '{line[27:41] if len(line) > 41 else ''}'")
        print(f"  Extracted SKU: '{pur['extracted_sku']}'")

def compare_files(file1, file2):
    """Compare SKU patterns between two MSA files"""
    print("\n" + "="*60)
    print(f"COMPARING FILES")
    print("="*60)
    
    records1 = parse_msa_complete(file1)
    records2 = parse_msa_complete(file2)
    
    # Compare PUR SKUs
    skus1 = set(pur['extracted_sku'] for pur in records1['purs'] if pur['extracted_sku'])
    skus2 = set(pur['extracted_sku'] for pur in records2['purs'] if pur['extracted_sku'])
    
    common_skus = skus1 & skus2
    only_in_1 = skus1 - skus2
    only_in_2 = skus2 - skus1
    
    print(f"\nSKUs in {file1.split('/')[-1]}: {len(skus1)}")
    print(f"SKUs in {file2.split('/')[-1]}: {len(skus2)}")
    print(f"Common SKUs: {len(common_skus)}")
    print(f"Only in first: {len(only_in_1)}")
    print(f"Only in second: {len(only_in_2)}")
    
    # Show examples of differences
    if only_in_2:
        print(f"\nExample SKUs only in {file2.split('/')[-1]}:")
        for sku in list(only_in_2)[:5]:
            print(f"  {sku}")

def main():
    # Analyze 08/08/2025 file
    actual_file = "MSA Data Fr/08082025"
    records = parse_msa_complete(actual_file)
    
    # Analyze SKU relationships
    pur_skus, bid_upcs = analyze_sku_relationships(records)
    
    # Analyze PUR format
    analyze_pur_format(records)
    
    # Compare with 08/01/2025
    prior_file = "MSA Data Fr/08012025"
    compare_files(prior_file, actual_file)
    
    # Key findings
    print("\n" + "="*60)
    print("KEY FINDINGS")
    print("="*60)
    print("""
1. PUR records use DISTRIBUTOR SKUs (not full UPCs)
2. These SKUs are typically 11-14 digits
3. They appear to be the last N digits of the full UPC
4. The format is: PUR + customer + spaces + distributor_sku
5. Line length is consistently 130 characters
    """)

if __name__ == "__main__":
    main()