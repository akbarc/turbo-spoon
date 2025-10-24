#!/usr/bin/env python3
"""
Match MSA Customer IDs to POS Account Lookup Codes
"""

import os
import pandas as pd
import pymssql
from collections import defaultdict
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class CustomerAccountMatcher:
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
                'week': 'count'  # How many weeks they appear
            }).reset_index()
            
            unique_customers.columns = ['customer_number', 'shipping_number', 'name', 'address', 
                                       'city', 'state', 'zip', 'store_number', 'class_of_trade', 
                                       'cash_carry', 'weeks_active']
            
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
    
    def clean_string(self, s):
        """Clean string for comparison"""
        if pd.isna(s) or s is None:
            return ''
        # Convert to uppercase, remove special chars, compress spaces
        s = str(s).upper()
        s = re.sub(r'[^\w\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s)
        return s.strip()
    
    def match_customers(self):
        """Match MSA customers to POS accounts"""
        print("\nMatching customers...")
        
        matches = []
        unmatched = []
        
        # Create clean name indexes for fuzzy matching
        pos_names = {self.clean_string(c['name']): c for c in self.pos_customers.to_dict('records')}
        pos_companies = {self.clean_string(c['company']): c for c in self.pos_customers.to_dict('records') if c['company']}
        pos_addresses = {self.clean_string(c['address']): c for c in self.pos_customers.to_dict('records')}
        
        for _, msa_customer in self.msa_customers.iterrows():
            # Clean MSA data
            msa_name = self.clean_string(msa_customer['name'])
            msa_address = self.clean_string(msa_customer['address'])
            msa_city = self.clean_string(msa_customer['city'])
            msa_state = self.clean_string(msa_customer['state'])
            msa_zip = str(msa_customer['zip'])[:5] if pd.notna(msa_customer['zip']) else ''
            
            match_found = False
            match_result = None
            
            # Strategy 1: Direct customer number match
            customer_num = str(msa_customer['customer_number']).strip()
            shipping_num = str(msa_customer['shipping_number']).strip()
            
            # Try as account number
            pos_match = self.pos_customers[self.pos_customers['account_number'] == customer_num]
            if not pos_match.empty:
                match_result = {
                    'match_type': 'account_number',
                    'confidence': 'high',
                    'pos_account': pos_match.iloc[0]['account_number'],
                    'pos_name': pos_match.iloc[0]['name']
                }
                match_found = True
            
            # Strategy 2: Name matching
            if not match_found and msa_name:
                # Try exact match
                if msa_name in pos_names:
                    pos_customer = pos_names[msa_name]
                    match_result = {
                        'match_type': 'exact_name',
                        'confidence': 'high',
                        'pos_account': pos_customer['account_number'],
                        'pos_name': pos_customer['name']
                    }
                    match_found = True
                
                # Try fuzzy match
                if not match_found:
                    # Check company names
                    if pos_companies:
                        best_match = process.extractOne(msa_name, pos_companies.keys(), scorer=fuzz.ratio)
                        if best_match and best_match[1] >= 85:  # 85% similarity threshold
                            pos_customer = pos_companies[best_match[0]]
                            match_result = {
                                'match_type': 'fuzzy_name',
                                'confidence': 'medium',
                                'pos_account': pos_customer['account_number'],
                                'pos_name': pos_customer['name'],
                                'similarity': best_match[1]
                            }
                            match_found = True
            
            # Strategy 3: Address matching
            if not match_found and msa_address and msa_city:
                for _, pos_customer in self.pos_customers.iterrows():
                    pos_addr = self.clean_string(pos_customer['address'])
                    pos_city = self.clean_string(pos_customer['city'])
                    pos_state = self.clean_string(pos_customer['state'])
                    
                    # Check if address and city match
                    if pos_addr and pos_city:
                        addr_similarity = fuzz.ratio(msa_address, pos_addr)
                        city_match = msa_city == pos_city
                        state_match = msa_state == pos_state
                        
                        if addr_similarity >= 80 and city_match and state_match:
                            match_result = {
                                'match_type': 'address',
                                'confidence': 'medium',
                                'pos_account': pos_customer['account_number'],
                                'pos_name': pos_customer['name'],
                                'addr_similarity': addr_similarity
                            }
                            match_found = True
                            break
            
            # Strategy 4: Phone number matching (if available)
            if not match_found and 'ship_to_customer_phone' in msa_customer and pd.notna(msa_customer.get('ship_to_customer_phone')):
                msa_phone = re.sub(r'\D', '', str(msa_customer['ship_to_customer_phone']))
                if len(msa_phone) >= 10:
                    for _, pos_customer in self.pos_customers.iterrows():
                        if pos_customer['phone']:
                            pos_phone = re.sub(r'\D', '', str(pos_customer['phone']))
                            if msa_phone == pos_phone or msa_phone[-10:] == pos_phone[-10:]:
                                match_result = {
                                    'match_type': 'phone',
                                    'confidence': 'high',
                                    'pos_account': pos_customer['account_number'],
                                    'pos_name': pos_customer['name']
                                }
                                match_found = True
                                break
            
            # Record results
            if match_found and match_result:
                matches.append({
                    'msa_customer_number': customer_num,
                    'msa_shipping_number': shipping_num,
                    'msa_name': msa_customer['name'],
                    'msa_address': msa_customer['address'],
                    'msa_city': msa_customer['city'],
                    'msa_state': msa_customer['state'],
                    'pos_account_number': match_result['pos_account'],
                    'pos_name': match_result['pos_name'],
                    'match_type': match_result['match_type'],
                    'confidence': match_result['confidence'],
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
                    'msa_store_number': msa_customer['store_number'],
                    'class_of_trade': msa_customer['class_of_trade'],
                    'cash_carry': msa_customer['cash_carry'],
                    'weeks_active': msa_customer['weeks_active']
                })
        
        return pd.DataFrame(matches), pd.DataFrame(unmatched)
    
    def analyze_results(self, matches_df, unmatched_df):
        """Analyze matching results"""
        print("\n" + "="*60)
        print("CUSTOMER MATCHING ANALYSIS")
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
            
            print("\nConfidence levels:")
            confidence = matches_df['confidence'].value_counts()
            for conf_level, count in confidence.items():
                pct = count/total_matched*100
                print(f"  {conf_level}: {count} ({pct:.1f}%)")
        
        if not unmatched_df.empty:
            print("\nUnmatched customer analysis:")
            
            # Cash & Carry analysis
            cash_carry = unmatched_df['cash_carry'].value_counts()
            print("\nCash & Carry indicator:")
            for indicator, count in cash_carry.items():
                print(f"  {indicator}: {count}")
            
            # Class of trade
            print("\nTop classes of trade (unmatched):")
            trade_classes = unmatched_df['class_of_trade'].value_counts().head(10)
            for trade_class, count in trade_classes.items():
                print(f"  {trade_class}: {count}")
            
            # Most active unmatched
            print("\nTop 20 most active unmatched customers:")
            top_unmatched = unmatched_df.nlargest(20, 'weeks_active')[
                ['msa_customer_number', 'msa_name', 'msa_city', 'msa_state', 'weeks_active']
            ]
            print(top_unmatched.to_string(index=False))
        
        # Export results
        matches_df.to_csv('customer_matches.csv', index=False)
        unmatched_df.to_csv('customer_unmatched.csv', index=False)
        
        print(f"\nResults exported:")
        print(f"  - customer_matches.csv ({len(matches_df)} records)")
        print(f"  - customer_unmatched.csv ({len(unmatched_df)} records)")
        
        # Create mapping file
        if not matches_df.empty:
            mapping = matches_df[['msa_customer_number', 'msa_shipping_number', 'pos_account_number']].copy()
            mapping.to_csv('customer_id_mapping.csv', index=False)
            print(f"  - customer_id_mapping.csv (for system integration)")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    matcher = CustomerAccountMatcher()
    
    try:
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
        
        if not unmatched_df.empty:
            # Check for patterns
            cash_carry_unmatched = unmatched_df[unmatched_df['cash_carry'] == 'Y']
            if not cash_carry_unmatched.empty:
                print(f"\n{len(cash_carry_unmatched)} unmatched are Cash & Carry")
                print("These might be walk-in customers without accounts")
            
            # Check for specific patterns in names
            common_patterns = ['SHELL', 'CHEVRON', 'BP', 'EXXON', 'CITGO', 'MARATHON', 'CIRCLE K', '7-ELEVEN']
            for pattern in common_patterns:
                pattern_matches = unmatched_df[unmatched_df['msa_name'].str.contains(pattern, case=False, na=False)]
                if not pattern_matches.empty:
                    print(f"\n{len(pattern_matches)} unmatched contain '{pattern}'")
        
    finally:
        matcher.close()


if __name__ == "__main__":
    main()