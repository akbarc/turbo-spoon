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
    
    # Check the Category table structure
    print("\nChecking Category table structure...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Category'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    print(f"\nCategory table columns:")
    for col_name, data_type in columns:
        print(f"  - {col_name}: {data_type}")
    
    # Get all categories
    print("\n" + "="*60)
    print("Getting all categories from Category table...")
    cursor.execute("""
        SELECT * FROM Category
        ORDER BY CategoryID
    """)
    
    categories = cursor.fetchall()
    print(f"\nFound {len(categories)} categories:")
    print("-"*40)
    for row in categories:
        print(f"ID: {row[0]:3}, Name: {row[1]}")
    
    # Now check how products link to categories
    print("\n" + "="*60)
    print("Checking Product table for category linkage...")
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Product' 
        AND (COLUMN_NAME LIKE '%categ%' OR COLUMN_NAME LIKE '%group%' OR COLUMN_NAME = 'CategoryID')
    """)
    
    prod_cat_cols = cursor.fetchall()
    print(f"\nProduct table category-related columns:")
    for col in prod_cat_cols:
        print(f"  - {col[0]}")
    
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
            p.Description,
            p.CategoryID,
            c.CategoryName
        FROM Product p
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        WHERE p.Barcode IN ('{barcode_list}')
        ORDER BY c.CategoryID, p.Barcode
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"\nMatched {len(results)} products with categories")
    
    # Count category distribution
    category_counts = Counter()
    category_names_dict = {}
    
    for barcode, desc, cat_id, cat_name in results:
        category_counts[cat_id] += 1
        if cat_id not in category_names_dict:
            category_names_dict[cat_id] = cat_name
    
    # Write full results to file
    output_file = 'Sales_Products_With_Categories.csv'
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
    print(f"Products not found: {len(sales_barcodes) - len(results)}")
    
    # Now update the sales file with actual category names
    print("\n" + "="*60)
    print("Creating sales file with actual category names...")
    
    # Create a dictionary for quick lookup
    barcode_to_category = {}
    for barcode, desc, cat_id, cat_name in results:
        barcode_to_category[barcode] = (cat_id, cat_name)
    
    # Process sales file
    with open('Sales - 06202025.csv', 'r') as infile:
        with open('Sales_With_Real_Categories.csv', 'w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            writer.writerow(['Customer_ID', 'Barcode', 'Category_ID', 'Category_Name', 'Quantity', 'Price'])
            
            for row in reader:
                if len(row) >= 4:
                    customer_id = row[0].strip()
                    barcode = row[1].strip()
                    quantity = row[2].strip()
                    price = row[3].strip()
                    
                    if barcode in barcode_to_category:
                        cat_id, cat_name = barcode_to_category[barcode]
                    else:
                        cat_id, cat_name = 'NOT_FOUND', 'NOT_FOUND'
                    
                    writer.writerow([customer_id, barcode, cat_id, cat_name, quantity, price])
    
    print(f"Sales with real categories saved to: Sales_With_Real_Categories.csv")
    
    conn.close()
    print("\nDatabase connection closed.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()