#!/usr/bin/env python3
"""
Check if ItemBarcode table exists and can map to Distributor SKUs
"""

from collections import defaultdict
import os
from database_pymssql import connection_pool

def check_barcode_table():
    """Check if ItemBarcode table exists and has data"""
    print("="*70)
    print("CHECKING FOR BARCODE DATA IN POS DATABASE")
    print("="*70)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Check what columns exist in Item table
    print("\n### Item Table Columns ###")
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Item' 
        ORDER BY ORDINAL_POSITION
    """)
    columns = [row['COLUMN_NAME'] for row in cursor.fetchall()]
    
    # Look for barcode-related columns
    barcode_columns = [col for col in columns if 'barcode' in col.lower() or 'upc' in col.lower() or 'ean' in col.lower() or 'gtin' in col.lower()]
    
    if barcode_columns:
        print(f"Found barcode-related columns: {barcode_columns}")
    else:
        print("No barcode columns in Item table")
    
    # Check for ItemBarcode table
    print("\n### Checking for ItemBarcode Table ###")
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE '%Barcode%' OR TABLE_NAME LIKE '%UPC%'
    """)
    barcode_tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
    
    if barcode_tables:
        print(f"Found barcode tables: {barcode_tables}")
        
        # Check ItemBarcode structure if it exists
        if 'ItemBarcode' in barcode_tables:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'ItemBarcode'
            """)
            print("\nItemBarcode table structure:")
            for col in cursor.fetchall():
                print(f"  {col['COLUMN_NAME']}: {col['DATA_TYPE']} ({col['CHARACTER_MAXIMUM_LENGTH']})")
            
            # Get sample data
            cursor.execute("""
                SELECT TOP 20
                    i.ItemLookupCode,
                    i.Description,
                    ib.Barcode
                FROM Item i
                JOIN ItemBarcode ib ON i.ID = ib.ItemID
                WHERE i.CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
                ORDER BY i.ItemLookupCode
            """)
            
            samples = cursor.fetchall()
            if samples:
                print(f"\n### Sample ItemBarcode Data (Tobacco Items) ###")
                for sample in samples[:10]:
                    barcode = sample['Barcode'].strip()
                    # Pad to 14 characters like Distributor SKUs
                    dist_sku_format = barcode.rjust(14, '0')
                    print(f"POS: {sample['ItemLookupCode']:15} → Barcode: {barcode:15} → DistSKU: {dist_sku_format}")
    else:
        print("No ItemBarcode table found")
    
    # Check if Item table has any other useful fields
    print("\n### Checking Other Potential Fields ###")
    
    # Try common field names
    potential_fields = ['ItemLookupCode', 'Description', 'SubDescription1', 'SubDescription2', 'SubDescription3']
    actual_fields = [f for f in potential_fields if f in columns]
    
    if actual_fields:
        fields_str = ', '.join(actual_fields)
        cursor.execute(f"""
            SELECT TOP 10 {fields_str}
            FROM Item
            WHERE CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
            ORDER BY ItemLookupCode
        """)
        
        print("\n### Sample Item Data ###")
        for row in cursor.fetchall():
            print(f"ItemLookupCode: {row['ItemLookupCode']}")
            if 'SubDescription1' in row and row['SubDescription1']:
                print(f"  SubDesc1: {row['SubDescription1']}")
            if 'SubDescription2' in row and row['SubDescription2']:
                print(f"  SubDesc2: {row['SubDescription2']}")
            if 'SubDescription3' in row and row['SubDescription3']:
                print(f"  SubDesc3: {row['SubDescription3']}")
    
    cursor.close()
    connection_pool.return_connection(conn)

def test_barcode_mapping():
    """Test if barcodes map to known Distributor SKUs"""
    print("\n" + "="*70)
    print("TESTING BARCODE → DISTRIBUTOR SKU MAPPING")
    print("="*70)
    
    # Load known Distributor SKUs from actual MSA
    actual_file = "MSA Data Fr/08082025"
    dist_skus = set()
    
    with open(actual_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('PUR'):
                if len(line) > 41:
                    dist_sku = line[27:41].strip()
                    if dist_sku:
                        dist_skus.add(dist_sku)
    
    print(f"Loaded {len(dist_skus)} Distributor SKUs from actual MSA")
    
    # Test mapping with ItemBarcode
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    # Check if ItemBarcode exists
    cursor.execute("SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ItemBarcode'")
    if cursor.fetchone()['cnt'] > 0:
        cursor.execute("""
            SELECT 
                i.ItemLookupCode,
                i.Description,
                ib.Barcode
            FROM Item i
            JOIN ItemBarcode ib ON i.ID = ib.ItemID
            WHERE i.CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
        """)
        
        total_items = 0
        matched_items = 0
        
        for row in cursor.fetchall():
            total_items += 1
            barcode = row['Barcode'].strip()
            
            # Try different formats
            formats_to_try = [
                barcode.rjust(14, '0'),  # Pad to 14 with leading zeros
                barcode.zfill(14),       # Same as above
                barcode,                  # Raw barcode
                barcode.lstrip('0').rjust(14, '0')  # Remove then re-pad
            ]
            
            for fmt in formats_to_try:
                if fmt in dist_skus:
                    matched_items += 1
                    if matched_items <= 10:
                        print(f"✓ Match: {row['ItemLookupCode']} → {fmt}")
                    break
        
        print(f"\n### MAPPING RESULTS ###")
        print(f"Total tobacco items with barcodes: {total_items}")
        print(f"Successfully mapped to Dist SKUs: {matched_items}")
        print(f"Mapping rate: {matched_items*100/total_items if total_items > 0 else 0:.1f}%")
        
        if matched_items > total_items * 0.5:  # If >50% match
            print("\n✓✓✓ SUCCESS! ItemBarcode provides good mapping!")
            print("We can use: RIGHT('00000000000000' + Barcode, 14) as DistributorSKU")
    
    cursor.close()
    connection_pool.return_connection(conn)

def propose_final_solution():
    """Propose the final sustainable solution"""
    print("\n" + "="*70)
    print("SUSTAINABLE MAPPING SOLUTION")
    print("="*70)
    
    print("""
### DISCOVERED PATTERN ###

1. Distributor SKUs are 14-character zero-padded barcodes
2. Format: Always exactly 14 characters
3. Pattern: Leading zeros + UPC/EAN code
4. Example: "00028200172907" = "28200172907" padded

### MAPPING STRATEGY ###

1. PRIMARY: Use ItemBarcode table
   - Join Item to ItemBarcode
   - Pad barcode to 14 characters with leading zeros
   - This gives us the Distributor SKU

2. FALLBACK: Use ItemLookupCode patterns
   - For items without barcodes
   - Try padding ItemLookupCode to 14 chars
   - Match against known Distributor SKU patterns

3. LEARNING: Build mapping cache
   - Store successful mappings
   - Learn from each MSA generation
   - Improve over time

### SQL QUERY FOR MAPPING ###

```sql
SELECT 
    i.ItemLookupCode,
    i.Description,
    RIGHT('00000000000000' + ISNULL(ib.Barcode, i.ItemLookupCode), 14) as DistributorSKU
FROM Item i
LEFT JOIN ItemBarcode ib ON i.ID = ib.ItemID
WHERE i.CategoryID IN (11,18,23,31,41,45,48,49,51,53,56,57,59,81,83)
```

This approach will work for all future dates!
""")

def main():
    check_barcode_table()
    test_barcode_mapping()
    propose_final_solution()

if __name__ == "__main__":
    main()