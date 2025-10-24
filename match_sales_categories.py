import csv

items_file = 'Items- 06202025.csv'
sales_file = 'Sales - 06202025.csv'
output_file = 'Sales_with_Categories_06202025.csv'

print("Loading Items data (POS)...")
items_dict = {}
with open(items_file, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            barcode = row[0].strip()
            category = row[1].strip()
            items_dict[barcode] = category

print(f"Loaded {len(items_dict)} items from POS")

print("\nProcessing Sales data...")
sales_with_categories = []
missing_barcodes = set()

with open(sales_file, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 4:
            customer_id = row[0].strip()
            barcode = row[1].strip()
            quantity = row[2].strip()
            price = row[3].strip()
            
            category = items_dict.get(barcode, 'NOT_FOUND')
            if category == 'NOT_FOUND':
                missing_barcodes.add(barcode)
            
            sales_with_categories.append([customer_id, barcode, category, quantity, price])

print(f"Processed {len(sales_with_categories)} sales records")

print("\nWriting output file...")
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Customer_ID', 'Barcode', 'Category', 'Quantity', 'Price'])
    writer.writerows(sales_with_categories)

print(f"\nOutput saved to: {output_file}")
print(f"Total sales records: {len(sales_with_categories)}")
print(f"Barcodes not found in POS: {len(missing_barcodes)}")

if missing_barcodes:
    print("\nFirst 10 missing barcodes:")
    for i, barcode in enumerate(list(missing_barcodes)[:10]):
        print(f"  {barcode}")