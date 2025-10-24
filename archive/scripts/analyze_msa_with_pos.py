#!/usr/bin/env python3
"""
MSA Inventory Analysis with POS Data Integration
Compares MSA reported inventory with actual POS database
"""

import os
import csv
import pandas as pd
import pymssql
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
import json

class MSAPOSInventoryAnalyzer:
    def __init__(self, csv_dir: str):
        self.csv_dir = csv_dir
        self.weeks = sorted([d for d in os.listdir(csv_dir) if os.path.isdir(os.path.join(csv_dir, d))])
        
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
        
        # Load UPC to ItemLookupCode mapping if exists
        self.upc_mapping = {}
        if os.path.exists('upc_to_itemcode_mapping.json'):
            with open('upc_to_itemcode_mapping.json', 'r') as f:
                self.upc_mapping = json.load(f)
    
    def get_week_dates(self, week_str: str) -> Tuple[datetime, datetime]:
        """Convert week string to date range"""
        # Parse MMDDYYYY format
        month = int(week_str[:2])
        day = int(week_str[2:4])
        year = int(week_str[4:])
        
        end_date = datetime(year, month, day)
        start_date = end_date - timedelta(days=6)
        
        return start_date, end_date
    
    def get_pos_inventory(self, item_lookup_code: str, end_date: datetime) -> float:
        """Get inventory from POS database for a specific item at a specific date"""
        query = """
        SELECT 
            i.ID,
            i.ItemLookupCode,
            i.Description,
            i.Quantity as CurrentInventory,
            i.QuantityCommitted,
            i.BinLocation
        FROM Item i
        WHERE i.ItemLookupCode = %s
        """
        
        self.cursor.execute(query, (item_lookup_code,))
        result = self.cursor.fetchone()
        
        if result:
            return float(result['CurrentInventory'] or 0)
        return None
    
    def get_pos_sales(self, item_lookup_code: str, start_date: datetime, end_date: datetime) -> float:
        """Get sales from POS database for a specific item in date range"""
        query = """
        SELECT 
            SUM(te.Quantity) as TotalSales
        FROM TransactionEntry te
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        WHERE i.ItemLookupCode = %s
        AND t.Time >= %s
        AND t.Time <= %s
        AND t.Status = 1  -- Completed transactions only
        """
        
        self.cursor.execute(query, (item_lookup_code, start_date, end_date))
        result = self.cursor.fetchone()
        
        if result and result['TotalSales']:
            return float(result['TotalSales'])
        return 0
    
    def get_pos_purchases(self, item_lookup_code: str, start_date: datetime, end_date: datetime) -> float:
        """Get purchases/receiving from POS database for a specific item in date range"""
        query = """
        SELECT 
            SUM(poe.QuantityReceivedToDate) as TotalReceived
        FROM PurchaseOrderEntry poe
        JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
        JOIN Item i ON poe.ItemID = i.ID
        WHERE i.ItemLookupCode = %s
        AND po.DateCreated >= %s
        AND po.DateCreated <= %s
        AND po.Status >= 2  -- Received or partially received
        """
        
        self.cursor.execute(query, (item_lookup_code, start_date, end_date))
        result = self.cursor.fetchone()
        
        if result and result['TotalReceived']:
            return float(result['TotalReceived'])
        return 0
    
    def find_item_by_upc(self, upc: str) -> str:
        """Find ItemLookupCode by UPC"""
        # First check our mapping
        if upc in self.upc_mapping:
            return self.upc_mapping[upc]
        
        # Try database
        query = """
        SELECT TOP 1
            i.ItemLookupCode
        FROM Item i
        LEFT JOIN Alias a ON i.ID = a.ItemID
        WHERE i.ItemLookupCode = %s
        OR a.Alias = %s
        OR i.ItemLookupCode = %s
        OR a.Alias = %s
        """
        
        # Try different UPC formats
        upc_formats = [
            upc,
            upc.lstrip('0'),
            '0' + upc if len(upc) == 11 else upc,
            upc[-12:] if len(upc) > 12 else upc
        ]
        
        for upc_format in upc_formats:
            self.cursor.execute(query, (upc_format, upc_format, upc_format, upc_format))
            result = self.cursor.fetchone()
            if result:
                # Cache the mapping
                self.upc_mapping[upc] = result['ItemLookupCode']
                return result['ItemLookupCode']
        
        return None
    
    def analyze_week(self, week: str, prev_week_inventory: Dict[str, float]) -> pd.DataFrame:
        """Analyze a single week's data"""
        results = []
        week_dir = os.path.join(self.csv_dir, week)
        
        # Load MSA data
        brands_file = os.path.join(week_dir, f"{week}_brands.csv")
        purchases_file = os.path.join(week_dir, f"{week}_purchases.csv")
        
        if not os.path.exists(brands_file):
            return pd.DataFrame()
        
        brands_df = pd.read_csv(brands_file)
        msa_purchases_df = pd.read_csv(purchases_file) if os.path.exists(purchases_file) else pd.DataFrame()
        
        # Get date range
        start_date, end_date = self.get_week_dates(week)
        
        print(f"\nAnalyzing week {week} ({start_date.date()} to {end_date.date()})")
        print(f"  Processing {len(brands_df)} SKUs...")
        
        current_week_inventory = {}
        
        for _, brand in brands_df.iterrows():
            sku = str(brand['distributor_sku']).strip()
            upc = str(brand['upc_code']).strip()
            description = str(brand['product_description']).strip()
            
            # Get MSA reported inventory
            msa_inventory = 0
            try:
                if str(brand['measure_code_1']) == '003':
                    msa_inventory = float(brand['measure_value_1']) if pd.notna(brand['measure_value_1']) else 0
            except:
                msa_inventory = 0
            
            # Find ItemLookupCode
            item_lookup_code = self.find_item_by_upc(upc) or self.find_item_by_upc(sku)
            
            # Get POS data
            pos_current_inventory = None
            pos_sales = 0
            pos_purchases = 0
            
            if item_lookup_code:
                pos_current_inventory = self.get_pos_inventory(item_lookup_code, end_date)
                pos_sales = self.get_pos_sales(item_lookup_code, start_date, end_date)
                pos_purchases = self.get_pos_purchases(item_lookup_code, start_date, end_date)
            
            # Get MSA sales from purchases file
            msa_sales = 0
            if not msa_purchases_df.empty:
                sku_sales = msa_purchases_df[msa_purchases_df['distributor_sku'] == sku]
                for _, sale in sku_sales.iterrows():
                    try:
                        qty = float(sale['measure_value_1']) if pd.notna(sale['measure_value_1']) else 0
                        msa_sales += qty
                    except:
                        pass
            
            # Calculate beginning inventory
            beginning_inventory = prev_week_inventory.get(sku, msa_inventory)
            
            # Calculate expected ending inventory
            calculated_inventory = beginning_inventory + pos_purchases - msa_sales
            
            # Calculate variances
            msa_variance = msa_inventory - calculated_inventory
            pos_variance = (pos_current_inventory - msa_inventory) if pos_current_inventory is not None else None
            sales_variance = pos_sales - msa_sales if item_lookup_code else None
            
            # Store current inventory for next week
            current_week_inventory[sku] = msa_inventory
            
            result = {
                'week': week,
                'sku': sku,
                'upc': upc,
                'item_lookup_code': item_lookup_code or 'NOT_FOUND',
                'description': description[:50],
                'beginning_inventory': beginning_inventory,
                'pos_purchases': pos_purchases,
                'pos_sales': pos_sales,
                'msa_sales': msa_sales,
                'sales_variance': sales_variance,
                'calculated_ending': calculated_inventory,
                'msa_reported': msa_inventory,
                'pos_current': pos_current_inventory,
                'msa_variance': msa_variance,
                'pos_variance': pos_variance
            }
            results.append(result)
        
        return pd.DataFrame(results), current_week_inventory
    
    def analyze_all_weeks(self):
        """Analyze all weeks in sequence"""
        all_results = []
        prev_week_inventory = {}
        
        for week in self.weeks:
            week_results, prev_week_inventory = self.analyze_week(week, prev_week_inventory)
            if not week_results.empty:
                all_results.append(week_results)
        
        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()
    
    def generate_report(self, results_df: pd.DataFrame):
        """Generate analysis report"""
        print("\n" + "="*80)
        print("MSA vs POS INVENTORY ANALYSIS REPORT")
        print("="*80)
        
        # Overall statistics
        total_records = len(results_df)
        matched_items = len(results_df[results_df['item_lookup_code'] != 'NOT_FOUND'])
        unmatched_items = total_records - matched_items
        
        print(f"\nTotal SKU-Week Records: {total_records}")
        print(f"Matched to POS: {matched_items} ({matched_items/total_records*100:.1f}%)")
        print(f"Not Found in POS: {unmatched_items} ({unmatched_items/total_records*100:.1f}%)")
        
        # For matched items
        matched_df = results_df[results_df['item_lookup_code'] != 'NOT_FOUND']
        
        if not matched_df.empty:
            print("\n" + "-"*50)
            print("MATCHED ITEMS ANALYSIS:")
            print("-"*50)
            
            # Sales comparison
            sales_comparison = matched_df[matched_df['sales_variance'].notna()]
            if not sales_comparison.empty:
                avg_sales_variance = sales_comparison['sales_variance'].mean()
                print(f"Average Sales Variance (POS - MSA): {avg_sales_variance:.2f}")
                
                # Items with significant sales variances
                large_variances = sales_comparison[abs(sales_comparison['sales_variance']) > 10]
                print(f"Items with sales variance > 10 units: {len(large_variances)}")
            
            # Inventory comparison
            inv_comparison = matched_df[matched_df['pos_variance'].notna()]
            if not inv_comparison.empty:
                avg_inv_variance = inv_comparison['pos_variance'].mean()
                print(f"Average Inventory Variance (POS - MSA): {avg_inv_variance:.2f}")
        
        # Top unmatched items by sales
        print("\n" + "-"*50)
        print("TOP UNMATCHED ITEMS (by MSA sales):")
        print("-"*50)
        unmatched_df = results_df[results_df['item_lookup_code'] == 'NOT_FOUND']
        if not unmatched_df.empty:
            top_unmatched = unmatched_df.nlargest(20, 'msa_sales')[['week', 'sku', 'upc', 'description', 'msa_sales', 'msa_reported']]
            print(top_unmatched.to_string(index=False))
        
        # Export detailed results
        output_file = os.path.join(os.path.dirname(self.csv_dir), 'msa_pos_inventory_comparison.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\nDetailed results exported to: {output_file}")
        
        # Save updated UPC mapping
        with open('upc_to_itemcode_mapping.json', 'w') as f:
            json.dump(self.upc_mapping, f, indent=2)
        print(f"Updated UPC mapping saved ({len(self.upc_mapping)} mappings)")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    csv_dir = "/Users/akbarchranya/georgiadashboard/MSA_CSV_Output"
    
    analyzer = MSAPOSInventoryAnalyzer(csv_dir)
    
    try:
        print("Analyzing MSA Data with POS Integration...")
        print("="*80)
        
        # Analyze all weeks
        results_df = analyzer.analyze_all_weeks()
        
        if not results_df.empty:
            # Generate report
            analyzer.generate_report(results_df)
        else:
            print("No data to analyze")
        
    finally:
        analyzer.close()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()