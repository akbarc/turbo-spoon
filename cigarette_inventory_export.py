#!/usr/bin/env python3
"""
Comprehensive Cigarette Inventory Export
Includes multi-price analysis, sales metrics, purchase order data, and UPC lookup
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# UPC API Configuration
UPC_API_KEY = 'abb286e1762c2760f56d08bdb9c96b2d7128e61f10113cbc7693d37e473eb6f0'
UPC_API_URL = 'https://go-upc.com/api/v1/code/'

def fetch_upc_data(barcode):
    """Fetch UPC data from go-upc API for a single barcode"""
    try:
        headers = {
            'Authorization': f'Bearer {UPC_API_KEY}'
        }
        url = f'{UPC_API_URL}{barcode}'
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # Return the entire response as JSON string
            return {
                'barcode': barcode,
                'success': True,
                'data': json.dumps(data, ensure_ascii=False)
            }
        else:
            return {
                'barcode': barcode,
                'success': False,
                'data': json.dumps({'error': f'HTTP {response.status_code}'})
            }
    except Exception as e:
        return {
            'barcode': barcode,
            'success': False,
            'data': json.dumps({'error': str(e)})
        }

def fetch_all_upc_data_parallel(barcodes, max_workers=50):
    """Fetch UPC data for all barcodes in parallel"""
    results = {}
    total = len(barcodes)
    completed = 0

    print(f"\n🔍 Fetching UPC data for {total} barcodes...")
    print(f"   Using {max_workers} parallel workers")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_barcode = {
            executor.submit(fetch_upc_data, barcode): barcode
            for barcode in barcodes
        }

        # Process completed tasks
        for future in as_completed(future_to_barcode):
            result = future.result()
            results[result['barcode']] = result['data']
            completed += 1

            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"   Progress: {completed}/{total} ({completed/total*100:.1f}%) - {rate:.1f} requests/sec")

    elapsed = time.time() - start_time
    print(f"✅ UPC lookup complete in {elapsed:.1f} seconds")
    print(f"   Success rate: {sum(1 for r in results.values() if 'error' not in r)}/{total}")

    return results

def get_alternate_barcodes(conn):
    """Get alternate barcodes for all items"""
    query = """
    SELECT
        ItemID,
        Barcode as AlternateBarcode
    FROM BarCode
    WHERE ItemID IN (
        SELECT i.ID
        FROM Item i
        INNER JOIN Category c ON i.CategoryID = c.ID
        WHERE c.Name LIKE '%CIGARETTE%'
            AND i.Inactive = 0
    )
    ORDER BY ItemID
    """
    return conn.execute_query(query, description="Get alternate barcodes")

def get_cigarette_inventory_data():
    """Get comprehensive cigarette inventory with sales at different price points"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # Calculate date ranges
        now = datetime.now()
        date_7d = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        date_30d = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        date_60d = (now - timedelta(days=60)).strftime('%Y-%m-%d')

        print(f"Querying data for date ranges:")
        print(f"  7 days:  {date_7d} to {now.strftime('%Y-%m-%d')}")
        print(f"  30 days: {date_30d} to {now.strftime('%Y-%m-%d')}")
        print(f"  60 days: {date_60d} to {now.strftime('%Y-%m-%d')}")

        # Main query to get all cigarette items with inventory and sales
        query = f"""
        -- Get all cigarette items
        WITH CigaretteItems AS (
            SELECT
                i.ID,
                i.ItemLookupCode as Barcode,
                i.Description as Name,
                i.Cost,
                i.Price as CurrentPrice,
                i.Quantity as CurrentStock,
                i.SupplierID
            FROM Item i
            INNER JOIN Category c ON i.CategoryID = c.ID
            WHERE c.Name LIKE '%CIGARETTE%'
                AND i.Inactive = 0
        ),
        -- Get last purchase order info for each item
        LastPurchase AS (
            SELECT
                poe.ItemID,
                poe.LastQuantityReceived as LastOrderQty,
                poe.Price as LastPurchasePrice,
                po.PONumber as PurchaseOrderNumber,
                poe.LastReceivedDate as LastPurchaseDate,
                s.SupplierName as LastSupplier,
                ROW_NUMBER() OVER (PARTITION BY poe.ItemID ORDER BY poe.LastReceivedDate DESC) as rn
            FROM PurchaseOrderEntry poe
            INNER JOIN PurchaseOrder po ON poe.PurchaseOrderID = po.ID
            LEFT JOIN Supplier s ON po.SupplierID = s.ID
            WHERE poe.LastQuantityReceived > 0
                AND poe.LastReceivedDate IS NOT NULL
        ),
        -- Sales last 7 days by price point
        Sales7D AS (
            SELECT
                te.ItemID,
                te.Price,
                SUM(te.Quantity) as QtySold
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{date_7d}'
                AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID, te.Price
        ),
        -- Total sales last 7 days
        TotalSales7D AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as TotalQty7D
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{date_7d}'
                AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID
        ),
        -- Total sales last 30 days
        TotalSales30D AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as TotalQty30D
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{date_30d}'
                AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID
        ),
        -- Total sales last 60 days
        TotalSales60D AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as TotalQty60D
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= '{date_60d}'
                AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID
        )
        SELECT
            ci.ID,
            ci.Barcode,
            ci.Name,
            ci.Cost,
            ci.CurrentPrice,
            ci.CurrentStock,
            COALESCE(ts7.TotalQty7D, 0) as TotalSold7D,
            COALESCE(ts30.TotalQty30D, 0) as TotalSold30D,
            COALESCE(ts60.TotalQty60D, 0) as TotalSold60D,
            lp.LastPurchaseDate,
            lp.LastSupplier,
            lp.LastOrderQty,
            lp.LastPurchasePrice
        FROM CigaretteItems ci
        LEFT JOIN TotalSales7D ts7 ON ci.ID = ts7.ItemID
        LEFT JOIN TotalSales30D ts30 ON ci.ID = ts30.ItemID
        LEFT JOIN TotalSales60D ts60 ON ci.ID = ts60.ItemID
        LEFT JOIN LastPurchase lp ON ci.ID = lp.ItemID AND lp.rn = 1
        ORDER BY ci.Name
        """

        print("\n⏳ Executing main inventory query...")
        df_inventory = conn.execute_query(query, description="Get cigarette inventory data")

        if df_inventory is None or len(df_inventory) == 0:
            print("❌ No cigarette inventory data found")
            return None

        print(f"✅ Found {len(df_inventory)} cigarette products")

        # Now get sales by price point for last 7 days
        price_query = f"""
        SELECT
            te.ItemID,
            te.Price,
            SUM(te.Quantity) as QtySold
        FROM TransactionEntry te
        INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        INNER JOIN Category c ON i.CategoryID = c.ID
        WHERE t.Time >= '{date_7d}'
            AND c.Name LIKE '%CIGARETTE%'
            AND i.Inactive = 0
        GROUP BY te.ItemID, te.Price
        ORDER BY te.ItemID, te.Price DESC
        """

        print("\n⏳ Executing price point analysis query...")
        df_prices = conn.execute_query(price_query, description="Get sales by price point")

        if df_prices is not None and len(df_prices) > 0:
            print(f"✅ Found {len(df_prices)} price point records")
        else:
            print("⚠️  No price point data found")
            df_prices = pd.DataFrame(columns=['ItemID', 'Price', 'QtySold'])

        # Get alternate barcodes
        print("\n⏳ Fetching alternate barcodes...")
        df_alternates = get_alternate_barcodes(conn)

        if df_alternates is not None and len(df_alternates) > 0:
            print(f"✅ Found {len(df_alternates)} alternate barcodes")
        else:
            print("⚠️  No alternate barcodes found")
            df_alternates = pd.DataFrame(columns=['ItemID', 'AlternateBarcode'])

        return df_inventory, df_prices, df_alternates

    finally:
        conn.close()

def build_export_dataframe(df_inventory, df_prices, df_alternates):
    """Build final export DataFrame with multi-price columns and UPC data"""

    print("\n🔄 Processing data for export...")

    # Convert numeric columns
    numeric_cols = ['Cost', 'CurrentPrice', 'CurrentStock', 'TotalSold7D', 'TotalSold30D', 'TotalSold60D',
                    'LastOrderQty', 'LastPurchasePrice']
    for col in numeric_cols:
        if col in df_inventory.columns:
            df_inventory[col] = pd.to_numeric(df_inventory[col], errors='coerce').fillna(0)

    # Convert date columns
    if 'LastPurchaseDate' in df_inventory.columns:
        df_inventory['LastPurchaseDate'] = pd.to_datetime(df_inventory['LastPurchaseDate'], errors='coerce')

    # Calculate averages
    df_inventory['AvgQty30D'] = (df_inventory['TotalSold30D'] / 30).round(2)
    df_inventory['AvgQty60D'] = (df_inventory['TotalSold60D'] / 60).round(2)

    # Pivot price data to get multiple price columns
    # For each item, get up to 5 different prices (Price1, Qty1, Price2, Qty2, etc.)
    price_pivot_data = {}

    if len(df_prices) > 0:
        df_prices['Price'] = pd.to_numeric(df_prices['Price'], errors='coerce').fillna(0)
        df_prices['QtySold'] = pd.to_numeric(df_prices['QtySold'], errors='coerce').fillna(0)

        for item_id in df_inventory['ID'].unique():
            item_prices = df_prices[df_prices['ItemID'] == item_id].sort_values('QtySold', ascending=False)

            # Store up to 5 price points
            for idx, (_, row) in enumerate(item_prices.head(5).iterrows()):
                col_num = idx + 1
                if item_id not in price_pivot_data:
                    price_pivot_data[item_id] = {}
                price_pivot_data[item_id][f'Price{col_num}_7D'] = row['Price']
                price_pivot_data[item_id][f'Qty{col_num}_7D'] = row['QtySold']

    # Add price columns to main dataframe
    for col_num in range(1, 6):
        df_inventory[f'Price{col_num}_7D'] = df_inventory['ID'].map(
            lambda x: price_pivot_data.get(x, {}).get(f'Price{col_num}_7D', 0)
        )
        df_inventory[f'Qty{col_num}_7D'] = df_inventory['ID'].map(
            lambda x: price_pivot_data.get(x, {}).get(f'Qty{col_num}_7D', 0)
        )

    # Collect all barcodes (primary + alternates)
    print("\n📊 Collecting all barcodes (primary + alternates)...")

    # Get primary barcodes
    primary_barcodes = df_inventory['Barcode'].dropna().unique().tolist()
    print(f"   Primary barcodes: {len(primary_barcodes)}")

    # Get alternate barcodes
    alternate_barcodes = df_alternates['AlternateBarcode'].dropna().unique().tolist() if len(df_alternates) > 0 else []
    print(f"   Alternate barcodes: {len(alternate_barcodes)}")

    # Combine all unique barcodes
    all_barcodes = list(set(primary_barcodes + alternate_barcodes))
    print(f"   Total unique barcodes to lookup: {len(all_barcodes)}")

    # Fetch UPC data for all barcodes
    upc_data = fetch_all_upc_data_parallel(all_barcodes, max_workers=50)

    # Build alternate barcodes mapping (ItemID -> list of alternate barcodes with UPC data)
    alternates_by_item = {}
    if len(df_alternates) > 0:
        for _, row in df_alternates.iterrows():
            item_id = row['ItemID']
            alt_barcode = row['AlternateBarcode']
            if pd.notna(alt_barcode) and alt_barcode in upc_data:
                if item_id not in alternates_by_item:
                    alternates_by_item[item_id] = []
                alternates_by_item[item_id].append({
                    'barcode': alt_barcode,
                    'upc_data': upc_data[alt_barcode]
                })

    # Add UPC raw data column (primary barcode)
    df_inventory['UPC_RawData_Primary'] = df_inventory['Barcode'].map(lambda x: upc_data.get(x, ''))

    # Add alternate barcodes UPC data (JSON array of all alternates with their UPC data)
    df_inventory['UPC_RawData_Alternates'] = df_inventory['ID'].map(
        lambda x: json.dumps(alternates_by_item.get(x, []), ensure_ascii=False) if x in alternates_by_item else ''
    )

    # Reorder columns for final export
    final_columns = [
        'Name',
        'Barcode',
        'Cost',
        'CurrentPrice',
        'Price1_7D', 'Qty1_7D',
        'Price2_7D', 'Qty2_7D',
        'Price3_7D', 'Qty3_7D',
        'Price4_7D', 'Qty4_7D',
        'Price5_7D', 'Qty5_7D',
        'TotalSold7D',
        'CurrentStock',
        'TotalSold30D',
        'AvgQty30D',
        'AvgQty60D',
        'LastPurchaseDate',
        'LastSupplier',
        'LastOrderQty',
        'LastPurchasePrice',
        'UPC_RawData_Primary',
        'UPC_RawData_Alternates'
    ]

    df_export = df_inventory[final_columns].copy()

    # Sort by name
    df_export = df_export.sort_values(['Name'])

    return df_export

def main():
    print("="*100)
    print("COMPREHENSIVE CIGARETTE INVENTORY EXPORT")
    print("="*100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get data from database
    result = get_cigarette_inventory_data()
    if result is None:
        return

    df_inventory, df_prices, df_alternates = result

    # Build export dataframe
    df_export = build_export_dataframe(df_inventory, df_prices, df_alternates)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'cigarette_inventory_export_{timestamp}.xlsx'

    # Export to Excel
    print(f"\n💾 Exporting to Excel: {filename}")

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Main export sheet
        df_export.to_excel(writer, sheet_name='Cigarette_Inventory', index=False)

        # Negative inventory items
        negative_stock = df_export[df_export['CurrentStock'] < 0].copy()
        if len(negative_stock) > 0:
            negative_stock = negative_stock.sort_values('CurrentStock')
            negative_stock.to_excel(writer, sheet_name='Negative_Inventory', index=False)

        # Top movers (last 30 days)
        top_movers = df_export.nlargest(50, 'TotalSold30D')
        top_movers.to_excel(writer, sheet_name='Top_50_Movers', index=False)

    print(f"\n✅ Export complete!")
    print(f"\nFile: {filename}")
    print(f"Total products: {len(df_export)}")
    print(f"Negative inventory items: {len(df_export[df_export['CurrentStock'] < 0])}")
    print(f"Total stock value: ${(df_export['CurrentStock'] * df_export['Cost']).sum():,.2f}")
    print(f"Total sales (30 days): {df_export['TotalSold30D'].sum():,.0f} units")

    # Print sample
    print("\n" + "="*100)
    print("SAMPLE DATA (First 10 rows)")
    print("="*100)
    print(df_export.head(10).to_string())

if __name__ == "__main__":
    main()
