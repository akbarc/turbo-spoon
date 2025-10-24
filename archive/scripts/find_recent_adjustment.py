#!/usr/bin/env python3
"""
Find recent $1 adjustments/transactions to trace where they are stored
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

def find_recent_adjustments():
    """Find recent $1 transactions and adjustments"""
    
    print(f"🔍 Looking for recent $1 adjustments/transactions...")
    print(f"🎯 Also searching for reference '{SEARCH_VALUE}'")
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
        
        # Get recent timestamp for searching (last 2 hours)
        recent_time = datetime.now() - timedelta(hours=2)
        
        print(f"Searching for transactions since: {recent_time}")
        print()
        
        # 1. Search for recent $1 transactions
        print("🔍 Recent $1 transactions:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 20 
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
            WHERE (ABS(t.Total - 1.00) < 0.01 OR ABS(t.Total + 1.00) < 0.01)
               OR t.Time >= %s
            ORDER BY t.Time DESC
        """, (recent_time,))
        
        recent_transactions = cursor.fetchall()
        
        if recent_transactions:
            print(f"Found {len(recent_transactions)} recent transactions:")
            for row in recent_transactions:
                trans_num, time, cust_id, total, comment, ref_num, fname, lname, company = row
                customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                
                print(f"\n  Transaction #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Total: ${total:.2f}")
                print(f"    Customer: {customer_name} (ID: {cust_id})")
                print(f"    Comment: {comment or 'None'}")
                print(f"    Reference: {ref_num or 'None'}")
                
                # Check if this transaction has our search value
                if (comment and SEARCH_VALUE in str(comment)) or (ref_num and SEARCH_VALUE in str(ref_num)):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
        else:
            print("No recent transactions found")
        
        # 2. Search TransactionEntry for $1 items
        print(f"\n🔍 Recent $1 transaction entries:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 20
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
            WHERE (ABS(te.Price - 1.00) < 0.01 OR ABS(te.Price + 1.00) < 0.01)
               OR (ABS(te.Price * te.Quantity - 1.00) < 0.01)
               OR t.Time >= %s
            ORDER BY t.Time DESC
        """, (recent_time,))
        
        transaction_entries = cursor.fetchall()
        
        if transaction_entries:
            print(f"Found {len(transaction_entries)} recent transaction entries:")
            for row in transaction_entries:
                entry_id, trans_num, item_id, price, qty, comment, upc, desc, time = row
                total_line = float(price) * float(qty) if price and qty else 0
                
                print(f"\n  Entry ID: {entry_id}")
                print(f"    Transaction: #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Item: {desc or 'Unknown'} (ID: {item_id})")
                print(f"    UPC: {upc or 'None'}")
                print(f"    Price: ${price:.2f} x {qty} = ${total_line:.2f}")
                print(f"    Comment: {comment or 'None'}")
                
                # Check if this has our search value
                if ((comment and SEARCH_VALUE in str(comment)) or 
                    (upc and SEARCH_VALUE in str(upc)) or
                    (desc and SEARCH_VALUE in str(desc))):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
        else:
            print("No recent transaction entries found")
        
        # 3. Search for adjustment-type transactions
        print(f"\n🔍 Recent adjustment-type transactions:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 20
                t.TransactionNumber,
                t.Time,
                t.Total,
                t.Comment,
                t.ReferenceNumber,
                te.Price,
                te.Quantity,
                te.Comment as EntryComment,
                i.Description,
                i.ItemLookupCode
            FROM [dbo].[Transaction] t
            LEFT JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
            WHERE t.Time >= %s
               AND (t.Comment LIKE '%adjust%' 
                    OR t.Comment LIKE '%correction%'
                    OR te.Comment LIKE '%adjust%'
                    OR te.Comment LIKE '%correction%'
                    OR i.Description LIKE '%adjust%')
            ORDER BY t.Time DESC
        """, (recent_time,))
        
        adjustments = cursor.fetchall()
        
        if adjustments:
            print(f"Found {len(adjustments)} recent adjustments:")
            for row in adjustments:
                trans_num, time, total, comment, ref_num, price, qty, entry_comment, desc, upc = row
                
                print(f"\n  Adjustment Transaction #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Total: ${total:.2f}")
                print(f"    Comment: {comment or 'None'}")
                print(f"    Reference: {ref_num or 'None'}")
                print(f"    Item: {desc or 'N/A'}")
                print(f"    UPC: {upc or 'N/A'}")
                print(f"    Entry Comment: {entry_comment or 'None'}")
                
                # Check for our search value
                if any(SEARCH_VALUE in str(field) for field in [comment, ref_num, entry_comment, desc, upc] if field):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
        else:
            print("No recent adjustments found")
        
        # 4. Check Payment table for recent $1 payments
        print(f"\n🔍 Recent $1 payments:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 10
                p.ID,
                p.CustomerID,
                p.Time,
                p.Amount,
                p.Comment,
                c.FirstName,
                c.LastName,
                c.Company
            FROM dbo.Payment p
            LEFT JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE (ABS(p.Amount - 1.00) < 0.01 OR ABS(p.Amount + 1.00) < 0.01)
               OR p.Time >= %s
            ORDER BY p.Time DESC
        """, (recent_time,))
        
        payments = cursor.fetchall()
        
        if payments:
            print(f"Found {len(payments)} recent payments:")
            for row in payments:
                pay_id, cust_id, time, amount, comment, fname, lname, company = row
                customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                
                print(f"\n  Payment ID: {pay_id}")
                print(f"    Time: {time}")
                print(f"    Amount: ${amount:.2f}")
                print(f"    Customer: {customer_name} (ID: {cust_id})")
                print(f"    Comment: {comment or 'None'}")
                
                if comment and SEARCH_VALUE in str(comment):
                    print(f"    🎯 CONTAINS SEARCH VALUE!")
        else:
            print("No recent payments found")
        
        # 5. Search for the exact value as a string in recent records
        print(f"\n🔍 Searching recent records for '{SEARCH_VALUE}':")
        print("-" * 40)
        
        # Search in all recent transactions for this exact value
        cursor.execute("""
            SELECT 
                'Transaction' as TableName,
                t.TransactionNumber as ID,
                t.Time,
                'Comment' as Field,
                t.Comment as Value
            FROM [dbo].[Transaction] t
            WHERE t.Time >= %s
              AND t.Comment LIKE %s
            
            UNION ALL
            
            SELECT 
                'Transaction' as TableName,
                t.TransactionNumber as ID,
                t.Time,
                'ReferenceNumber' as Field,
                t.ReferenceNumber as Value
            FROM [dbo].[Transaction] t
            WHERE t.Time >= %s
              AND t.ReferenceNumber LIKE %s
            
            UNION ALL
            
            SELECT 
                'TransactionEntry' as TableName,
                te.ID,
                t.Time,
                'Comment' as Field,
                te.Comment as Value
            FROM dbo.TransactionEntry te
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= %s
              AND te.Comment LIKE %s
            
            ORDER BY Time DESC
        """, (recent_time, f'%{SEARCH_VALUE}%', recent_time, f'%{SEARCH_VALUE}%', recent_time, f'%{SEARCH_VALUE}%'))
        
        exact_matches = cursor.fetchall()
        
        if exact_matches:
            print(f"🎯 Found {len(exact_matches)} exact matches!")
            for row in exact_matches:
                table, record_id, time, field, value = row
                print(f"\n  ✅ MATCH FOUND!")
                print(f"    Table: {table}")
                print(f"    Record ID: {record_id}")
                print(f"    Time: {time}")
                print(f"    Field: {field}")
                print(f"    Value: {value}")
        else:
            print("No exact matches found in recent records")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎯 SEARCH COMPLETE")
        print("If you just made the adjustment, it should appear in the results above.")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_recent_adjustments() 