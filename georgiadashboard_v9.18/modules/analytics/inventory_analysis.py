#!/usr/bin/env python3

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_inventory_health():
    """Comprehensive inventory analysis to identify dead stock, low stock, and overstock"""
    
    end_date = datetime.now()
    start_date_90d = end_date - timedelta(days=90)
    start_date_30d = end_date - timedelta(days=30)
    start_date_7d = end_date - timedelta(days=7)
    
    logger.info("Starting comprehensive inventory analysis...")
    
    # Main inventory analysis query
    inventory_query = f"""
    WITH CurrentInventory AS (
        SELECT 
            i.ID as ItemID,
            i.ItemLookupCode as SKU,
            i.Description,
            c.Name as Category,
            i.Quantity as CurrentStock,
            i.Cost,
            i.Price,
            i.ReorderPoint,
            i.RestockLevel,
            i.Quantity * i.Cost as InventoryValue,
            i.LastSold,
            i.LastReceived,
            DATEDIFF(day, i.LastSold, GETDATE()) as DaysSinceLastSold,
            DATEDIFF(day, i.LastReceived, GETDATE()) as DaysSinceLastReceived
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE i.Quantity != 0 OR i.LastSold IS NOT NULL
    ),
    Sales90Days AS (
        SELECT 
            te.ItemID,
            SUM(te.Quantity) as Units90Days,
            COUNT(DISTINCT t.TransactionNumber) as Trans90Days,
            MAX(t.[Time]) as LastSaleDate
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.[Time] >= '{start_date_90d.strftime('%Y-%m-%d')}'
            AND te.Quantity > 0
        GROUP BY te.ItemID
    ),
    Sales30Days AS (
        SELECT 
            te.ItemID,
            SUM(te.Quantity) as Units30Days,
            COUNT(DISTINCT t.TransactionNumber) as Trans30Days
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.[Time] >= '{start_date_30d.strftime('%Y-%m-%d')}'
            AND te.Quantity > 0
        GROUP BY te.ItemID
    ),
    Sales7Days AS (
        SELECT 
            te.ItemID,
            SUM(te.Quantity) as Units7Days,
            COUNT(DISTINCT t.TransactionNumber) as Trans7Days
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.[Time] >= '{start_date_7d.strftime('%Y-%m-%d')}'
            AND te.Quantity > 0
        GROUP BY te.ItemID
    )
    SELECT 
        ci.SKU,
        ci.Description,
        ci.Category,
        ci.CurrentStock,
        ci.Cost,
        ci.Price,
        ci.InventoryValue,
        ci.ReorderPoint,
        ci.RestockLevel,
        ISNULL(s90.Units90Days, 0) as Units90Days,
        ISNULL(s30.Units30Days, 0) as Units30Days,
        ISNULL(s7.Units7Days, 0) as Units7Days,
        ISNULL(s90.Trans90Days, 0) as Trans90Days,
        ISNULL(s30.Trans30Days, 0) as Trans30Days,
        ISNULL(s7.Trans7Days, 0) as Trans7Days,
        ci.DaysSinceLastSold,
        ci.DaysSinceLastReceived,
        s90.LastSaleDate,
        -- Calculate daily velocity
        CASE 
            WHEN s7.Units7Days > 0 THEN s7.Units7Days / 7.0
            WHEN s30.Units30Days > 0 THEN s30.Units30Days / 30.0
            WHEN s90.Units90Days > 0 THEN s90.Units90Days / 90.0
            ELSE 0
        END as DailyVelocity,
        -- Calculate days of stock
        CASE 
            WHEN s7.Units7Days > 0 THEN ci.CurrentStock / (s7.Units7Days / 7.0)
            WHEN s30.Units30Days > 0 THEN ci.CurrentStock / (s30.Units30Days / 30.0)
            WHEN s90.Units90Days > 0 THEN ci.CurrentStock / (s90.Units90Days / 90.0)
            ELSE 999999
        END as DaysOfStock
    FROM CurrentInventory ci
    LEFT JOIN Sales90Days s90 ON ci.ItemID = s90.ItemID
    LEFT JOIN Sales30Days s30 ON ci.ItemID = s30.ItemID
    LEFT JOIN Sales7Days s7 ON ci.ItemID = s7.ItemID
    WHERE ci.CurrentStock > 0 OR s90.Units90Days > 0
    """
    
    try:
        with SQLServerConnection() as db:
            logger.info("Fetching inventory and sales data...")
            df = db.execute_query(inventory_query, description="Inventory analysis")
            
            if df.empty:
                logger.warning("No inventory data found")
                return None
            
            logger.info(f"Analyzing {len(df)} products...")
            
            # Categorize inventory health
            def categorize_inventory(row):
                stock = row['CurrentStock']
                velocity = row['DailyVelocity']
                days_stock = row['DaysOfStock']
                days_since_sold = row['DaysSinceLastSold']
                units_30 = row['Units30Days']
                units_90 = row['Units90Days']
                reorder_point = row['ReorderPoint']
                
                # Dead stock: No sales in 60+ days with inventory
                if stock > 0 and units_90 == 0:
                    return 'DEAD STOCK - No sales 90+ days'
                elif stock > 0 and units_30 == 0 and days_since_sold > 30:
                    return 'SLOW/DEAD - No sales 30+ days'
                
                # Critical low stock
                elif stock > 0 and stock <= reorder_point and velocity > 1:
                    return 'CRITICAL LOW - Below reorder point'
                elif stock > 0 and days_stock < 3 and velocity > 0.5:
                    return 'CRITICAL LOW - <3 days stock'
                
                # Low stock
                elif stock > 0 and days_stock < 7 and velocity > 0.5:
                    return 'LOW STOCK - <7 days supply'
                elif stock > 0 and days_stock < 14 and velocity > 1:
                    return 'LOW STOCK - High velocity'
                
                # Overstock
                elif stock > 0 and days_stock > 180 and velocity < 0.5:
                    return 'OVERSTOCK - 180+ days supply'
                elif stock > 0 and days_stock > 90 and velocity < 1:
                    return 'OVERSTOCK - 90+ days supply'
                elif stock > 0 and days_stock > 60 and velocity < 2:
                    return 'MODERATE OVERSTOCK - 60+ days'
                
                # Healthy
                elif stock > 0 and days_stock >= 7 and days_stock <= 30:
                    return 'HEALTHY - Optimal stock level'
                elif stock > 0 and days_stock > 30 and days_stock <= 60:
                    return 'OK - Adequate stock'
                
                # Out of stock
                elif stock == 0 and row['Units7Days'] > 0:
                    return 'OUT OF STOCK - Recent demand!'
                elif stock == 0 and units_30 > 0:
                    return 'OUT OF STOCK - Monthly demand'
                
                else:
                    return 'MONITOR - Review needed'
            
            df['InventoryStatus'] = df.apply(categorize_inventory, axis=1)
            
            # Calculate additional metrics
            df['TurnoverRate30Days'] = df.apply(
                lambda x: (x['Units30Days'] / x['CurrentStock'] * 12) if x['CurrentStock'] > 0 else 0, 
                axis=1
            )
            
            # Identify specific issues
            dead_stock = df[df['InventoryStatus'].str.contains('DEAD')]
            critical_low = df[df['InventoryStatus'].str.contains('CRITICAL LOW')]
            low_stock = df[df['InventoryStatus'].str.contains('LOW STOCK')]
            overstock = df[df['InventoryStatus'].str.contains('OVERSTOCK')]
            out_of_stock = df[df['InventoryStatus'].str.contains('OUT OF STOCK')]
            
            # Sort by priority
            dead_stock = dead_stock.sort_values('InventoryValue', ascending=False)
            critical_low = critical_low.sort_values('DailyVelocity', ascending=False)
            low_stock = low_stock.sort_values('DailyVelocity', ascending=False)
            overstock = overstock.sort_values('InventoryValue', ascending=False)
            out_of_stock = out_of_stock.sort_values('Units7Days', ascending=False)
            
            # Generate report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"inventory_health_report_{timestamp}.txt"
            excel_file = f"inventory_analysis_{timestamp}.xlsx"
            
            # Save to Excel with multiple sheets
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = {
                    'Status': ['Dead Stock', 'Critical Low', 'Low Stock', 'Overstock', 
                              'Out of Stock', 'Healthy', 'Total'],
                    'Count': [
                        len(dead_stock),
                        len(critical_low),
                        len(low_stock),
                        len(overstock),
                        len(out_of_stock),
                        len(df[df['InventoryStatus'].str.contains('HEALTHY|OK')]),
                        len(df)
                    ],
                    'Inventory Value': [
                        dead_stock['InventoryValue'].sum(),
                        critical_low['InventoryValue'].sum(),
                        low_stock['InventoryValue'].sum(),
                        overstock['InventoryValue'].sum(),
                        0,
                        df[df['InventoryStatus'].str.contains('HEALTHY|OK')]['InventoryValue'].sum(),
                        df['InventoryValue'].sum()
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Dead stock sheet
                if not dead_stock.empty:
                    dead_stock[['SKU', 'Description', 'Category', 'CurrentStock', 'Cost', 
                               'InventoryValue', 'DaysSinceLastSold', 'Units90Days']].to_excel(
                        writer, sheet_name='Dead Stock', index=False
                    )
                
                # Critical items sheet
                critical_combined = pd.concat([critical_low, out_of_stock])
                if not critical_combined.empty:
                    critical_combined[['SKU', 'Description', 'CurrentStock', 'DailyVelocity', 
                                      'DaysOfStock', 'Units7Days', 'ReorderPoint', 'InventoryStatus']].to_excel(
                        writer, sheet_name='Critical Items', index=False
                    )
                
                # Overstock sheet
                if not overstock.empty:
                    overstock[['SKU', 'Description', 'CurrentStock', 'InventoryValue', 
                              'DailyVelocity', 'DaysOfStock', 'Units30Days']].to_excel(
                        writer, sheet_name='Overstock', index=False
                    )
                
                # All items sheet
                df.to_excel(writer, sheet_name='All Items', index=False)
            
            # Generate text report
            with open(report_file, 'w') as f:
                f.write("="*100 + "\n")
                f.write(" "*35 + "INVENTORY HEALTH ANALYSIS\n")
                f.write("="*100 + "\n")
                f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*100 + "\n\n")
                
                # Executive Summary
                total_value = df['InventoryValue'].sum()
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-"*100 + "\n")
                f.write(f"Total SKUs Analyzed: {len(df):,}\n")
                f.write(f"Total Inventory Value: ${total_value:,.2f}\n")
                f.write(f"Dead Stock Value: ${dead_stock['InventoryValue'].sum():,.2f} ({len(dead_stock)} items)\n")
                f.write(f"Overstock Value: ${overstock['InventoryValue'].sum():,.2f} ({len(overstock)} items)\n")
                f.write(f"Critical Low Stock Items: {len(critical_low)}\n")
                f.write(f"Out of Stock (with demand): {len(out_of_stock)}\n\n")
                
                # Dead Stock Section
                f.write("="*100 + "\n")
                f.write("🚨 DEAD STOCK - IMMEDIATE ACTION REQUIRED\n")
                f.write("="*100 + "\n")
                f.write("Items with no sales in 30-90+ days:\n\n")
                
                if not dead_stock.empty:
                    for _, item in dead_stock.head(20).iterrows():
                        f.write(f"• {item['Description'][:50]:<50} SKU: {item['SKU']}\n")
                        f.write(f"  Stock: {item['CurrentStock']:.0f} units | Value: ${item['InventoryValue']:,.2f} | ")
                        f.write(f"Last sold: {item['DaysSinceLastSold']:.0f} days ago\n\n")
                    
                    if len(dead_stock) > 20:
                        f.write(f"  ... and {len(dead_stock)-20} more items\n\n")
                
                # Critical Low Stock
                f.write("="*100 + "\n")
                f.write("⚠️  CRITICAL LOW STOCK - REORDER IMMEDIATELY\n")
                f.write("="*100 + "\n")
                
                if not critical_low.empty:
                    for _, item in critical_low.head(20).iterrows():
                        f.write(f"• {item['Description'][:50]:<50} SKU: {item['SKU']}\n")
                        f.write(f"  Stock: {item['CurrentStock']:.0f} | ")
                        f.write(f"Daily velocity: {item['DailyVelocity']:.1f} | ")
                        f.write(f"Days remaining: {item['DaysOfStock']:.1f}\n\n")
                
                # Out of Stock with Demand
                f.write("="*100 + "\n")
                f.write("❌ OUT OF STOCK - LOST SALES\n")
                f.write("="*100 + "\n")
                
                if not out_of_stock.empty:
                    for _, item in out_of_stock.head(15).iterrows():
                        f.write(f"• {item['Description'][:50]:<50} SKU: {item['SKU']}\n")
                        f.write(f"  Recent demand: {item['Units7Days']:.0f} units in 7 days | ")
                        f.write(f"30-day demand: {item['Units30Days']:.0f} units\n\n")
                
                # Overstock
                f.write("="*100 + "\n")
                f.write("📦 OVERSTOCK - CONSIDER PROMOTIONS\n")
                f.write("="*100 + "\n")
                
                if not overstock.empty:
                    for _, item in overstock.head(15).iterrows():
                        f.write(f"• {item['Description'][:50]:<50} SKU: {item['SKU']}\n")
                        f.write(f"  Stock: {item['CurrentStock']:.0f} | Value: ${item['InventoryValue']:,.2f} | ")
                        f.write(f"Days of supply: {item['DaysOfStock']:.0f}\n\n")
                
                # Recommendations
                f.write("="*100 + "\n")
                f.write("💡 RECOMMENDATIONS\n")
                f.write("="*100 + "\n")
                
                dead_value = dead_stock['InventoryValue'].sum()
                if dead_value > 0:
                    f.write(f"1. DEAD STOCK: ${dead_value:,.2f} tied up in non-moving inventory\n")
                    f.write("   • Run clearance sale or promotions\n")
                    f.write("   • Bundle with fast-moving items\n")
                    f.write("   • Consider vendor returns if possible\n\n")
                
                if len(critical_low) > 0:
                    f.write(f"2. CRITICAL ITEMS: {len(critical_low)} items need immediate reorder\n")
                    top_critical = critical_low.head(5)
                    for _, item in top_critical.iterrows():
                        f.write(f"   • {item['Description'][:40]} - Order NOW\n")
                    f.write("\n")
                
                if len(out_of_stock) > 0:
                    lost_sales = out_of_stock['Units7Days'].sum() * out_of_stock['Price'].mean()
                    f.write(f"3. LOST SALES: Estimated ${lost_sales:,.2f} in lost revenue (7 days)\n")
                    f.write("   • Set up automatic reorder points\n")
                    f.write("   • Increase safety stock for high-velocity items\n\n")
                
                overstock_value = overstock['InventoryValue'].sum()
                if overstock_value > total_value * 0.3:
                    f.write(f"4. OVERSTOCK: ${overstock_value:,.2f} in excess inventory\n")
                    f.write("   • Implement FIFO rotation\n")
                    f.write("   • Create bundle deals\n")
                    f.write("   • Adjust reorder quantities\n")
                
                f.write("\n" + "="*100 + "\n")
                f.write("END OF REPORT\n")
                f.write("="*100 + "\n")
            
            # Print summary to console
            print("\n" + "="*80)
            print("INVENTORY HEALTH ANALYSIS COMPLETE")
            print("="*80)
            
            print(f"\n🔍 INVENTORY SNAPSHOT:")
            print(f"  Total SKUs: {len(df):,}")
            print(f"  Total Value: ${total_value:,.2f}")
            
            print(f"\n🚨 CRITICAL ISSUES:")
            print(f"  Dead Stock: {len(dead_stock)} items (${dead_stock['InventoryValue'].sum():,.2f})")
            print(f"  Critical Low: {len(critical_low)} items")
            print(f"  Out of Stock: {len(out_of_stock)} items with active demand")
            print(f"  Overstock: {len(overstock)} items (${overstock['InventoryValue'].sum():,.2f})")
            
            if not dead_stock.empty:
                print(f"\n💀 TOP 5 DEAD STOCK ITEMS:")
                for idx, item in dead_stock.head(5).iterrows():
                    print(f"  • {item['Description'][:40]:<40} ${item['InventoryValue']:>10,.2f}")
            
            if not critical_low.empty:
                print(f"\n⚠️  TOP 5 CRITICAL LOW STOCK:")
                for idx, item in critical_low.head(5).iterrows():
                    print(f"  • {item['Description'][:40]:<40} {item['DaysOfStock']:>4.1f} days left")
            
            if not out_of_stock.empty:
                print(f"\n❌ TOP 5 OUT OF STOCK (WITH DEMAND):")
                for idx, item in out_of_stock.head(5).iterrows():
                    print(f"  • {item['Description'][:40]:<40} {item['Units7Days']:>4.0f} units/week demand")
            
            print(f"\n💾 FILES SAVED:")
            print(f"  📊 Excel Analysis: {excel_file}")
            print(f"  📄 Detailed Report: {report_file}")
            
            return excel_file, report_file
            
    except Exception as e:
        logger.error(f"Error analyzing inventory: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    excel_file, report_file = analyze_inventory_health()
    
    if excel_file:
        print(f"\n✅ Analysis completed successfully!")
        print(f"📊 Open {excel_file} for detailed inventory analysis")
        print(f"📄 Read {report_file} for actionable recommendations")
    else:
        print("\n❌ Analysis failed. Please check the logs.")