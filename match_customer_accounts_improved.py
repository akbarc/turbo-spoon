#!/usr/bin/env python3
"""
Improved Customer Account Matching
Uses phone/account number pattern: last 8 digits, with leading zero rotation
"""

import os
import pandas as pd
import pymssql
from collections import defaultdict
import re

class ImprovedCustomerMatcher:
    def __init__(self):
        self.csv_dir = "/Users/akbarchranya/georgiadashboard/MSA_CSV_Output"
        
        # Database connection
        self.conn = pymssql.connect(
            server='10.1.10.105',
            user='amchranya',
            password='2000Akbar!',
            database='GAWDB',
            port=1433,
            tds_version='7.0',
            timeout=30
        )
        self.cursor = self.conn.cursor(as_dict=True)
        
        # Load data
        self.msa_customers = self.load_msa_customers()
        self.pos_customers = self.load_pos_customers()
        
    def load_msa_customers(self):
        """Load all unique customers from MSA SID records"""
        print("Loading MSA customer data...")
        all_customers = []
        
        for week in os.listdir(self.csv_dir):
            week_dir = os.path.join(self.csv_dir, week)
            if not os.path.isdir(week_dir):
                continue
                
            customers_file = os.path.join(week_dir, f"{week}_customers.csv")
            if os.path.exists(customers_file):
                df = pd.read_csv(customers_file)
                df['week'] = week
                all_customers.append(df)
        
        if all_customers:
            combined = pd.concat(all_customers, ignore_index=True)
            
            # Get unique customers
            unique_customers = combined.groupby(['ship_to_customer_number', 'ship_to_customer_shipping_number']).agg({
                'ship_to_customer_name': 'first',
                'ship_to_customer_address': 'first',
                'ship_to_customer_city': 'first',
                'ship_to_customer_state': 'first',
                'ship_to_customer_zip': 'first',
                'ship_to_customer_store_number': 'first',
                'ship_to_customer_class_of_trade': 'first',
                'ship_to_customer_cash_carry_indicator': 'first',
                'ship_to_customer_phone': 'first',
                'week': 'count'
            }).reset_index()
            
            unique_customers.columns = ['customer_number', 'shipping_number', 'name', 'address', 
                                       'city', 'state', 'zip', 'store_number', 'class_of_trade', 
                                       'cash_carry', 'phone', 'weeks_active']
            
            print(f"Loaded {len(unique_customers)} unique MSA customers")
            return unique_customers
        
        return pd.DataFrame()
    
    def load_pos_customers(self):
        """Load all customers from POS database"""
        print("Loading POS customer data...")
        
        query = """
        SELECT 
            c.AccountNumber,
            c.AccountTypeID,
            c.FirstName,
            c.LastName,
            c.Company,
            c.Address,
            c.Address2,
            c.City,
            c.State,
            c.Zip,
            c.PhoneNumber,
            c.EmailAddress,
            c.TaxNumber,
            c.CreditLimit,
            c.AccountBalance,
            c.LastVisit,
            c.TotalSales,
            c.TotalVisits,
            c.Notes
        FROM Customer c
        WHERE c.AccountNumber IS NOT NULL
        ORDER BY c.AccountNumber
        """
        
        self.cursor.execute(query)
        customers = []
        
        for row in self.cursor.fetchall():
            # Create display name
            name_parts = []
            if row['Company']:
                name_parts.append(row['Company'])
            elif row['FirstName'] or row['LastName']:
                if row['FirstName']:
                    name_parts.append(row['FirstName'])
                if row['LastName']:
                    name_parts.append(row['LastName'])
            
            customers.append({
                'account_number': row['AccountNumber'],
                'account_type': row['AccountTypeID'],
                'name': ' '.join(name_parts),
                'company': row['Company'] or '',
                'first_name': row['FirstName'] or '',
                'last_name': row['LastName'] or '',
                'address': row['Address'] or '',
                'address2': row['Address2'] or '',
                'city': row['City'] or '',
                'state': row['State'] or '',
                'zip': row['Zip'] or '',
                'phone': row['PhoneNumber'] or '',
                'email': row['EmailAddress'] or '',
                'tax_number': row['TaxNumber'] or '',
                'credit_limit': row['CreditLimit'],
                'balance': row['AccountBalance'],
                'last_visit': row['LastVisit'],
                'total_sales': row['TotalSales'],
                'total_visits': row['TotalVisits']
            })
        
        df = pd.DataFrame(customers)
        print(f"Loaded {len(df)} POS customers")
        return df
    
    def extract_account_key(self, number_str):
        """
        Extract account key from phone/account number:
        - Take last 8 digits
        - If first digit is 0, move it to the end
        """
        if pd.isna(number_str) or number_str is None:
            return None
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', str(number_str))
        
        if len(digits) < 8:
            return None
        
        # Take last 8 digits
        last_8 = digits[-8:]
        
        # If first digit is 0, move it to end
        if last_8[0] == '0':
            last_8 = last_8[1:] + '0'
        
        return last_8
    
    def match_customers(self):
        """Match MSA customers to POS accounts using improved logic"""
        print("\nMatching customers using phone/account number pattern...")
        
        matches = []
        unmatched = []
        
        # Create POS lookup dictionaries
        pos_by_account_key = {}
        pos_by_phone_key = {}
        
        # Build POS lookup indexes
        for _, pos_customer in self.pos_customers.iterrows():
            # Extract key from account number
            account_key = self.extract_account_key(pos_customer['account_number'])
            if account_key:
                if account_key not in pos_by_account_key:
                    pos_by_account_key[account_key] = []
                pos_by_account_key[account_key].append(pos_customer)
            
            # Extract key from phone number
            phone_key = self.extract_account_key(pos_customer['phone'])
            if phone_key:
                if phone_key not in pos_by_phone_key:
                    pos_by_phone_key[phone_key] = []
                pos_by_phone_key[phone_key].append(pos_customer)
        
        print(f"Built indexes: {len(pos_by_account_key)} account keys, {len(pos_by_phone_key)} phone keys")
        
        # Match each MSA customer
        for _, msa_customer in self.msa_customers.iterrows():
            customer_num = str(msa_customer['customer_number']).strip()
            shipping_num = str(msa_customer['shipping_number']).strip()
            
            match_found = False
            match_result = None
            
            # Extract keys from MSA customer number and phone
            msa_customer_key = self.extract_account_key(customer_num)
            msa_phone_key = self.extract_account_key(msa_customer['phone']) if 'phone' in msa_customer else None
            
            # Strategy 1: Match by customer number key
            if msa_customer_key and msa_customer_key in pos_by_account_key:
                pos_matches = pos_by_account_key[msa_customer_key]
                if pos_matches:
                    pos_customer = pos_matches[0]  # Take first match
                    match_result = {
                        'match_type': 'account_key',
                        'confidence': 'high',
                        'pos_account': pos_customer['account_number'],
                        'pos_name': pos_customer['name'],
                        'matched_key': msa_customer_key
                    }
                    match_found = True
            
            # Strategy 2: Match by phone number key
            if not match_found and msa_phone_key:
                if msa_phone_key in pos_by_phone_key:
                    pos_matches = pos_by_phone_key[msa_phone_key]
                    if pos_matches:
                        pos_customer = pos_matches[0]
                        match_result = {
                            'match_type': 'phone_key',
                            'confidence': 'high',
                            'pos_account': pos_customer['account_number'],
                            'pos_name': pos_customer['name'],
                            'matched_key': msa_phone_key
                        }
                        match_found = True
                
                # Also check account keys
                if not match_found and msa_phone_key in pos_by_account_key:
                    pos_matches = pos_by_account_key[msa_phone_key]
                    if pos_matches:
                        pos_customer = pos_matches[0]
                        match_result = {
                            'match_type': 'phone_to_account_key',
                            'confidence': 'high',
                            'pos_account': pos_customer['account_number'],
                            'pos_name': pos_customer['name'],
                            'matched_key': msa_phone_key
                        }
                        match_found = True
            
            # Strategy 3: Try customer number as phone key
            if not match_found and msa_customer_key and msa_customer_key in pos_by_phone_key:
                pos_matches = pos_by_phone_key[msa_customer_key]
                if pos_matches:
                    pos_customer = pos_matches[0]
                    match_result = {
                        'match_type': 'customer_to_phone_key',
                        'confidence': 'medium',
                        'pos_account': pos_customer['account_number'],
                        'pos_name': pos_customer['name'],
                        'matched_key': msa_customer_key
                    }
                    match_found = True
            
            # Record results
            if match_found and match_result:
                matches.append({
                    'msa_customer_number': customer_num,
                    'msa_shipping_number': shipping_num,
                    'msa_name': msa_customer['name'],
                    'msa_address': msa_customer['address'],
                    'msa_city': msa_customer['city'],
                    'msa_state': msa_customer['state'],
                    'msa_phone': msa_customer.get('phone', ''),
                    'pos_account_number': match_result['pos_account'],
                    'pos_name': match_result['pos_name'],
                    'match_type': match_result['match_type'],
                    'confidence': match_result['confidence'],
                    'matched_key': match_result['matched_key'],
                    'weeks_active': msa_customer['weeks_active']
                })
            else:
                unmatched.append({
                    'msa_customer_number': customer_num,
                    'msa_shipping_number': shipping_num,
                    'msa_name': msa_customer['name'],
                    'msa_address': msa_customer['address'],
                    'msa_city': msa_customer['city'],
                    'msa_state': msa_customer['state'],
                    'msa_phone': msa_customer.get('phone', ''),
                    'msa_store_number': msa_customer['store_number'],
                    'class_of_trade': msa_customer['class_of_trade'],
                    'cash_carry': msa_customer['cash_carry'],
                    'extracted_key': msa_customer_key,
                    'phone_key': msa_phone_key,
                    'weeks_active': msa_customer['weeks_active']
                })
        
        return pd.DataFrame(matches), pd.DataFrame(unmatched)
    
    def analyze_results(self, matches_df, unmatched_df):
        """Analyze matching results"""
        print("\n" + "="*60)
        print("IMPROVED CUSTOMER MATCHING ANALYSIS")
        print("="*60)
        
        total_msa = len(self.msa_customers)
        total_matched = len(matches_df)
        total_unmatched = len(unmatched_df)
        
        print(f"\nTotal MSA customers: {total_msa}")
        print(f"Matched to POS: {total_matched} ({total_matched/total_msa*100:.1f}%)")
        print(f"Unmatched: {total_unmatched} ({total_unmatched/total_msa*100:.1f}%)")
        
        if not matches_df.empty:
            print("\nMatch types breakdown:")
            match_types = matches_df['match_type'].value_counts()
            for match_type, count in match_types.items():
                pct = count/total_matched*100
                print(f"  {match_type}: {count} ({pct:.1f}%)")
            
            print("\nSample matches:")
            sample = matches_df.head(10)[['msa_customer_number', 'msa_name', 'pos_account_number', 
                                         'pos_name', 'match_type', 'matched_key']]
            print(sample.to_string(index=False))
        
        if not unmatched_df.empty:
            print("\nUnmatched customer analysis:")
            print(f"Total unmatched: {len(unmatched_df)}")
            
            # Show extracted keys for debugging
            print("\nSample unmatched with extracted keys:")
            sample_unmatched = unmatched_df.head(10)[['msa_customer_number', 'msa_name', 
                                                      'extracted_key', 'phone_key']]
            print(sample_unmatched.to_string(index=False))
        
        # Export results
        matches_df.to_csv('customer_matches_improved.csv', index=False)
        unmatched_df.to_csv('customer_unmatched_improved.csv', index=False)
        
        print(f"\nResults exported:")
        print(f"  - customer_matches_improved.csv ({len(matches_df)} records)")
        print(f"  - customer_unmatched_improved.csv ({len(unmatched_df)} records)")
        
        # Create mapping file
        if not matches_df.empty:
            mapping = matches_df[['msa_customer_number', 'msa_shipping_number', 
                                 'pos_account_number', 'matched_key']].copy()
            mapping.to_csv('customer_id_mapping_improved.csv', index=False)
            print(f"  - customer_id_mapping_improved.csv (for system integration)")
    
    def test_key_extraction(self):
        """Test the key extraction logic with examples"""
        print("\n" + "="*60)
        print("KEY EXTRACTION EXAMPLES")
        print("="*60)
        
        test_cases = [
            "4047701234",   # Phone number
            "012345678",    # Leading zero
            "87654321",     # Regular 8 digits
            "9012466298",   # Account number
            "1234567890",   # 10 digits
            "04047701234",  # Phone with leading zero
        ]
        
        for test in test_cases:
            key = self.extract_account_key(test)
            print(f"{test:15} → {key}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    matcher = ImprovedCustomerMatcher()
    
    try:
        # Test key extraction logic
        matcher.test_key_extraction()
        
        if matcher.msa_customers.empty:
            print("No MSA customers found")
            return
        
        if matcher.pos_customers.empty:
            print("No POS customers found")
            return
        
        # Perform matching
        matches_df, unmatched_df = matcher.match_customers()
        
        # Analyze results
        matcher.analyze_results(matches_df, unmatched_df)
        
        print("\n" + "="*60)
        print("KEY INSIGHTS")
        print("="*60)
        
        if not matches_df.empty:
            # Check match distribution
            print(f"\nMatching succeeded using 8-digit key extraction")
            print(f"Leading zero rotation rule applied")
            
            # Show confidence distribution
            confidence_dist = matches_df['confidence'].value_counts()
            print("\nConfidence levels:")
            for conf, count in confidence_dist.items():
                print(f"  {conf}: {count}")
        
    finally:
        matcher.close()


if __name__ == "__main__":
    main()