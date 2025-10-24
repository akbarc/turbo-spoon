#!/usr/bin/env python3
"""
Build a master customer roster from all MSA files
"""

import os
from collections import defaultdict

def build_customer_roster():
    """Build a complete customer roster from all MSA files"""
    customer_roster = {}
    msa_dir = "MSA Data Fr"
    
    # Process all MSA files to build customer roster
    for filename in sorted(os.listdir(msa_dir)):
        if filename.isdigit() and len(filename) == 8:
            filepath = os.path.join(msa_dir, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('SID'):
                        customer_id = line[3:11].strip()
                        if customer_id and len(line.rstrip()) > 200:
                            # Store the full SID record for this customer
                            # Keep the most recent version
                            customer_roster[customer_id] = line.rstrip('\r\n')
    
    print(f"Built roster with {len(customer_roster)} unique customers")
    return customer_roster

def check_customer_coverage():
    """Check how many customers we can find full records for"""
    roster = build_customer_roster()
    
    # Check against 08/08/2025
    actual_customers = set()
    with open('MSA Data Fr/08082025', 'r') as f:
        for line in f:
            if line.startswith('SID'):
                customer_id = line[3:11].strip()
                if customer_id:
                    actual_customers.add(customer_id)
    
    print(f"\nActual 08/08 customers: {len(actual_customers)}")
    
    found = 0
    missing = []
    for cust_id in actual_customers:
        if cust_id in roster:
            found += 1
        else:
            missing.append(cust_id)
    
    print(f"Found in roster: {found}/{len(actual_customers)}")
    
    if missing:
        print(f"\nMissing from roster: {missing[:10]}")
        # These might be brand new customers
    
    return roster

if __name__ == '__main__':
    roster = check_customer_coverage()
    
    # Save roster for use in generator
    import json
    with open('customer_roster.json', 'w') as f:
        json.dump(roster, f, indent=2)
    
    print("\nSaved customer roster to customer_roster.json")