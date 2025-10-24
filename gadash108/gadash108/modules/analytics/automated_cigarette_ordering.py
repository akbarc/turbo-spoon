#!/usr/bin/env python3
"""
Automated Cigarette Ordering System
Based on inventory movement analysis, sales patterns, and purchase history
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime, timedelta
import csv
import os
from collections import defaultdict

class AutomatedCigaretteOrdering:
    def __init__(self):
        self.db = SQLServerConnection()
        self.tobacco_categories = ['CIGARETTE', 'CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'T7 SMOKELESS GA', 'ECIG - PODS']
        
        # Ordering thresholds based on your business patterns
        self.urgent_weeks_threshold = 2.0    # Order when less than 2 weeks of stock
        self.low_weeks_threshold = 4.0       # Monitor when less than 4 weeks of stock
        self.safety_stock_multiplier = 1.5   # Order 1.5x weekly movement for safety
        
        # Supplier preferences (based on your data analysis)
        self.preferred_suppliers = {
            'CIGARETTE': {
                'Newport': 'PETREY WHOLESALE CO',
                'Marlboro': 'PETREY WHOLESALE CO', 
                '24/7': 'BLUE RIDGE TOBACCO COMPANY',
                'Default': 'PETREY WHOLESALE CO'
            },
            'CIGARS': {
                'Swisher': 'SZ WHOLESALE',
                'Black': 'TEXAS WHOLESALE',
                'Default': 'SZ WHOLESALE'
            }
        }

    def analyze_current_inventory_status(self):
        """Analyze current inventory status and movement patterns"""
        print('=== AUTOMATED ORDERING ANALYSIS ===\n')
        
        query = """
        WITH WeeklyMovement AS (
            SELECT 
                i.ID as ItemID,
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as current_stock,
                c.Name as Category,
                -- Calculate weekly movement over last 8 weeks
                SUM(te.Quantity) / 8.0 as avg_weekly_movement,
                MAX(te.Quantity) as peak_daily_movement,
                COUNT(DISTINCT DATEPART(week, t.Time)) as weeks_with_sales,
                -- Recent trend (last 2 weeks vs previous 6 weeks)
                SUM(CASE WHEN t.Time >= DATEADD(day, -14, GETDATE()) THEN te.Quantity ELSE 0 END) / 2.0 as recent_weekly_avg,
                SUM(CASE WHEN t.Time < DATEADD(day, -14, GETDATE()) AND t.Time >= DATEADD(day, -56, GETDATE()) THEN te.Quantity ELSE 0 END) / 6.0 as historical_weekly_avg,
                -- Customer analysis
                COUNT(DISTINCT CASE WHEN cust.Company IS NOT NULL AND LEN(cust.Company) > 2 THEN t.CustomerID END) as wholesale_customers,
                COUNT(DISTINCT CASE WHEN cust.Company IS NULL OR LEN(cust.Company) <= 2 THEN t.CustomerID END) as retail_customers,
                -- Profitability
                AVG(te.Price - te.Cost) as avg_margin_per_unit,
                SUM((te.Price - te.Cost) * te.Quantity) as total_profit_8weeks
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            LEFT JOIN dbo.Customer cust ON t.CustomerID = cust.ID
            WHERE c.Name IN ('CIGARETTE', 'CIGARS', 'CIGAR GA')
              AND t.Time >= DATEADD(day, -56, GETDATE())  -- 8 weeks
              AND i.Inactive = 0
            GROUP BY i.ID, i.Description, i.ItemLookupCode, i.Quantity, c.Name
        ),
        PurchaseHistory AS (
            SELECT 
                i.ID as ItemID,
                AVG(poe.QuantityOrdered) as avg_order_qty,
                MAX(poe.QuantityOrdered) as max_order_qty,
                COUNT(DISTINCT po.ID) as total_orders_6months,
                MAX(po.DateCreated) as last_order_date,
                DATEDIFF(day, MAX(po.DateCreated), GETDATE()) as days_since_last_order,
                -- Primary supplier
                (SELECT TOP 1 s.SupplierName 
                 FROM dbo.Supplier s
                 JOIN dbo.PurchaseOrder po2 ON s.ID = po2.SupplierID
                 JOIN dbo.PurchaseOrderEntry poe2 ON po2.ID = poe2.PurchaseOrderID
                 WHERE poe2.ItemID = i.ID AND po2.DateCreated >= DATEADD(month, -6, GETDATE())
                 GROUP BY s.SupplierName
                 ORDER BY SUM(poe2.QuantityOrdered) DESC) as primary_supplier,
                -- Average cost
                AVG(poe.Price) as avg_purchase_cost
            FROM dbo.Item i
            JOIN dbo.PurchaseOrderEntry poe ON i.ID = poe.ItemID
            JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
            WHERE po.DateCreated >= DATEADD(month, -6, GETDATE())
            GROUP BY i.ID
        )
        SELECT 
            wm.*,
            ph.avg_order_qty,
            ph.max_order_qty,
            ph.total_orders_6months,
            ph.last_order_date,
            ph.days_since_last_order,
            ph.primary_supplier,
            ph.avg_purchase_cost,
            -- Calculate ordering metrics
            CASE 
                WHEN wm.avg_weekly_movement > 0 THEN wm.current_stock / wm.avg_weekly_movement
                ELSE 999
            END as weeks_of_stock,
            -- Suggested order quantity based on movement and safety stock
            CASE 
                WHEN wm.avg_weekly_movement > 0 THEN 
                    CEILING(wm.avg_weekly_movement * 6 * 1.5)  -- 6 weeks supply + 50% safety stock
                ELSE 0
            END as suggested_order_qty,
            -- Order priority
            CASE 
                WHEN wm.current_stock <= 0 THEN 'CRITICAL'
                WHEN wm.avg_weekly_movement > 0 AND wm.current_stock / wm.avg_weekly_movement <= 2 THEN 'URGENT'
                WHEN wm.avg_weekly_movement > 0 AND wm.current_stock / wm.avg_weekly_movement <= 4 THEN 'LOW'
                WHEN wm.avg_weekly_movement > 0 AND wm.current_stock / wm.avg_weekly_movement > 12 THEN 'OVERSTOCKED'
                ELSE 'NORMAL'
            END as order_priority,
            -- Trend analysis
            CASE 
                WHEN wm.recent_weekly_avg > wm.historical_weekly_avg * 1.2 THEN 'INCREASING'
                WHEN wm.recent_weekly_avg < wm.historical_weekly_avg * 0.8 THEN 'DECREASING'
                ELSE 'STABLE'
            END as demand_trend
        FROM WeeklyMovement wm
        LEFT JOIN PurchaseHistory ph ON wm.ItemID = ph.ItemID
        WHERE wm.avg_weekly_movement > 0  -- Only items that actually sell
        ORDER BY 
            CASE 
                WHEN wm.current_stock <= 0 THEN 1
                WHEN wm.avg_weekly_movement > 0 AND wm.current_stock / wm.avg_weekly_movement <= 2 THEN 2
                WHEN wm.avg_weekly_movement > 0 AND wm.current_stock / wm.avg_weekly_movement <= 4 THEN 3
                ELSE 4
            END,
            wm.total_profit_8weeks DESC
        """
        
        result = self.db.execute_query(query, [], 'Automated Ordering Analysis')
        return result

    def generate_automated_purchase_orders(self, analysis_data):
        """Generate automated purchase orders based on analysis"""
        
        # Group by supplier and priority
        orders_by_supplier = defaultdict(list)
        
        for _, row in analysis_data.iterrows():
            if row['order_priority'] in ['CRITICAL', 'URGENT', 'LOW']:
                supplier = self.determine_best_supplier(row)
                
                order_item = {
                    'item_id': row['ItemID'],
                    'sku': row['SKU'],
                    'description': row['Description'],
                    'category': row['Category'],
                    'current_stock': row['current_stock'],
                    'weeks_of_stock': row['weeks_of_stock'],
                    'avg_weekly_movement': row['avg_weekly_movement'],
                    'suggested_order_qty': row['suggested_order_qty'],
                    'order_priority': row['order_priority'],
                    'demand_trend': row['demand_trend'],
                    'avg_purchase_cost': row['avg_purchase_cost'],
                    'total_profit_8weeks': row['total_profit_8weeks'],
                    'days_since_last_order': row['days_since_last_order']
                }
                
                orders_by_supplier[supplier].append(order_item)
        
        return orders_by_supplier

    def determine_best_supplier(self, item_data):
        """Determine the best supplier for an item based on history and preferences"""
        
        # First, use historical supplier if available
        if pd.notna(item_data['primary_supplier']) and item_data['primary_supplier']:
            return item_data['primary_supplier']
        
        # Otherwise, use category-based preferences
        category = item_data['Category']
        description = item_data['Description'].upper()
        
        if category == 'CIGARETTE':
            if 'NEWPORT' in description:
                return self.preferred_suppliers['CIGARETTE']['Newport']
            elif 'MARL' in description or 'MARLBORO' in description:
                return self.preferred_suppliers['CIGARETTE']['Marlboro']
            elif '24/7' in description:
                return self.preferred_suppliers['CIGARETTE']['24/7']
            else:
                return self.preferred_suppliers['CIGARETTE']['Default']
        
        elif category in ['CIGARS', 'CIGAR GA']:
            if 'SWISHER' in description or 'SS ' in description:
                return self.preferred_suppliers['CIGARS']['Swisher']
            elif 'BLACK' in description or 'BLK' in description:
                return self.preferred_suppliers['CIGARS']['Black']
            else:
                return self.preferred_suppliers['CIGARS']['Default']
        
        return 'PETREY WHOLESALE CO'  # Default supplier

    def export_purchase_orders_csv(self, orders_by_supplier, filename_prefix="automated_po"):
        """Export purchase orders to CSV files by supplier"""
        
        export_dir = "automated_purchase_orders"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exported_files = []
        
        for supplier, items in orders_by_supplier.items():
            if not items:
                continue
            
            # Clean supplier name for filename
            safe_supplier = "".join(c for c in supplier if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_supplier = safe_supplier.replace(' ', '_')
            
            filename = f"{filename_prefix}_{safe_supplier}_{timestamp}.csv"
            filepath = os.path.join(export_dir, filename)
            
            # Calculate totals
            total_items = len(items)
            total_qty = sum(item['suggested_order_qty'] for item in items)
            total_value = sum(item['suggested_order_qty'] * float(item['avg_purchase_cost'] or 0) for item in items)
            critical_items = len([item for item in items if item['order_priority'] == 'CRITICAL'])
            urgent_items = len([item for item in items if item['order_priority'] == 'URGENT'])
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                # Write header with summary
                f.write(f"# AUTOMATED PURCHASE ORDER\n")
                f.write(f"# Supplier: {supplier}\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total Items: {total_items}\n")
                f.write(f"# Total Quantity: {total_qty:,}\n")
                f.write(f"# Estimated Value: ${total_value:,.2f}\n")
                f.write(f"# Critical Items: {critical_items}\n")
                f.write(f"# Urgent Items: {urgent_items}\n")
                f.write(f"#\n")
                f.write(f"# ORDERING LOGIC:\n")
                f.write(f"# - CRITICAL: Out of stock (0 units)\n")
                f.write(f"# - URGENT: Less than 2 weeks of stock\n")
                f.write(f"# - LOW: Less than 4 weeks of stock\n")
                f.write(f"# - Suggested quantity = 6 weeks supply + 50% safety stock\n")
                f.write(f"#\n")
                
                writer = csv.writer(f)
                
                # Write CSV headers
                headers = [
                    'Priority', 'SKU', 'Description', 'Category',
                    'Current Stock', 'Weeks of Stock', 'Weekly Movement',
                    'Suggested Order Qty', 'Est. Cost Per Unit', 'Est. Total Cost',
                    'Demand Trend', '8-Week Profit', 'Days Since Last Order'
                ]
                writer.writerow(headers)
                
                # Sort items by priority
                priority_order = {'CRITICAL': 1, 'URGENT': 2, 'LOW': 3}
                items.sort(key=lambda x: (priority_order.get(x['order_priority'], 4), -x['total_profit_8weeks']))
                
                # Write items
                for item in items:
                    est_cost = float(item['avg_purchase_cost'] or 0)
                    est_total = item['suggested_order_qty'] * est_cost
                    
                    row = [
                        item['order_priority'],
                        item['sku'],
                        item['description'],
                        item['category'],
                        f"{item['current_stock']:.0f}",
                        f"{item['weeks_of_stock']:.1f}" if item['weeks_of_stock'] != 999 else "∞",
                        f"{item['avg_weekly_movement']:.1f}",
                        f"{item['suggested_order_qty']:.0f}",
                        f"${est_cost:.2f}",
                        f"${est_total:.2f}",
                        item['demand_trend'],
                        f"${item['total_profit_8weeks']:.2f}",
                        f"{item['days_since_last_order']:.0f}" if pd.notna(item['days_since_last_order']) else "Never"
                    ]
                    writer.writerow(row)
            
            exported_files.append(filepath)
            print(f"✅ {supplier}: {total_items} items, ${total_value:,.2f} estimated value → {filepath}")
        
        return exported_files

    def create_weekly_ordering_summary(self, analysis_data):
        """Create a summary report for weekly ordering decisions"""
        
        summary = {
            'total_items_analyzed': len(analysis_data),
            'critical_items': len(analysis_data[analysis_data['order_priority'] == 'CRITICAL']),
            'urgent_items': len(analysis_data[analysis_data['order_priority'] == 'URGENT']),
            'low_stock_items': len(analysis_data[analysis_data['order_priority'] == 'LOW']),
            'overstocked_items': len(analysis_data[analysis_data['order_priority'] == 'OVERSTOCKED']),
            'total_estimated_order_value': 0,
            'top_priority_items': [],
            'supplier_breakdown': defaultdict(int)
        }
        
        # Calculate totals and identify top priority items
        for _, row in analysis_data.iterrows():
            if row['order_priority'] in ['CRITICAL', 'URGENT', 'LOW']:
                est_cost = row['avg_purchase_cost'] or 0
                summary['total_estimated_order_value'] += row['suggested_order_qty'] * float(est_cost)
                
                supplier = self.determine_best_supplier(row)
                summary['supplier_breakdown'][supplier] += 1
                
                if row['order_priority'] in ['CRITICAL', 'URGENT']:
                    summary['top_priority_items'].append({
                        'description': row['Description'],
                        'priority': row['order_priority'],
                        'current_stock': row['current_stock'],
                        'weeks_of_stock': row['weeks_of_stock'],
                        'suggested_qty': row['suggested_order_qty']
                    })
        
        # Sort top priority items
        priority_order = {'CRITICAL': 1, 'URGENT': 2}
        summary['top_priority_items'].sort(key=lambda x: (priority_order[x['priority']], x['weeks_of_stock']))
        summary['top_priority_items'] = summary['top_priority_items'][:20]  # Top 20
        
        return summary

def main():
    ordering_system = AutomatedCigaretteOrdering()
    
    print('🚬 AUTOMATED CIGARETTE ORDERING SYSTEM')
    print('=' * 50)
    
    # Step 1: Analyze current inventory status
    print('\n📊 ANALYZING CURRENT INVENTORY STATUS...')
    analysis_data = ordering_system.analyze_current_inventory_status()
    
    if analysis_data.empty:
        print('❌ No data available for analysis')
        return
    
    print(f'✅ Analyzed {len(analysis_data)} cigarette/tobacco products')
    
    # Step 2: Generate automated purchase orders
    print('\n🛒 GENERATING AUTOMATED PURCHASE ORDERS...')
    orders_by_supplier = ordering_system.generate_automated_purchase_orders(analysis_data)
    
    if not orders_by_supplier:
        print('✅ No items currently need ordering - all stock levels are adequate')
        return
    
    # Step 3: Export purchase orders to CSV
    print('\n📄 EXPORTING PURCHASE ORDERS TO CSV...')
    exported_files = ordering_system.export_purchase_orders_csv(orders_by_supplier)
    
    # Step 4: Create summary report
    print('\n📋 WEEKLY ORDERING SUMMARY')
    print('-' * 30)
    summary = ordering_system.create_weekly_ordering_summary(analysis_data)
    
    print(f'Total Items Analyzed: {summary["total_items_analyzed"]:,}')
    print(f'Critical Items (Out of Stock): {summary["critical_items"]}')
    print(f'Urgent Items (<2 weeks): {summary["urgent_items"]}')
    print(f'Low Stock Items (<4 weeks): {summary["low_stock_items"]}')
    print(f'Overstocked Items (>12 weeks): {summary["overstocked_items"]}')
    print(f'Estimated Total Order Value: ${summary["total_estimated_order_value"]:,.2f}')
    
    print('\n🏢 SUPPLIER BREAKDOWN:')
    for supplier, count in summary['supplier_breakdown'].items():
        print(f'  {supplier}: {count} items')
    
    print('\n🔥 TOP PRIORITY ITEMS:')
    for item in summary['top_priority_items'][:10]:
        weeks_stock = f"{item['weeks_of_stock']:.1f}" if item['weeks_of_stock'] != 999 else "∞"
        print(f'  {item["priority"]:8} | {item["description"][:40]:40} | Stock: {item["current_stock"]:4.0f} | {weeks_stock:4} weeks')
    
    print(f'\n✅ AUTOMATED ORDERING COMPLETE')
    print(f'📁 {len(exported_files)} CSV files exported to automated_purchase_orders/ directory')
    print('\n💡 NEXT STEPS:')
    print('   1. Review the generated CSV files for each supplier')
    print('   2. Adjust quantities based on current promotions or special circumstances')
    print('   3. Contact suppliers to place orders')
    print('   4. Update POS system when orders are received')

if __name__ == '__main__':
    main()
