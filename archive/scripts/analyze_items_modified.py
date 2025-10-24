import csv

# Analyze the Items Modified file structure
print("Analyzing Items- 06202025 MODIFIED.csv structure...")
print("=" * 80)

with open("Items- 06202025 MODIFIED.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    # Show header columns
    print(f"Total columns: {len(header)}")
    print("\nKey columns:")
    for i, col in enumerate(header):
        if i in [0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 28, 29]:
            print(f"  Column {i}: {col}")
    
    print("\n" + "=" * 80)
    print("Analyzing first 5 rows to understand the pattern...")
    
    for row_num, row in enumerate(reader, 1):
        if row_num > 5:
            break
            
        print(f"\nRow {row_num}:")
        
        # Column 1 has the BID line
        bid_line = row[1] if len(row) > 1 else ""
        print(f"  BID line: {bid_line[:50]}...")
        
        if 'BID' in bid_line:
            # Extract UPC (positions 5-18)
            upc = bid_line[5:18] if len(bid_line) >= 18 else ""
            print(f"  UPC (13 digits): {upc}")
            
            # Extract product name (positions 18-118)
            product = bid_line[18:118].strip() if len(bid_line) >= 118 else ""
            print(f"  Product: {product}")
        
        # Columns 2-15 appear to be different length extractions from the UPC
        print(f"  Column 2 (3 digits): {row[2] if len(row) > 2 else ''}")
        print(f"  Column 3 (4 digits): {row[3] if len(row) > 3 else ''}")
        print(f"  Column 4 (5 digits): {row[4] if len(row) > 4 else ''}")
        print(f"  Column 5 (6 digits): {row[5] if len(row) > 5 else ''}")
        
        # Column 29 is TRUE MATCH
        print(f"  Column 28 (TRUE MATCH): {row[28] if len(row) > 28 else ''}")
        
        # Column 30 is the SKU when matched
        print(f"  Column 29 (SKU): {row[29] if len(row) > 29 else ''}")

print("\n" + "=" * 80)
print("Looking for rows where TRUE MATCH = 1...")

# Find all matches
with open("Items- 06202025 MODIFIED.csv", 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    
    matches = []
    for row in reader:
        if len(row) > 29 and row[28] == '1':
            bid_line = row[1] if len(row) > 1 else ""
            if 'BID' in bid_line and len(bid_line) >= 18:
                upc = bid_line[5:18]
                sku = row[29].strip()
                product = bid_line[18:118].strip() if len(bid_line) >= 118 else ""
                matches.append((upc, sku, product))
    
    print(f"Found {len(matches)} matches:")
    for i, (upc, sku, product) in enumerate(matches[:10], 1):
        print(f"  {i}. UPC {upc} -> SKU {sku} ({product[:40]}...)")

print("\n" + "=" * 80)
print("Understanding the logic:")
print("The file tries different length substrings of the UPC to match against POS SKUs")
print("Columns 2-15 contain progressively longer substrings (3-15 digits)")
print("When a match is found, column 28 = 1 and column 29 has the matching SKU")