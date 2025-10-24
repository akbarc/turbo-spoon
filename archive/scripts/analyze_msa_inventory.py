#!/usr/bin/env python3
"""
MSA Inventory Analysis
Calculates ending inventory based on: Beginning Inventory + Purchases - Sales
Compares with MSA reported inventory to find variances
"""

import os
import csv
import pandas as pd
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple

class MSAInventoryAnalyzer:
    def __init__(self, csv_dir: str):
        self.csv_dir = csv_dir
        self.weeks = sorted([d for d in os.listdir(csv_dir) if os.path.isdir(os.path.join(csv_dir, d))])
        self.inventory_tracking = defaultdict(dict)  # {sku: {week: inventory}}
        self.sales_tracking = defaultdict(dict)  # {sku: {week: sales}}
        self.purchases_tracking = defaultdict(dict)  # {sku: {week: purchases}}
        
    def load_week_data(self, week: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load brands, purchases, and combined data for a week"""
        week_dir = os.path.join(self.csv_dir, week)
        
        # Load brands (contains inventory)
        brands_file = os.path.join(week_dir, f"{week}_brands.csv")
        brands_df = pd.read_csv(brands_file) if os.path.exists(brands_file) else pd.DataFrame()
        
        # Load purchases (contains sales data)
        purchases_file = os.path.join(week_dir, f"{week}_purchases.csv")
        purchases_df = pd.read_csv(purchases_file) if os.path.exists(purchases_file) else pd.DataFrame()
        
        # Load combined for easier analysis
        combined_file = os.path.join(week_dir, f"{week}_combined.csv")
        combined_df = pd.read_csv(combined_file) if os.path.exists(combined_file) else pd.DataFrame()
        
        return brands_df, purchases_df, combined_df
    
    def calculate_inventory_movements(self):
        """Calculate inventory movements across all weeks"""
        results = []
        
        for i, week in enumerate(self.weeks):
            print(f"\nProcessing week: {week}")
            brands_df, purchases_df, combined_df = self.load_week_data(week)
            
            if brands_df.empty:
                continue
            
            # Process each SKU in brands
            for _, brand in brands_df.iterrows():
                sku = str(brand['distributor_sku']).strip()
                upc = str(brand['upc_code']).strip()
                description = str(brand['product_description']).strip()
                
                # Get MSA reported inventory (measure_value_1 for measure_code_1 = 003)
                msa_inventory = 0
                try:
                    if str(brand['measure_code_1']) == '003':
                        msa_inventory = float(brand['measure_value_1']) if pd.notna(brand['measure_value_1']) else 0
                except:
                    msa_inventory = 0
                
                # Calculate sales for this SKU in this week
                week_sales = 0
                if not purchases_df.empty:
                    sku_sales = purchases_df[purchases_df['distributor_sku'] == sku]
                    for _, sale in sku_sales.iterrows():
                        try:
                            # measure_value_1 in purchases is quantity shipped
                            qty = float(sale['measure_value_1']) if pd.notna(sale['measure_value_1']) else 0
                            week_sales += qty
                        except:
                            pass
                
                # Get previous week's inventory
                prev_inventory = 0
                if i > 0:
                    prev_week = self.weeks[i-1]
                    if sku in self.inventory_tracking and prev_week in self.inventory_tracking[sku]:
                        prev_inventory = self.inventory_tracking[sku][prev_week]
                    else:
                        # Try to find from previous MSA file
                        prev_brands_df, _, _ = self.load_week_data(prev_week)
                        if not prev_brands_df.empty:
                            prev_sku_data = prev_brands_df[prev_brands_df['distributor_sku'] == sku]
                            if not prev_sku_data.empty:
                                try:
                                    prev_inventory = float(prev_sku_data.iloc[0]['measure_value_1']) if pd.notna(prev_sku_data.iloc[0]['measure_value_1']) else 0
                                except:
                                    prev_inventory = 0
                
                # For first week, use MSA inventory as beginning inventory
                if i == 0:
                    beginning_inventory = msa_inventory
                else:
                    beginning_inventory = prev_inventory
                
                # Calculate expected ending inventory
                # Ending = Beginning + Purchases - Sales
                # For now, we assume no purchases (would need separate purchase orders data)
                purchases = 0  # This would come from purchase orders/receiving data
                
                calculated_inventory = beginning_inventory + purchases - week_sales
                
                # Calculate variance
                variance = msa_inventory - calculated_inventory
                variance_pct = (variance / msa_inventory * 100) if msa_inventory != 0 else 0
                
                # Store for next week
                self.inventory_tracking[sku][week] = msa_inventory
                self.sales_tracking[sku][week] = week_sales
                
                # Record results
                result = {
                    'week': week,
                    'sku': sku,
                    'upc': upc,
                    'description': description[:50],  # Truncate for display
                    'beginning_inventory': beginning_inventory,
                    'purchases': purchases,
                    'sales': week_sales,
                    'calculated_ending': calculated_inventory,
                    'msa_reported': msa_inventory,
                    'variance': variance,
                    'variance_pct': variance_pct
                }
                results.append(result)
        
        return pd.DataFrame(results)
    
    def analyze_variances(self, results_df: pd.DataFrame):
        """Analyze and summarize variances"""
        print("\n" + "="*80)
        print("INVENTORY VARIANCE ANALYSIS")
        print("="*80)
        
        # Overall statistics
        total_records = len(results_df)
        records_with_variance = len(results_df[results_df['variance'] != 0])
        
        print(f"\nTotal SKU-Week Records: {total_records}")
        print(f"Records with Variance: {records_with_variance} ({records_with_variance/total_records*100:.1f}%)")
        
        # Variance by week
        print("\n" + "-"*50)
        print("VARIANCE BY WEEK:")
        print("-"*50)
        for week in results_df['week'].unique():
            week_data = results_df[results_df['week'] == week]
            week_variance = week_data['variance'].abs().sum()
            week_items = len(week_data[week_data['variance'] != 0])
            print(f"{week}: {week_items} items with variance, Total absolute variance: {week_variance:.0f}")
        
        # Top variances
        print("\n" + "-"*50)
        print("TOP 20 VARIANCES (by absolute value):")
        print("-"*50)
        top_variances = results_df.nlargest(20, 'variance', keep='all')[['week', 'sku', 'description', 'sales', 'msa_reported', 'calculated_ending', 'variance']]
        print(top_variances.to_string(index=False))
        
        # Items with consistent variances
        print("\n" + "-"*50)
        print("ITEMS WITH CONSISTENT VARIANCES ACROSS WEEKS:")
        print("-"*50)
        sku_variance_counts = results_df[results_df['variance'] != 0].groupby('sku').agg({
            'variance': ['count', 'mean', 'std'],
            'description': 'first'
        })
        
        # Items that have variances in multiple weeks
        consistent_issues = sku_variance_counts[sku_variance_counts[('variance', 'count')] >= 3]
        if not consistent_issues.empty:
            consistent_issues.columns = ['weeks_with_variance', 'avg_variance', 'std_variance', 'description']
            print(consistent_issues.head(20).to_string())
        
        return results_df
    
    def export_results(self, results_df: pd.DataFrame):
        """Export results to CSV"""
        output_file = os.path.join(os.path.dirname(self.csv_dir), 'msa_inventory_analysis.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\nDetailed results exported to: {output_file}")
        
        # Create summary by SKU
        summary_df = results_df.groupby('sku').agg({
            'description': 'first',
            'upc': 'first',
            'sales': 'sum',
            'variance': 'mean',
            'variance_pct': 'mean'
        }).round(2)
        
        summary_file = os.path.join(os.path.dirname(self.csv_dir), 'msa_inventory_summary.csv')
        summary_df.to_csv(summary_file)
        print(f"Summary by SKU exported to: {summary_file}")


def main():
    csv_dir = "/Users/akbarchranya/georgiadashboard/MSA_CSV_Output"
    
    analyzer = MSAInventoryAnalyzer(csv_dir)
    
    print("Analyzing MSA Inventory Data...")
    print("Formula: Ending Inventory = Beginning Inventory + Purchases - Sales")
    print("Note: Purchase data not available, so formula is: Ending = Beginning - Sales")
    
    # Calculate inventory movements
    results_df = analyzer.calculate_inventory_movements()
    
    # Analyze variances
    results_df = analyzer.analyze_variances(results_df)
    
    # Export results
    analyzer.export_results(results_df)
    
    # Check for patterns
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    
    # Items that never sold but have inventory changes
    no_sales_changes = results_df[(results_df['sales'] == 0) & (results_df['variance'] != 0)]
    if not no_sales_changes.empty:
        print(f"\n{len(no_sales_changes)} items have inventory changes without sales")
        print("This suggests:")
        print("  - Purchases/receiving not captured in this analysis")
        print("  - Inventory adjustments")
        print("  - Returns not properly recorded")
    
    # Items with negative calculated inventory
    negative_inventory = results_df[results_df['calculated_ending'] < 0]
    if not negative_inventory.empty:
        print(f"\n{len(negative_inventory)} items would have negative inventory")
        print("This suggests:")
        print("  - Missing purchase/receiving data")
        print("  - Beginning inventory understated")
        print("  - Sales overstated")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()