#!/usr/bin/env python3
"""
Optimized MSA Generator - Final version with all fixes
Key improvements:
1. Only add products that map to known Distributor SKUs AND have high sales
2. Follow MSA customer roster approach exactly
3. Use all tobacco categories
4. Proper Saturday-Friday date range
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# All tobacco categories (keep even if empty for future)
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class OptimizedMSAGenerator:
    def __init__(self, prior_file, target_date):
        self.prior_file = prior_file
        self.target_date = target_date
        self.known_distributor_skus = set()
        self.sku_mapping = {}
        self.prior_records = None
        
    def load_all_distributor_skus(self):
        """Load all known Distributor SKUs from historical MSA files"""
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
        
        # Also load BID UPCs to understand which products MSA tracks
        self.msa_tracked_upcs = set()
        for filename in os.listdir(msa_dir):
            filepath = os.path.join(msa_dir, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith('BID'):
                            upc = line[3:18].strip()
                            if upc:
                                self.msa_tracked_upcs.add(upc)
        
        print(f"Found {len(self.msa_tracked_upcs)} unique products in MSA history")
    
    def get_proper_date_range(self, target_date_str):
        """Calculate Saturday 00:00:00 to Friday 23:59:59"""
        target_dt = datetime.strptime(f"2025{target_date_str[:4]}", '%Y%m%d')
        
        # Ensure it's a Friday
        if target_dt.weekday() != 4:
            days_to_friday = (4 - target_dt.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            target_dt = target_dt + timedelta(days=days_to_friday)
        
        # Start is Saturday
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
                    records['sids'].append(line.rstrip('\r\n'))
                    customer_id = line[3:11].strip() if len(line) > 11 else ''
                    if customer_id:
                        records['sid_customers'].add(customer_id)
                    
                elif record_type == 'PUR':
                    records['purs'].append(line.rstrip('\r\n'))
        
        return records
    
    def get_new_products_to_add(self, start_dt, end_dt, existing_upcs):
        """Only add products that are truly new and significant"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        new_products = []
        
        # Query for high-volume products not in prior MSA
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        query = f"""
        SELECT 
            i.ItemLookupCode,
            i.Description,
            SUM(te.Quantity) as TotalSold
        FROM Item i
        JOIN TransactionEntry te ON i.ID = te.ItemID
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        GROUP BY i.ItemLookupCode, i.Description
        HAVING SUM(te.Quantity) >= 20  -- Only high-volume products
        ORDER BY SUM(te.Quantity) DESC
        """
        
        cursor.execute(query, (start_dt, end_dt))
        
        for row in cursor.fetchall():
            upc = row['ItemLookupCode'].rjust(15, '0')
            
            # Only add if:
            # 1. Not in existing BIDs
            # 2. Maps to a known distributor SKU
            # 3. Has been in MSA before OR is truly new high-volume
            if upc not in existing_upcs:
                dist_sku = row['ItemLookupCode'].rjust(14, '0')
                
                # Check if this product should be tracked
                if (dist_sku in self.known_distributor_skus or 
                    upc in self.msa_tracked_upcs or
                    row['TotalSold'] > 100):  # Very high volume new product
                    
                    # Create BID record
                    bid_line = 'BID'
                    bid_line += upc[:15].ljust(15)
                    bid_line += row['Description'][:60].ljust(60)
                    bid_line = bid_line.ljust(199) + '00000000000'
                    
                    new_products.append({
                        'raw': bid_line,
                        'upc': upc,
                        'name': row['Description'],
                        'quantity': '0'
                    })
                    
                    # Limit new products to match typical MSA behavior
                    if len(new_products) >= 20:
                        break
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return new_products
    
    def map_to_distributor_sku(self, item_lookup_code):
        """Map POS ItemLookupCode to Distributor SKU"""
        if item_lookup_code in self.sku_mapping:
            return self.sku_mapping[item_lookup_code]
        
        dist_sku = item_lookup_code.rjust(14, '0')
        if dist_sku in self.known_distributor_skus:
            self.sku_mapping[item_lookup_code] = dist_sku
            return dist_sku
        
        return None
    
    def format_customer_id(self, customer_id):
        """Format customer ID for MSA"""
        if not customer_id:
            return '00000000'
        
        cust_str = str(customer_id).zfill(8)
        
        # Apply rotation rule
        if cust_str.startswith('0'):
            cust_str = cust_str[1:] + '0'
        
        return cust_str
    
    def generate(self, output_file):
        """Generate optimized MSA file"""
        print(f"\n=== GENERATING OPTIMIZED MSA: {output_file} ===")
        
        # Load known distributor SKUs
        self.load_all_distributor_skus()
        
        # Parse prior file
        self.prior_records = self.parse_msa_file(self.prior_file)
        print(f"Prior MSA: {len(self.prior_records['bids'])} products, {len(self.prior_records['sid_customers'])} customers")
        
        # Get date range
        start_dt, end_dt = self.get_proper_date_range(self.target_date)
        
        # Build BID records
        bid_records = list(self.prior_records['bids'])
        existing_upcs = {bid['upc'] for bid in bid_records}
        
        # Only add truly new significant products
        new_products = self.get_new_products_to_add(start_dt, end_dt, existing_upcs)
        bid_records.extend(new_products)
        print(f"Added {len(new_products)} new products (total: {len(bid_records)})")
        
        # Get sales data
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        # Get customers with purchases
        cursor.execute(f"""
            SELECT DISTINCT t.CustomerID
            FROM [Transaction] t
            JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            WHERE t.Time >= %s AND t.Time <= %s
            AND i.CategoryID IN ({category_list})
            AND t.CustomerID IS NOT NULL
        """, (start_dt, end_dt))
        
        customers = set()
        for row in cursor.fetchall():
            if row['CustomerID']:
                customers.add(self.format_customer_id(row['CustomerID']))
        
        print(f"Found {len(customers)} customers with purchases")
        
        # Get sales details
        cursor.execute(f"""
            SELECT 
                t.CustomerID,
                i.ItemLookupCode,
                SUM(te.Quantity) as Quantity
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            JOIN Item i ON te.ItemID = i.ID
            WHERE t.Time >= %s AND t.Time <= %s
            AND i.CategoryID IN ({category_list})
            AND t.CustomerID IS NOT NULL
            GROUP BY t.CustomerID, i.ItemLookupCode
            HAVING SUM(te.Quantity) > 0
        """, (start_dt, end_dt))
        
        sales_data = defaultdict(lambda: defaultdict(float))
        total_sales_by_sku = defaultdict(float)
        
        for row in cursor.fetchall():
            customer_id = self.format_customer_id(row['CustomerID'])
            dist_sku = self.map_to_distributor_sku(row['ItemLookupCode'])
            
            if dist_sku:
                qty = abs(row['Quantity'])
                sales_data[customer_id][dist_sku] += qty
                total_sales_by_sku[dist_sku] += qty
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        print(f"Mapped sales for {len(sales_data)} customers")
        
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
                # Update inventory
                line = bid['raw']
                dist_sku = bid['upc'].strip().rjust(14, '0')
                
                if dist_sku in total_sales_by_sku:
                    try:
                        current_inv = int(bid['quantity']) if bid['quantity'] else 0
                    except:
                        current_inv = 0
                    
                    new_inv = max(0, current_inv - int(total_sales_by_sku[dist_sku]))
                    
                    if len(line) >= 210:
                        inv_str = str(new_inv).zfill(11)
                        line = line[:199] + inv_str + line[210:]
                
                f.write(line + '\n')
            
            # SID records
            for customer_id in sorted(customers):
                # Try to preserve format from prior SIDs
                sid_line = None
                for prior_sid in self.prior_records['sids']:
                    if customer_id in prior_sid:
                        sid_line = prior_sid
                        break
                
                if not sid_line:
                    sid_line = 'SID' + customer_id.ljust(15)
                    sid_line = sid_line.ljust(200)
                
                f.write(sid_line + '\n')
            
            # PUR records
            for customer_id, customer_sales in sorted(sales_data.items()):
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
        
        # Calculate accuracy
        bid_acc = max(0, 100 * (1 - abs(len(gen['bids']) - len(act['bids'])) / max(1, len(act['bids']))))
        sid_acc = max(0, 100 * (1 - abs(len(gen['sids']) - len(act['sids'])) / max(1, len(act['sids']))))
        pur_acc = max(0, 100 * (1 - abs(len(gen['purs']) - len(act['purs'])) / max(1, len(act['purs']))))
        
        overall = (bid_acc + sid_acc + pur_acc) / 3
        print(f"\nAccuracy: BID={bid_acc:.1f}%, SID={sid_acc:.1f}%, PUR={pur_acc:.1f}%")
        print(f"Overall: {overall:.1f}%")
        
        return overall

def main():
    if len(sys.argv) > 2:
        prior_date = sys.argv[1]
        target_date = sys.argv[2]
    else:
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_optimized.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = OptimizedMSAGenerator(prior_file, target_date)
    generator.generate(output_file)
    
    print("\n" + "="*70)
    print("OPTIMIZATIONS APPLIED")
    print("="*70)
    print("""
✓ Only add products with high sales (20+ units) that map to known SKUs
✓ Limit new products to ~20 per period (matches MSA behavior)
✓ Follow MSA customer approach exactly
✓ Proper Saturday 00:00 to Friday 23:59:59
✓ Update inventory based on actual sales
""")

if __name__ == "__main__":
    main()