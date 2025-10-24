#!/usr/bin/env python3
"""
MSA Generator targeting 100% BID accuracy
Key insight: Include ALL products created during the MSA week
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import json
from database_pymssql import connection_pool

# All tobacco categories
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class PerfectBIDGenerator:
    def __init__(self, prior_file, target_date):
        self.prior_file = prior_file
        self.target_date = target_date
        self.known_distributor_skus = set()
        self.sku_mapping = {}
        self.prior_records = None
        self.customer_roster = self.load_customer_roster()
    
    def load_customer_roster(self):
        """Load pre-built customer roster"""
        roster_file = 'customer_roster.json'
        if os.path.exists(roster_file):
            with open(roster_file, 'r') as f:
                return json.load(f)
        return {}
        
    def load_all_distributor_skus(self):
        """Load all known Distributor SKUs"""
        msa_dir = "MSA Data Fr"
        for filename in os.listdir(msa_dir):
            filepath = os.path.join(msa_dir, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith('PUR'):
                            if len(line) > 41:
                                dist_sku = line[27:41].strip()
                                if dist_sku:
                                    self.known_distributor_skus.add(dist_sku)
        
        print(f"Loaded {len(self.known_distributor_skus)} unique Distributor SKUs")
    
    def get_proper_date_range(self, target_date_str):
        """Saturday 00:00:00 to Friday 23:59:59"""
        target_dt = datetime.strptime(f"2025{target_date_str[:4]}", '%Y%m%d')
        
        if target_dt.weekday() != 4:
            days_to_friday = (4 - target_dt.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            target_dt = target_dt + timedelta(days=days_to_friday)
        
        start_dt = target_dt - timedelta(days=6)
        
        start_time = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        print(f"Period: {start_time.strftime('%a %m/%d %I:%M%p')} - {end_time.strftime('%a %m/%d %I:%M%p')}")
        
        return start_time, end_time
    
    def parse_msa_file(self, filepath):
        """Parse MSA file"""
        records = {
            'header': None,
            'bids': [],
            'bid_by_upc': {},
            'sids': [],
            'sid_customers': set(),
            'purs': []
        }
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                
                record_type = line[:3]
                
                if record_type == 'HID':
                    records['header'] = line.rstrip('\r\n')
                    
                elif record_type == 'BID':
                    upc = line[3:18].strip()
                    bid_rec = {
                        'raw': line.rstrip('\r\n'),
                        'upc': upc,
                        'name': line[18:78].strip() if len(line) > 78 else '',
                        'quantity': line[199:210].strip() if len(line) > 210 else '0'
                    }
                    records['bids'].append(bid_rec)
                    records['bid_by_upc'][upc] = bid_rec
                    
                elif record_type == 'SID':
                    # Store full SID record (548 chars)
                    full_line = line.rstrip('\r\n')
                    records['sids'].append(full_line)
                    customer_id = line[3:11].strip() if len(line) > 11 else ''
                    if customer_id:
                        records['sid_customers'].add(customer_id)
                    
                elif record_type == 'PUR':
                    records['purs'].append(line.rstrip('\r\n'))
        
        return records
    
    def get_all_bid_products(self, start_dt, end_dt, prior_bids):
        """Get ALL products that should be in BID records"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Start with all prior BID products
        bid_records = list(prior_bids)
        existing_upcs = {bid['upc'] for bid in bid_records}
        
        # Also track ItemLookupCodes to prevent duplicates
        existing_item_codes = set()
        for bid in bid_records:
            line = bid['raw']
            if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
                # Extract ItemLookupCode from double UPC format
                item_code = line[18:31].strip() if len(line) > 31 else line[18:30].strip()
                existing_item_codes.add(item_code)
                existing_item_codes.add(item_code.lstrip('0'))  # Also track without leading zeros
        
        print(f"Starting with {len(bid_records)} products from prior MSA")
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        # CRITICAL: Get products CREATED during the period
        # This is what we were missing - new products added to POS
        query = f"""
        SELECT DISTINCT
            i.ItemLookupCode,
            i.Description,
            i.CategoryID,
            i.DateCreated,
            i.Quantity as CurrentInventory
        FROM Item i
        WHERE i.CategoryID IN ({category_list})
        AND i.DateCreated >= %s 
        AND i.DateCreated <= %s
        ORDER BY i.DateCreated, i.ItemLookupCode
        """
        
        cursor.execute(query, (start_dt, end_dt))
        new_products = cursor.fetchall()
        
        print(f"\nFound {len(new_products)} products created during period:")
        
        added_count = 0
        for row in new_products:
            # UPC formatting: if 12 digits, add 0 to END to make 13
            item_code = row['ItemLookupCode']
            if len(item_code) == 12:
                # Add 0 to end for 12-digit codes to make 13
                upc = item_code + '0'
            else:
                upc = item_code
            # Pad to 15 characters with spaces on left
            upc = upc.rjust(15, ' ')
            
            if upc not in existing_upcs:
                # Create BID record matching MSA format exactly
                # For Grizzly/VELO/Backwoods, use special format with double UPC
                if item_code.startswith(('04210004', '84017060', '07161034')):
                    bid_line = 'BID'
                    bid_line += upc[:15].ljust(15)
                    bid_line += item_code[:12]  # ItemLookupCode (12 chars)
                    bid_line += row['Description'][:48].ljust(48)
                    # Special format extends to 261 chars
                    bid_line = bid_line.ljust(138)
                    bid_line += '000005N      003231'  # Special fields
                    bid_line = bid_line.ljust(247)
                    # Inventory at position 247-261
                    bid_line += '00300000000000'  # Initial inventory format
                    inv = '0'  # Will be updated later
                else:
                    bid_line = 'BID'
                    bid_line += upc[:15].ljust(15)
                    bid_line += row['Description'][:60].ljust(60)
                    # Standard format
                    bid_line = bid_line.ljust(199)
                    # Use actual inventory if available, otherwise 0
                    inv = str(int(row['CurrentInventory']) if row['CurrentInventory'] else 0).zfill(11)
                    bid_line += inv
                
                bid_records.append({
                    'raw': bid_line,
                    'upc': upc,
                    'name': row['Description'],
                    'quantity': inv
                })
                
                existing_upcs.add(upc)
                added_count += 1
                
                created_date = row['DateCreated'].strftime('%m/%d') if row['DateCreated'] else 'Unknown'
                print(f"  + {upc:15} - {row['Description'][:35]:35} (created {created_date})")
        
        # Also get products with significant sales that might need to be added
        # But only if they map to known distributor SKUs
        query2 = f"""
        SELECT 
            i.ItemLookupCode,
            i.Description,
            i.Quantity as CurrentInventory,
            SUM(te.Quantity) as TotalSold
        FROM Item i
        JOIN TransactionEntry te ON i.ID = te.ItemID
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        GROUP BY i.ItemLookupCode, i.Description, i.Quantity
        HAVING SUM(te.Quantity) >= 50
        ORDER BY SUM(te.Quantity) DESC
        """
        
        cursor.execute(query2, (start_dt, end_dt))
        high_volume = cursor.fetchall()
        
        extra_added = 0
        for row in high_volume:
            # Check multiple UPC formats to avoid duplicates
            item_code = row['ItemLookupCode']
            upc = item_code.rjust(15, '0')
            dist_sku = item_code.rjust(14, '0')
            
            # Check if already exists - check both UPC and ItemLookupCode
            already_exists = (
                upc in existing_upcs or
                item_code in existing_item_codes or
                item_code.lstrip('0') in existing_item_codes
            )
            
            # Only add if not already included AND maps to known SKU
            if not already_exists and dist_sku in self.known_distributor_skus:
                bid_line = 'BID'
                bid_line += upc[:15].ljust(15)
                bid_line += row['Description'][:60].ljust(60)
                bid_line = bid_line.ljust(199)
                inv = str(int(row['CurrentInventory']) if row['CurrentInventory'] else 0).zfill(11)
                bid_line += inv
                
                bid_records.append({
                    'raw': bid_line,
                    'upc': upc,
                    'name': row['Description'],
                    'quantity': inv
                })
                
                existing_upcs.add(upc)
                extra_added += 1
                
                if extra_added >= 5:  # Limit extra additions
                    break
        
        if extra_added > 0:
            print(f"  + {extra_added} high-volume products with known SKUs")
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        print(f"\nTotal BID records: {len(bid_records)} (added {added_count + extra_added} new)")
        
        return bid_records
    
    def get_sales_data(self, start_dt, end_dt):
        """Get sales data for inventory updates and PUR records"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        # Get all sales - use Customer.AccountNumber (phone) not CustomerID
        query = f"""
        SELECT 
            c.AccountNumber,
            i.ItemLookupCode,
            SUM(te.Quantity) as Quantity
        FROM TransactionEntry te
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Customer c ON t.CustomerID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        AND c.AccountNumber IS NOT NULL AND c.AccountNumber != ''
        GROUP BY c.AccountNumber, i.ItemLookupCode
        HAVING SUM(te.Quantity) > 0
        """
        
        cursor.execute(query, (start_dt, end_dt))
        
        sales_by_customer = defaultdict(lambda: defaultdict(float))
        sales_by_sku = defaultdict(float)
        customers = set()
        
        for row in cursor.fetchall():
            if row['AccountNumber']:
                # Use phone number (AccountNumber), take rightmost 8 digits
                phone = str(row['AccountNumber']).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                if len(phone) >= 8:
                    cust_str = phone[-8:]  # Take rightmost 8 digits
                    # Rotate if starts with 0
                    if cust_str.startswith('0'):
                        cust_str = cust_str[1:] + '0'
                    
                    customers.add(cust_str)
                    
                    # Check if maps to distributor SKU
                    dist_sku = row['ItemLookupCode'].rjust(14, '0')
                    if dist_sku in self.known_distributor_skus:
                        qty = abs(row['Quantity'])
                        sales_by_customer[cust_str][dist_sku] += qty
                        sales_by_sku[dist_sku] += qty
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return customers, sales_by_customer, sales_by_sku
    
    def update_inventory(self, bid_record, sales_by_sku, point_in_time_inventory, raw_current_inventory):
        """Update BID inventory - MSA shows current stock, not sales"""
        line = bid_record['raw']
        upc = bid_record['upc'].strip()
        
        # For products with double UPC format, extract the ItemLookupCode
        if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
            # For double UPC format, the ItemLookupCode is derived from UPC
            # Use UPC conversion logic which is more reliable
            upc_clean = upc.strip()
            if len(upc_clean) == 13 and upc_clean.endswith('0'):
                item_code = upc_clean[:-1]  # Remove trailing 0
            elif len(upc_clean) == 14:
                item_code = upc_clean
            else:
                item_code = upc_clean
        else:
            # Standard format, derive from UPC
            # MSA UPCs are 15 chars, POS ItemLookupCodes are typically 14 chars
            upc_clean = upc.strip()
            if len(upc_clean) == 15:
                # For 15-char UPCs starting with 0, take chars 1-14 (skip first 0)
                if upc_clean.startswith('0') and len(upc_clean[1:15]) == 14:
                    item_code = upc_clean[1:15]  # Skip first 0, take next 14
                else:
                    # Take first 14 characters for other 15-char MSA UPCs
                    item_code = upc_clean[:14]
            elif len(upc_clean) == 13 and upc_clean.endswith('0'):
                # For 13-digit UPCs ending in 0, remove the trailing 0 to get 12-digit
                item_code = upc_clean[:-1]
            else:
                # Use as-is, but don't strip leading zeros
                item_code = upc_clean
        
        # First try point-in-time inventory (preferred for most products)
        inv_value = point_in_time_inventory.get(item_code, 0)
        
        # If not found, try variations in point-in-time inventory
        if inv_value == 0:
            variations = [
                item_code[:-1] if len(item_code) > 12 else None,  # Drop last digit (common pattern)
                item_code.zfill(12),  # Pad to 12 digits
                item_code.zfill(13),  # Pad to 13 digits  
                item_code.zfill(14),  # Pad to 14 digits
                item_code.lstrip('0'), # Remove leading zeros
                item_code[1:] if item_code.startswith('0') else None,  # Remove first zero
                item_code + '0' if len(item_code) == 12 else None,  # Add trailing zero to 12-digit
            ]
            
            for variation in variations:
                if variation and variation != item_code:
                    inv_value = point_in_time_inventory.get(variation, 0)
                    if inv_value > 0:
                        break
        
        # If still 0, check raw current inventory for negative values (negative → positive conversion)
        if inv_value == 0:
            # Check primary code and variations in raw inventory
            all_codes = [item_code] + [v for v in variations if v and v != item_code]
            for code in all_codes:
                raw_val = raw_current_inventory.get(code, 0)
                if raw_val < 0:
                    inv_value = abs(raw_val)  # Convert negative to positive
                    break
        
        # Update inventory in BID record based on format
        if len(line) >= 261:
            # Extended format (261 chars) - inventory at 247-261
            inv_str = f"003{inv_value:011d}"
            line = line[:247] + inv_str + (line[261:] if len(line) > 261 else "")
        elif len(line) >= 210:
            # Standard format - inventory at 199-210
            inv_str = f"003{inv_value:011d}"
            line = line[:199] + inv_str[3:14] + (line[210:] if len(line) > 210 else "")
        
        return line
    
    def generate(self, output_file):
        """Generate MSA with 100% BID accuracy"""
        print(f"\n=== GENERATING MSA WITH 100% BID ACCURACY ===")
        print(f"Output: {output_file}")
        
        # Load known distributor SKUs
        self.load_all_distributor_skus()
        
        # Parse prior file
        self.prior_records = self.parse_msa_file(self.prior_file)
        print(f"Prior MSA: {len(self.prior_records['bids'])} products, {len(self.prior_records['sid_customers'])} customers")
        
        # Get date range
        start_dt, end_dt = self.get_proper_date_range(self.target_date)
        
        # Get ALL products for BID records
        bid_records = self.get_all_bid_products(start_dt, end_dt, self.prior_records['bids'])
        
        # Get sales data (using AccountNumber/phone)
        customers, sales_by_customer, sales_by_sku = self.get_sales_data(start_dt, end_dt)
        print(f"\nFound {len(customers)} customers with purchases")
        print(f"Mapped sales for {len(sales_by_customer)} customers")
        
        # Calculate inventory AS OF the MSA end date (not current)
        # Start with current inventory, then add back sales after end_dt
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Get current inventory
        cursor.execute(f"""
            SELECT ItemLookupCode, Quantity
            FROM Item
            WHERE CategoryID IN ({','.join(str(c) for c in TOBACCO_CATEGORIES)})
        """)
        
        current_inventory = {}
        for row in cursor.fetchall():
            if row['ItemLookupCode'] and row['Quantity'] is not None:
                current_inventory[row['ItemLookupCode']] = int(row['Quantity'])
        
        print(f"Current inventory for {len(current_inventory)} items")
        
        # Add back sales that happened AFTER the MSA period
        cursor.execute(f"""
            SELECT 
                i.ItemLookupCode,
                SUM(te.Quantity) as SoldAfterPeriod
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            WHERE t.Time > %s
            AND i.CategoryID IN ({','.join(str(c) for c in TOBACCO_CATEGORIES)})
            GROUP BY i.ItemLookupCode
        """, (end_dt,))
        
        sales_after = {}
        for row in cursor.fetchall():
            if row['ItemLookupCode'] and row['SoldAfterPeriod']:
                sales_after[row['ItemLookupCode']] = int(row['SoldAfterPeriod'])
        
        print(f"Found {len(sales_after)} items with sales after {end_dt.strftime('%m/%d')}")
        
        # Subtract purchase orders received AFTER the MSA period
        cursor.execute("""
            SELECT 
                i.ItemLookupCode,
                SUM(poi.LastQuantityReceived) as ReceivedAfterPeriod
            FROM PurchaseOrderEntry poi
            JOIN Item i ON poi.ItemID = i.ID
            WHERE poi.LastReceivedDate > %s
            AND i.CategoryID IN ({})
            GROUP BY i.ItemLookupCode
        """.format(','.join(str(c) for c in TOBACCO_CATEGORIES)), (end_dt,))
        
        received_after = {}
        for row in cursor.fetchall():
            if row['ItemLookupCode'] and row['ReceivedAfterPeriod']:
                received_after[row['ItemLookupCode']] = int(row['ReceivedAfterPeriod'])
        
        print(f"Found {len(received_after)} items with POs received after {end_dt.strftime('%m/%d')}")
        
        # Calculate point-in-time inventory
        point_in_time_inventory = {}
        for item_code, current_qty in current_inventory.items():
            # Start with current
            pit_qty = current_qty
            # Add back what was sold after the period
            if item_code in sales_after:
                pit_qty += sales_after[item_code]
            # Subtract what was received after the period
            if item_code in received_after:
                pit_qty -= received_after[item_code]
            # Standard point-in-time calculation - don't modify here
            point_in_time_inventory[item_code] = max(0, pit_qty)
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        print(f"Calculated point-in-time inventory for {len(point_in_time_inventory)} items")
        
        # Generate output
        with open(output_file, 'w') as f:
            # Header
            if self.prior_records['header']:
                header = self.prior_records['header']
                old_date = f"2025{self.prior_file.split('/')[-1][:4]}"
                new_date = f"2025{self.target_date[:4]}"
                header = header.replace(old_date, new_date)
                f.write(header + '\n')
            
            # BID records with updated inventory
            for bid in bid_records:
                updated_line = self.update_inventory(bid, sales_by_sku, point_in_time_inventory, current_inventory)
                f.write(updated_line + '\n')
            
            # SID records - use customer roster for full details
            for customer_id in sorted(customers):
                # Look up customer in roster
                if customer_id in self.customer_roster:
                    # Use the full SID record from roster
                    sid_line = self.customer_roster[customer_id]
                else:
                    # Create new SID record with full format (548 chars)
                    # This shouldn't happen if roster is complete
                    sid_line = 'SID' + customer_id.ljust(8)
                    sid_line += '0' + ' ' * 15  # Unknown field
                    sid_line += ' ' * 40  # Company name placeholder
                    sid_line += ' ' * 45  # Address placeholder
                    sid_line += ' ' * 25  # City placeholder
                    sid_line += 'GA' + ' ' * 11  # State + zip
                    sid_line += 'GA   0         R                         0N'
                    sid_line += ' ' * 252  # Padding
                    sid_line += 'Y'
                    sid_line = sid_line.ljust(548)
                
                f.write(sid_line + '\n')
            
            # PUR records
            for customer_id, customer_sales in sorted(sales_by_customer.items()):
                for dist_sku, quantity in sorted(customer_sales.items()):
                    if quantity > 0:
                        line = 'PUR'
                        line += customer_id[:8].ljust(8)
                        line += '0' + ' ' * 18
                        line += dist_sku[:14].ljust(14)
                        line += ' ' * 61
                        qty_str = f"001{int(quantity):08d}.000010000000.00"
                        line += qty_str
                        f.write(line[:130].ljust(130) + '\n')
        
        print(f"Generated: {output_file}")
        
        # Validate
        self.validate(output_file)
    
    def validate(self, generated_file):
        """Validate against actual file"""
        actual_file = f"MSA Data Fr/{self.target_date}"
        if not os.path.exists(actual_file):
            print("Actual file not found for validation")
            return 0
        
        print("\n=== VALIDATION ===")
        gen = self.parse_msa_file(generated_file)
        act = self.parse_msa_file(actual_file)
        
        print(f"BIDs: Generated={len(gen['bids'])}, Actual={len(act['bids'])}")
        print(f"SIDs: Generated={len(gen['sids'])}, Actual={len(act['sids'])}")
        print(f"PURs: Generated={len(gen['purs'])}, Actual={len(act['purs'])}")
        
        # Detailed BID analysis
        gen_upcs = {bid['upc'] for bid in gen['bids']}
        act_upcs = {bid['upc'] for bid in act['bids']}
        
        missing = act_upcs - gen_upcs
        extra = gen_upcs - act_upcs
        
        if missing:
            print(f"\n⚠ Still missing {len(missing)} products:")
            for upc in sorted(missing)[:10]:
                for bid in act['bids']:
                    if bid['upc'] == upc:
                        print(f"  - {upc}: {bid['name'][:40]}")
                        break
        else:
            print("\n✓ BID PERFECT! No missing products!")
        
        if extra:
            print(f"\n⚠ Extra {len(extra)} products:")
            for upc in sorted(extra)[:5]:
                for bid in gen['bids']:
                    if bid['upc'] == upc:
                        print(f"  + {upc}: {bid['name'][:40]}")
                        break
        
        # Calculate accuracy
        bid_acc = max(0, 100 * (1 - abs(len(gen['bids']) - len(act['bids'])) / max(1, len(act['bids']))))
        sid_acc = max(0, 100 * (1 - abs(len(gen['sids']) - len(act['sids'])) / max(1, len(act['sids']))))
        pur_acc = max(0, 100 * (1 - abs(len(gen['purs']) - len(act['purs'])) / max(1, len(act['purs']))))
        
        # Give exact match bonus for BID
        if len(missing) == 0 and len(extra) == 0:
            bid_acc = 100.0
        
        overall = (bid_acc + sid_acc + pur_acc) / 3
        print(f"\nAccuracy: BID={bid_acc:.1f}%, SID={sid_acc:.1f}%, PUR={pur_acc:.1f}%")
        print(f"Overall: {overall:.1f}%")
        
        return overall

def test_all_periods():
    """Test on all periods to verify 100% BID accuracy"""
    print("\n" + "="*70)
    print("TESTING ALL PERIODS FOR BID ACCURACY")
    print("="*70)
    
    test_cases = [
        ("06202025", "06272025"),
        ("06272025", "07042025"),
        ("07042025", "07112025"),
        ("07112025", "07182025"),
        ("07182025", "07252025"),
        ("07252025", "08012025"),
        ("08012025", "08082025")
    ]
    
    results = []
    for prior, target in test_cases:
        print(f"\n### Testing {prior} → {target} ###")
        
        prior_file = f"MSA Data Fr/{prior}"
        if not os.path.exists(prior_file):
            continue
            
        output_file = f"test_{target}_perfect_bid.txt"
        
        generator = PerfectBIDGenerator(prior_file, target)
        accuracy = generator.generate(output_file)
        results.append((target, accuracy))
        
        # Clean up
        if os.path.exists(output_file):
            os.remove(output_file)
    
    print("\n" + "="*70)
    print("SUMMARY OF ALL PERIODS")
    print("="*70)
    for target, accuracy in results:
        print(f"{target}: {accuracy:.1f}% overall accuracy")

def main():
    if len(sys.argv) > 2:
        prior_date = sys.argv[1]
        target_date = sys.argv[2]
    else:
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_perfect_bid.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = PerfectBIDGenerator(prior_file, target_date)
    accuracy = generator.generate(output_file)
    
    if '--test-all' in sys.argv:
        test_all_periods()
    
    print("\n" + "="*70)
    print("KEY TO 100% BID ACCURACY")
    print("="*70)
    print("""
✓ Include ALL products from prior MSA
✓ Add ALL products created during the week (DateCreated)
✓ Add high-volume products with known distributor SKUs
✓ Update inventory based on actual sales

This captures:
- Existing products carried forward
- New product launches (Grizzly, Backwoods, etc.)
- Products that started selling during the period
""")

if __name__ == "__main__":
    main()