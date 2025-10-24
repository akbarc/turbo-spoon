#!/usr/bin/env python3
"""
Match MSA Purchases (PUR records) to POS Transactions
Uses customer mapping and item mapping to reconcile sales
"""

import os
import pandas as pd
import pymssql
from datetime import datetime, timedelta
import json
from collections import defaultdict

class PurchaseMatcher:
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
        
        # Load mappings
        self.customer_mapping = self.load_customer_mapping()
        self.item_mapping = self.load_item_mapping()
        
        print(f"Loaded {len(self.customer_mapping)} customer mappings")
        print(f"Loaded {len(self.item_mapping)} item mappings")
    
    def load_customer_mapping(self):
        """Load customer ID mapping from previous analysis"""
        mapping = {}
        if os.path.exists('customer_id_mapping_improved.csv'):
            df = pd.read_csv('customer_id_mapping_improved.csv')
            for _, row in df.iterrows():
                key = f"{row['msa_customer_number']}_{row['msa_shipping_number']}"
                mapping[key] = row['pos_account_number']
        return mapping
    
    def load_item_mapping(self):
        """Load item/SKU mapping"""
        mapping = {}
        
        # First try to load from previous analysis
        if os.path.exists('upc_to_itemcode_mapping.json'):
            with open('upc_to_itemcode_mapping.json', 'r') as f:
                upc_mapping = json.load(f)
                mapping.update(upc_mapping)
        
        # Also load from database
        query = """
        SELECT 
            i.ItemLookupCode,
            i.Description,
            a.Alias
        FROM Item i
        LEFT JOIN Alias a ON i.ID = a.ItemID
        """
        
        self.cursor.execute(query)
        for row in self.cursor.fetchall():
            if row['Alias']:
                mapping[row['Alias']] = row['ItemLookupCode']
            # Also map the ItemLookupCode to itself
            mapping[row['ItemLookupCode']] = row['ItemLookupCode']
        
        return mapping
    
    def get_week_dates(self, week_str: str) -> tuple:
        """Convert week string to date range"""
        month = int(week_str[:2])
        day = int(week_str[2:4])
        year = int(week_str[4:])
        
        end_date = datetime(year, month, day)
        start_date = end_date - timedelta(days=6)
        
        return start_date, end_date
    
    def load_msa_purchases(self, week: str):
        """Load MSA purchase records for a week"""
        week_dir = os.path.join(self.csv_dir, week)
        purchases_file = os.path.join(week_dir, f"{week}_purchases.csv")
        
        if os.path.exists(purchases_file):
            df = pd.read_csv(purchases_file)
            
            # Also load brands to get product descriptions
            brands_file = os.path.join(week_dir, f"{week}_brands.csv")
            if os.path.exists(brands_file):
                brands_df = pd.read_csv(brands_file)
                # Ensure distributor_sku is string type in both dataframes
                df['distributor_sku'] = df['distributor_sku'].astype(str)
                brands_df['distributor_sku'] = brands_df['distributor_sku'].astype(str)
                # Merge to get product descriptions
                df = df.merge(
                    brands_df[['distributor_sku', 'upc_code', 'product_description']], 
                    on='distributor_sku', 
                    how='left'
                )
            
            return df
        return pd.DataFrame()
    
    def load_pos_transactions(self, start_date: datetime, end_date: datetime):
        """Load POS transactions for date range"""
        query = """
        SELECT 
            t.TransactionNumber,
            t.Time as TransactionTime,
            t.CustomerID,
            c.AccountNumber,
            te.ItemID,
            i.ItemLookupCode,
            i.Description as ItemDescription,
            te.Quantity,
            te.Price,
            te.Price * te.Quantity as ExtendedPrice,
            te.SalesTax
        FROM [Transaction] t
        JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Customer c ON t.CustomerID = c.ID
        WHERE t.Time >= %s 
        AND t.Time <= %s
        AND t.Status = 1  -- Completed transactions only
        ORDER BY t.Time, t.TransactionNumber
        """
        
        self.cursor.execute(query, (start_date, end_date))
        transactions = []
        
        for row in self.cursor.fetchall():
            transactions.append({
                'transaction_number': row['TransactionNumber'],
                'transaction_time': row['TransactionTime'],
                'customer_id': row['CustomerID'],
                'account_number': row['AccountNumber'] or '',
                'item_id': row['ItemID'],
                'item_lookup_code': row['ItemLookupCode'],
                'item_description': row['ItemDescription'],
                'quantity': float(row['Quantity'] or 0),
                'price': float(row['Price'] or 0),
                'extended_price': float(row['ExtendedPrice'] or 0),
                'sales_tax': float(row['SalesTax'] or 0)
            })
        
        return pd.DataFrame(transactions)
    
    def match_purchases_for_week(self, week: str):
        """Match purchases for a specific week"""
        print(f"\nAnalyzing week: {week}")
        
        # Get date range
        start_date, end_date = self.get_week_dates(week)
        print(f"  Date range: {start_date.date()} to {end_date.date()}")
        
        # Load MSA purchases
        msa_purchases = self.load_msa_purchases(week)
        if msa_purchases.empty:
            print("  No MSA purchases found")
            return pd.DataFrame()
        
        print(f"  MSA purchases: {len(msa_purchases)} records")
        
        # Load POS transactions
        pos_transactions = self.load_pos_transactions(start_date, end_date)
        print(f"  POS transactions: {len(pos_transactions)} records")
        
        # Aggregate MSA by customer and SKU
        msa_summary = msa_purchases.groupby(['ship_to_customer_number', 'ship_to_customer_shipping_number', 'distributor_sku']).agg({
            'measure_value_1': 'sum',  # Quantity
            'measure_value_2': 'sum',  # Dollars
            'upc_code': 'first',
            'product_description': 'first'
        }).reset_index()
        
        msa_summary.columns = ['customer_number', 'shipping_number', 'sku', 'msa_quantity', 'msa_dollars', 'upc', 'description']
        
        # Aggregate POS by customer and item
        if not pos_transactions.empty:
            pos_summary = pos_transactions.groupby(['account_number', 'item_lookup_code']).agg({
                'quantity': 'sum',
                'extended_price': 'sum',
                'item_description': 'first'
            }).reset_index()
            
            pos_summary.columns = ['account_number', 'item_code', 'pos_quantity', 'pos_dollars', 'pos_description']
        else:
            pos_summary = pd.DataFrame()
        
        # Match records
        matches = []
        unmatched_msa = []
        
        for _, msa_row in msa_summary.iterrows():
            # Get customer mapping
            customer_key = f"{msa_row['customer_number']}_{msa_row['shipping_number']}"
            pos_account = self.customer_mapping.get(customer_key)
            
            # Get item mapping
            item_code = None
            # Try different mappings
            if msa_row['sku'] in self.item_mapping:
                item_code = self.item_mapping[msa_row['sku']]
            elif msa_row['upc'] in self.item_mapping:
                item_code = self.item_mapping[msa_row['upc']]
            else:
                # Try without leading zeros
                sku_clean = str(msa_row['sku']).lstrip('0')
                upc_clean = str(msa_row['upc']).lstrip('0')
                if sku_clean in self.item_mapping:
                    item_code = self.item_mapping[sku_clean]
                elif upc_clean in self.item_mapping:
                    item_code = self.item_mapping[upc_clean]
            
            # Look for matching POS transaction
            match_found = False
            if pos_account and item_code and not pos_summary.empty:
                pos_match = pos_summary[
                    (pos_summary['account_number'] == pos_account) & 
                    (pos_summary['item_code'] == item_code)
                ]
                
                if not pos_match.empty:
                    pos_row = pos_match.iloc[0]
                    matches.append({
                        'week': week,
                        'customer_number': msa_row['customer_number'],
                        'pos_account': pos_account,
                        'sku': msa_row['sku'],
                        'item_code': item_code,
                        'description': msa_row['description'],
                        'msa_quantity': msa_row['msa_quantity'],
                        'pos_quantity': pos_row['pos_quantity'],
                        'quantity_variance': pos_row['pos_quantity'] - msa_row['msa_quantity'],
                        'msa_dollars': msa_row['msa_dollars'],
                        'pos_dollars': pos_row['pos_dollars'],
                        'dollar_variance': pos_row['pos_dollars'] - msa_row['msa_dollars']
                    })
                    match_found = True
            
            if not match_found:
                unmatched_msa.append({
                    'week': week,
                    'customer_number': msa_row['customer_number'],
                    'shipping_number': msa_row['shipping_number'],
                    'sku': msa_row['sku'],
                    'upc': msa_row['upc'],
                    'description': msa_row['description'],
                    'msa_quantity': msa_row['msa_quantity'],
                    'msa_dollars': msa_row['msa_dollars'],
                    'pos_account': pos_account or 'NO_CUSTOMER_MATCH',
                    'item_code': item_code or 'NO_ITEM_MATCH'
                })
        
        return pd.DataFrame(matches), pd.DataFrame(unmatched_msa)
    
    def analyze_all_weeks(self):
        """Analyze all weeks of purchases"""
        all_matches = []
        all_unmatched = []
        
        weeks = sorted([d for d in os.listdir(self.csv_dir) if os.path.isdir(os.path.join(self.csv_dir, d))])
        
        for week in weeks[:2]:  # Start with first 2 weeks for testing
            matches, unmatched = self.match_purchases_for_week(week)
            if not matches.empty:
                all_matches.append(matches)
            if not unmatched.empty:
                all_unmatched.append(unmatched)
        
        if all_matches:
            matches_df = pd.concat(all_matches, ignore_index=True)
        else:
            matches_df = pd.DataFrame()
        
        if all_unmatched:
            unmatched_df = pd.concat(all_unmatched, ignore_index=True)
        else:
            unmatched_df = pd.DataFrame()
        
        return matches_df, unmatched_df
    
    def generate_report(self, matches_df, unmatched_df):
        """Generate purchase matching report"""
        print("\n" + "="*60)
        print("PURCHASE MATCHING ANALYSIS")
        print("="*60)
        
        total_msa = len(matches_df) + len(unmatched_df)
        
        if total_msa == 0:
            print("No purchases to analyze")
            return
        
        match_rate = len(matches_df) / total_msa * 100 if total_msa > 0 else 0
        
        print(f"\nTotal purchase records: {total_msa}")
        print(f"Matched: {len(matches_df)} ({match_rate:.1f}%)")
        print(f"Unmatched: {len(unmatched_df)} ({100-match_rate:.1f}%)")
        
        if not matches_df.empty:
            print("\n" + "-"*50)
            print("MATCHED PURCHASES ANALYSIS:")
            print("-"*50)
            
            # Quantity variance analysis
            avg_qty_var = matches_df['quantity_variance'].mean()
            abs_qty_var = matches_df['quantity_variance'].abs().mean()
            print(f"Average quantity variance: {avg_qty_var:.2f}")
            print(f"Average absolute quantity variance: {abs_qty_var:.2f}")
            
            # Dollar variance analysis
            if 'dollar_variance' in matches_df.columns:
                avg_dollar_var = matches_df['dollar_variance'].mean()
                abs_dollar_var = matches_df['dollar_variance'].abs().mean()
                print(f"Average dollar variance: ${avg_dollar_var:.2f}")
                print(f"Average absolute dollar variance: ${abs_dollar_var:.2f}")
            
            # Perfect matches
            perfect_matches = matches_df[matches_df['quantity_variance'] == 0]
            print(f"\nPerfect quantity matches: {len(perfect_matches)} ({len(perfect_matches)/len(matches_df)*100:.1f}%)")
            
            # Large variances
            large_var = matches_df[matches_df['quantity_variance'].abs() > 10]
            if not large_var.empty:
                print(f"Matches with >10 unit variance: {len(large_var)}")
                print("\nTop variances:")
                top_var = large_var.nlargest(10, 'quantity_variance')[['description', 'msa_quantity', 'pos_quantity', 'quantity_variance']]
                print(top_var.to_string(index=False))
        
        if not unmatched_df.empty:
            print("\n" + "-"*50)
            print("UNMATCHED PURCHASES ANALYSIS:")
            print("-"*50)
            
            # Reason breakdown
            no_customer = len(unmatched_df[unmatched_df['pos_account'] == 'NO_CUSTOMER_MATCH'])
            no_item = len(unmatched_df[unmatched_df['item_code'] == 'NO_ITEM_MATCH'])
            
            print(f"No customer match: {no_customer}")
            print(f"No item match: {no_item}")
            print(f"Both missing: {len(unmatched_df[(unmatched_df['pos_account'] == 'NO_CUSTOMER_MATCH') & (unmatched_df['item_code'] == 'NO_ITEM_MATCH')])}")
            
            # Top unmatched by quantity
            print("\nTop unmatched by quantity:")
            top_unmatched = unmatched_df.nlargest(10, 'msa_quantity')[['customer_number', 'description', 'msa_quantity', 'pos_account', 'item_code']]
            print(top_unmatched.to_string(index=False))
        
        # Export results
        if not matches_df.empty:
            matches_df.to_csv('purchase_matches.csv', index=False)
            print(f"\nMatched purchases exported to: purchase_matches.csv")
        
        if not unmatched_df.empty:
            unmatched_df.to_csv('purchase_unmatched.csv', index=False)
            print(f"Unmatched purchases exported to: purchase_unmatched.csv")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    matcher = PurchaseMatcher()
    
    try:
        # Analyze purchases
        matches_df, unmatched_df = matcher.analyze_all_weeks()
        
        # Generate report
        matcher.generate_report(matches_df, unmatched_df)
        
        print("\n" + "="*60)
        print("KEY INSIGHTS")
        print("="*60)
        
        if not matches_df.empty or not unmatched_df.empty:
            total = len(matches_df) + len(unmatched_df)
            match_rate = len(matches_df) / total * 100 if total > 0 else 0
            
            print(f"\nPurchase matching rate: {match_rate:.1f}%")
            
            if match_rate < 50:
                print("\nLow match rate suggests:")
                print("  - Item mapping needs improvement")
                print("  - Timing differences between systems")
                print("  - Different aggregation levels")
        
    finally:
        matcher.close()


if __name__ == "__main__":
    main()