#!/usr/bin/env python3
"""
Get last 3 purchases from Petrey
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

def get_petrey_purchases():
    """Get last 3 purchase orders from Petrey"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # First, find Petrey supplier ID
        supplier_query = """
        SELECT ID, SupplierName, Code
        FROM Supplier
        WHERE UPPER(SupplierName) LIKE '%PETREY%'
           OR UPPER(Code) LIKE '%PETREY%'
        """

        supplier_df = conn.execute_query(supplier_query, description="Find Petrey supplier")

        if len(supplier_df) == 0:
            print("Petrey supplier not found. Checking all suppliers...")

            # List all suppliers to find the right one
            all_suppliers = """
            SELECT TOP 50 ID, SupplierName, Code
            FROM Supplier
            ORDER BY SupplierName
            """
            all_supp_df = conn.execute_query(all_suppliers, description="List all suppliers")
            print("\nAvailable suppliers:")
            for _, row in all_supp_df.iterrows():
                if 'petr' in str(row['SupplierName']).lower() or 'ptr' in str(row['SupplierName']).lower():
                    print(f"  {row['ID']}: {row['SupplierName']} ({row['Code']})")
            return None

        print(f"Found Petrey: {supplier_df.iloc[0]['SupplierName']} (ID: {supplier_df.iloc[0]['ID']})")
        petrey_id = supplier_df.iloc[0]['ID']

        # Check for PurchaseOrder table structure
        check_tables = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%Purchase%'
           OR TABLE_NAME LIKE '%Order%'
           OR TABLE_NAME LIKE '%Receipt%'
           OR TABLE_NAME LIKE '%Invoice%'
        ORDER BY TABLE_NAME
        """

        tables_df = conn.execute_query(check_tables, description="Check purchase tables")
        print(f"\nPurchase-related tables: {tables_df['TABLE_NAME'].tolist()}")

        # Try PurchaseOrder table
        if 'PurchaseOrder' in tables_df['TABLE_NAME'].tolist():
            # Get last 3 purchase orders
            po_query = f"""
            SELECT TOP 3
                po.ID as PO_Number,
                po.PONumber,
                po.DateCreated,
                po.Total,
                po.SubTotal,
                po.Tax,
                po.Shipping,
                po.StoreID,
                po.Status,
                s.SupplierName
            FROM PurchaseOrder po
            INNER JOIN Supplier s ON po.SupplierID = s.ID
            WHERE po.SupplierID = {petrey_id}
            ORDER BY po.DateCreated DESC
            """

            po_df = conn.execute_query(po_query, description="Get last 3 Petrey POs")

            if len(po_df) > 0:
                print("\n" + "="*80)
                print("LAST 3 PURCHASES FROM PETREY")
                print("="*80)

                for idx, po in po_df.iterrows():
                    print(f"\nPurchase Order #{idx + 1}:")
                    print(f"  PO Number: {po['PONumber']}")
                    print(f"  Date: {po['DateCreated']}")
                    print(f"  Total: ${po['Total']:.2f}")
                    print(f"  Subtotal: ${po['SubTotal']:.2f}")
                    print(f"  Tax: ${po['Tax']:.2f}")
                    print(f"  Shipping: ${po['Shipping']:.2f}")
                    print(f"  Status: {po['Status']}")

                    # Get line items for this PO
                    if 'PurchaseOrderEntry' in tables_df['TABLE_NAME'].tolist():
                        items_query = f"""
                        SELECT TOP 20
                            poe.ItemID,
                            i.ItemLookupCode as SKU,
                            i.Description,
                            poe.QuantityOrdered,
                            poe.QuantityReceived,
                            poe.Price as UnitCost,
                            (poe.Price * poe.QuantityOrdered) as TotalCost
                        FROM PurchaseOrderEntry poe
                        INNER JOIN Item i ON poe.ItemID = i.ID
                        WHERE poe.PurchaseOrderID = {po['PO_Number']}
                        ORDER BY TotalCost DESC
                        """

                        items_df = conn.execute_query(items_query, description=f"Get items for PO {po['PONumber']}")

                        if len(items_df) > 0:
                            print(f"\n  Top Items (showing up to 20):")
                            for _, item in items_df.head(10).iterrows():
                                print(f"    • {item['Description'][:50]:50} | Qty: {item['QuantityOrdered']:6.0f} | Cost: ${item['UnitCost']:7.2f} | Total: ${item['TotalCost']:9.2f}")

                            if len(items_df) > 10:
                                print(f"    ... and {len(items_df) - 10} more items")

                # Save to Excel
                with pd.ExcelWriter('petrey_last_3_purchases.xlsx', engine='openpyxl') as writer:
                    po_df.to_excel(writer, sheet_name='Purchase_Orders', index=False)

                    # Get all items from these 3 POs
                    if 'PurchaseOrderEntry' in tables_df['TABLE_NAME'].tolist():
                        all_items_query = f"""
                        SELECT
                            po.PONumber,
                            po.DateCreated as PO_Date,
                            i.ItemLookupCode as SKU,
                            i.Description,
                            poe.QuantityOrdered,
                            poe.QuantityReceived,
                            poe.Price as UnitCost,
                            (poe.Price * poe.QuantityOrdered) as TotalCost
                        FROM PurchaseOrderEntry poe
                        INNER JOIN Item i ON poe.ItemID = i.ID
                        INNER JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
                        WHERE po.ID IN ({','.join(map(str, po_df['PO_Number'].tolist()))})
                        ORDER BY po.DateCreated DESC, TotalCost DESC
                        """

                        all_items_df = conn.execute_query(all_items_query, description="Get all items from 3 POs")
                        all_items_df.to_excel(writer, sheet_name='All_Items', index=False)

                        print(f"\n✅ Detailed report saved to: petrey_last_3_purchases.xlsx")

                return po_df
            else:
                print(f"No purchase orders found for Petrey (Supplier ID: {petrey_id})")
                return None

        else:
            print("PurchaseOrder table not found in database")
            return None

    finally:
        conn.close()

if __name__ == "__main__":
    get_petrey_purchases()