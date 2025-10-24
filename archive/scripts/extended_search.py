#!/usr/bin/env python3
"""
Extended search for "24158012204903" - more creative patterns and all tables
"""

import pymssql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', '10.1.10.105')
database = os.getenv('DB_DATABASE', 'GAWDB')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

SEARCH_VALUE = "24158012204903"

def extended_search():
    """Extended search with creative patterns"""
    
    print(f"🔍 Extended search for '{SEARCH_VALUE}'...")
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
        
        # 1. Search for partial matches (substrings)
        print(f"\n🔍 Searching for partial matches...")
        
        # Try different partial patterns
        patterns = [
            SEARCH_VALUE[-8:],  # Last 8 digits: 04903
            SEARCH_VALUE[-6:],  # Last 6 digits: 204903
            SEARCH_VALUE[:8],   # First 8 digits: 24158012
            SEARCH_VALUE[2:-2], # Middle part: 15801220490
            SEARCH_VALUE[-4:],  # Last 4 digits: 4903
        ]
        
        for pattern in patterns:
            print(f"\n   Searching for pattern: '{pattern}'")
            
            # Search in Item table for this pattern
            try:
                item_query = """
                    SELECT TOP 10 ID, ItemLookupCode, Description
                    FROM dbo.Item
                    WHERE ItemLookupCode LIKE %s
                       OR Description LIKE %s
                """
                cursor.execute(item_query, (f'%{pattern}%', f'%{pattern}%'))
                results = cursor.fetchall()
                
                if results:
                    print(f"      ✅ Found {len(results)} items with pattern '{pattern}':")
                    for row in results:
                        print(f"         ID: {row[0]}, UPC: {row[1]}, Description: {row[2]}")
                else:
                    print(f"      ❌ No items found with pattern '{pattern}'")
                    
            except Exception as e:
                print(f"      ❌ Error searching pattern '{pattern}': {e}")
        
        # 2. Search all tables in database
        print(f"\n🔍 Searching ALL tables in database...")
        
        # Get all table names
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' 
            AND TABLE_SCHEMA = 'dbo'
            ORDER BY TABLE_NAME
        """)
        
        all_tables = [row[0] for row in cursor.fetchall()]
        print(f"   Found {len(all_tables)} tables to search")
        
        # Search each table for text columns containing our value
        for table_name in all_tables:
            try:
                # Get text columns for this table
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = %s 
                    AND TABLE_SCHEMA = 'dbo'
                    AND (DATA_TYPE LIKE '%char%' OR DATA_TYPE LIKE '%text%')
                """, (table_name,))
                
                text_columns = cursor.fetchall()
                
                if text_columns:
                    # Build dynamic search query
                    where_conditions = []
                    params = []
                    
                    for col_name, col_type in text_columns:
                        if col_type not in ['text', 'ntext']:  # Skip problematic text types in WHERE
                            where_conditions.append(f"[{col_name}] LIKE %s")
                            params.append(f'%{SEARCH_VALUE}%')
                    
                    if where_conditions:
                        query = f"""
                            SELECT TOP 5 *
                            FROM [dbo].[{table_name}]
                            WHERE {' OR '.join(where_conditions)}
                        """
                        
                        cursor.execute(query, params)
                        results = cursor.fetchall()
                        
                        if results:
                            print(f"   ✅ Found {len(results)} results in {table_name}")
                            # Get column names
                            column_names = [desc[0] for desc in cursor.description]
                            for i, row in enumerate(results[:2]):  # Show first 2
                                print(f"      Row {i+1}: {dict(zip(column_names, row))}")
                        
            except Exception as e:
                # Skip tables that cause errors (permissions, etc.)
                continue
        
        # 3. Search for similar UPC patterns
        print(f"\n🔍 Searching for similar UPC patterns...")
        
        # Check if this might be a UPC-A vs UPC-E or EAN conversion
        # UPC patterns to try
        upc_variants = [
            SEARCH_VALUE,
            SEARCH_VALUE.zfill(14),  # Pad to 14 digits with leading zeros
            SEARCH_VALUE.zfill(12),  # Pad to 12 digits 
            f"0{SEARCH_VALUE}",       # Add single leading zero
            SEARCH_VALUE[1:] if SEARCH_VALUE.startswith('0') else SEARCH_VALUE,  # Remove leading zero
        ]
        
        for variant in upc_variants:
            if variant != SEARCH_VALUE:  # Don't repeat exact search
                try:
                    cursor.execute("""
                        SELECT ID, ItemLookupCode, Description
                        FROM dbo.Item
                        WHERE ItemLookupCode = %s
                    """, (variant,))
                    
                    results = cursor.fetchall()
                    if results:
                        print(f"   ✅ Found match with variant '{variant}':")
                        for row in results:
                            print(f"      ID: {row[0]}, UPC: {row[1]}, Description: {row[2]}")
                            
                except Exception as e:
                    continue
        
        # 4. Search for numbers that contain this sequence
        print(f"\n🔍 Searching for numeric fields containing this sequence...")
        
        # Search primary key fields and other numeric fields
        numeric_searches = [
            ("Transaction", "TransactionNumber"),
            ("TransactionEntry", "ID"),
            ("Customer", "ID"),
            ("Item", "ID"),
            ("Payment", "ID"),
        ]
        
        for table, column in numeric_searches:
            try:
                query = f"""
                    SELECT TOP 10 *
                    FROM [dbo].[{table}]
                    WHERE CAST([{column}] AS VARCHAR) LIKE %s
                """
                cursor.execute(query, (f'%{SEARCH_VALUE}%',))
                results = cursor.fetchall()
                
                if results:
                    print(f"   ✅ Found {len(results)} results in {table}.{column}")
                    column_names = [desc[0] for desc in cursor.description]
                    for row in results[:2]:
                        print(f"      {dict(zip(column_names, row))}")
                        
            except Exception as e:
                continue
        
        # 5. Search for this value in datetime fields (if it could be a timestamp)
        print(f"\n🔍 Checking if this could be a timestamp...")
        
        # Check if this number could represent a Unix timestamp or other date format
        try:
            # Convert to potential timestamp formats
            if len(SEARCH_VALUE) >= 10:
                timestamp_val = int(SEARCH_VALUE[:10])  # Unix timestamp (first 10 digits)
                from datetime import datetime
                
                try:
                    dt = datetime.fromtimestamp(timestamp_val)
                    print(f"   💡 First 10 digits as Unix timestamp: {dt}")
                    
                    # Search for transactions around this date
                    cursor.execute("""
                        SELECT TOP 5 TransactionNumber, Time
                        FROM [dbo].[Transaction]
                        WHERE CAST(Time AS DATE) = %s
                    """, (dt.date(),))
                    
                    date_results = cursor.fetchall()
                    if date_results:
                        print(f"   ✅ Found {len(date_results)} transactions on {dt.date()}")
                        for row in date_results:
                            print(f"      Transaction: {row[0]}, Time: {row[1]}")
                            
                except (ValueError, OSError):
                    print(f"   ❌ Not a valid Unix timestamp")
                    
        except Exception as e:
            print(f"   ❌ Error in timestamp check: {e}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🔍 EXTENDED SEARCH COMPLETE")
        print("If no results found, this value may not exist in the database,")
        print("or it may be in a format/location not covered by these searches.")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    extended_search() 