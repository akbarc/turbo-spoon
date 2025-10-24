#!/usr/bin/env python3
"""
One Week Cigarette Order Generator
Generates order for exactly 1 week supply of cigarettes only
"""

from database_pymssql import SQLServerConnection
import pandas as pd
from datetime import datetime
import csv
import os

class WeeklyCigaretteOrder:
    def __init__(self):
        self.db = SQLServerConnection()
        
    def generate_one_week_order(self):
        """Generate order for 1 week of cigarettes only"""
        
        query = """
        WITH WeeklyMovement AS (
            SELECT 
                i.ID as ItemID,
                i.Description,
                i.ItemLookupCode as SKU,
                i.Quantity as current_stock,
                -- Calculate average weekly movement over last 4 weeks
                SUM(te.Quantity) / 4.0 as avg_weekly_movement,
                -- Get supplier info
                (SELECT TOP 1 s.SupplierName 
                 FROM dbo.Supplier s
                 JOIN dbo.PurchaseOrder po ON s.ID = po.SupplierID
                 JOIN dbo.PurchaseOrderEntry poe ON po.ID = poe.PurchaseOrderID
                 WHERE poe.ItemID = i.ID 
                 GROUP BY s.SupplierName
                 ORDER BY MAX(po.DateCreated) DESC) as supplier,
                -- Average cost
                (SELECT TOP 1 poe.Price
                 FROM dbo.PurchaseOrderEntry poe
                 JOIN dbo.PurchaseOrder po ON poe.PurchaseOrderID = po.ID
                 WHERE poe.ItemID = i.ID
                 ORDER BY po.DateCreated DESC) as unit_cost
            FROM dbo.Item i
            JOIN dbo.TransactionEntry te ON i.ID = te.ItemID
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN dbo.Category c ON i.CategoryID = c.ID
            WHERE c.Name = 'CIGARETTE'  -- ONLY cigarettes
              AND t.Time >= DATEADD(day, -28, GETDATE())  -- Last 4 weeks
              AND i.Inactive = 0
            GROUP BY i.ID, i.Description, i.ItemLookupCode, i.Quantity
            HAVING SUM(te.Quantity) > 0  -- Only items that actually sold
        )
        SELECT 
            Description,
            SKU,
            current_stock,
            ROUND(avg_weekly_movement, 0) as weekly_sales,
            -- Order exactly 1 week worth
            CEILING(avg_weekly_movement) as order_qty,
            ISNULL(supplier, 'PETREY WHOLESALE CO') as supplier,
            ISNULL(unit_cost, 0) as unit_cost,
            CEILING(avg_weekly_movement) * ISNULL(unit_cost, 0) as total_cost
        FROM WeeklyMovement
        WHERE avg_weekly_movement > 0
        ORDER BY avg_weekly_movement DESC
        """
        
        result = self.db.execute_query(query, [], 'Generate 1-Week Cigarette Order')
        return result
    
    def export_order(self, order_data):
        """Export the order to CSV"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cigarette_order_1week_{timestamp}.csv"
        
        # Group by supplier
        suppliers = order_data.groupby('supplier')
        
        print("\n📦 ONE WEEK CIGARETTE ORDER")
        print("=" * 60)
        
        total_qty = 0
        total_value = 0
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['ONE WEEK CIGARETTE ORDER - For Tuesday Delivery'])
            writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
            writer.writerow([])
            
            for supplier, items in suppliers:
                supplier_total_qty = items['order_qty'].sum()
                supplier_total_value = items['total_cost'].sum()
                
                total_qty += supplier_total_qty
                total_value += supplier_total_value
                
                # Write supplier section
                writer.writerow([f'SUPPLIER: {supplier}'])
                writer.writerow(['Description', 'SKU', 'Current Stock', 'Weekly Sales', 'Order Qty', 'Unit Cost', 'Total Cost'])
                
                for _, row in items.iterrows():
                    writer.writerow([
                        row['Description'],
                        row['SKU'],
                        f"{row['current_stock']:.0f}",
                        f"{row['weekly_sales']:.0f}",
                        f"{row['order_qty']:.0f}",
                        f"${row['unit_cost']:.2f}",
                        f"${row['total_cost']:.2f}"
                    ])
                
                writer.writerow([])
                writer.writerow(['', '', '', '', f"Subtotal: {supplier_total_qty:.0f}", '', f"${supplier_total_value:,.2f}"])
                writer.writerow([])
                
                print(f"\n{supplier}:")
                print(f"  Items: {len(items)}")
                print(f"  Quantity: {supplier_total_qty:,.0f} units")
                print(f"  Value: ${supplier_total_value:,.2f}")
            
            # Write totals
            writer.writerow([])
            writer.writerow(['GRAND TOTAL', '', '', '', f"{total_qty:.0f} units", '', f"${total_value:,.2f}"])
        
        print("\n" + "=" * 60)
        print(f"TOTAL ORDER:")
        print(f"  Items: {len(order_data)} SKUs")
        print(f"  Quantity: {total_qty:,.0f} units")
        print(f"  Value: ${total_value:,.2f}")
        print(f"\n✅ Order saved to: {filename}")
        
        return filename

def main():
    order_system = WeeklyCigaretteOrder()
    
    print("🚬 GENERATING 1-WEEK CIGARETTE ORDER")
    print("For Tuesday delivery")
    print("-" * 40)
    
    # Generate order
    order_data = order_system.generate_one_week_order()
    
    if order_data.empty:
        print("❌ No data available")
        return
    
    # Export order
    filename = order_system.export_order(order_data)
    
    print("\n📋 Order ready for submission to suppliers")

if __name__ == '__main__':
    main()