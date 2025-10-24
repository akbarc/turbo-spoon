import pymssql
import os
from dotenv import load_dotenv
import csv
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
    
    # Get all categories using correct column names
    print("\n" + "="*60)
    print("Getting all categories from Category table...")
    cursor.execute("""
        SELECT ID, Name, Code, DepartmentID
        FROM Category
        ORDER BY ID
    """)
    
    categories = cursor.fetchall()
    print(f"\nFound {len(categories)} categories in database:")
    print("-"*60)
    for cat_id, name, code, dept_id in categories:
        print(f"ID: {cat_id:3}, Name: {name:30}, Code: {code if code else 'N/A':10}, DeptID: {dept_id}")
    
    # Now check Product table structure
    print("\n" + "="*60)
    print("Checking Product table structure...")
    cursor.execute("""
        SELECT TOP 5 * FROM Product
    """)
    
    sample_products = cursor.fetchall()
    
    # Get column names
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Product'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = [row[0] for row in cursor.fetchall()]
    print(f"\nProduct table has {len(columns)} columns")
    
    # Look for category-related columns
    category_columns = [col for col in columns if 'categ' in col.lower() or 'group' in col.lower() or col.lower() == 'categoryid']
    print(f"\nCategory-related columns in Product table: {category_columns}")
    
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
    # Using ItemNumber as barcode field based on previous investigations
    barcode_list = "','".join(sales_barcodes)
    query = f"""
        SELECT 
            p.ItemNumber as Barcode,
            p.ItemName as Description,
            p.CategoryID,
            c.Name as CategoryName
        FROM Product p
        LEFT JOIN Category c ON p.CategoryID = c.ID
        WHERE p.ItemNumber IN ('{barcode_list}')
        ORDER BY p.CategoryID, p.ItemNumber
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"\nMatched {len(results)} products with categories")
    
    if len(results) == 0:
        # Try with different column names
        print("\nTrying alternative column names...")
        query = f"""
            SELECT TOP 10
                ItemNumber,
                ItemName,
                CategoryID
            FROM Product
            WHERE ItemNumber IS NOT NULL
        """
        cursor.execute(query)
        sample = cursor.fetchall()
        print("\nSample products:")
        for row in sample:
            print(f"  Barcode: {row[0]}, Name: {row[1]}, CategoryID: {row[2]}")
    
    # Count category distribution
    category_counts = Counter()
    category_names_dict = {}
    
    for row in results:
        barcode, desc, cat_id, cat_name = row
        category_counts[cat_id] += 1
        if cat_id not in category_names_dict:
            category_names_dict[cat_id] = cat_name
    
    # Write full results to file
    if len(results) > 0:
        output_file = 'Sales_Products_With_Real_Categories.csv'
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Barcode', 'Product_Description', 'Category_ID', 'Category_Name'])
            for row in results:
                writer.writerow(row)
        
        print(f"\nFull results saved to: {output_file}")
        
        # Show category distribution
        print("\n" + "="*60)
        print("CATEGORY DISTRIBUTION IN SALES:")
        print("="*60)
        
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        for cat_id, count in sorted_categories:
            cat_name = category_names_dict.get(cat_id, 'Unknown')
            print(f"Category {cat_id:3}: {cat_name:30} - {count:4} products")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"{'='*60}")
    print(f"Total unique categories in database: {len(categories)}")
    print(f"Categories used in sales: {len(category_counts)}")
    print(f"Total products matched: {len(results)}")
    print(f"Products not found in database: {len(sales_barcodes) - len(results)}")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()