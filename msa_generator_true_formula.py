#!/usr/bin/env python3
"""
MSA Generator using TRUE FORMULA: Prior MSA Inventory + Changes
Key Discovery: MSA maintains its own inventory separate from POS
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
import json
from database_pymssql import connection_pool

# All tobacco categories
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class TrueFormulaMSAGenerator:
    def __init__(self, prior_file, target_date):
        self.prior_file = prior_file
        self.target_date = target_date
        self.prior_msa_inventory = {}  # Key insight: Track MSA's own inventory
        self.prior_records = None
        self.customer_roster = self.load_customer_roster()
    
    def load_customer_roster(self):
        """Load pre-built customer roster"""
        roster_file = 'customer_roster.json'
        if os.path.exists(roster_file):
            with open(roster_file, 'r') as f:
                return json.load(f)
        return {}
    
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
        """Parse MSA file and extract inventory values"""
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
                    
                    # Extract inventory based on format
                    if len(line) >= 261:
                        # Extended format
                        inv_str = line[247:261]
                    elif len(line) >= 210:
                        # Standard format
                        inv_str = line[199:210]
                    else:
                        inv_str = '00300000000'
                    
                    # Parse inventory value
                    inv_value = int(inv_str.replace('003', '').replace('-', '').strip())
                    
                    bid_rec = {
                        'raw': line.rstrip('\r\n'),
                        'upc': upc,
                        'name': line[18:78].strip() if len(line) > 78 else '',
                        'inventory': inv_value
                    }
                    records['bids'].append(bid_rec)
                    records['bid_by_upc'][upc] = bid_rec
                    
                    # Store in MSA inventory tracker
                    self.prior_msa_inventory[upc] = inv_value
                    
                elif record_type == 'SID':
                    full_line = line.rstrip('\r\n')
                    records['sids'].append(full_line)
                    customer_id = line[3:11].strip() if len(line) > 11 else ''
                    if customer_id:
                        records['sid_customers'].add(customer_id)
                    
                elif record_type == 'PUR':
                    records['purs'].append(line.rstrip('\r\n'))
        
        return records
    
    def get_upc_to_itemcode_mapping(self):
        """Build mapping from MSA UPCs to POS ItemLookupCodes"""
        mapping = {}
        
        # From prior MSA BID records, extract the ItemLookupCode mappings
        for bid in self.prior_records['bids']:
            upc = bid['upc'].strip()
            line = bid['raw']
            
            # For double UPC format, extract ItemLookupCode
            if len(line) > 30 and line[18:30].strip() and line[18:30].strip()[0].isdigit():
                item_code = line[18:31].strip() if len(line) > 31 else line[18:30].strip()
                mapping[upc] = item_code
            else:
                # Standard format - derive from UPC
                if len(upc) == 15:
                    if upc.startswith('0'):
                        item_code = upc[1:15]  # Skip first 0
                    else:
                        item_code = upc[:14]
                elif len(upc) == 13 and upc.endswith('0'):
                    item_code = upc[:-1]  # Remove trailing 0
                else:
                    item_code = upc
                
                mapping[upc] = item_code.strip()
        
        return mapping
    
    def calculate_msa_inventory(self, upc, start_dt, end_dt):
        """
        TRUE MSA FORMULA:
        New_MSA_Inventory = Prior_MSA_Inventory - Sales + Purchases
        """
        # Start with prior MSA inventory (NOT POS inventory!)
        prior_inv = self.prior_msa_inventory.get(upc, 0)
        
        # Get ItemLookupCode for database queries
        upc_mapping = self.get_upc_to_itemcode_mapping()
        item_code = upc_mapping.get(upc)
        
        if not item_code:
            # Try standard conversion if not in mapping
            upc_clean = upc.strip()
            if len(upc_clean) == 13 and upc_clean.endswith('0'):
                item_code = upc_clean[:-1]
            elif len(upc_clean) == 15 and upc_clean.startswith('0'):
                item_code = upc_clean[1:15]
            else:
                item_code = upc_clean
        
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Find Item ID
        cursor.execute('SELECT ID FROM Item WHERE ItemLookupCode = %s', (item_code,))
        item = cursor.fetchone()
        
        if not item:
            # Try variations
            variations = [
                item_code.lstrip('0'),
                item_code.zfill(12),
                item_code.zfill(13),
                item_code.zfill(14),
            ]
            for var in variations:
                cursor.execute('SELECT ID FROM Item WHERE ItemLookupCode = %s', (var,))
                item = cursor.fetchone()
                if item:
                    break
        
        sales = 0
        purchases = 0
        
        if item:
            item_id = item['ID']
            
            # Calculate sales during period
            cursor.execute('''
                SELECT SUM(te.Quantity) as TotalSold
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE te.ItemID = %s
                AND t.Time >= %s AND t.Time <= %s
                AND te.Quantity > 0
            ''', (item_id, start_dt, end_dt))
            
            result = cursor.fetchone()
            sales = int(result['TotalSold'] or 0) if result else 0
            
            # Calculate purchases (POs received during period)
            cursor.execute('''
                SELECT SUM(poi.LastQuantityReceived) as TotalReceived
                FROM PurchaseOrderEntry poi
                WHERE poi.ItemID = %s
                AND poi.LastReceivedDate >= %s 
                AND poi.LastReceivedDate <= %s
            ''', (item_id, start_dt, end_dt))
            
            result = cursor.fetchone()
            purchases = int(result['TotalReceived'] or 0) if result else 0
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        # THE TRUE MSA FORMULA
        new_inventory = prior_inv - sales + purchases
        
        # MSA doesn't allow negative inventory
        new_inventory = max(0, new_inventory)
        
        return new_inventory, prior_inv, sales, purchases
    
    def generate(self, output_file):
        """Generate MSA using the TRUE formula"""
        print(f"\n=== GENERATING MSA WITH TRUE FORMULA ===")
        print(f"Formula: MSA_Inventory = Prior_MSA - Sales + Purchases")
        print(f"Output: {output_file}")
        
        # Parse prior file to get MSA inventory baseline
        self.prior_records = self.parse_msa_file(self.prior_file)
        print(f"Prior MSA: {len(self.prior_records['bids'])} products with MSA inventory loaded")
        
        # Get date range
        start_dt, end_dt = self.get_proper_date_range(self.target_date)
        
        # Track inventory changes
        inventory_updates = []
        
        # Generate output
        with open(output_file, 'w') as f:
            # Header
            if self.prior_records['header']:
                header = self.prior_records['header']
                old_date = f"2025{self.prior_file.split('/')[-1][:4]}"
                new_date = f"2025{self.target_date[:4]}"
                header = header.replace(old_date, new_date)
                f.write(header + '\n')
            
            # BID records with TRUE MSA inventory calculation
            for bid in self.prior_records['bids']:
                upc = bid['upc']
                line = bid['raw']
                
                # Calculate new inventory using TRUE formula
                new_inv, prior_inv, sales, purchases = self.calculate_msa_inventory(upc, start_dt, end_dt)
                
                # Track significant changes for reporting
                if sales > 0 or purchases > 0:
                    inventory_updates.append({
                        'upc': upc,
                        'name': bid['name'][:30],
                        'prior': prior_inv,
                        'sales': sales,
                        'purchases': purchases,
                        'new': new_inv
                    })
                
                # Update inventory in BID record
                if len(line) >= 261:
                    # Extended format
                    inv_str = f"003{new_inv:011d}"
                    line = line[:247] + inv_str + (line[261:] if len(line) > 261 else "")
                elif len(line) >= 210:
                    # Standard format
                    inv_str = f"{new_inv:011d}"
                    line = line[:199] + inv_str + (line[210:] if len(line) > 210 else "")
                
                f.write(line + '\n')
            
            # Get sales data for PUR records
            conn = connection_pool.get_connection()
            cursor = conn.cursor(as_dict=True)
            
            category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
            
            cursor.execute(f"""
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
                AND c.AccountNumber IS NOT NULL
                GROUP BY c.AccountNumber, i.ItemLookupCode
                HAVING SUM(te.Quantity) > 0
            """, (start_dt, end_dt))
            
            sales_by_customer = defaultdict(lambda: defaultdict(float))
            customers = set()
            
            for row in cursor.fetchall():
                if row['AccountNumber']:
                    phone = str(row['AccountNumber']).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
                    if len(phone) >= 8:
                        cust_str = phone[-8:]
                        if cust_str.startswith('0'):
                            cust_str = cust_str[1:] + '0'
                        customers.add(cust_str)
                        
                        # Format as distributor SKU
                        dist_sku = row['ItemLookupCode'].rjust(14, '0')
                        qty = abs(row['Quantity'])
                        sales_by_customer[cust_str][dist_sku] += qty
            
            cursor.close()
            connection_pool.return_connection(conn)
            
            # SID records
            for customer_id in sorted(customers):
                if customer_id in self.customer_roster:
                    sid_line = self.customer_roster[customer_id]
                else:
                    sid_line = 'SID' + customer_id.ljust(8)
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
        
        # Report significant inventory changes
        if inventory_updates:
            print("\nTop Inventory Changes (TRUE FORMULA):")
            sorted_updates = sorted(inventory_updates, key=lambda x: abs(x['new'] - x['prior']), reverse=True)
            for update in sorted_updates[:10]:
                change = update['new'] - update['prior']
                print(f"  {update['name']:30} Prior:{update['prior']:4} -Sales:{update['sales']:3} +PO:{update['purchases']:3} = New:{update['new']:4} (Δ{change:+4})")
        
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
        
        # Check inventory accuracy
        exact_matches = 0
        total_compared = 0
        inventory_diffs = []
        
        for upc in act['bid_by_upc']:
            if upc in gen['bid_by_upc']:
                gen_inv = gen['bid_by_upc'][upc]['inventory']
                act_inv = act['bid_by_upc'][upc]['inventory']
                
                total_compared += 1
                if gen_inv == act_inv:
                    exact_matches += 1
                else:
                    diff = act_inv - gen_inv
                    inventory_diffs.append({
                        'upc': upc,
                        'name': act['bid_by_upc'][upc]['name'][:30],
                        'gen': gen_inv,
                        'act': act_inv,
                        'diff': diff
                    })
        
        accuracy = (exact_matches / total_compared * 100) if total_compared > 0 else 0
        
        print(f"\nInventory Accuracy:")
        print(f"  Exact Matches: {exact_matches}/{total_compared} ({accuracy:.1f}%)")
        
        if inventory_diffs:
            print(f"\nTop Inventory Differences:")
            sorted_diffs = sorted(inventory_diffs, key=lambda x: abs(x['diff']), reverse=True)
            for diff in sorted_diffs[:5]:
                print(f"  {diff['name']:30} Gen:{diff['gen']:4} Act:{diff['act']:4} (Δ{diff['diff']:+4})")
        
        return accuracy

def main():
    if len(sys.argv) > 2:
        prior_date = sys.argv[1]
        target_date = sys.argv[2]
    else:
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_true_formula.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = TrueFormulaMSAGenerator(prior_file, target_date)
    accuracy = generator.generate(output_file)
    
    print("\n" + "="*70)
    print("KEY DISCOVERY: TRUE MSA INVENTORY FORMULA")
    print("="*70)
    print("""
✓ MSA maintains its own inventory separate from POS
✓ Formula: New_MSA = Prior_MSA - Sales + Purchases  
✓ POS current inventory is IGNORED
✓ This explains why products with 0 in MSA stay at 0

This is why we had discrepancies:
- We were using POS inventory
- MSA uses its own tracked inventory
- Products not in prior MSA won't appear even if in POS
""")

if __name__ == "__main__":
    main()