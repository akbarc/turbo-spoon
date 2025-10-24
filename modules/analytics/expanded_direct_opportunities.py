#!/usr/bin/env python3
"""
Expanded Direct Purchase Opportunity Analysis
Comprehensive analysis including all product categories
"""

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json
import re

def analyze_expanded_opportunities():
    """Comprehensive analysis of all direct purchase opportunities."""
    
    with SQLServerConnection() as db:
        print("=" * 120)
        print("COMPREHENSIVE DIRECT PURCHASE OPPORTUNITY ANALYSIS")
        print("=" * 120)
        
        # Get ALL products with significant sales, not just top categories
        query_all_products = """
        WITH ProductDetails AS (
            SELECT 
                i.ID as ItemID,
                i.ItemLookupCode,
                i.Description,
                i.DepartmentID,
                i.CategoryID,
                ISNULL(cat.Name, 'UNCATEGORIZED') as CategoryName,
                i.SupplierID,
                ISNULL(s.SupplierName, 'NO SUPPLIER') as SupplierName,
                s.ContactName,
                s.PhoneNumber as SupplierPhone,
                -- 12 month metrics for better picture
                SUM(te.Quantity) as TotalUnits,
                SUM(te.Price * te.Quantity) as TotalRevenue,
                SUM(te.Cost * te.Quantity) as TotalCost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                AVG(te.Price) as AvgSellingPrice,
                AVG(te.Cost) as AvgCost,
                COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                COUNT(DISTINCT CONVERT(varchar(7), t.Time, 120)) as ActiveMonths,
                MAX(t.Time) as LastSoldDate,
                MIN(t.Time) as FirstSoldDate
            FROM [dbo].[Transaction] t
            JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            LEFT JOIN Supplier s ON i.SupplierID = s.ID
            WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())
                AND te.Price > 0  -- Exclude voids/returns
            GROUP BY i.ID, i.ItemLookupCode, i.Description, i.DepartmentID, 
                     i.CategoryID, cat.Name, i.SupplierID, s.SupplierName, 
                     s.ContactName, s.PhoneNumber
        )
        SELECT *
        FROM ProductDetails
        WHERE TotalRevenue > 2000  -- Lower threshold to catch more opportunities
        ORDER BY TotalRevenue DESC
        """
        
        df_all = db.execute_query(query_all_products, description="Get all products with sales")
        
        print(f"\nTotal products analyzed: {len(df_all):,}")
        print(f"Total revenue (12 months): ${df_all['TotalRevenue'].sum():,.2f}")
        
        # Expanded manufacturer/brand mapping
        brand_mapping = {
            # Tobacco/Nicotine
            'SWISHER': 'Swisher International',
            'BACKWOODS': 'ITG Brands',
            'DUTCH': 'ITG Brands',
            'GAME': 'Swedish Match',
            'WHITE OWL': 'Swedish Match',
            'ZYN': 'Swedish Match',
            'BLACK & MILD': 'John Middleton Co',
            'BLACK&MILD': 'John Middleton Co',
            'BLK & MLD': 'John Middleton Co',
            'ACID': 'Drew Estate',
            'ROMEO': 'Altadis USA',
            'MONTECRISTO': 'Altadis USA',
            'OPTIMO': 'Optimo Cigars',
            'GARCIA': 'Garcia y Vega',
            
            # Vaping
            'JUUL': 'JUUL Labs',
            'VUSE': 'Reynolds (Excluded)',
            'HYDE': 'Hyde Vapes',
            'ELFBAR': 'Elf Bar',
            'ELF BAR': 'Elf Bar',
            'BREEZE': 'Breeze Smoke',
            'GEEK BAR': 'Geek Bar',
            'GEEK': 'Geek Bar',
            'RAZ': 'RAZ Vape',
            'LOST MARY': 'Lost Mary',
            'FLUM': 'Flum Float',
            'TYSON': 'Mike Tyson Vapes',
            'DEATH ROW': 'Death Row Vapes',
            'FUME': 'Fume Vapes',
            'KANGVAPE': 'KangVape',
            'PUFF BAR': 'Puff Bar',
            
            # Energy/Drinks
            'MONSTER': 'Monster Beverage Corp',
            'RED BULL': 'Red Bull GmbH',
            'REDBULL': 'Red Bull GmbH',
            'PRIME': 'Prime Hydration LLC',
            'BODY ARMOR': 'Coca-Cola Company',
            'BODYARMOR': 'Coca-Cola Company',
            '5-HOUR': 'Living Essentials LLC',
            '5 HOUR': 'Living Essentials LLC',
            'CELSIUS': 'Celsius Holdings',
            'BANG': 'Vital Pharmaceuticals',
            'REIGN': 'Monster Beverage Corp',
            'C4': 'Nutrabolt',
            'GHOST': 'Ghost Lifestyle',
            'ALANI': 'Alani Nu',
            'GATORADE': 'PepsiCo',
            'POWERADE': 'Coca-Cola Company',
            'VITAMIN WATER': 'Coca-Cola Company',
            'SMART WATER': 'Coca-Cola Company',
            'FIJI': 'The Wonderful Company',
            'CORE': 'Core Nutrition LLC',
            'ESSENTIA': 'Essentia Water',
            
            # Kratom/CBD/Hemp
            'OPMS': 'OPMS Kratom',
            'MIT45': 'MIT45 Kratom',
            'MIT 45': 'MIT45 Kratom',
            'VIVA ZEN': 'Vivazen Botanicals',
            'VIVAZEN': 'Vivazen Botanicals',
            'K SHOT': 'K Shot Kratom',
            'KSHOT': 'K Shot Kratom',
            'REMARKABLE HERBS': 'Remarkable Herbs',
            'WHOLE HERBS': 'Whole Herbs Kratom',
            'HUSH': 'Hush Kratom',
            'BUMBLE BEE': 'Bumble Bee Kratom',
            'DIAMOND': 'Diamond CBD',
            'DELTA': 'Various Delta-8 Brands',
            '3CHI': '3Chi',
            'CAKE': 'Cake Delta-8',
            
            # Accessories/Supplies
            'BIC': 'BIC Corporation',
            'CLIPPER': 'Clipper Lighters',
            'ZIPPO': 'Zippo Manufacturing',
            'RAW': 'RAW Rolling Papers',
            'ZIG ZAG': 'Zig-Zag Papers',
            'ZIGZAG': 'Zig-Zag Papers',
            'JOB': 'JOB Rolling Papers',
            'OCB': 'OCB Papers',
            'ELEMENTS': 'Elements Papers',
            'JUICY': 'Juicy Jay\'s',
            
            # Snacks/Candy
            'HARIBO': 'Haribo GmbH',
            'SOUR PATCH': 'Mondelez International',
            'SKITTLES': 'Mars Wrigley',
            'STARBURST': 'Mars Wrigley',
            'M&M': 'Mars Wrigley',
            'REESE': 'Hershey Company',
            'HERSHEY': 'Hershey Company',
            'KIT KAT': 'Hershey Company',
            'SNICKERS': 'Mars Wrigley',
            'TWIX': 'Mars Wrigley',
            'MILKY WAY': 'Mars Wrigley',
            'AIRHEADS': 'Perfetti Van Melle',
            'MENTOS': 'Perfetti Van Melle',
            'TROLLI': 'Ferrara Candy',
            'LAFFY TAFFY': 'Ferrara Candy',
            'NERDS': 'Ferrara Candy',
            'SWEDISH FISH': 'Mondelez International',
            'MIKE AND IKE': 'Just Born',
            'HOT TAMALES': 'Just Born',
            
            # Other
            'TYLENOL': 'Johnson & Johnson',
            'ADVIL': 'Pfizer',
            'EXCEDRIN': 'GlaxoSmithKline',
            'TUMS': 'GlaxoSmithKline',
            'PEPTO': 'Procter & Gamble'
        }
        
        def identify_manufacturer(description, supplier_name):
            if pd.isna(description):
                return 'Unknown'
            desc_upper = str(description).upper()
            supp_upper = str(supplier_name).upper() if not pd.isna(supplier_name) else ""
            
            for pattern, manufacturer in brand_mapping.items():
                if pattern in desc_upper or pattern in supp_upper:
                    return manufacturer
            return 'Independent/Other'
        
        # Apply manufacturer identification
        df_all['Manufacturer'] = df_all.apply(lambda x: identify_manufacturer(x['Description'], x['SupplierName']), axis=1)
        
        # Identify distributor vs direct relationships
        distributor_indicators = ['DISTRIBUTOR', 'WHOLESALE', 'SUPPLY', 'DISTRIBUTION', 
                                'TRADING', 'IMPORTS', 'SALES CORP', 'SALES INC', 
                                'GROCERY', 'FOODS', 'BEVERAGE']
        
        def is_likely_distributor(supplier_name):
            if pd.isna(supplier_name) or supplier_name == 'NO SUPPLIER':
                return True
            supp_upper = str(supplier_name).upper()
            return any(indicator in supp_upper for indicator in distributor_indicators)
        
        df_all['ViaDistributor'] = df_all['SupplierName'].apply(is_likely_distributor)
        
        # Filter for opportunities (via distributor, not excluded manufacturers)
        excluded = ['Reynolds (Excluded)', 'Unknown']
        df_opportunities = df_all[
            (df_all['ViaDistributor'] == True) & 
            (~df_all['Manufacturer'].isin(excluded))
        ].copy()
        
        # Calculate savings potential (10-25% based on category)
        def calculate_savings_pct(category):
            high_margin_categories = ['CIGARS', 'CBD/HEMP', 'KRATOM', 'VITAMINS']
            medium_margin_categories = ['ELECTRONIC CIG', 'ECIG - PODS', 'DRINKS', 'CANDYS']
            
            if category in high_margin_categories:
                return (0.15, 0.25)  # 15-25%
            elif category in medium_margin_categories:
                return (0.10, 0.20)  # 10-20%
            else:
                return (0.08, 0.15)  # 8-15%
        
        df_opportunities['SavingsRates'] = df_opportunities['CategoryName'].apply(calculate_savings_pct)
        df_opportunities['PotentialSavingsLow'] = df_opportunities.apply(lambda x: x['TotalCost'] * x['SavingsRates'][0], axis=1)
        df_opportunities['PotentialSavingsHigh'] = df_opportunities.apply(lambda x: x['TotalCost'] * x['SavingsRates'][1], axis=1)
        
        # Aggregate by manufacturer
        print("\n" + "=" * 120)
        print("TOP 30 MANUFACTURER OPPORTUNITIES (12-MONTH DATA)")
        print("=" * 120)
        
        manufacturer_summary = df_opportunities.groupby('Manufacturer').agg({
            'TotalRevenue': 'sum',
            'TotalCost': 'sum',
            'GrossProfit': 'sum',
            'TotalUnits': 'sum',
            'PotentialSavingsLow': 'sum',
            'PotentialSavingsHigh': 'sum',
            'Description': 'count',
            'UniqueCustomers': 'mean'
        }).rename(columns={'Description': 'SKUCount', 'UniqueCustomers': 'AvgCustomersPerSKU'})
        
        manufacturer_summary['GPMargin'] = (manufacturer_summary['GrossProfit'] / manufacturer_summary['TotalRevenue'] * 100).round(1)
        manufacturer_summary = manufacturer_summary.sort_values('TotalRevenue', ascending=False)
        
        print(f"\n{'Manufacturer':<30} {'Annual Revenue':>14} {'Cost':>12} {'GP%':>6} {'Savings Range':>25} {'SKUs':>6} {'Avg Cust':>8}")
        print("-" * 120)
        
        for manufacturer, row in manufacturer_summary.head(30).iterrows():
            if manufacturer != 'Independent/Other':
                savings_range = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
                print(f"{manufacturer[:30]:<30} ${row['TotalRevenue']:>13,.0f} ${row['TotalCost']:>11,.0f} {row['GPMargin']:>5.1f}% {savings_range:>25} {row['SKUCount']:>6.0f} {row['AvgCustomersPerSKU']:>8.0f}")
        
        # New opportunities not in previous report
        print("\n" + "=" * 120)
        print("ADDITIONAL HIGH-VALUE OPPORTUNITIES NOT PREVIOUSLY IDENTIFIED")
        print("=" * 120)
        
        new_manufacturers = ['Monster Beverage Corp', 'Living Essentials LLC', 'John Middleton Co',
                           'Vivazen Botanicals', 'MIT45 Kratom', 'K Shot Kratom', 'Drew Estate',
                           'Mars Wrigley', 'Hershey Company', 'Mondelez International',
                           'RAW Rolling Papers', 'Zig-Zag Papers', 'Ferrara Candy']
        
        new_opps = manufacturer_summary[manufacturer_summary.index.isin(new_manufacturers)]
        
        print(f"\n{'Manufacturer':<30} {'Products':<40} {'Annual Rev':>12} {'Savings':>20}")
        print("-" * 105)
        
        for manufacturer in new_manufacturers:
            if manufacturer in manufacturer_summary.index:
                row = manufacturer_summary.loc[manufacturer]
                # Get top products for this manufacturer
                top_products = df_opportunities[df_opportunities['Manufacturer'] == manufacturer].nlargest(3, 'TotalRevenue')
                product_names = ', '.join([p[:30] for p in top_products['Description'].head(2)])
                savings = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
                print(f"{manufacturer[:30]:<30} {product_names[:40]:<40} ${row['TotalRevenue']:>11,.0f} {savings:>20}")
        
        # Category breakdown with more detail
        print("\n" + "=" * 120)
        print("COMPLETE CATEGORY OPPORTUNITY BREAKDOWN")
        print("=" * 120)
        
        category_detail = df_opportunities.groupby('CategoryName').agg({
            'TotalRevenue': 'sum',
            'TotalCost': 'sum',
            'PotentialSavingsLow': 'sum',
            'PotentialSavingsHigh': 'sum',
            'Description': 'count',
            'TotalUnits': 'sum',
            'Manufacturer': lambda x: len(x.unique())
        }).rename(columns={'Description': 'ProductCount', 'Manufacturer': 'ManufacturerCount'})
        
        category_detail = category_detail.sort_values('TotalRevenue', ascending=False)
        
        print(f"\n{'Category':<25} {'Annual Revenue':>14} {'Annual Savings':>22} {'Products':>10} {'Brands':>8} {'Units':>12}")
        print("-" * 95)
        
        for category, row in category_detail.head(20).iterrows():
            savings_range = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
            print(f"{category[:25]:<25} ${row['TotalRevenue']:>13,.0f} {savings_range:>22} {row['ProductCount']:>10.0f} {row['ManufacturerCount']:>8.0f} {row['TotalUnits']:>12,.0f}")
        
        # High-velocity items perfect for direct relationships
        print("\n" + "=" * 120)
        print("HIGH-VELOCITY ITEMS (>1000 units/month)")
        print("=" * 120)
        
        df_opportunities['MonthlyUnits'] = df_opportunities['TotalUnits'] / df_opportunities['ActiveMonths']
        high_velocity = df_opportunities[df_opportunities['MonthlyUnits'] > 1000].sort_values('TotalRevenue', ascending=False)
        
        print(f"\n{'Product':<45} {'Manufacturer':<25} {'Monthly Units':>13} {'Annual Rev':>12} {'Savings':>18}")
        print("-" * 115)
        
        for _, row in high_velocity.head(15).iterrows():
            savings = f"${row['PotentialSavingsLow']:,.0f}-${row['PotentialSavingsHigh']:,.0f}"
            print(f"{row['Description'][:45]:<45} {row['Manufacturer'][:25]:<25} {row['MonthlyUnits']:>13,.0f} ${row['TotalRevenue']:>11,.0f} {savings:>18}")
        
        # Summary statistics
        print("\n" + "=" * 120)
        print("EXECUTIVE SUMMARY")
        print("=" * 120)
        
        total_opportunity_revenue = df_opportunities['TotalRevenue'].sum()
        total_savings_low = df_opportunities['PotentialSavingsLow'].sum()
        total_savings_high = df_opportunities['PotentialSavingsHigh'].sum()
        
        print(f"\n📊 TOTAL OPPORTUNITY METRICS:")
        print(f"   • Products identified: {len(df_opportunities):,}")
        print(f"   • Annual revenue at risk: ${total_opportunity_revenue:,.0f}")
        print(f"   • Potential annual savings: ${total_savings_low:,.0f} - ${total_savings_high:,.0f}")
        print(f"   • Average savings percentage: {(total_savings_low/df_opportunities['TotalCost'].sum()*100):.1f}% - {(total_savings_high/df_opportunities['TotalCost'].sum()*100):.1f}%")
        print(f"   • Unique manufacturers: {df_opportunities['Manufacturer'].nunique()}")
        
        print(f"\n🎯 TOP 10 IMMEDIATE ACTION ITEMS:")
        top_10_manufacturers = manufacturer_summary.head(10)
        for i, (manufacturer, row) in enumerate(top_10_manufacturers.iterrows(), 1):
            if manufacturer != 'Independent/Other':
                print(f"   {i:2}. {manufacturer}: ${row['TotalRevenue']:,.0f} revenue, ${row['PotentialSavingsHigh']:,.0f} max savings")
        
        # Export comprehensive results
        with pd.ExcelWriter('comprehensive_direct_opportunities.xlsx', engine='openpyxl') as writer:
            manufacturer_summary.to_excel(writer, sheet_name='By Manufacturer')
            category_detail.to_excel(writer, sheet_name='By Category')
            high_velocity.to_excel(writer, sheet_name='High Velocity Items', index=False)
            df_opportunities.nlargest(100, 'TotalRevenue').to_excel(writer, sheet_name='Top 100 Products', index=False)
        
        print("\n✅ Analysis complete! Files saved: comprehensive_direct_opportunities.xlsx")
        print("=" * 120)

if __name__ == "__main__":
    analyze_expanded_opportunities()