import pymssql
import os
from dotenv import load_dotenv
import csv

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
    
    # First, let's find tables that might contain category information
    print("\nSearching for category-related tables...")
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        AND (TABLE_NAME LIKE '%categ%' OR TABLE_NAME LIKE '%group%' OR TABLE_NAME LIKE '%type%')
        ORDER BY TABLE_NAME
    """)
    
    tables = cursor.fetchall()
    print(f"\nFound {len(tables)} potential category tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check for product groups or categories
    print("\n" + "="*60)
    print("Checking tblProductGroups for categories...")
    cursor.execute("""
        SELECT GroupID, GroupName
        FROM tblProductGroups
        ORDER BY GroupID
    """)
    
    categories = cursor.fetchall()
    print(f"\nFound {len(categories)} product groups/categories:")
    print("-"*40)
    for cat_id, cat_name in categories:
        print(f"{cat_id:3}: {cat_name}")
    
    # Now let's match the sales barcodes with their categories
    print("\n" + "="*60)
    print("Matching sales barcodes with categories from database...")
    
    # Read the sales file
    sales_barcodes = set()
    with open('Sales - 06202025.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                barcode = row[1].strip()
                sales_barcodes.add(barcode)
    
    print(f"\nFound {len(sales_barcodes)} unique barcodes in sales")
    
    # Get product information with categories for these barcodes
    barcode_list = "','".join(sales_barcodes)
    query = f"""
        SELECT 
            p.Barcode,
            p.Description as ProductName,
            p.GroupID,
            pg.GroupName as CategoryName
        FROM tblProducts p
        LEFT JOIN tblProductGroups pg ON p.GroupID = pg.GroupID
        WHERE p.Barcode IN ('{barcode_list}')
        ORDER BY pg.GroupID, p.Barcode
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"\nMatched {len(results)} products with categories")
    
    # Write results to file
    output_file = 'Sales_Barcodes_With_DB_Categories.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Barcode', 'Product_Name', 'Category_ID', 'Category_Name'])
        for row in results:
            writer.writerow(row)
    
    print(f"\nResults saved to: {output_file}")
    
    # Show category distribution
    print("\n" + "="*60)
    print("Category distribution in sales:")
    cursor.execute(f"""
        SELECT 
            pg.GroupID,
            pg.GroupName,
            COUNT(DISTINCT p.Barcode) as ProductCount
        FROM tblProducts p
        LEFT JOIN tblProductGroups pg ON p.GroupID = pg.GroupID
        WHERE p.Barcode IN ('{barcode_list}')
        GROUP BY pg.GroupID, pg.GroupName
        ORDER BY COUNT(DISTINCT p.Barcode) DESC
    """)
    
    distribution = cursor.fetchall()
    print("-"*60)
    for group_id, group_name, count in distribution:
        print(f"{group_id:3}: {group_name:30} - {count:3} products")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()