import pymssql
import os
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv()

# Database connection parameters
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_DATABASE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')

print(f"Connecting to database: {database} on server: {server}")

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
    
    # Check Item table columns for UPC or barcode fields
    print("\nChecking Item table structure for UPC/barcode fields...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Item'
        AND (COLUMN_NAME LIKE '%UPC%' OR COLUMN_NAME LIKE '%barcode%' 
             OR COLUMN_NAME LIKE '%code%' OR COLUMN_NAME LIKE '%EAN%')
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    print(f"\nPotential barcode/UPC columns in Item table:")
    for col_name, data_type in columns:
        print(f"  - {col_name}: {data_type}")
    
    # Get sample data to understand the structure
    print("\n" + "="*60)
    print("Sample data from Item table (tobacco products):")
    cursor.execute("""
        SELECT TOP 10
            ItemLookupCode,
            Description,
            CategoryID,
            c.Name as CategoryName
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        WHERE c.Name LIKE '%NICOTINE%'
    """)
    
    results = cursor.fetchall()
    for row in results:
        print(f"  ItemLookupCode: {row[0]:20} | {row[1][:40]:40} | Cat: {row[3]}")
    
    # Check if there's an Alias or AlternateID table
    print("\n" + "="*60)
    print("Checking for alias/alternate ID tables...")
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        AND (TABLE_NAME LIKE '%alias%' OR TABLE_NAME LIKE '%alternate%' 
             OR TABLE_NAME LIKE '%UPC%' OR TABLE_NAME LIKE '%barcode%')
        ORDER BY TABLE_NAME
    """)
    
    tables = cursor.fetchall()
    if tables:
        print(f"\nFound potential UPC/alias tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # Check structure of these tables
            cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{table[0]}'
                ORDER BY ORDINAL_POSITION
            """)
            cols = [row[0] for row in cursor.fetchall()]
            print(f"    Columns: {', '.join(cols[:5])}...")
    
    # Now let's read a sample MSA barcode and try different matching approaches
    print("\n" + "="*60)
    print("Testing different barcode matching approaches...")
    
    # Get a few MSA barcodes
    msa_barcodes = []
    with open('MSA Data Fr/08082025', 'r') as f:
        for line in f:
            if line.startswith('BID'):
                barcode = line[5:18].strip().lstrip('0')
                if barcode and len(msa_barcodes) < 5:
                    msa_barcodes.append(barcode)
    
    print(f"\nSample MSA barcodes to test:")
    for bc in msa_barcodes:
        print(f"  {bc}")
    
    # Try to find these in different ways
    for barcode in msa_barcodes[:2]:  # Test first 2
        print(f"\nSearching for MSA barcode: {barcode}")
        
        # Try exact match
        cursor.execute("""
            SELECT ItemLookupCode, Description 
            FROM Item 
            WHERE ItemLookupCode = %s
        """, (barcode,))
        result = cursor.fetchone()
        if result:
            print(f"  Found exact match: {result[1]}")
        
        # Try LIKE match
        cursor.execute("""
            SELECT ItemLookupCode, Description 
            FROM Item 
            WHERE ItemLookupCode LIKE %s
        """, (f'%{barcode[-6:]}%',))  # Search by last 6 digits
        results = cursor.fetchall()
        if results:
            print(f"  Found {len(results)} partial matches:")
            for r in results[:3]:
                print(f"    {r[0]}: {r[1][:40]}")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()