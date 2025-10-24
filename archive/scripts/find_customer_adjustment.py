#!/usr/bin/env python3
"""
Find transactions for customer account 6784635564 and the $1 adjustment
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
CUSTOMER_ACCOUNT = "6784635564"

def find_customer_adjustment():
    """Find the customer and their recent transactions"""
    
    print(f"🔍 Looking for customer account: {CUSTOMER_ACCOUNT}")
    print(f"🎯 And searching for reference: {SEARCH_VALUE}")
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
        
        # 1. Find the customer by account number
        print("🔍 Finding customer by account number:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT ID, FirstName, LastName, Company, AccountNumber, 
                   PhoneNumber, EmailAddress, Notes
            FROM dbo.Customer
            WHERE AccountNumber = %s
               OR AccountNumber LIKE %s
        """, (CUSTOMER_ACCOUNT, f'%{CUSTOMER_ACCOUNT}%'))
        
        customers = cursor.fetchall()
        
        if customers:
            print(f"Found {len(customers)} customer(s):")
            customer_ids = []
            
            for row in customers:
                cust_id, fname, lname, company, account, phone, email, notes = row
                customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                customer_ids.append(cust_id)
                
                print(f"\n  👤 Customer ID: {cust_id}")
                print(f"    Name: {customer_name}")
                print(f"    Account: {account}")
                print(f"    Phone: {phone or 'None'}")
                print(f"    Email: {email or 'None'}")
                print(f"    Notes: {notes or 'None'}")
                
                # Check if notes contain our search value
                if notes and SEARCH_VALUE in str(notes):
                    print(f"    🎯 NOTES CONTAIN SEARCH VALUE!")
        else:
            print(f"❌ No customer found with account number: {CUSTOMER_ACCOUNT}")
            
            # Try partial search
            print(f"\n🔍 Trying partial search for account containing '{CUSTOMER_ACCOUNT}':")
            cursor.execute("""
                SELECT ID, FirstName, LastName, Company, AccountNumber
                FROM dbo.Customer
                WHERE AccountNumber LIKE %s
                ORDER BY ID DESC
            """, (f'%{CUSTOMER_ACCOUNT[-6:]}%',))  # Try last 6 digits
            
            partial_customers = cursor.fetchall()
            if partial_customers:
                print(f"Found {len(partial_customers)} customers with similar account numbers:")
                customer_ids = []
                for row in partial_customers[:5]:  # Show first 5
                    cust_id, fname, lname, company, account = row
                    customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                    customer_ids.append(cust_id)
                    print(f"  ID: {cust_id}, Account: {account}, Name: {customer_name}")
            else:
                print("No customers found with similar account numbers")
                customer_ids = []
        
        # 2. If we found customers, get their recent transactions
        if customer_ids:
            print(f"\n🔍 Recent transactions for these customers:")
            print("-" * 40)
            
            # Get recent transactions (last 7 days)
            recent_time = datetime.now() - timedelta(days=7)
            
            for customer_id in customer_ids:
                cursor.execute("""
                    SELECT TOP 20
                        t.TransactionNumber,
                        t.Time,
                        t.Total,
                        t.Comment,
                        t.ReferenceNumber
                    FROM [dbo].[Transaction] t
                    WHERE t.CustomerID = %s
                      AND t.Time >= %s
                    ORDER BY t.Time DESC
                """, (customer_id, recent_time))
                
                transactions = cursor.fetchall()
                
                if transactions:
                    print(f"\n  📝 Customer {customer_id} - Found {len(transactions)} recent transactions:")
                    
                    for row in transactions:
                        trans_num, time, total, comment, ref_num = row
                        
                        print(f"\n    Transaction #{trans_num}")
                        print(f"      Time: {time}")
                        print(f"      Total: ${float(total):.2f}")
                        print(f"      Comment: {comment or 'None'}")
                        print(f"      Reference: {ref_num or 'None'}")
                        
                        # Highlight $1 transactions
                        if abs(float(total)) == 1.00:
                            print(f"      💰 THIS IS A $1 TRANSACTION!")
                        
                        # Check for our search value
                        if ((comment and SEARCH_VALUE in str(comment)) or 
                            (ref_num and SEARCH_VALUE in str(ref_num))):
                            print(f"      🎯 CONTAINS SEARCH VALUE!")
                else:
                    print(f"\n  ❌ No recent transactions for customer {customer_id}")
        
        # 3. Search for the reference value in ALL transactions regardless of customer
        print(f"\n🔍 Searching ALL transactions for reference '{SEARCH_VALUE}':")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 10
                t.TransactionNumber,
                t.Time,
                t.CustomerID,
                t.Total,
                t.Comment,
                t.ReferenceNumber,
                c.FirstName,
                c.LastName,
                c.Company,
                c.AccountNumber
            FROM [dbo].[Transaction] t
            LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
            WHERE t.Comment LIKE %s
               OR t.ReferenceNumber LIKE %s
            ORDER BY t.Time DESC
        """, (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%'))
        
        ref_transactions = cursor.fetchall()
        
        if ref_transactions:
            print(f"🎯 Found {len(ref_transactions)} transactions with reference '{SEARCH_VALUE}':")
            
            for row in ref_transactions:
                trans_num, time, cust_id, total, comment, ref_num, fname, lname, company, account = row
                customer_name = company if company else f"{fname or ''} {lname or ''}".strip() or "No Name"
                
                print(f"\n  ✅ MATCH FOUND!")
                print(f"    Transaction: #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Total: ${float(total):.2f}")
                print(f"    Customer: {customer_name} (ID: {cust_id})")
                print(f"    Customer Account: {account or 'None'}")
                print(f"    Comment: {comment or 'None'}")
                print(f"    Reference: {ref_num or 'None'}")
                
                if abs(float(total)) == 1.00:
                    print(f"    💰 THIS IS A $1 TRANSACTION!")
        else:
            print(f"❌ No transactions found with reference '{SEARCH_VALUE}'")
        
        # 4. Search TransactionEntry for the reference value
        print(f"\n🔍 Searching transaction entries for reference '{SEARCH_VALUE}':")
        print("-" * 40)
        
        cursor.execute("""
            SELECT TOP 10
                te.ID,
                te.TransactionNumber,
                te.Comment,
                te.Price,
                te.Quantity,
                t.Time,
                t.CustomerID,
                i.ItemLookupCode,
                i.Description
            FROM dbo.TransactionEntry te
            JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
            LEFT JOIN dbo.Item i ON te.ItemID = i.ID
            WHERE te.Comment LIKE %s
               OR i.ItemLookupCode LIKE %s
               OR i.Description LIKE %s
            ORDER BY t.Time DESC
        """, (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%'))
        
        entry_matches = cursor.fetchall()
        
        if entry_matches:
            print(f"🎯 Found {len(entry_matches)} transaction entries with reference:")
            
            for row in entry_matches:
                entry_id, trans_num, comment, price, qty, time, cust_id, upc, desc = row
                total_line = float(price) * float(qty) if price and qty else 0
                
                print(f"\n  ✅ ENTRY MATCH!")
                print(f"    Entry ID: {entry_id}")
                print(f"    Transaction: #{trans_num}")
                print(f"    Time: {time}")
                print(f"    Customer ID: {cust_id}")
                print(f"    Item: {desc or 'Unknown'}")
                print(f"    UPC: {upc or 'None'}")
                print(f"    Price: ${float(price):.2f} x {float(qty)} = ${total_line:.2f}")
                print(f"    Comment: {comment or 'None'}")
                
                if abs(total_line) == 1.00:
                    print(f"    💰 THIS IS A $1 LINE ITEM!")
        else:
            print(f"❌ No transaction entries found with reference '{SEARCH_VALUE}'")
        
        # 5. Check if there's an item with this UPC
        print(f"\n🔍 Checking if '{SEARCH_VALUE}' is a product UPC:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT ID, ItemLookupCode, Description, Price, Cost
            FROM dbo.Item
            WHERE ItemLookupCode = %s
               OR ItemLookupCode = %s
               OR ItemLookupCode = %s
        """, (SEARCH_VALUE, SEARCH_VALUE.lstrip('0'), f"0{SEARCH_VALUE}"))
        
        item_matches = cursor.fetchall()
        
        if item_matches:
            print(f"🎯 Found {len(item_matches)} items with this UPC:")
            
            for row in item_matches:
                item_id, upc, desc, price, cost = row
                print(f"\n  📦 Item ID: {item_id}")
                print(f"    UPC: {upc}")
                print(f"    Description: {desc}")
                print(f"    Price: ${float(price):.2f}")
                print(f"    Cost: ${float(cost):.2f}")
        else:
            print(f"❌ No items found with UPC '{SEARCH_VALUE}'")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎯 CUSTOMER SEARCH COMPLETE")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_customer_adjustment() 