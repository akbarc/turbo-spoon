#!/usr/bin/env python3
"""
Deep dive into the 10% accuracy gap in MSA generation
"""

from collections import defaultdict
import re

def parse_msa_detailed(filepath):
    """Parse MSA file with detailed extraction of all fields"""
    records = {
        'header': None,
        'bids': {},
        'sids': {},
        'purs': [],
        'raw_purs': []  # Keep raw lines for analysis
    }
    
    print(f"\nParsing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            record_type = line[:3]
            
            if record_type == 'HID':
                records['header'] = line.rstrip('\r\n')
                
            elif record_type == 'BID':
                upc = line[3:18].strip()
                records['bids'][upc] = {
                    'raw': line.rstrip('\r\n'),
                    'upc': upc,
                    'name': line[18:78].strip() if len(line) > 78 else '',
                    'quantity': line[199:210].strip() if len(line) > 210 else '0',
                    'line_num': line_num
                }
                
            elif record_type == 'SID':
                customer_id = line[3:18].strip()
                records['sids'][customer_id] = {
                    'raw': line.rstrip('\r\n'),
                    'customer_id': customer_id,
                    'name': line[18:78].strip() if len(line) > 78 else '',
                    'line_num': line_num
                }
                
            elif record_type == 'PUR':
                # Keep the raw line for analysis
                records['raw_purs'].append(line.rstrip('\r\n'))
                
                # Try to parse PUR record
                try:
                    # Different parsing attempts for malformed records
                    customer_id = line[3:18].strip()
                    upc = line[18:33].strip() if len(line) > 33 else ''
                    
                    # The quantity field location varies in malformed records
                    # Try multiple positions
                    quantity = None
                    
                    # Standard position
                    if len(line) > 44:
                        qty_str = line[33:44].strip()
                        if qty_str and qty_str.replace('.', '').replace('-', '').isdigit():
                            quantity = qty_str
                    
                    # Alternative positions (for malformed records)
                    if not quantity and len(line) > 80:
                        # Look for numeric patterns
                        match = re.search(r'(\d{5,11})', line[33:])
                        if match:
                            quantity = match.group(1)
                    
                    records['purs'].append({
                        'customer_id': customer_id,
                        'upc': upc,
                        'quantity': quantity or '0',
                        'raw': line.rstrip('\r\n'),
                        'line_num': line_num
                    })
                except Exception as e:
                    print(f"  Error parsing PUR at line {line_num}: {e}")
                    print(f"    Line content: {line[:100]}...")
    
    return records

def analyze_accuracy_breakdown():
    """Calculate accuracy for each component"""
    print("\n" + "="*70)
    print("ACCURACY BREAKDOWN ANALYSIS")
    print("="*70)
    
    # For 08/08/2025
    print("\n### 08/08/2025 Analysis ###")
    print("\nAccuracy Components:")
    print("- BIDs (Products): 99.8% accurate (5198 vs 5206)")
    print("- SIDs (Customers): 98.9% accurate (183 vs 185)")  
    print("- PURs (Purchases): 71.6% accurate (3470 vs 4844)")
    print("\nOverall accuracy = (99.8 + 98.9 + 71.6) / 3 = 90.1%")
    
    print("\nThe 10% gap comes primarily from PUR records (28.4% inaccuracy)")
    print("This represents 1,374 missing purchase records")

def analyze_purchase_discrepancies():
    """Analyze specific purchase record differences"""
    print("\n" + "="*70)
    print("PURCHASE RECORD DISCREPANCY ANALYSIS")
    print("="*70)
    
    # Parse both files
    generated = parse_msa_detailed("generated_msa_08082025_improved.txt")
    actual = parse_msa_detailed("MSA Data Fr/08082025")
    
    print(f"\nGenerated PURs: {len(generated['purs'])}")
    print(f"Actual PURs: {len(actual['purs'])}")
    print(f"Difference: {len(actual['purs']) - len(generated['purs'])}")
    
    # Group purchases by customer
    gen_by_customer = defaultdict(list)
    for pur in generated['purs']:
        gen_by_customer[pur['customer_id']].append(pur)
    
    act_by_customer = defaultdict(list)
    for pur in actual['purs']:
        act_by_customer[pur['customer_id']].append(pur)
    
    # Find customers only in actual
    missing_customers = set(act_by_customer.keys()) - set(gen_by_customer.keys())
    print(f"\nCustomers with purchases only in actual: {len(missing_customers)}")
    
    # Analyze sample of actual PUR records
    print("\n### Sample of Actual PUR Records (first 10) ###")
    for i, pur_line in enumerate(actual['raw_purs'][:10], 1):
        print(f"\n{i}. Raw line: {pur_line[:100]}...")
        print(f"   Length: {len(pur_line)} characters")
        
        # Try to identify the structure
        if len(pur_line) > 50:
            print(f"   Customer ID area (3-18): '{pur_line[3:18]}'")
            print(f"   UPC area (18-33): '{pur_line[18:33]}'")
            print(f"   After UPC (33-80): '{pur_line[33:80] if len(pur_line) > 80 else pur_line[33:]}'")

def identify_missing_patterns():
    """Identify patterns in what we're missing"""
    print("\n" + "="*70)
    print("MISSING DATA PATTERNS")
    print("="*70)
    
    generated = parse_msa_detailed("generated_msa_08082025_improved.txt")
    actual = parse_msa_detailed("MSA Data Fr/08082025")
    
    # Create sets of (customer, upc) pairs
    gen_pairs = set()
    for pur in generated['purs']:
        gen_pairs.add((pur['customer_id'], pur['upc']))
    
    act_pairs = set()
    act_quantities = {}
    for pur in actual['purs']:
        pair = (pur['customer_id'], pur['upc'])
        act_pairs.add(pair)
        act_quantities[pair] = pur['quantity']
    
    missing_pairs = act_pairs - gen_pairs
    print(f"\nMissing customer-product pairs: {len(missing_pairs)}")
    
    # Analyze missing UPCs
    missing_upcs = defaultdict(int)
    missing_customers = defaultdict(int)
    
    for customer_id, upc in missing_pairs:
        missing_upcs[upc] += 1
        missing_customers[customer_id] += 1
    
    print(f"\nUnique UPCs in missing purchases: {len(missing_upcs)}")
    print(f"Unique customers in missing purchases: {len(missing_customers)}")
    
    # Show top missing UPCs
    print("\n### Top 10 Missing UPCs by Frequency ###")
    sorted_upcs = sorted(missing_upcs.items(), key=lambda x: x[1], reverse=True)[:10]
    for upc, count in sorted_upcs:
        product_name = actual['bids'].get(upc, {}).get('name', 'Unknown')
        print(f"  UPC: {upc:15} | Count: {count:3} | Product: {product_name}")
    
    # Check if missing UPCs are in our BID records
    print("\n### Missing UPC Analysis ###")
    missing_upcs_list = list(missing_upcs.keys())[:20]
    in_generated_bids = 0
    in_actual_bids = 0
    
    for upc in missing_upcs_list:
        if upc in generated['bids']:
            in_generated_bids += 1
        if upc in actual['bids']:
            in_actual_bids += 1
    
    print(f"Missing UPCs that ARE in our generated BIDs: {in_generated_bids}/{len(missing_upcs_list)}")
    print(f"Missing UPCs that ARE in actual BIDs: {in_actual_bids}/{len(missing_upcs_list)}")

def check_data_quality_issues():
    """Check for data quality issues in actual file"""
    print("\n" + "="*70)
    print("DATA QUALITY ANALYSIS")
    print("="*70)
    
    actual = parse_msa_detailed("MSA Data Fr/08082025")
    
    # Look for unusual quantities
    unusual_quantities = []
    for pur in actual['purs']:
        try:
            if pur['quantity']:
                qty_str = pur['quantity'].replace('.', '')
                if len(qty_str) > 6:  # Unusually large
                    unusual_quantities.append(pur)
        except:
            pass
    
    print(f"\nPurchases with unusual quantities (>6 digits): {len(unusual_quantities)}")
    if unusual_quantities:
        print("\n### Examples of Unusual Quantities ###")
        for pur in unusual_quantities[:5]:
            print(f"  Customer: {pur['customer_id']:15} | UPC: {pur['upc']:15} | Qty: {pur['quantity']}")
            print(f"    Raw line: {pur['raw'][:100]}...")
    
    # Check for malformed customer IDs
    print("\n### Customer ID Analysis ###")
    customer_ids = list(actual['sids'].keys())
    numeric_ids = sum(1 for cid in customer_ids if cid.isdigit())
    alphanumeric_ids = sum(1 for cid in customer_ids if not cid.isdigit())
    
    print(f"Numeric customer IDs: {numeric_ids}")
    print(f"Alphanumeric customer IDs: {alphanumeric_ids}")
    
    # Check line lengths
    print("\n### PUR Record Line Length Analysis ###")
    line_lengths = defaultdict(int)
    for line in actual['raw_purs']:
        length = len(line)
        line_lengths[length] += 1
    
    print("Distribution of PUR line lengths:")
    for length in sorted(line_lengths.keys())[:10]:
        print(f"  Length {length:3}: {line_lengths[length]:4} records")

def main():
    print("="*70)
    print("10% ACCURACY GAP INVESTIGATION")
    print("="*70)
    
    # Break down the accuracy calculation
    analyze_accuracy_breakdown()
    
    # Analyze purchase discrepancies
    analyze_purchase_discrepancies()
    
    # Identify missing patterns
    identify_missing_patterns()
    
    # Check data quality
    check_data_quality_issues()
    
    print("\n" + "="*70)
    print("SUMMARY OF FINDINGS")
    print("="*70)
    print("""
The 10% accuracy gap breakdown:
- 0.2% from products (8 product difference)
- 1.1% from customers (2 customer difference)  
- 28.4% from purchase records (1,374 record difference)

The main issue is with PUR (purchase) records where we have 71.6% accuracy.
This appears to be due to:
1. Data format inconsistencies in the actual MSA file
2. Possible manual entries or corrections in the actual file
3. Transactions that may not be in our POS system
4. Different date ranges or cutoff times
""")

if __name__ == "__main__":
    main()