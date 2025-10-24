#!/usr/bin/env python3
"""
Direct Purchase Opportunity Analysis
Identifies best-selling products that could be purchased directly from manufacturers
Excludes major tobacco companies (RJR, Altria/PM) as per user requirements
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json

def analyze_direct_purchase_opportunities():
    """Find products with high sales volume that could benefit from direct purchasing."""
    
    with SQLServerConnection() as db:
        print("=" * 100)
        print("DIRECT MANUFACTURER PURCHASE OPPORTUNITY ANALYSIS")
        print("=" * 100)
        
        # Get top selling products with vendor/supplier info
        query_products = """
        WITH ProductSales AS (
            SELECT 
                i.ID as ItemID,
                i.ItemLookupCode,
                i.Description,
                i.DepartmentID,
                i.CategoryID,
                cat.Name as CategoryName,
                i.SupplierID,
                s.SupplierName,
                s.ContactName,
                -- Sales metrics from last 6 months
                SUM(te.Quantity) as TotalUnits,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                SUM(te.Cost * te.Quantity) as TotalCost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                AVG(te.Price) as AvgSellingPrice,
                AVG(te.Cost) as AvgCost,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                MAX(t.Time) as LastSoldDate
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            LEFT JOIN Supplier s ON i.SupplierID = s.ID
            WHERE t.Time >= DATEADD(MONTH, -6, GETDATE())
            GROUP BY i.ID, i.ItemLookupCode, i.Description, i.DepartmentID, 
                     i.CategoryID, cat.Name, i.SupplierID, s.SupplierName, s.ContactName
        )
        SELECT TOP 200
            ItemLookupCode,
            Description,
            CategoryName,
            SupplierName,
            TotalUnits,
            TotalRevenue,
            TotalCost,
            GrossProfit,
            CASE 
                WHEN TotalRevenue > 0 
                THEN (GrossProfit / TotalRevenue) * 100 
                ELSE 0 
            END as GPMargin,
            AvgSellingPrice,
            AvgCost,
            TransactionCount,
            UniqueCustomers,
            LastSoldDate
        FROM ProductSales
        WHERE TotalRevenue > 5000  -- Focus on products with meaningful revenue
        ORDER BY TotalRevenue DESC
        """
        
        df_products = db.execute_query(query_products, description="Get top products with supplier info")
        
        # Identify products likely NOT direct from manufacturer
        # These are typically from distributors/wholesalers
        distributor_keywords = ['DISTRIBUTOR', 'WHOLESALE', 'SUPPLY', 'DISTRIBUTION', 
                              'TRADING', 'IMPORTS', 'SALES', 'CORP', 'INC', 'LLC']
        
        # Exclude RJR and Altria/PM products
        excluded_manufacturers = ['RJR', 'R.J. REYNOLDS', 'REYNOLDS', 'ALTRIA', 'PHILIP MORRIS', 
                                'PHILLIP MORRIS', 'PM USA', 'MARLBORO', 'CAMEL', 'NEWPORT',
                                'AMERICAN SPIRIT', 'WINSTON', 'SALEM']
        
        def is_distributor(supplier_name):
            if pd.isna(supplier_name):
                return True
            supplier_upper = str(supplier_name).upper()
            return any(keyword in supplier_upper for keyword in distributor_keywords)
        
        def is_excluded_manufacturer(description, category):
            if pd.isna(description) and pd.isna(category):
                return False
            desc_upper = str(description).upper() if not pd.isna(description) else ""
            cat_upper = str(category).upper() if not pd.isna(category) else ""
            combined = desc_upper + " " + cat_upper
            return any(brand in combined for brand in excluded_manufacturers)
        
        # Filter for opportunities
        df_products['IsDistributor'] = df_products['SupplierName'].apply(is_distributor)
        df_products['IsExcluded'] = df_products.apply(lambda x: is_excluded_manufacturer(x['Description'], x['CategoryName']), axis=1)
        
        # Focus on non-cigarette tobacco products and other high-volume categories
        opportunity_categories = ['CIGARS', 'ELECTRONIC CIG', 'ECIG - PODS', 'KRATOM', 
                                'VITAMINS', 'DRINKS', 'NICOTINE POUCHES', 'CBD/HEMP',
                                'BLUNT WRAP', 'CIG ROLLING PAPER', 'LIGHTERS']
        
        df_opportunities = df_products[
            (df_products['IsDistributor'] == True) & 
            (df_products['IsExcluded'] == False) &
            (df_products['CategoryName'].isin(opportunity_categories))
        ].copy()
        
        # Calculate potential savings (conservative 10-20% estimate)
        df_opportunities['PotentialSavingsLow'] = df_opportunities['TotalCost'] * 0.10
        df_opportunities['PotentialSavingsHigh'] = df_opportunities['TotalCost'] * 0.20
        
        # Group by brand/manufacturer patterns
        print("\n" + "=" * 100)
        print("TOP DIRECT PURCHASE OPPORTUNITIES (6-MONTH SALES)")
        print("=" * 100)
        
        # Identify brand patterns
        brand_patterns = {
            'SWISHER': 'Swisher International',
            'BACKWOODS': 'ITG Brands',
            'DUTCH': 'ITG Brands', 
            'GAME': 'Swedish Match',
            'WHITE OWL': 'Swedish Match',
            'ZYN': 'Swedish Match',
            'VUSE': 'Reynolds (Excluded)',
            'JUUL': 'JUUL Labs',
            'HYDE': 'Hyde',
            'ELFBAR': 'Elf Bar',
            'BREEZE': 'Breeze Smoke',
            'GEEK BAR': 'Geek Bar',
            'MONSTER': 'Monster Beverage',
            'RED BULL': 'Red Bull',
            'PRIME': 'Prime Hydration',
            'BODY ARMOR': 'Coca-Cola',
            '5-HOUR': '5-Hour Energy',
            'VIVA ZEN': 'Viva Zen',
            'OPMS': 'OPMS Kratom',
            'MIT45': 'MIT45',
            'BIC': 'BIC Corporation',
            'CLIPPER': 'Clipper'
        }
        
        def identify_brand(description):
            if pd.isna(description):
                return 'Unknown'
            desc_upper = str(description).upper()
            for pattern, brand in brand_patterns.items():
                if pattern in desc_upper:
                    return brand
            return 'Other'
        
        df_opportunities['Brand'] = df_opportunities['Description'].apply(identify_brand)
        
        # Aggregate by brand
        brand_summary = df_opportunities.groupby('Brand').agg({
            'TotalRevenue': 'sum',
            'TotalCost': 'sum',
            'GrossProfit': 'sum',
            'TotalUnits': 'sum',
            'PotentialSavingsLow': 'sum',
            'PotentialSavingsHigh': 'sum',
            'Description': 'count'
        }).rename(columns={'Description': 'ProductCount'})
        
        brand_summary['GPMargin'] = (brand_summary['GrossProfit'] / brand_summary['TotalRevenue'] * 100).round(1)
        brand_summary = brand_summary.sort_values('TotalRevenue', ascending=False)
        
        print("\nBY BRAND/MANUFACTURER OPPORTUNITY:")
        print("-" * 100)
        print(f"{'Brand/Manufacturer':<25} {'Revenue':>12} {'Cost':>12} {'GP%':>6} {'Est. Savings':>20} {'# SKUs':>8}")
        print("-" * 100)
        
        for brand, row in brand_summary.head(15).iterrows():
            if brand not in ['Unknown', 'Other', 'Reynolds (Excluded)']:
                savings_range = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
                print(f"{brand:<25} ${row['TotalRevenue']:>11,.0f} ${row['TotalCost']:>11,.0f} {row['GPMargin']:>5.1f}% {savings_range:>20} {row['ProductCount']:>8.0f}")
        
        # Top individual products
        print("\n" + "=" * 100)
        print("TOP 20 INDIVIDUAL PRODUCTS TO CONSIDER")
        print("=" * 100)
        print(f"{'Product':<40} {'Category':<20} {'Revenue':>12} {'Units':>10} {'Savings':>15}")
        print("-" * 100)
        
        top_products = df_opportunities.nlargest(20, 'TotalRevenue')
        for _, row in top_products.iterrows():
            savings_est = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
            print(f"{row['Description'][:40]:<40} {row['CategoryName'][:20]:<20} ${row['TotalRevenue']:>11,.0f} {row['TotalUnits']:>10,.0f} {savings_est:>15}")
        
        # Category summary
        print("\n" + "=" * 100)
        print("OPPORTUNITY BY CATEGORY")
        print("=" * 100)
        
        category_summary = df_opportunities.groupby('CategoryName').agg({
            'TotalRevenue': 'sum',
            'TotalCost': 'sum',
            'PotentialSavingsLow': 'sum',
            'PotentialSavingsHigh': 'sum',
            'Description': 'count'
        }).rename(columns={'Description': 'ProductCount'})
        
        category_summary = category_summary.sort_values('TotalRevenue', ascending=False)
        
        print(f"{'Category':<25} {'6-Month Revenue':>15} {'Est. Annual Savings':>25} {'# Products':>12}")
        print("-" * 80)
        
        for category, row in category_summary.iterrows():
            annual_savings_low = row['PotentialSavingsLow'] * 2  # Extrapolate to annual
            annual_savings_high = row['PotentialSavingsHigh'] * 2
            savings_range = f"${annual_savings_low:,.0f}-${annual_savings_high:,.0f}"
            print(f"{category:<25} ${row['TotalRevenue']:>14,.0f} {savings_range:>25} {row['ProductCount']:>12.0f}")
        
        # Recommendations
        print("\n" + "=" * 100)
        print("KEY RECOMMENDATIONS")
        print("=" * 100)
        
        total_savings_low = df_opportunities['PotentialSavingsLow'].sum() * 2  # Annual
        total_savings_high = df_opportunities['PotentialSavingsHigh'].sum() * 2
        
        print(f"\n1. TOTAL ANNUAL SAVINGS OPPORTUNITY: ${total_savings_low:,.0f} - ${total_savings_high:,.0f}")
        
        print("\n2. TOP PRIORITY BRANDS TO APPROACH:")
        priority_brands = brand_summary[~brand_summary.index.isin(['Unknown', 'Other', 'Reynolds (Excluded)'])].head(5)
        for i, (brand, row) in enumerate(priority_brands.iterrows(), 1):
            print(f"   {i}. {brand}: ${row['TotalRevenue']*2:,.0f} annual revenue, ${row['PotentialSavingsLow']*2:,.0f}-${row['PotentialSavingsHigh']*2:,.0f} potential savings")
        
        print("\n3. QUICK WINS (High volume, easy to switch):")
        quick_wins = df_opportunities[df_opportunities['TotalUnits'] > 5000].nlargest(5, 'PotentialSavingsHigh')
        for i, (_, row) in enumerate(quick_wins.iterrows(), 1):
            print(f"   {i}. {row['Description'][:40]}: {row['TotalUnits']:,.0f} units, ${row['PotentialSavingsHigh']*2:,.0f} annual savings")
        
        # Export results
        results = {
            'analysis_date': datetime.now().isoformat(),
            'period': '6 months',
            'total_annual_savings_opportunity': {
                'low': float(total_savings_low),
                'high': float(total_savings_high)
            },
            'brand_opportunities': brand_summary.head(10).to_dict('index'),
            'top_products': top_products[['Description', 'CategoryName', 'TotalRevenue', 
                                         'TotalUnits', 'PotentialSavingsLow', 'PotentialSavingsHigh']].to_dict('records'),
            'category_summary': category_summary.to_dict('index')
        }
        
        with open('direct_purchase_opportunities.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save detailed Excel report
        with pd.ExcelWriter('direct_purchase_opportunities.xlsx', engine='openpyxl') as writer:
            df_opportunities.to_excel(writer, sheet_name='All Opportunities', index=False)
            brand_summary.to_excel(writer, sheet_name='By Brand')
            category_summary.to_excel(writer, sheet_name='By Category')
            top_products.to_excel(writer, sheet_name='Top Products', index=False)
        
        print("\n✅ Analysis complete!")
        print("📊 Files saved: direct_purchase_opportunities.json and .xlsx")
        print("=" * 100)

if __name__ == "__main__":
    analyze_direct_purchase_opportunities()