import csv

sales_file = 'Sales - 06202025.csv'

print("Extracting all unique barcodes from Sales data...")
barcodes = set()

with open(sales_file, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            barcode = row[1].strip()
            barcodes.add(barcode)

sorted_barcodes = sorted(barcodes)

print(f"\nTotal unique barcodes: {len(sorted_barcodes)}\n")
print("All barcodes:")
print("-" * 20)
for barcode in sorted_barcodes:
    print(barcode)