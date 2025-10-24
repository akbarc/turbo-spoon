import csv
import pymssql
import os
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

print("Understanding the UPC to SKU matching LOGIC...")
print("=" * 80)

# Connect to database
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_NAME', 'database')
username = os.getenv('DB_USERNAME', 'user')
password = os.getenv('DB_PASSWORD', 'password')

conn = pymssql.connect(server, username, password, database)
cursor = conn.cursor()

# Get all POS SKUs
cursor.execute("SELECT DISTINCT ItemLookupCode FROM Item WHERE CategoryID IN (11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83)")
pos_skus = set([str(row[0]) for row in cursor.fetchall()])
print(f"Found {len(pos_skus)} POS SKUs in tobacco categories")

# Analyze the Items Modified file to understand the pattern
print("\nAnalyzing Items Modified file to discover the matching logic...")

with open("Items- 06202025 MODIFIED.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    # The columns represent different substring lengths
    print("\nColumn headers show the substring lengths being tested:")
    for i in range(2, 15):
        print(f"  Column {i}: {header[i]}")
    
    match_patterns = Counter()
    successful_matches = []
    
    for row_num, row in enumerate(reader, 1):
        if len(row) > 29:
            bid_line = row[1] if len(row) > 1 else ""
            
            if 'BID' in bid_line and len(bid_line) >= 18:
                # Extract the full UPC from BID line
                full_upc = bid_line[5:18]
                
                # Check each substring length (columns 2-14 are 3-15 digit substrings)
                for col_idx in range(2, 15):  # Columns 2-14
                    if col_idx < len(row):
                        substring = row[col_idx].strip()
                        if substring and substring in pos_skus:
                            length = col_idx - 1  # Column 2 = 3 digits, Column 3 = 4 digits, etc.
                            match_patterns[length] += 1
                            successful_matches.append({
                                'full_upc': full_upc,
                                'substring': substring,
                                'length': length,
                                'product': bid_line[18:118].strip() if len(bid_line) >= 118 else ""
                            })
                            print(f"\nMATCH FOUND - Row {row_num}:")
                            print(f"  Full UPC: {full_upc}")
                            print(f"  Matched SKU: {substring} (using {length} digits)")
                            print(f"  Product: {successful_matches[-1]['product'][:50]}...")
                            break  # Found a match, no need to check other lengths

print("\n" + "=" * 80)
print("DISCOVERED LOGIC PATTERNS:")
print(f"Total matches found: {len(successful_matches)}")
print("\nMost common substring lengths that matched:")
for length, count in match_patterns.most_common():
    print(f"  {length+2} digit substring: {count} matches")

if successful_matches:
    print("\nExamples of the matching logic:")
    for match in successful_matches[:5]:
        print(f"\n  UPC {match['full_upc']} -> Take {match['length']+2} digits -> SKU {match['substring']}")
        print(f"    Product: {match['product'][:40]}...")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("The logic is to try different substring lengths of the MSA UPC")
print("until we find an exact match in the POS SKU database.")
print("Different products may match at different substring lengths!")

cursor.close()
conn.close()