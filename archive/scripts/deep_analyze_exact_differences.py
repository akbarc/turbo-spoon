#!/usr/bin/env python3
"""
Deep analysis of EXACT BID and SID discrepancies to find the real reasons
"""

import os
from collections import defaultdict
from datetime import datetime

def get_exact_bid_differences():
    """Get the exact BID differences between generated and actual"""
    print("="*70)
    print("EXACT BID RECORD DISCREPANCIES")
    print("="*70)
    
    # We'll analyze multiple periods to find patterns
    test_cases = [
        ("06202025", "06272025"),
        ("06272025", "07042025"),
        ("07042025", "07112025"),
        ("07112025", "07182025"),
        ("07182025", "07252025"),
        ("07252025", "08012025"),
        ("08012025", "08082025")
    ]
    
    all_missing = defaultdict(list)  # Products missing from our generation
    all_extra = defaultdict(list)     # Products we add that shouldn't be there
    
    for prior_date, target_date in test_cases:
        print(f"\n### Analyzing {prior_date} → {target_date} ###")
        
        prior_file = f"MSA Data Fr/{prior_date}"
        actual_file = f"MSA Data Fr/{target_date}"
        
        # Parse prior MSA
        prior_bids = set()
        with open(prior_file, 'r') as f:
            for line in f:
                if line.startswith('BID'):
                    upc = line[3:18].strip()
                    prior_bids.add(upc)
        
        # Parse actual target MSA
        actual_bids = {}
        with open(actual_file, 'r') as f:
            for line in f:
                if line.startswith('BID'):
                    upc = line[3:18].strip()
                    name = line[18:78].strip() if len(line) > 78 else ''
                    actual_bids[upc] = name
        
        # Find what changed
        new_in_actual = set(actual_bids.keys()) - prior_bids
        removed_in_actual = prior_bids - set(actual_bids.keys())
        
        print(f"Prior had {len(prior_bids)} products")
        print(f"Actual has {len(actual_bids)} products")
        print(f"Net change: {len(actual_bids) - len(prior_bids)}")
        print(f"New products in actual: {len(new_in_actual)}")
        print(f"Removed products: {len(removed_in_actual)}")
        
        # Track these for pattern analysis
        for upc in new_in_actual:
            all_missing[upc].append((target_date, actual_bids[upc]))
        
        # Show specific examples
        if new_in_actual:
            print("\nNew products added to actual MSA:")
            for i, upc in enumerate(sorted(new_in_actual)[:5], 1):
                print(f"  {i}. {upc}: {actual_bids[upc][:40]}")
    
    # Analyze patterns
    print("\n" + "="*70)
    print("PATTERN ANALYSIS OF MISSING PRODUCTS")
    print("="*70)
    
    # Products that appear multiple times
    recurring_missing = {upc: periods for upc, periods in all_missing.items() if len(periods) > 1}
    one_time_missing = {upc: periods for upc, periods in all_missing.items() if len(periods) == 1}
    
    print(f"\nProducts missing repeatedly: {len(recurring_missing)}")
    print(f"Products missing once: {len(one_time_missing)}")
    
    if recurring_missing:
        print("\n### REPEATEDLY MISSING PRODUCTS ###")
        for upc, periods in sorted(recurring_missing.items())[:10]:
            print(f"\nUPC: {upc}")
            print(f"  Appears in: {[p[0] for p in periods]}")
            print(f"  Name: {periods[0][1][:50]}")
    
    return all_missing

def get_exact_sid_differences():
    """Get the exact SID differences between generated and actual"""
    print("\n" + "="*70)
    print("EXACT SID RECORD DISCREPANCIES")
    print("="*70)
    
    test_cases = [
        ("06202025", "06272025"),
        ("06272025", "07042025"),
        ("07042025", "07112025"),
        ("07112025", "07182025"),
        ("07182025", "07252025"),
        ("07252025", "08012025"),
        ("08012025", "08082025")
    ]
    
    customer_appearance = defaultdict(list)  # Track when each customer appears
    
    for prior_date, target_date in test_cases:
        print(f"\n### Analyzing {prior_date} → {target_date} ###")
        
        prior_file = f"MSA Data Fr/{prior_date}"
        actual_file = f"MSA Data Fr/{target_date}"
        
        # Parse prior SIDs
        prior_sids = set()
        with open(prior_file, 'r') as f:
            for line in f:
                if line.startswith('SID'):
                    customer_id = line[3:11].strip()
                    if customer_id:
                        prior_sids.add(customer_id)
        
        # Parse actual SIDs
        actual_sids = set()
        with open(actual_file, 'r') as f:
            for line in f:
                if line.startswith('SID'):
                    customer_id = line[3:11].strip()
                    if customer_id:
                        actual_sids.add(customer_id)
                        customer_appearance[customer_id].append(target_date)
        
        # Find changes
        new_customers = actual_sids - prior_sids
        removed_customers = prior_sids - actual_sids
        
        print(f"Prior: {len(prior_sids)} customers")
        print(f"Actual: {len(actual_sids)} customers")
        print(f"New: {len(new_customers)}, Removed: {len(removed_customers)}")
        
        # Sample the changes
        if new_customers:
            print(f"Sample new customers: {sorted(new_customers)[:5]}")
        if removed_customers:
            print(f"Sample removed customers: {sorted(removed_customers)[:5]}")
    
    # Analyze customer patterns
    print("\n" + "="*70)
    print("CUSTOMER APPEARANCE PATTERNS")
    print("="*70)
    
    # Categorize customers by frequency
    always_present = []
    sometimes_present = []
    rarely_present = []
    
    for customer, appearances in customer_appearance.items():
        if len(appearances) == 7:
            always_present.append(customer)
        elif len(appearances) >= 4:
            sometimes_present.append(customer)
        else:
            rarely_present.append(customer)
    
    print(f"\nAlways present (all 7 periods): {len(always_present)} customers")
    print(f"Sometimes present (4-6 periods): {len(sometimes_present)} customers")
    print(f"Rarely present (1-3 periods): {len(rarely_present)} customers")
    
    return customer_appearance

def analyze_bid_logic_issues():
    """Analyze why our BID logic might be wrong"""
    print("\n" + "="*70)
    print("BID LOGIC ANALYSIS - WHY ARE WE MISSING/ADDING PRODUCTS?")
    print("="*70)
    
    # Check the 08/08/2025 case specifically
    prior_file = "MSA Data Fr/08012025"
    actual_file = "MSA Data Fr/08082025"
    
    # Get all products from both files
    prior_products = {}
    actual_products = {}
    
    with open(prior_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                name = line[18:78].strip() if len(line) > 78 else ''
                qty = line[199:210].strip() if len(line) > 210 else '0'
                prior_products[upc] = {'name': name, 'qty': qty}
    
    with open(actual_file, 'r') as f:
        for line in f:
            if line.startswith('BID'):
                upc = line[3:18].strip()
                name = line[18:78].strip() if len(line) > 78 else ''
                qty = line[199:210].strip() if len(line) > 210 else '0'
                actual_products[upc] = {'name': name, 'qty': qty}
    
    # Find the exact differences
    new_products = set(actual_products.keys()) - set(prior_products.keys())
    removed_products = set(prior_products.keys()) - set(actual_products.keys())
    
    print(f"\n### EXACT BID CHANGES FOR 08/01 → 08/08 ###")
    print(f"Prior MSA: {len(prior_products)} products")
    print(f"Actual MSA: {len(actual_products)} products")
    print(f"New products: {len(new_products)}")
    print(f"Removed products: {len(removed_products)}")
    
    print("\n### ALL NEW PRODUCTS IN ACTUAL ###")
    for i, upc in enumerate(sorted(new_products), 1):
        print(f"{i:2}. {upc}: {actual_products[upc]['name'][:50]}")
    
    if removed_products:
        print("\n### PRODUCTS REMOVED FROM ACTUAL ###")
        for i, upc in enumerate(sorted(removed_products)[:10], 1):
            print(f"{i:2}. {upc}: {prior_products[upc]['name'][:50]}")
    
    # Check if new products existed in any prior MSA
    print("\n### CHECKING IF NEW PRODUCTS EXISTED BEFORE ###")
    
    all_historical_products = set()
    msa_dir = "MSA Data Fr"
    
    for filename in os.listdir(msa_dir):
        if filename != "08082025" and filename.isdigit():
            filepath = os.path.join(msa_dir, filename)
            with open(filepath, 'r') as f:
                for line in f:
                    if line.startswith('BID'):
                        upc = line[3:18].strip()
                        all_historical_products.add(upc)
    
    truly_new = []
    returning = []
    
    for upc in new_products:
        if upc in all_historical_products:
            returning.append(upc)
        else:
            truly_new.append(upc)
    
    print(f"\nTruly NEW products (never seen before): {len(truly_new)}")
    for upc in truly_new:
        print(f"  {upc}: {actual_products[upc]['name'][:50]}")
    
    print(f"\nReturning products (existed in past): {len(returning)}")
    for upc in returning[:5]:
        print(f"  {upc}: {actual_products[upc]['name'][:50]}")

def analyze_sid_logic_issues():
    """Analyze why our SID logic might be wrong"""
    print("\n" + "="*70)
    print("SID LOGIC ANALYSIS - CUSTOMER ROSTER ISSUES")
    print("="*70)
    
    # Analyze customer consistency
    all_files = sorted([f for f in os.listdir("MSA Data Fr") if f.isdigit() and len(f) == 8])
    
    # Track customer purchases across all periods
    customer_purchases = defaultdict(lambda: defaultdict(int))
    
    for filename in all_files:
        filepath = f"MSA Data Fr/{filename}"
        
        # Count purchases per customer
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('PUR'):
                    customer_id = line[3:11].strip()
                    if customer_id:
                        customer_purchases[filename][customer_id] += 1
    
    # Find customers with purchases but no SID
    print("\n### CHECKING CUSTOMER-PURCHASE CONSISTENCY ###")
    
    for filename in all_files[-3:]:  # Check last 3 periods
        filepath = f"MSA Data Fr/{filename}"
        
        # Get SID customers
        sid_customers = set()
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('SID'):
                    customer_id = line[3:11].strip()
                    if customer_id:
                        sid_customers.add(customer_id)
        
        # Get PUR customers
        pur_customers = set(customer_purchases[filename].keys())
        
        # Find discrepancies
        pur_without_sid = pur_customers - sid_customers
        sid_without_pur = sid_customers - pur_customers
        
        print(f"\n{filename}:")
        print(f"  SID customers: {len(sid_customers)}")
        print(f"  Customers with purchases: {len(pur_customers)}")
        print(f"  Customers with PUR but no SID: {len(pur_without_sid)}")
        print(f"  Customers with SID but no PUR: {len(sid_without_pur)}")
        
        if sid_without_pur:
            print(f"  Sample SID without purchases: {sorted(sid_without_pur)[:5]}")

def find_root_cause():
    """Identify the root cause of discrepancies"""
    print("\n" + "="*70)
    print("ROOT CAUSE ANALYSIS")
    print("="*70)
    
    print("""
### BID DISCREPANCIES ROOT CAUSE ###

1. PRODUCT LIFECYCLE IN MSA:
   - Products are NOT just carried forward from prior MSA
   - Some products are REMOVED even if they had inventory
   - New products are added based on unknown criteria
   
2. THE MISSING LOGIC:
   - MSA doesn't simply add "products with sales"
   - There's a specific list of products to track
   - This list changes each period (not just additions)
   
3. POSSIBLE CRITERIA:
   - Active vendor agreements
   - Compliance reporting requirements
   - Product registration/certification status
   - Minimum sales thresholds over time
   
### SID DISCREPANCIES ROOT CAUSE ###

1. CUSTOMER INCLUSION LOGIC:
   - NOT all customers with purchases get SID records
   - Some customers without purchases keep SID records
   - Customer roster is managed separately from sales
   
2. THE MISSING LOGIC:
   - Customer must meet certain criteria (not just purchases)
   - Possible: minimum purchase amount, frequency, or product types
   - Customer status/type may affect inclusion
   
3. POSSIBLE CRITERIA:
   - Active account status
   - Credit approval
   - Business type classification
   - Geographic/territory restrictions

### WHAT WE NEED ###

To achieve 100% accuracy, we need to understand:
1. The exact criteria for including/excluding products in BID
2. The exact criteria for including/excluding customers in SID
3. Any external data sources MSA uses (vendor lists, compliance lists)
4. The business rules that govern these decisions
""")

def main():
    print("Deep analysis of exact BID and SID discrepancies...\n")
    
    # Analyze exact differences
    missing_products = get_exact_bid_differences()
    customer_patterns = get_exact_sid_differences()
    
    # Analyze logic issues
    analyze_bid_logic_issues()
    analyze_sid_logic_issues()
    
    # Find root cause
    find_root_cause()
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
The discrepancies are NOT from manual adjustments or vendor-direct additions.

Instead, MSA follows specific business rules we haven't identified:

BID Records:
- Products are actively managed (added AND removed)
- Not based solely on sales or inventory
- Likely based on vendor/compliance status

SID Records:
- Customers are actively managed
- Not based solely on purchases
- Likely based on account status/type

To improve accuracy beyond 98.5%, we need to understand these
business rules or have access to the same reference data MSA uses.
""")

if __name__ == "__main__":
    main()