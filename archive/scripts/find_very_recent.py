#!/usr/bin/env python3
"""
Find very recent transactions (last hour) to locate the $1 adjustment
"""

import pymssql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', '10.1.10.105')
database = os.getenv('DB_DATABASE', 'GAWDB')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

SEARCH_VALUE = "24158012204903"

def find_very_recent():
    """Find transactions from the last hour"""
    
    print(f"🔍 Looking for VERY recent transactions (last hour)...")
    print(f"🎯 Searching for '{SEARCH_VALUE}' or $1 adjustments")
    print("=" * 60)
    
    try:
        conn = pymssql.connect(
            server=server,
            user=username,
            password=password,
            database=database,
            tds_version='7.0'
        )
        cursor = conn.cursor()
        
        # Get very recent timestamp (last 1 hour)
        very_recent = datetime.now() - timedelta(hours=1)
        
        print(f"Searching for transactions since: {very_recent}")
        print()
        
        # 1. Get ALL recent transactions (any amount)
        print("🔍 ALL transactions in the last hour:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT TOP 50
                t.TransactionNumber,
                t.Time,
                t.CustomerID,
                t.Total,
                t.Comment,
                t.ReferenceNumber,
                c.FirstName,
                c.LastName,
                c.Company
            FROM [dbo].[Transaction] t
            LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
            WHERE t.Time >= %s
            ORDER BY t.Time DESC
        """, (very_recent,))
        
        all_recent = cursor.fetchall()
        
        if all_recent:
            print(f"Found {len(all_recent)} transactions in the last hour:")
            
            for row in all_recent:
                trans_num, time, cust_id, total, comment, ref_num, fname, lname, company = row
                customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                
                print(f"\n  📝 Transaction #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Total: ${float(total):.2f}")
                print(f"    Customer: {customer_name} (ID: {cust_id})")
                print(f"    Comment: {comment or 'None'}")
                print(f"    Reference: {ref_num or 'None'}")
                
                # Highlight if this contains our search value or is $1
                if abs(float(total)) == 1.00:
                    print(f"    💰 THIS IS A $1 TRANSACTION!")
                
                if ((comment and SEARCH_VALUE in str(comment)) or 
                    (ref_num and SEARCH_VALUE in str(ref_num))):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
        else:
            print("No transactions found in the last hour")
        
        # 2. Check TransactionEntry for recent entries
        print(f"\n🔍 Transaction entries in the last hour:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT TOP 50
                te.ID,
                te.TransactionNumber,
                te.ItemID,
                te.Price,
                te.Quantity,
                te.Comment,
                i.ItemLookupCode,
                i.Description,
                t.Time
            FROM dbo.TransactionEntry te
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
            WHERE t.Time >= %s
            ORDER BY t.Time DESC, te.ID DESC
        """, (very_recent,))
        
        recent_entries = cursor.fetchall()
        
        if recent_entries:
            print(f"Found {len(recent_entries)} transaction entries:")
            
            for row in recent_entries[:10]:  # Show first 10
                entry_id, trans_num, item_id, price, qty, comment, upc, desc, time = row
                total_line = float(price) * float(qty) if price and qty else 0
                
                print(f"\n  📄 Entry ID: {entry_id}")
                print(f"    Transaction: #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Item: {desc or 'Unknown'} (ID: {item_id})")
                print(f"    UPC: {upc or 'None'}")
                print(f"    Price: ${float(price):.2f} x {float(qty)} = ${total_line:.2f}")
                print(f"    Comment: {comment or 'None'}")
                
                # Check for our search value or $1 amount
                if abs(total_line) == 1.00:
                    print(f"    💰 THIS IS A $1 LINE ITEM!")
                
                if ((comment and SEARCH_VALUE in str(comment)) or 
                    (upc and SEARCH_VALUE in str(upc)) or
                    (desc and SEARCH_VALUE in str(desc))):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
            
            if len(recent_entries) > 10:
                print(f"\n  ... and {len(recent_entries) - 10} more entries")
        else:
            print("No transaction entries found in the last hour")
        
        # 3. Search for any records containing our exact value anywhere
        print(f"\n🔍 Searching ALL recent records for '{SEARCH_VALUE}':")
        print("-" * 50)
        
        # Search across multiple tables for the exact value
        search_tables = [
            ("Transaction", "Comment", "TransactionNumber"),
            ("Transaction", "ReferenceNumber", "TransactionNumber"),
            ("TransactionEntry", "Comment", "ID"),
            ("Payment", "Comment", "ID"),
            ("Customer", "Notes", "ID"),
            ("Item", "Description", "ID"),
            ("Item", "ItemLookupCode", "ID"),
            ("Item", "Notes", "ID"),
        ]
        
        found_matches = False
        
        for table, column, id_column in search_tables:
            try:
                query = f"""
                    SELECT TOP 10 {id_column}, {column}, 
                           CASE WHEN EXISTS (SELECT 1 FROM [dbo].[Transaction] WHERE TransactionNumber = {table}.{id_column}) 
                                THEN (SELECT Time FROM [dbo].[Transaction] WHERE TransactionNumber = {table}.{id_column})
                                ELSE NULL END as TransTime
                    FROM dbo.{table}
                    WHERE {column} LIKE %s
                """
                
                # Special handling for Transaction table
                if table == "Transaction":
                    query = f"""
                        SELECT {id_column}, {column}, Time
                        FROM [dbo].{table}
                        WHERE {column} LIKE %s
                        ORDER BY Time DESC
                    """
                
                cursor.execute(query, (f'%{SEARCH_VALUE}%',))
                results = cursor.fetchall()
                
                if results:
                    found_matches = True
                    print(f"\n  ✅ Found {len(results)} matches in {table}.{column}:")
                    
                    for row in results:
                        record_id, value, trans_time = row
                        print(f"    🎯 {table} ID {record_id}: {value}")
                        if trans_time:
                            print(f"       Time: {trans_time}")
                        
            except Exception as e:
                # Skip problematic queries
                continue
        
        if not found_matches:
            print("No matches found for the search value")
        
        # 4. Check the most recent transaction number
        print(f"\n🔍 Latest transaction information:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT TOP 1 TransactionNumber, Time, Total, Comment, ReferenceNumber
            FROM [dbo].[Transaction]
            ORDER BY TransactionNumber DESC
        """)
        
        latest = cursor.fetchone()
        if latest:
            trans_num, time, total, comment, ref_num = latest
            print(f"Latest transaction: #{trans_num}")
            print(f"Time: {time}")
            print(f"Total: ${float(total):.2f}")
            print(f"Comment: {comment or 'None'}")
            print(f"Reference: {ref_num or 'None'}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎯 VERY RECENT SEARCH COMPLETE")
        print("The adjustment should appear in the results above if it was processed.")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_very_recent() 