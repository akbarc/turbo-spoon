#!/usr/bin/env python3
"""
Search for specific value "24158012204903" across the database
Looks in comments, references, descriptions, and other text fields
"""

import pymssql
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', '10.1.10.105')
database = os.getenv('DB_DATABASE', 'GAWDB')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

SEARCH_VALUE = "24158012204903"

def search_in_database():
    """Search for the specific value across multiple tables"""
    
    print(f"🔍 Searching for '{SEARCH_VALUE}' in database...")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = pymssql.connect(
            server=server,
            user=username,
            password=password,
            database=database,
            tds_version='7.0'
        )
        cursor = conn.cursor()
        
        results_found = []
        
        # Define search queries for different tables and fields
        search_queries = [
            {
                'table': 'Transaction',
                'query': """
                    SELECT TransactionNumber, Time, CustomerID, Total, Comment, ReferenceNumber
                    FROM [dbo].[Transaction]
                    WHERE Comment LIKE %s 
                       OR ReferenceNumber LIKE %s
                       OR CAST(TransactionNumber AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'TransactionEntry',
                'query': """
                    SELECT TOP 100 te.ID, te.TransactionNumber, te.ItemID, 
                           te.Price, te.Quantity, te.Comment,
                           i.Description, i.ItemLookupCode
                    FROM dbo.TransactionEntry te
                    LEFT JOIN dbo.Item i ON te.ItemID = i.ID
                    WHERE te.Comment LIKE %s
                       OR i.ItemLookupCode LIKE %s
                       OR i.Description LIKE %s
                       OR CAST(te.ID AS VARCHAR) LIKE %s
                       OR CAST(te.TransactionNumber AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', 
                          f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'Customer',
                'query': """
                    SELECT ID, FirstName, LastName, Company, AccountNumber, 
                           PhoneNumber, EmailAddress, Notes
                    FROM dbo.Customer
                    WHERE Notes LIKE %s
                       OR AccountNumber LIKE %s
                       OR PhoneNumber LIKE %s
                       OR EmailAddress LIKE %s
                       OR CAST(ID AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%',
                          f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'Item',
                'query': """
                    SELECT ID, ItemLookupCode, Description, Price, Cost, Notes
                    FROM dbo.Item
                    WHERE ItemLookupCode LIKE %s
                       OR Description LIKE %s
                       OR Notes LIKE %s
                       OR CAST(ID AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'Payment',
                'query': """
                    SELECT ID, CustomerID, Time, Amount, Comment
                    FROM dbo.Payment
                    WHERE Comment LIKE %s
                       OR CAST(ID AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'AccountReceivable',
                'query': """
                    SELECT ID, CustomerID, Date, OriginalAmount, TransactionNumber
                    FROM dbo.AccountReceivable
                    WHERE CAST(ID AS VARCHAR) LIKE %s
                       OR CAST(TransactionNumber AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            },
            {
                'table': 'AccountReceivableHistory',
                'query': """
                    SELECT ID, AccountReceivableID, Amount, Comment, Date
                    FROM dbo.AccountReceivableHistory
                    WHERE Comment LIKE %s
                       OR CAST(ID AS VARCHAR) LIKE %s
                       OR CAST(AccountReceivableID AS VARCHAR) LIKE %s
                """,
                'params': (f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%', f'%{SEARCH_VALUE}%')
            }
        ]
        
        # Execute searches
        for search in search_queries:
            print(f"\n🔍 Searching in {search['table']}...")
            
            try:
                cursor.execute(search['query'], search['params'])
                results = cursor.fetchall()
                
                if results:
                    print(f"   ✅ Found {len(results)} results in {search['table']}")
                    
                    # Get column names
                    column_names = [desc[0] for desc in cursor.description]
                    
                    # Store results
                    table_results = {
                        'table': search['table'],
                        'columns': column_names,
                        'data': results
                    }
                    results_found.append(table_results)
                    
                    # Display first few results
                    for i, row in enumerate(results[:5]):  # Show first 5 results
                        print(f"   Row {i+1}:")
                        for j, value in enumerate(row):
                            if value and str(value).find(SEARCH_VALUE) != -1:
                                print(f"      {column_names[j]}: {value} ⭐ MATCH")
                            else:
                                print(f"      {column_names[j]}: {value}")
                        print()
                        
                    if len(results) > 5:
                        print(f"   ... and {len(results) - 5} more results")
                    
                else:
                    print(f"   ❌ No results found in {search['table']}")
                    
            except Exception as e:
                print(f"   ❌ Error searching {search['table']}: {e}")
        
        # Additional search for UPC/Barcode patterns (exact match)
        print(f"\n🔍 Searching for exact UPC/Barcode matches...")
        try:
            upc_query = """
                SELECT i.ID, i.ItemLookupCode, i.Description, cat.Name as Category
                FROM dbo.Item i
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE i.ItemLookupCode = %s
                   OR i.ItemLookupCode = %s
                   OR i.ItemLookupCode = %s
            """
            # Try different formats
            cursor.execute(upc_query, (
                SEARCH_VALUE,  # Exact match
                SEARCH_VALUE.lstrip('0'),  # Remove leading zeros
                f"0{SEARCH_VALUE}"  # Add leading zero
            ))
            
            upc_results = cursor.fetchall()
            if upc_results:
                print(f"   ✅ Found {len(upc_results)} exact UPC matches")
                for row in upc_results:
                    print(f"   Item ID: {row[0]}, UPC: {row[1]}, Description: {row[2]}, Category: {row[3]}")
            else:
                print(f"   ❌ No exact UPC matches found")
                
        except Exception as e:
            print(f"   ❌ Error in UPC search: {e}")
        
        # Search in recent transactions for this UPC
        print(f"\n🔍 Searching recent transactions with this UPC...")
        try:
            recent_query = """
                SELECT TOP 20 
                    t.TransactionNumber, 
                    t.Time, 
                    te.Quantity,
                    te.Price,
                    i.ItemLookupCode,
                    i.Description
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                JOIN dbo.Item i ON te.ItemID = i.ID
                WHERE i.ItemLookupCode LIKE %s
                   OR i.ItemLookupCode = %s
                ORDER BY t.Time DESC
            """
            cursor.execute(recent_query, (f'%{SEARCH_VALUE}%', SEARCH_VALUE.lstrip('0')))
            
            transaction_results = cursor.fetchall()
            if transaction_results:
                print(f"   ✅ Found {len(transaction_results)} recent transactions")
                for row in transaction_results:
                    print(f"   Transaction: {row[0]}, Date: {row[1]}, Qty: {row[2]}, Price: ${row[3]:.2f}")
                    print(f"   UPC: {row[4]}, Item: {row[5]}")
                    print()
            else:
                print(f"   ❌ No recent transactions found")
                
        except Exception as e:
            print(f"   ❌ Error in transaction search: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 SEARCH SUMMARY:")
        if results_found:
            print(f"✅ Found matches in {len(results_found)} table(s):")
            for result in results_found:
                print(f"   • {result['table']}: {len(result['data'])} result(s)")
        else:
            print("❌ No matches found for this value")
            print(f"\n💡 Suggestions:")
            print(f"   • The value '{SEARCH_VALUE}' might be:")
            print(f"     - A UPC/barcode with different formatting")
            print(f"     - A partial match in a longer field")
            print(f"     - In a table not searched yet")
            print(f"     - A value that was deleted or modified")
        
        conn.close()
        return results_found
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return []

if __name__ == "__main__":
    results = search_in_database() 