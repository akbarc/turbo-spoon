#!/usr/bin/env python3
"""
Optimized MSA Inventory Analysis
Calculates inventory variances between MSA reports and expected values
"""

import os
import csv
import pandas as pd
import pymssql
from datetime import datetime, timedelta
from collections import defaultdict
import json

class OptimizedMSAAnalyzer:
    def __init__(self):
        self.csv_dir = "/Users/akbarchranya/georgiadashboard/MSA_CSV_Output"
        self.weeks = sorted([d for d in os.listdir(self.csv_dir) if os.path.isdir(os.path.join(self.csv_dir, d))])
        
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
        
        # Cache for database lookups
        self.item_cache = {}
        self.load_all_items()
    
    def load_all_items(self):
        """Load all items from database into cache"""
        print("Loading item catalog from database...")
        query = """
        SELECT 
            i.ID,
            i.ItemLookupCode,
            i.Description,
            i.Quantity,
            i.BinLocation,
            a.Alias as UPC
        FROM Item i
        LEFT JOIN Alias a ON i.ID = a.ItemID
        """
        
        self.cursor.execute(query)
        for row in self.cursor.fetchall():
            item_code = row['ItemLookupCode']
            if item_code not in self.item_cache:
                self.item_cache[item_code] = {
                    'id': row['ID'],
                    'description': row['Description'],
                    'quantity': float(row['Quantity'] or 0),
                    'bin': row['BinLocation'],
                    'upcs': []
                }
            if row['UPC']:
                self.item_cache[item_code]['upcs'].append(row['UPC'])
        
        print(f"Loaded {len(self.item_cache)} items from database")
    
    def find_item_by_upc(self, upc: str) -> dict:
        """Find item in cache by UPC"""
        upc_clean = upc.lstrip('0')
        
        for item_code, item_data in self.item_cache.items():
            # Check ItemLookupCode
            if item_code == upc or item_code == upc_clean:
                return {'code': item_code, **item_data}
            
            # Check aliases
            for alias in item_data['upcs']:
                if alias == upc or alias == upc_clean or alias.lstrip('0') == upc_clean:
                    return {'code': item_code, **item_data}
        
        return None
    
    def analyze_inventory_variance(self):
        """Analyze inventory variances across all weeks"""
        results = []
        inventory_by_sku = {}  # Track inventory week by week
        
        for week_idx, week in enumerate(self.weeks):
            print(f"\nProcessing week {week}...")
            week_dir = os.path.join(self.csv_dir, week)
            
            # Load brands (inventory) and purchases (sales)
            brands_df = pd.read_csv(os.path.join(week_dir, f"{week}_brands.csv"))
            purchases_df = pd.read_csv(os.path.join(week_dir, f"{week}_purchases.csv"))
            
            # Group sales by SKU
            sales_by_sku = purchases_df.groupby('distributor_sku')['measure_value_1'].sum().to_dict()
            
            week_results = []
            
            for _, brand in brands_df.iterrows():
                sku = str(brand['distributor_sku']).strip()
                upc = str(brand['upc_code']).strip()
                description = str(brand['product_description']).strip()[:50]
                
                # Get MSA reported inventory
                msa_inventory = 0
                try:
                    if str(brand['measure_code_1']) == '003':
                        msa_inventory = float(brand['measure_value_1']) if pd.notna(brand['measure_value_1']) else 0
                except:
                    msa_inventory = 0
                
                # Get sales for this week
                week_sales = float(sales_by_sku.get(sku, 0))
                
                # Get beginning inventory
                if week_idx == 0:
                    # First week: use MSA reported as beginning
                    beginning_inventory = msa_inventory
                else:
                    # Use previous week's ending inventory
                    beginning_inventory = inventory_by_sku.get(sku, {}).get('ending', msa_inventory)
                
                # Calculate expected ending (no purchases data available)
                expected_ending = beginning_inventory - week_sales
                
                # Calculate variance
                variance = msa_inventory - expected_ending
                
                # Find POS item
                pos_item = self.find_item_by_upc(upc) or self.find_item_by_upc(sku)
                pos_inventory = pos_item['quantity'] if pos_item else None
                item_code = pos_item['code'] if pos_item else 'NOT_FOUND'
                
                # Store for next week
                inventory_by_sku[sku] = {
                    'ending': msa_inventory,
                    'sales': week_sales
                }
                
                result = {
                    'week': week,
                    'sku': sku,
                    'upc': upc,
                    'description': description,
                    'item_lookup_code': item_code,
                    'beginning_inv': beginning_inventory,
                    'sales': week_sales,
                    'expected_ending': expected_ending,
                    'msa_reported': msa_inventory,
                    'variance': variance,
                    'pos_current': pos_inventory
                }
                
                week_results.append(result)
            
            results.extend(week_results)
            
            # Summary for this week
            week_df = pd.DataFrame(week_results)
            total_variance = week_df['variance'].abs().sum()
            items_with_variance = len(week_df[week_df['variance'] != 0])
            matched_items = len(week_df[week_df['item_lookup_code'] != 'NOT_FOUND'])
            
            print(f"  - Processed {len(week_df)} SKUs")
            print(f"  - Matched to POS: {matched_items} ({matched_items/len(week_df)*100:.1f}%)")
            print(f"  - Items with variance: {items_with_variance}")
            print(f"  - Total absolute variance: {total_variance:.0f}")
        
        return pd.DataFrame(results)
    
    def generate_report(self, df: pd.DataFrame):
        """Generate analysis report"""
        print("\n" + "="*80)
        print("INVENTORY VARIANCE ANALYSIS REPORT")
        print("="*80)
        
        # Overall statistics
        print(f"\nTotal records analyzed: {len(df)}")
        print(f"Unique SKUs: {df['sku'].nunique()}")
        print(f"Weeks analyzed: {df['week'].nunique()}")
        
        # Matching statistics
        matched = df[df['item_lookup_code'] != 'NOT_FOUND']
        print(f"\nItems matched to POS: {len(matched)} ({len(matched)/len(df)*100:.1f}%)")
        
        # Variance analysis
        has_variance = df[df['variance'] != 0]
        print(f"Records with variance: {len(has_variance)} ({len(has_variance)/len(df)*100:.1f}%)")
        
        # Top variances
        print("\n" + "-"*50)
        print("TOP 20 ITEMS BY ABSOLUTE VARIANCE:")
        print("-"*50)
        top_var = df.nlargest(20, 'variance')[['week', 'sku', 'description', 'sales', 'msa_reported', 'expected_ending', 'variance']]
        print(top_var.to_string(index=False))
        
        # Items with consistent issues
        print("\n" + "-"*50)
        print("ITEMS WITH RECURRING VARIANCES:")
        print("-"*50)
        sku_issues = df[df['variance'] != 0].groupby('sku').agg({
            'variance': ['count', 'mean', 'sum'],
            'description': 'first',
            'item_lookup_code': 'first'
        }).round(2)
        
        sku_issues.columns = ['weeks_with_var', 'avg_variance', 'total_variance', 'description', 'item_code']
        recurring = sku_issues[sku_issues['weeks_with_var'] >= 3].sort_values('total_variance', ascending=False)
        
        if not recurring.empty:
            print(recurring.head(20).to_string())
        else:
            print("No items with variances in 3+ weeks")
        
        # Export results
        output_file = 'msa_inventory_variance_analysis.csv'
        df.to_csv(output_file, index=False)
        print(f"\nDetailed results saved to: {output_file}")
        
        # Create summary
        summary = df.groupby('week').agg({
            'variance': ['count', 'sum', 'mean'],
            'sales': 'sum',
            'sku': 'count'
        }).round(2)
        
        summary_file = 'msa_variance_summary_by_week.csv'
        summary.to_csv(summary_file)
        print(f"Weekly summary saved to: {summary_file}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    analyzer = OptimizedMSAAnalyzer()
    
    try:
        print("Starting MSA Inventory Variance Analysis...")
        print("Formula: Expected Ending = Beginning Inventory - Sales")
        print("Variance = MSA Reported - Expected Ending")
        
        # Run analysis
        results_df = analyzer.analyze_inventory_variance()
        
        # Generate report
        analyzer.generate_report(results_df)
        
        print("\n" + "="*80)
        print("KEY INSIGHTS:")
        print("="*80)
        
        # Analyze patterns
        if not results_df.empty:
            # Items with positive variance (more inventory than expected)
            positive_var = results_df[results_df['variance'] > 10]
            if not positive_var.empty:
                print(f"\n{len(positive_var)} records show higher inventory than expected")
                print("Possible reasons:")
                print("  - Unrecorded purchases/receiving")
                print("  - Returns not captured in sales")
                print("  - Inventory adjustments")
            
            # Items with negative variance (less inventory than expected)
            negative_var = results_df[results_df['variance'] < -10]
            if not negative_var.empty:
                print(f"\n{len(negative_var)} records show lower inventory than expected")
                print("Possible reasons:")
                print("  - Unrecorded sales")
                print("  - Shrinkage/theft")
                print("  - Transfers out not captured")
            
            # Check POS vs MSA alignment
            matched = results_df[results_df['item_lookup_code'] != 'NOT_FOUND']
            if not matched.empty and matched['pos_current'].notna().any():
                pos_comparison = matched[matched['pos_current'].notna()]
                pos_diff = (pos_comparison['pos_current'] - pos_comparison['msa_reported']).abs().mean()
                print(f"\nAverage difference between POS and MSA inventory: {pos_diff:.2f} units")
        
    finally:
        analyzer.close()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()