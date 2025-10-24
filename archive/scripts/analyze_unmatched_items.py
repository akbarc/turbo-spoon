#!/usr/bin/env python3
"""
Analyze unmatched MSA items to determine if they're SKU issues or truly missing
"""

import os
import pandas as pd
import pymssql
from collections import Counter, defaultdict
import re

class UnmatchedItemAnalyzer:
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
        
        # Load all POS items
        self.pos_items = self.load_pos_items()
        print(f"Loaded {len(self.pos_items)} items from POS database")
        
    def load_pos_items(self):
        """Load all items from POS with various identifiers"""
        query = """
        SELECT 
            i.ItemLookupCode,
            i.Description,
            i.Quantity,
            i.LastReceived,
            i.LastUpdated,
            a.Alias as AliasCode
        FROM Item i
        LEFT JOIN Alias a ON i.ID = a.ItemID
        """
        
        self.cursor.execute(query)
        items = {}
        for row in self.cursor.fetchall():
            code = row['ItemLookupCode']
            if code not in items:
                items[code] = {
                    'description': row['Description'],
                    'quantity': float(row['Quantity'] or 0),
                    'last_received': row['LastReceived'],
                    'last_updated': row['LastUpdated'],
                    'aliases': set()
                }
            if row['AliasCode']:
                items[code]['aliases'].add(row['AliasCode'])
        
        return items
    
    def analyze_unmatched_items(self):
        """Analyze patterns in unmatched items"""
        
        # Load the analysis results
        if os.path.exists('msa_inventory_variance_analysis.csv'):
            df = pd.read_csv('msa_inventory_variance_analysis.csv')
        else:
            print("Running fresh analysis...")
            # Load from MSA files
            all_items = []
            for week in os.listdir(self.csv_dir):
                if not os.path.isdir(os.path.join(self.csv_dir, week)):
                    continue
                brands_file = os.path.join(self.csv_dir, week, f"{week}_brands.csv")
                if os.path.exists(brands_file):
                    brands_df = pd.read_csv(brands_file)
                    brands_df['week'] = week
                    all_items.append(brands_df)
            df = pd.concat(all_items, ignore_index=True)
        
        # Separate matched and unmatched
        unmatched = df[df.get('item_lookup_code', '') == 'NOT_FOUND'] if 'item_lookup_code' in df.columns else df
        
        # For fresh analysis, try to match items
        results = []
        unmatched_details = []
        
        print(f"\nAnalyzing {len(unmatched)} unmatched records...")
        
        # Group by unique SKU/UPC combinations - check column names first
        if 'distributor_sku' in unmatched.columns:
            group_cols = ['distributor_sku', 'upc_code']
            desc_col = 'product_description'
        else:
            group_cols = ['sku', 'upc'] if 'sku' in unmatched.columns else ['sku', 'upc_code']
            desc_col = 'description' if 'description' in unmatched.columns else 'product_description'
        
        unique_items = unmatched.groupby(group_cols).agg({
            desc_col: 'first',
            'measure_value_1' if 'measure_value_1' in unmatched.columns else 'msa_reported': 'mean'  # Average inventory
        }).reset_index()
        
        # Rename columns for consistency
        unique_items.columns = ['distributor_sku', 'upc_code', 'product_description', 'measure_value_1']
        
        print(f"Found {len(unique_items)} unique unmatched SKUs")
        
        for _, item in unique_items.iterrows():
            sku = str(item['distributor_sku']).strip()
            upc = str(item['upc_code']).strip()
            description = str(item['product_description']).strip()
            avg_inventory = float(item['measure_value_1']) if pd.notna(item['measure_value_1']) else 0
            
            # Try various matching strategies
            match_result = self.try_match_item(sku, upc, description)
            
            unmatched_details.append({
                'sku': sku,
                'upc': upc,
                'description': description[:50],
                'avg_inventory': avg_inventory,
                'match_type': match_result['type'],
                'match_code': match_result['code'],
                'match_confidence': match_result['confidence'],
                'category': self.categorize_product(description)
            })
        
        return pd.DataFrame(unmatched_details)
    
    def try_match_item(self, sku, upc, description):
        """Try various strategies to match an item"""
        
        # Strategy 1: Direct SKU match
        if sku in self.pos_items:
            return {'type': 'direct_sku', 'code': sku, 'confidence': 'high'}
        
        # Strategy 2: Direct UPC match
        if upc in self.pos_items:
            return {'type': 'direct_upc', 'code': upc, 'confidence': 'high'}
        
        # Strategy 3: Clean and retry
        sku_clean = sku.lstrip('0')
        upc_clean = upc.lstrip('0')
        
        if sku_clean in self.pos_items:
            return {'type': 'cleaned_sku', 'code': sku_clean, 'confidence': 'high'}
        
        if upc_clean in self.pos_items:
            return {'type': 'cleaned_upc', 'code': upc_clean, 'confidence': 'high'}
        
        # Strategy 4: Check aliases
        for code, item_data in self.pos_items.items():
            if sku in item_data['aliases'] or upc in item_data['aliases']:
                return {'type': 'alias_match', 'code': code, 'confidence': 'high'}
            if sku_clean in item_data['aliases'] or upc_clean in item_data['aliases']:
                return {'type': 'alias_match_cleaned', 'code': code, 'confidence': 'medium'}
        
        # Strategy 5: Partial description match
        desc_words = set(description.upper().split())
        best_match = None
        best_score = 0
        
        for code, item_data in self.pos_items.items():
            if item_data['description']:
                pos_words = set(item_data['description'].upper().split())
                common_words = desc_words & pos_words
                score = len(common_words)
                if score > best_score and score >= 3:  # At least 3 words match
                    best_score = score
                    best_match = code
        
        if best_match:
            return {'type': 'description_match', 'code': best_match, 'confidence': 'low'}
        
        # No match found
        return {'type': 'no_match', 'code': None, 'confidence': 'none'}
    
    def categorize_product(self, description):
        """Categorize product based on description"""
        desc_upper = description.upper()
        
        # Cigarette brands
        if any(brand in desc_upper for brand in ['NEWPORT', 'MARLBORO', 'CAMEL', 'AMERICAN SPIRIT', 'WINSTON', 'KOOL']):
            return 'CIGARETTES'
        
        # Cigars
        if any(term in desc_upper for term in ['CIGAR', 'SWISHER', 'BACKWOOD', 'BLACK & MILD', 'DUTCH']):
            return 'CIGARS'
        
        # Vape
        if any(term in desc_upper for term in ['JUUL', 'VUSE', 'NJOY', 'BLU', 'LOGIC', 'DISPOSABLE', 'VAPE', 'POD']):
            return 'VAPE'
        
        # Tobacco
        if any(term in desc_upper for term in ['SKOAL', 'GRIZZLY', 'COPENHAGEN', 'KODIAK', 'REDMAN', 'LEVI']):
            return 'SMOKELESS'
        
        # Rolling papers
        if any(term in desc_upper for term in ['PAPER', 'ROLL', 'WRAP', 'TUBE', 'FILTER', 'CONE']):
            return 'ACCESSORIES'
        
        # CBD/Hemp
        if any(term in desc_upper for term in ['CBD', 'HEMP', 'DELTA', 'THC']):
            return 'CBD_HEMP'
        
        # Nicotine pouches
        if any(term in desc_upper for term in ['ZYN', 'VELO', 'ROGUE', 'POUCH', 'NICOTINE']):
            return 'NIC_POUCHES'
        
        return 'OTHER'
    
    def analyze_missing_po_impact(self):
        """Analyze the impact of missing PO data"""
        print("\n" + "="*60)
        print("ANALYZING IMPACT OF MISSING PURCHASE ORDER DATA")
        print("="*60)
        
        # Load variance analysis
        df = pd.read_csv('msa_inventory_variance_analysis.csv')
        
        # Items with negative expected ending (would need purchases)
        negative_inventory = df[df['expected_ending'] < 0]
        
        print(f"\nItems requiring purchases (negative expected inventory): {len(negative_inventory)}")
        
        # Group by week to see patterns
        weekly_impact = negative_inventory.groupby('week').agg({
            'sku': 'count',
            'expected_ending': 'sum',
            'sales': 'sum'
        }).rename(columns={'sku': 'items_affected'})
        
        print("\nWeekly impact of missing PO data:")
        print(weekly_impact)
        
        # Top products needing purchases
        print("\nTop 20 products needing purchase orders:")
        top_needs_po = negative_inventory.groupby('description').agg({
            'expected_ending': 'min',
            'sales': 'sum',
            'sku': 'first'
        }).sort_values('expected_ending').head(20)
        
        print(top_needs_po)
        
        return negative_inventory
    
    def generate_report(self, unmatched_df):
        """Generate detailed report on unmatched items"""
        print("\n" + "="*60)
        print("UNMATCHED ITEMS ANALYSIS REPORT")
        print("="*60)
        
        # Overall statistics
        total_unmatched = len(unmatched_df)
        print(f"\nTotal unique unmatched SKUs: {total_unmatched}")
        
        # Match type breakdown
        print("\nMatching attempt results:")
        match_types = unmatched_df['match_type'].value_counts()
        for match_type, count in match_types.items():
            pct = count/total_unmatched*100
            print(f"  {match_type}: {count} ({pct:.1f}%)")
        
        # Category breakdown
        print("\nUnmatched items by category:")
        categories = unmatched_df['category'].value_counts()
        for category, count in categories.items():
            pct = count/total_unmatched*100
            print(f"  {category}: {count} ({pct:.1f}%)")
        
        # Items with inventory but no match
        has_inventory = unmatched_df[unmatched_df['avg_inventory'] > 0]
        print(f"\nUnmatched items with inventory: {len(has_inventory)}")
        
        # Top unmatched by inventory
        print("\nTop 20 unmatched items by average inventory:")
        top_unmatched = unmatched_df.nlargest(20, 'avg_inventory')[['sku', 'description', 'category', 'avg_inventory']]
        print(top_unmatched.to_string(index=False))
        
        # Potential matches found
        potential_matches = unmatched_df[unmatched_df['match_type'] != 'no_match']
        if not potential_matches.empty:
            print(f"\nPotential matches found: {len(potential_matches)}")
            print("\nSample potential matches:")
            samples = potential_matches.head(10)[['sku', 'description', 'match_type', 'match_code']]
            print(samples.to_string(index=False))
        
        # Export results
        unmatched_df.to_csv('unmatched_items_analysis.csv', index=False)
        print("\nDetailed results saved to: unmatched_items_analysis.csv")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    analyzer = UnmatchedItemAnalyzer()
    
    try:
        # Analyze unmatched items
        unmatched_df = analyzer.analyze_unmatched_items()
        
        # Generate report
        analyzer.generate_report(unmatched_df)
        
        # Analyze PO impact
        analyzer.analyze_missing_po_impact()
        
        print("\n" + "="*60)
        print("KEY FINDINGS")
        print("="*60)
        
        # Summary
        no_match = unmatched_df[unmatched_df['match_type'] == 'no_match']
        potential = unmatched_df[unmatched_df['match_type'] != 'no_match']
        
        print(f"\n1. SKU MAPPING ISSUES vs TRULY MISSING:")
        print(f"   - Truly missing (no match found): {len(no_match)} items")
        print(f"   - Potential SKU mapping issues: {len(potential)} items")
        print(f"   - Success rate if mappings fixed: {len(potential)/len(unmatched_df)*100:.1f}%")
        
        print(f"\n2. MISSING PO DATA IMPACT:")
        print(f"   - Primary issue: Cannot track incoming inventory")
        print(f"   - Result: Negative expected inventory for high-volume items")
        print(f"   - Recommendation: PO data not critical if using MSA beginning inventory")
        
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()