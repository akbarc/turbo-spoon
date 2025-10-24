#!/usr/bin/env python3
"""
Find the remaining 17% UPC mappings by analyzing sales patterns
Match MSA sales to POS sales based on customer, quantity, and time
"""

import pymssql
import os
import re
import csv
from datetime import datetime, timedelta
from collections import defaultdict, Counter

os.environ['TDSVER'] = '7.0'

def connect_db():
    """Connect to POS database"""
    try:
        conn = pymssql.connect(
            server='10.1.10.105',
            user='amchranya',
            password='2000Akbar!',
            database='GAWDB',
            tds_version='7.0',
            login_timeout=30
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def parse_msa_sales(filepath):
    """Parse PUR records from MSA file to get sales"""
    sales = []
    
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            if line.startswith('PUR'):
                # Extract customer, UPC, quantity, price
                customer_id = line[3:30].strip()
                upc = line[30:60].strip() if len(line) > 30 else ""
                
                # Parse quantity and price
                qty = 0
                price = 0.0
                if len(line) > 90:
                    data_section = line[90:]
                    
                    # Look for 001 (quantity marker)
                    if '001' in data_section:
                        idx = data_section.index('001')
                        qty_str = data_section[idx+3:idx+14]
                        if '.' in qty_str:
                            try:
                                qty = int(float(qty_str))
                            except:
                                pass
                    
                    # Look for 002 (price marker)
                    if '002' in data_section:
                        idx = data_section.index('002')
                        price_str = data_section[idx+3:idx+14]
                        try:
                            price = float(price_str)
                        except:
                            pass
                
                if qty > 0:  # Only include actual sales
                    sales.append({
                        'customer': customer_id,
                        'upc': upc,
                        'quantity': qty,
                        'price': price
                    })
    
    return sales

def parse_csv_sales(filepath):
    """Parse sales from CSV file"""
    sales = []
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                sales.append({
                    'customer': row[0].strip(),
                    'upc': row[1].strip(),
                    'quantity': int(row[2]),
                    'price': float(row[3])
                })
    
    return sales

def find_upc_mappings():
    """Find UPC mappings by matching sales patterns"""
    
    print("="*70)
    print("FINDING REMAINING UPC MAPPINGS THROUGH SALES ANALYSIS")
    print("="*70)
    
    # Parse MSA sales for 08082025
    print("\nParsing MSA sales data...")
    msa_sales = parse_msa_sales('MSA Data Fr/08082025')
    print(f"  Found {len(msa_sales)} MSA sales transactions")
    
    # Group MSA sales by customer and UPC
    msa_sales_map = defaultdict(list)
    msa_upc_totals = defaultdict(int)
    
    for sale in msa_sales:
        key = (sale['customer'], sale['upc'])
        msa_sales_map[key].append(sale)
        msa_upc_totals[sale['upc']] += sale['quantity']
    
    # Get unique MSA UPCs
    msa_upcs = set(s['upc'] for s in msa_sales)
    print(f"  Unique MSA UPCs in sales: {len(msa_upcs)}")
    
    # Connect to database
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor(as_dict=True)
    
    # Get the week's dates (Aug 2-8, 2025)
    week_start = datetime(2025, 8, 2)
    week_end = datetime(2025, 8, 8, 23, 59, 59)
    
    # Get POS sales for the same week
    print("\nQuerying POS sales for the same week...")
    
    category_ids = [11, 23, 31, 45, 48, 49, 51, 56, 57, 81, 83]
    category_filter = ','.join(str(c) for c in category_ids)
    
    query = f"""
    SELECT 
        c.AccountNumber,
        i.ItemLookupCode as UPC,
        i.Description,
        SUM(te.Quantity) as Quantity,
        AVG(te.Price) as Price
    FROM TransactionEntry te
    INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    INNER JOIN Customer c ON t.CustomerID = c.ID
    WHERE t.Time >= %s AND t.Time <= %s
      AND i.CategoryID IN ({category_filter})
      AND te.Quantity > 0
    GROUP BY c.AccountNumber, i.ItemLookupCode, i.Description
    ORDER BY SUM(te.Quantity) DESC
    """
    
    cursor.execute(query, (week_start, week_end))
    pos_sales = cursor.fetchall()
    
    print(f"  Found {len(pos_sales)} POS sales aggregations")
    
    # Group POS sales by quantity for matching
    pos_by_qty = defaultdict(list)
    for sale in pos_sales:
        qty = int(sale['Quantity'])
        pos_by_qty[qty].append(sale)
    
    # Now try to match unmatched MSA UPCs
    print("\n" + "="*70)
    print("MATCHING UNMATCHED UPCs BY SALES PATTERNS")
    print("="*70)
    
    # First, identify which MSA UPCs are already matched
    matched_upcs = set()
    unmatched_upcs = set()
    
    for msa_upc in msa_upcs:
        # Check if this UPC matches using our known transformation (remove trailing 0)
        if len(msa_upc) > 0 and msa_upc[-1] == '0':
            pos_upc = msa_upc[:-1]
            
            # Check if this POS UPC exists
            found = False
            for sale in pos_sales:
                if sale['UPC'] == pos_upc or sale['UPC'] == '0' + pos_upc:
                    matched_upcs.add(msa_upc)
                    found = True
                    break
            
            if not found:
                unmatched_upcs.add(msa_upc)
        else:
            unmatched_upcs.add(msa_upc)
    
    print(f"\nAlready matched: {len(matched_upcs)} UPCs")
    print(f"Still unmatched: {len(unmatched_upcs)} UPCs")
    
    # Now match the unmatched by sales patterns
    mappings_found = {}
    
    print("\nSearching for matches based on sales quantities...")
    
    for msa_upc in list(unmatched_upcs)[:100]:  # Process first 100 unmatched
        total_qty = msa_upc_totals[msa_upc]
        
        # Look for POS products with same total quantity
        candidates = pos_by_qty.get(total_qty, [])
        
        if candidates:
            # If only one candidate with exact quantity, likely a match
            if len(candidates) == 1:
                pos_match = candidates[0]
                mappings_found[msa_upc] = {
                    'pos_upc': pos_match['UPC'],
                    'description': pos_match['Description'],
                    'confidence': 'HIGH',
                    'reason': f'Unique quantity match: {total_qty}'
                }
            else:
                # Multiple candidates - need more analysis
                # Check for price similarity too
                for sale in msa_sales:
                    if sale['upc'] == msa_upc:
                        msa_price = sale['price']
                        
                        # Find POS sale with similar price
                        for pos_sale in candidates:
                            if abs(float(pos_sale['Price']) - msa_price) < 0.50:
                                mappings_found[msa_upc] = {
                                    'pos_upc': pos_sale['UPC'],
                                    'description': pos_sale['Description'],
                                    'confidence': 'MEDIUM',
                                    'reason': f'Qty={total_qty}, Price match'
                                }
                                break
                        break
    
    # Display found mappings
    print("\n" + "="*70)
    print("NEW UPC MAPPINGS DISCOVERED")
    print("="*70)
    
    if mappings_found:
        print(f"\nFound {len(mappings_found)} new mappings:")
        
        for msa_upc, mapping in list(mappings_found.items())[:20]:
            print(f"\nMSA: {msa_upc}")
            print(f"  → POS: {mapping['pos_upc']}")
            print(f"  Product: {mapping['description'][:50]}")
            print(f"  Confidence: {mapping['confidence']}")
            print(f"  Reason: {mapping['reason']}")
    
    # Analyze patterns in unmatched UPCs
    print("\n" + "="*70)
    print("ANALYZING UNMATCHED UPC PATTERNS")
    print("="*70)
    
    # Check if there are other transformation patterns
    unmatched_lengths = Counter(len(upc) for upc in unmatched_upcs)
    print("\nUnmatched UPC length distribution:")
    for length, count in sorted(unmatched_lengths.items()):
        print(f"  {length:2} digits: {count:3} UPCs")
    
    # Sample some unmatched to see patterns
    print("\nSample unmatched MSA UPCs:")
    for upc in list(unmatched_upcs)[:10]:
        qty = msa_upc_totals[upc]
        print(f"  {upc} (sold {qty} units)")
    
    # Try different transformation patterns
    print("\n" + "="*70)
    print("TESTING ALTERNATIVE TRANSFORMATIONS")
    print("="*70)
    
    alternative_matches = 0
    
    for msa_upc in unmatched_upcs:
        # Try removing leading zeros from MSA UPC
        msa_stripped = msa_upc.lstrip('0')
        
        for pos_sale in pos_sales:
            pos_upc = pos_sale['UPC']
            
            # Check various patterns
            if (pos_upc == msa_stripped or 
                pos_upc.lstrip('0') == msa_stripped or
                pos_upc + '0' == msa_upc or
                '0' + pos_upc == msa_upc):
                
                alternative_matches += 1
                if alternative_matches <= 5:
                    print(f"\nMatch found:")
                    print(f"  MSA: {msa_upc}")
                    print(f"  POS: {pos_upc}")
                    print(f"  Product: {pos_sale['Description'][:50]}")
                break
    
    print(f"\nAlternative transformations found: {alternative_matches} matches")
    
    conn.close()
    
    # Also check the CSV files if available
    if os.path.exists('Sales - 06202025.csv'):
        print("\n" + "="*70)
        print("CHECKING CSV SALES DATA")
        print("="*70)
        
        csv_sales = parse_csv_sales('Sales - 06202025.csv')
        csv_upcs = set(s['upc'] for s in csv_sales)
        
        print(f"\nCSV has {len(csv_upcs)} unique UPCs")
        
        # Check how CSV UPCs relate to MSA UPCs
        csv_to_msa_matches = 0
        for csv_upc in csv_upcs:
            # Check if adding 0 makes it match MSA
            if csv_upc + '0' in msa_upcs:
                csv_to_msa_matches += 1
            elif '0' + csv_upc + '0' in msa_upcs:
                csv_to_msa_matches += 1
        
        print(f"CSV UPCs that match MSA (with transformation): {csv_to_msa_matches}")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"""
Total MSA UPCs in sales: {len(msa_upcs)}
Already matched: {len(matched_upcs)} ({100*len(matched_upcs)/len(msa_upcs):.1f}%)
Still unmatched: {len(unmatched_upcs)} ({100*len(unmatched_upcs)/len(msa_upcs):.1f}%)
New mappings found: {len(mappings_found)}
Alternative patterns: {alternative_matches}

The remaining unmatched UPCs likely need:
1. Manual mapping table from MULTICAT
2. Different transformation rules per manufacturer
3. Historical data to understand old UPC formats
    """)

if __name__ == "__main__":
    find_upc_mappings()