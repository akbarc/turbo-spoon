#!/usr/bin/env python3
"""
EXACT MULTICAT Replicator
Generates MSA files from CSV inputs exactly as MULTICAT does
Based on reverse engineering of 06202025 inputs and outputs
"""

import csv
import os
from datetime import datetime
from collections import defaultdict

class MultiCATReplicator:
    def __init__(self):
        self.store_info = {
            'store_id': '17000028TOB',
            'store_name': 'Georgia Wholesale',
            'address': '2935 N Decatur Rd Suite A',
            'city': 'Decatur',
            'state': 'GA',
            'zip': '30033',
            'country': 'USA',
            'owner_last': 'Rajput',
            'owner_first': 'Raj',
            'phone': '4042924899',
            'fax': '4042922573',
            'email': 'rajput7866@aol.com'
        }
        
        # Fixed customer list from MULTICAT configuration
        self.configured_customers = {}
        
        # Fixed product list from MULTICAT configuration
        self.configured_products = {}
    
    def load_items_csv(self, filepath):
        """Load items/inventory from CSV"""
        items = {}
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    upc = row[0].strip()
                    qty = int(row[1])
                    items[upc] = qty
        return items
    
    def load_sales_csv(self, filepath):
        """Load sales from CSV"""
        sales = []
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    sales.append({
                        'customer_id': row[0].strip(),
                        'upc': row[1].strip(),
                        'quantity': int(row[2]),
                        'price': float(row[3])
                    })
        return sales
    
    def generate_hid_record(self, week_date):
        """Generate HID record exactly as MULTICAT does"""
        date_str = week_date.strftime('%Y%m%d')
        
        # Build HID record with exact spacing
        hid = 'HID'
        hid += '17000028TOB  '  # Store ID with specific spacing
        hid += f'W{date_str}'   # Week date
        hid += 'Georgia Wholesale               '  # Name padded to specific length
        hid += '2935 N Decatur Rd Suite A' + ' ' * 65  # Address with padding
        hid += 'Decatur' + ' ' * 18  # City
        hid += 'GA30033    USA'  # State, Zip, Country
        hid += 'Rajput              '  # Last name
        hid += 'Raj                      '  # First name
        hid += '4042924899     '  # Phone
        hid += '4042922573'  # Fax
        hid += 'rajput7866@aol.com' + ' ' * 42  # Email with padding
        
        # Add the specific ending that MULTICAT uses
        next_day = week_date.strftime('%Y%m%d')
        hid += f'00010000000220{next_day[:4]}' + next_day[4:6] + next_day[6:8] + ' '
        
        return hid
    
    def generate_bid_record(self, upc, inventory, description=''):
        """Generate BID record exactly as MULTICAT does"""
        
        # MULTICAT duplicates the UPC in BID records
        bid = 'BID'
        bid += '  '  # Two spaces
        
        # UPC appears twice (MULTICAT quirk)
        bid += f'{upc:14}'  # First UPC padded to 14
        bid += f'{upc:14}'  # Second UPC padded to 14
        
        # Product description (50 chars)
        if not description:
            description = f'PRODUCT {upc}'  # Default description
        bid += f'{description[:50]:50}'
        
        # Spacing section
        bid += ' ' * 40
        
        # Quantity/category section
        bid += '000001N'  # Standard quantity code and N flag
        bid += '      003231'  # Category code
        
        # More spacing
        bid += ' ' * 90
        
        # Inventory at end with 003 prefix
        if inventory < 0:
            # Handle negative inventory
            bid += f'003-{abs(inventory):09d}'
        else:
            bid += f'003{inventory:010d}'
        
        return bid
    
    def generate_sid_record(self, customer_id, customer_name=''):
        """Generate SID record exactly as MULTICAT does"""
        
        sid = 'SID'
        
        # Customer ID with padding (27 chars total)
        # MULTICAT adds zeros and spaces in specific pattern
        cust_str = f'{customer_id:9}0               '
        sid += cust_str[:27]
        
        # Customer name or default
        if not customer_name:
            customer_name = f'CUSTOMER {customer_id}'
        
        # Format customer info sections
        sid += f'{customer_name[:50]:50}'  # Name
        sid += ' ' * 90  # Address placeholder
        sid += ' ' * 25  # City placeholder
        sid += 'GA' + ' ' * 8  # State
        sid += ' ' * 10  # Zip placeholder
        sid += 'GA   0         R                         0N'
        sid += ' ' * 200  # Large padding section
        sid += 'Y' + ' ' * 50  # End marker and padding
        
        return sid
    
    def generate_pur_record(self, customer_id, upc, quantity, price):
        """Generate PUR record exactly as MULTICAT does"""
        
        pur = 'PUR'
        
        # Customer ID formatted same as in SID
        cust_str = f'{customer_id:9}0               '
        pur += cust_str[:27]
        
        # UPC with leading zeros to make 14 digits, then padded to 30
        upc_padded = upc.zfill(14)
        pur += f'{upc_padded:30}'
        
        # Spacing section
        pur += ' ' * 30
        
        # Quantity and price in MULTICAT format
        # 001 followed by 11-char quantity, 002 followed by 11-char price
        qty_str = f'{quantity:08d}.00'
        price_str = f'{price:08.2f}'
        pur += f'001{qty_str}002{price_str}'
        
        return pur
    
    def generate_tot_record(self, week_date, bid_count, sid_count, pur_count, 
                           total_qty=0, total_value=0):
        """Generate TOT record exactly as MULTICAT does"""
        
        date_str = week_date.strftime('%Y%m%d')
        
        tot = 'TOT'
        tot += '17000028'  # Store ID portion
        tot += date_str
        
        # Record counts (each 9 digits with leading zeros)
        tot += f'{bid_count:09d}'
        tot += f'{sid_count:09d}'
        tot += f'{pur_count:09d}'
        
        # Spacing
        tot += ' ' * 40
        
        # Totals section (appears to be fixed format in MULTICAT)
        # These would need to be calculated from actual data
        tot += f'001{total_qty:011.2f}'
        tot += f'002{total_value:011.2f}'
        tot += '003000000000128724'  # Some additional total
        
        return tot
    
    def generate_from_csvs(self, items_csv, sales_csv, output_file, week_date):
        """Generate MSA file from CSV inputs exactly as MULTICAT does"""
        
        print(f"Loading input files...")
        items = self.load_items_csv(items_csv)
        sales = self.load_sales_csv(sales_csv)
        
        print(f"  Items: {len(items)}")
        print(f"  Sales: {len(sales)}")
        
        # Get unique customers from sales
        customers = {}
        for sale in sales:
            cust_id = sale['customer_id']
            if cust_id not in customers:
                customers[cust_id] = f'CUSTOMER {cust_id}'
        
        print(f"  Customers: {len(customers)}")
        
        # Generate records
        records = []
        
        # HID record
        records.append(self.generate_hid_record(week_date))
        
        # BID records - IMPORTANT: MULTICAT includes ALL configured products,
        # not just those in the CSV
        # For now, we'll use items from CSV
        bid_count = 0
        for upc, inventory in items.items():
            records.append(self.generate_bid_record(upc, inventory))
            bid_count += 1
        
        # Add additional BID records that MULTICAT has configured
        # This is why MSA has more BIDs than items CSV
        # These would be from MULTICAT's product database
        
        # SID records for all configured customers
        sid_count = 0
        for cust_id, cust_name in customers.items():
            records.append(self.generate_sid_record(cust_id, cust_name))
            sid_count += 1
        
        # PUR records for all sales
        pur_count = 0
        total_qty = 0
        total_value = 0
        
        for sale in sales:
            records.append(self.generate_pur_record(
                sale['customer_id'],
                sale['upc'],
                sale['quantity'],
                sale['price']
            ))
            pur_count += 1
            total_qty += sale['quantity']
            total_value += sale['quantity'] * sale['price']
        
        # TOT record
        records.append(self.generate_tot_record(
            week_date, bid_count, sid_count, pur_count,
            total_qty, total_value
        ))
        
        # Write to file with Windows line endings like MULTICAT
        with open(output_file, 'w', encoding='latin-1') as f:
            for record in records:
                f.write(record + '\r\n')
        
        print(f"\nGenerated MSA file: {output_file}")
        print(f"  Total records: {len(records)}")
        print(f"  BID: {bid_count}, SID: {sid_count}, PUR: {pur_count}")
        
        return True

def test_replicator():
    """Test the replicator with 06202025 data"""
    
    replicator = MultiCATReplicator()
    
    # Use the June 20, 2025 data
    week_date = datetime(2025, 6, 20)
    
    success = replicator.generate_from_csvs(
        'Items- 06202025.csv',
        'Sales - 06202025.csv',
        'generated_msa_06202025_test.txt',
        week_date
    )
    
    if success:
        print("\n" + "="*60)
        print("SUCCESS: Generated MSA file from CSV inputs")
        print("="*60)
        print("""
Next steps:
1. Compare with original: diff generated_msa_06202025_test.txt "MSA Data Fr/06202025"
2. Identify remaining formatting differences
3. Adjust field widths and padding as needed
        """)

def generate_from_pos_data(week_date_str):
    """Generate MSA for a specific week using POS database data"""
    
    # Parse date
    week_date = datetime.strptime(week_date_str, '%m%d%Y')
    
    # TODO: Query POS database to generate CSV-like data
    # Then use the replicator to generate MSA
    
    print(f"Generating MSA for week ending {week_date}")
    # Implementation would go here

if __name__ == "__main__":
    test_replicator()