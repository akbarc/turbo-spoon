#!/usr/bin/env python3
"""
Get last 3 purchases from Petrey with details
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

conn = db.SQLServerConnection()
if conn.connect():
    # Get last 3 Petrey purchases
    po_query = '''
    SELECT TOP 3
        po.ID as PO_ID,
        po.PONumber,
        po.DateCreated,
        po.Status,
        po.Shipping,
        po.OtherFees,
        CASE po.Status
            WHEN 0 THEN 'Open'
            WHEN 1 THEN 'Partial'
            WHEN 2 THEN 'Complete'
            ELSE 'Unknown'
        END as StatusText
    FROM PurchaseOrder po
    WHERE po.SupplierID = 1330
    ORDER BY po.DateCreated DESC
    '''

    po_df = conn.execute_query(po_query, description='Last 3 Petrey POs')

    print('='*80)
    print('LAST 3 PURCHASES FROM PETREY WHOLESALE')
    print('='*80)

    for idx, po in po_df.iterrows():
        print(f'\nPurchase Order #{idx + 1}:')
        print(f'  PO Number: {po["PONumber"]}')
        print(f'  Date: {po["DateCreated"]}')
        print(f'  Status: {po["StatusText"]}')
        if po['Shipping'] and float(po['Shipping']) > 0:
            print(f'  Shipping: ${float(po["Shipping"]):.2f}')

        # Get items for this PO
        items_query = f'''
        SELECT TOP 15
            poe.ItemID,
            i.ItemLookupCode as SKU,
            i.Description,
            poe.QuantityOrdered,
            poe.QuantityReceived,
            poe.Price as UnitCost,
            (poe.Price * poe.QuantityOrdered) as ExtendedCost
        FROM PurchaseOrderEntry poe
        INNER JOIN Item i ON poe.ItemID = i.ID
        WHERE poe.PurchaseOrderID = {po["PO_ID"]}
        ORDER BY ExtendedCost DESC
        '''

        items_df = conn.execute_query(items_query, description=f'Items for PO {po["PONumber"]}')

        if len(items_df) > 0:
            # Convert to float for calculations
            items_df['ExtendedCost'] = items_df['ExtendedCost'].astype(float)
            items_df['UnitCost'] = items_df['UnitCost'].astype(float)

            total = items_df['ExtendedCost'].sum()
            print(f'  Total Value: ${total:.2f}')
            print(f'\n  Items ({len(items_df)} shown):')
            print(f'  {"Description":50} {"Qty":>8} {"Unit Cost":>10} {"Total":>12}')
            print(f'  {"-"*50} {"-"*8} {"-"*10} {"-"*12}')

            for _, item in items_df.iterrows():
                desc = item['Description'][:48] if len(item['Description']) > 48 else item['Description']
                print(f'  {desc:50} {item["QuantityOrdered"]:8.0f} ${item["UnitCost"]:9.2f} ${item["ExtendedCost"]:11.2f}')

    # Save detailed report
    with pd.ExcelWriter('petrey_last_3_purchases.xlsx', engine='openpyxl') as writer:
        po_df.to_excel(writer, sheet_name='Purchase_Orders', index=False)

        # Get all items from these 3 POs
        all_items_query = f'''
        SELECT
            po.PONumber,
            po.DateCreated as PO_Date,
            i.ItemLookupCode as SKU,
            i.Description,
            poe.QuantityOrdered,
            poe.QuantityReceived,
            poe.Price as UnitCost,
            (poe.Price * poe.QuantityOrdered) as ExtendedCost
        FROM PurchaseOrderEntry poe
        INNER JOIN Item i ON poe.ItemID = i.ID
        INNER JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
        WHERE po.ID IN ({','.join(map(str, po_df['PO_ID'].tolist()))})
        ORDER BY po.DateCreated DESC, ExtendedCost DESC
        '''

        all_items_df = conn.execute_query(all_items_query, description='All items from 3 POs')
        all_items_df.to_excel(writer, sheet_name='All_Items', index=False)

    print(f'\n✅ Detailed Excel report saved: petrey_last_3_purchases.xlsx')

    conn.close()