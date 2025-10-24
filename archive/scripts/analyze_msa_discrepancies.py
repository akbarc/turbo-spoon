#!/usr/bin/env python3
"""
Analyze discrepancies between generated and actual MSA files
"""

from collections import defaultdict
from database_pymssql import connection_pool

def parse_msa_file_detailed(filepath):
    """Parse MSA file with detailed record extraction"""
    records = {
        'header': None,
        'bids': {},  # UPC -> bid data
        'sids': {},  # Customer ID -> sid data
        'purs': []   # List of purchase records
    }
    
    print(f"Parsing MSA file: {filepath}")
    
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip():
                continue
                
            record_type = line[:3]
            
            if record_type == 'HID':
                records['header'] = line.rstrip('\n')
            elif record_type == 'BID':
                # Parse BID record
                upc = line[3:18].strip()
                bid_data = {
                    'raw': line.rstrip('\n'),
                    'upc': upc,
                    'name': line[18:78].strip(),
                    'quantity': line[199:210].strip()
                }
                records['bids'][upc] = bid_data
            elif record_type == 'SID':
                customer_id = line[3:18].strip()
                records['sids'][customer_id] = {
                    'raw': line.rstrip('\n'),
                    'customer_id': customer_id,
                    'name': line[18:78].strip()
                }
            elif record_type == 'PUR':
                # Parse purchase record
                pur_data = {
                    'raw': line.rstrip('\n'),
                    'customer_id': line[3:18].strip(),
                    'upc': line[18:33].strip(),
                    'quantity': line[33:44].strip(),
                    'date': line[44:52].strip() if len(line) > 52 else ''
                }
                records['purs'].append(pur_data)
    
    print(f"Found {len(records['bids'])} unique products")
    print(f"Found {len(records['sids'])} unique customers")
    print(f"Found {len(records['purs'])} purchase records")
    
    return records

def analyze_missing_products(generated_file, actual_file, prior_file):
    """Analyze products that are in actual but not in generated"""
    print("\n=== ANALYZING MISSING PRODUCTS ===")
    
    # Parse all three files
    generated = parse_msa_file_detailed(generated_file)
    actual = parse_msa_file_detailed(actual_file)
    prior = parse_msa_file_detailed(prior_file)
    
    # Find missing products
    missing_upcs = set(actual['bids'].keys()) - set(generated['bids'].keys())
    
    print(f"\nProducts in actual but not generated: {len(missing_upcs)}")
    
    # Check if these were in the prior file
    new_products = []
    existing_products = []
    
    for upc in missing_upcs:
        if upc in prior['bids']:
            existing_products.append(upc)
        else:
            new_products.append(upc)
    
    print(f"  - New products (not in 08/01): {len(new_products)}")
    print(f"  - Existing products (were in 08/01): {len(existing_products)}")
    
    # Show details of missing products
    print("\nNew products added between 08/01 and 08/08:")
    for upc in new_products:
        product = actual['bids'][upc]
        print(f"  UPC: {upc} | Name: {product['name']} | Qty: {product['quantity']}")
    
    if existing_products:
        print("\nExisting products that disappeared from generated:")
        for upc in existing_products[:5]:  # Show first 5
            product = actual['bids'][upc]
            prior_product = prior['bids'][upc]
            print(f"  UPC: {upc} | Name: {product['name']}")
            print(f"    Prior qty: {prior_product['quantity']} | Actual qty: {product['quantity']}")
    
    return missing_upcs, new_products, existing_products

def analyze_missing_customers(generated_file, actual_file):
    """Analyze customers and their purchases"""
    print("\n=== ANALYZING MISSING CUSTOMERS ===")
    
    generated = parse_msa_file_detailed(generated_file)
    actual = parse_msa_file_detailed(actual_file)
    
    # Find missing customers
    generated_customers = set(generated['sids'].keys())
    actual_customers = set(actual['sids'].keys())
    missing_customers = actual_customers - generated_customers
    
    print(f"\nCustomers in actual but not generated: {len(missing_customers)}")
    
    # Analyze what these customers purchased
    missing_customer_purchases = defaultdict(list)
    
    for pur in actual['purs']:
        if pur['customer_id'] in missing_customers:
            missing_customer_purchases[pur['customer_id']].append(pur)
    
    print(f"Missing customers made {sum(len(p) for p in missing_customer_purchases.values())} purchases")
    
    # Show sample of what they bought
    print("\nSample of what missing customers purchased:")
    for customer_id in list(missing_customers)[:3]:  # Show first 3 customers
        purchases = missing_customer_purchases[customer_id]
        print(f"\nCustomer {customer_id}: {len(purchases)} purchases")
        for pur in purchases[:5]:  # Show first 5 purchases
            upc = pur['upc']
            product_name = actual['bids'].get(upc, {}).get('name', 'Unknown')
            print(f"  - UPC: {upc} | Qty: {pur['quantity']} | Product: {product_name}")
    
    return missing_customers, missing_customer_purchases

def analyze_purchase_differences(generated_file, actual_file):
    """Analyze purchase record differences"""
    print("\n=== ANALYZING PURCHASE RECORDS ===")
    
    generated = parse_msa_file_detailed(generated_file)
    actual = parse_msa_file_detailed(actual_file)
    
    print(f"Generated purchases: {len(generated['purs'])}")
    print(f"Actual purchases: {len(actual['purs'])}")
    print(f"Difference: {len(actual['purs']) - len(generated['purs'])}")
    
    # Group purchases by customer and UPC for comparison
    def group_purchases(purchases):
        grouped = defaultdict(lambda: defaultdict(float))
        for pur in purchases:
            grouped[pur['customer_id']][pur['upc']] += float(pur['quantity']) if pur['quantity'] else 0
        return grouped
    
    gen_grouped = group_purchases(generated['purs'])
    act_grouped = group_purchases(actual['purs'])
    
    # Find purchases only in actual
    missing_purchases = []
    for customer_id, customer_purs in act_grouped.items():
        for upc, qty in customer_purs.items():
            if customer_id not in gen_grouped or upc not in gen_grouped[customer_id]:
                missing_purchases.append((customer_id, upc, qty))
    
    print(f"\nUnique customer-product combinations only in actual: {len(missing_purchases)}")
    
    # Analyze patterns in missing purchases
    missing_upcs = defaultdict(float)
    for _, upc, qty in missing_purchases:
        missing_upcs[upc] += qty
    
    print(f"Unique products in missing purchases: {len(missing_upcs)}")
    
    # Show top missing products by quantity
    print("\nTop 10 products by missing quantity:")
    sorted_missing = sorted(missing_upcs.items(), key=lambda x: x[1], reverse=True)
    for upc, total_qty in sorted_missing[:10]:
        product_name = actual['bids'].get(upc, {}).get('name', 'Unknown')
        print(f"  UPC: {upc} | Total missing qty: {total_qty} | Product: {product_name}")
    
    return missing_purchases

def check_database_categories(missing_upcs):
    """Check if missing UPCs exist in database and their categories"""
    print("\n=== CHECKING DATABASE FOR MISSING PRODUCTS ===")
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Try to find these UPCs in the database
    found_in_db = []
    not_in_db = []
    
    for upc in missing_upcs:
        # Try various substring lengths
        found = False
        for length in range(3, len(upc) + 1):
            substring = upc[:length]
            cursor.execute("""
                SELECT ItemLookupCode, Description, CategoryID 
                FROM Item 
                WHERE ItemLookupCode = %s
            """, substring)
            result = cursor.fetchone()
            if result:
                found_in_db.append({
                    'upc': upc,
                    'sku': result['ItemLookupCode'],
                    'description': result['Description'],
                    'category_id': result['CategoryID']
                })
                found = True
                break
        
        if not found:
            not_in_db.append(upc)
    
    print(f"Found in database: {len(found_in_db)}")
    print(f"Not found in database: {len(not_in_db)}")
    
    # Analyze categories
    if found_in_db:
        print("\nProducts found in database:")
        tobacco_cats = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]
        for item in found_in_db:
            in_tobacco = "YES" if item['category_id'] in tobacco_cats else "NO"
            print(f"  UPC: {item['upc']} -> SKU: {item['sku']}")
            print(f"    Category: {item['category_id']} | In tobacco list: {in_tobacco}")
            print(f"    Description: {item['description']}")
    
    if not_in_db:
        print("\nUPCs not found in database:")
        for upc in not_in_db:
            print(f"  - {upc}")
    
    cursor.close()
    connection_pool.return_connection(conn)
    
    return found_in_db, not_in_db

def main():
    # File paths
    generated_file = "generated_msa_08082025.txt"
    actual_file = "MSA Data Fr/08082025"
    prior_file = "MSA Data Fr/08012025"
    
    # Analyze missing products
    missing_upcs, new_products, existing_products = analyze_missing_products(
        generated_file, actual_file, prior_file
    )
    
    # Analyze missing customers
    missing_customers, missing_customer_purchases = analyze_missing_customers(
        generated_file, actual_file
    )
    
    # Analyze purchase differences
    missing_purchases = analyze_purchase_differences(generated_file, actual_file)
    
    # Check database for missing products
    if missing_upcs:
        found_in_db, not_in_db = check_database_categories(missing_upcs)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF FINDINGS")
    print("="*60)
    print(f"Missing products: {len(missing_upcs)}")
    print(f"  - New additions: {len(new_products)}")
    print(f"  - Should have been included: {len(existing_products)}")
    print(f"Missing customers: {len(missing_customers)}")
    print(f"Missing purchase transactions: {len(missing_purchases)}")
    
    # Check for date issues
    print("\n=== DATE ANALYSIS ===")
    print("Note: We're querying 08/02-08/08 for week ending 08/08/2025")
    print("MSA weeks typically run Saturday to Friday")
    print("If purchases are 'future' dated, it might be timezone or data entry issues")

if __name__ == "__main__":
    main()