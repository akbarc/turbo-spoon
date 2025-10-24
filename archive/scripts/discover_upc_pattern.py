import csv

print("Discovering the UPC to SKU extraction LOGIC from Items Modified file...")
print("=" * 80)

# Read the Items Modified file
with open("Items- 06202025 MODIFIED.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    print("Understanding the columns:")
    print(f"  Column 1: {header[1]} (contains full BID line)")
    print(f"  Columns 2-14: Different length UPC substrings")
    for i in range(2, 15):
        print(f"    Column {i}: {header[i]}")
    print(f"  Columns 15-27: Match indicators for each length")
    print(f"  Column 28: {header[28]} (final match indicator)")
    print(f"  Column 29: {header[29]} (matched SKU)")
    
    print("\n" + "=" * 80)
    print("Analyzing actual data rows...")
    
    # Look at first 20 rows to understand the pattern
    for row_num, row in enumerate(reader, 1):
        if row_num > 20:
            break
            
        bid_line = row[1] if len(row) > 1 else ""
        
        if 'BID' in bid_line and len(bid_line) >= 18:
            full_upc = bid_line[5:18]
            product = bid_line[18:118].strip() if len(bid_line) >= 118 else ""
            
            print(f"\nRow {row_num}: {product[:40]}...")
            print(f"  Full UPC: {full_upc}")
            
            # Check what substrings are extracted
            print(f"  Substrings extracted from UPC:")
            for col in range(2, 15):
                if col < len(row) and row[col]:
                    digit_count = col + 1  # Column 2 = 3 digits, Column 3 = 4 digits, etc.
                    print(f"    {digit_count:2} digits: {row[col]}")
            
            # Check if there's a match
            if len(row) > 28 and row[28] == '1':
                if len(row) > 29 and row[29]:
                    print(f"  ✓ MATCHED! SKU = {row[29]}")
                else:
                    print(f"  ✓ Match found but no SKU in column 29")

print("\n" + "=" * 80)
print("KEY INSIGHT:")
print("The logic is extracting different length substrings from the MSA UPC")
print("and trying to match them against POS SKUs.")
print("\nThe extraction appears to be from the END of the UPC (right side)")
print("For example, UPC 6092499034260:")
print("  3 digits: 260 (last 3)")
print("  4 digits: 4260 (last 4)")
print("  5 digits: 34260 (last 5)")
print("  etc...")
print("\nWhen a substring matches a POS SKU, that's the mapping!")