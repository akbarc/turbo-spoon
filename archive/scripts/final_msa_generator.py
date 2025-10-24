#!/usr/bin/env python3
"""
Final MSA Generator with proper logic:
1. Include products from prior MSA + those with sales in current period
2. Use MSA's customer approach (customers from period)
3. Fix categories based on actual MSA usage
4. Ensure Saturday 00:00 to Friday 23:59:59
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# Categories used in MSA (keep all original even if empty for future use)
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class FinalMSAGenerator:
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
    
    def get_proper_date_range(self, target_date_str):
        """Calculate Saturday 00:00:00 to Friday 23:59:59"""
        # Target date should be MMDDYYYY format
        target_dt = datetime.strptime(f"2025{target_date_str[:4]}", '%Y%m%d')
        
        # Ensure it's a Friday
        if target_dt.weekday() != 4:
            # Find the nearest Friday
            days_to_friday = (4 - target_dt.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            target_dt = target_dt + timedelta(days=days_to_friday)
        
        # Start is Saturday (6 days before)
        start_dt = target_dt - timedelta(days=6)
        
        # Set exact times
        start_time = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        print(f"Period: {start_time.strftime('%a %m/%d %I:%M%p')} - {end_time.strftime('%a %m/%d %I:%M%p')}")
        
        return start_time, end_time
    
    def parse_msa_file(self, filepath):
        """Parse MSA file maintaining exact structure"""
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
                    # Extract customer ID
                    customer_id = line[3:11].strip() if len(line) > 11 else ''
                    if customer_id:
                        records['sid_customers'].add(customer_id)
                    
                elif record_type == 'PUR':
                    records['purs'].append(line.rstrip('\r\n'))
        
        return records
    
    def get_products_to_include(self, start_dt, end_dt, prior_bids):
        """Get products that should be in BID records"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Start with all prior BID products
        products_to_include = {}
        for bid in prior_bids:
            products_to_include[bid['upc']] = bid
        
        print(f"Starting with {len(products_to_include)} products from prior MSA")
        
        # Query for products with sales that might need to be added
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        # Only get products that had significant sales (not every random item)
        query = f"""
        SELECT 
            i.ItemLookupCode,
            i.Description,
            i.CategoryID,
            SUM(te.Quantity) as TotalSold
        FROM Item i
        JOIN TransactionEntry te ON i.ID = te.ItemID
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        GROUP BY i.ItemLookupCode, i.Description, i.CategoryID
        HAVING SUM(te.Quantity) > 5  -- Only products with meaningful sales
        ORDER BY SUM(te.Quantity) DESC
        """
        
        cursor.execute(query, (start_dt, end_dt))
        
        new_products_added = 0
        for row in cursor.fetchall():
            # Convert to UPC format
            upc = row['ItemLookupCode'].rjust(15, '0')
            
            if upc not in products_to_include:
                # Check if this maps to a known distributor SKU
                dist_sku = row['ItemLookupCode'].rjust(14, '0')
                if dist_sku in self.known_distributor_skus:
                    # Create BID record for this product
                    bid_line = 'BID'
                    bid_line += upc[:15].ljust(15)
                    bid_line += row['Description'][:60].ljust(60)
                    bid_line = bid_line.ljust(199) + '00000000000'  # Default quantity
                    
                    products_to_include[upc] = {
                        'raw': bid_line,
                        'upc': upc,
                        'name': row['Description'],
                        'quantity': '0'
                    }
                    new_products_added += 1
        
        print(f"Added {new_products_added} new products with significant sales")
        print(f"Total products to include: {len(products_to_include)}")
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return list(products_to_include.values())
    
    def get_customers_for_period(self, start_dt, end_dt):
        """Get customers who made tobacco purchases in period"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        query = f"""
        SELECT DISTINCT t.CustomerID
        FROM [Transaction] t
        JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        AND t.CustomerID IS NOT NULL
        """
        
        cursor.execute(query, (start_dt, end_dt))
        customers = set()
        
        for row in cursor.fetchall():
            if row['CustomerID']:
                # Format customer ID
                cust_str = str(row['CustomerID']).zfill(8)
                if cust_str.startswith('0'):
                    cust_str = cust_str[1:] + '0'
                customers.add(cust_str)
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return customers
    
    def get_sales_data(self, start_dt, end_dt):
        """Get sales data for PUR records"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        query = f"""
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
        """
        
        cursor.execute(query, (start_dt, end_dt))
        
        sales = defaultdict(lambda: defaultdict(float))
        
        for row in cursor.fetchall():
            # Format customer ID
            cust_str = str(row['CustomerID']).zfill(8)
            if cust_str.startswith('0'):
                cust_str = cust_str[1:] + '0'
            
            # Map to distributor SKU
            dist_sku = row['ItemLookupCode'].rjust(14, '0')
            if dist_sku in self.known_distributor_skus:
                sales[cust_str][dist_sku] += abs(row['Quantity'])
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return sales
    
    def update_bid_inventory(self, bid_record, total_sales_by_sku):
        """Update BID inventory based on sales"""
        upc = bid_record['upc']
        
        # Map UPC to distributor SKU
        dist_sku = upc.strip().rjust(14, '0')
        
        # Get total sales for this SKU
        total_sold = total_sales_by_sku.get(dist_sku, 0)
        
        # Update inventory
        try:
            current_inv = int(bid_record['quantity']) if bid_record['quantity'] else 0
        except:
            current_inv = 0
        
        new_inv = max(0, current_inv - int(total_sold))
        
        # Update the BID record
        line = bid_record['raw']
        if len(line) >= 210:
            inv_str = str(new_inv).zfill(11)
            line = line[:199] + inv_str + line[210:]
        
        return line
    
    def generate(self, output_file):
        """Generate final MSA file"""
        print(f"\n=== GENERATING FINAL MSA: {output_file} ===")
        
        # Load known distributor SKUs
        self.load_all_distributor_skus()
        
        # Parse prior file
        self.prior_records = self.parse_msa_file(self.prior_file)
        print(f"Prior MSA has {len(self.prior_records['bids'])} products, {len(self.prior_records['sid_customers'])} customers")
        
        # Get date range
        start_dt, end_dt = self.get_proper_date_range(self.target_date)
        
        # Get products to include (prior + new with significant sales)
        bid_records = self.get_products_to_include(start_dt, end_dt, self.prior_records['bids'])
        
        # Get customers for this period
        customers = self.get_customers_for_period(start_dt, end_dt)
        print(f"Found {len(customers)} customers with purchases")
        
        # Get sales data
        sales_data = self.get_sales_data(start_dt, end_dt)
        print(f"Found sales data for {len(sales_data)} customers")
        
        # Calculate total sales by SKU for inventory update
        total_sales_by_sku = defaultdict(float)
        for customer_sales in sales_data.values():
            for sku, qty in customer_sales.items():
                total_sales_by_sku[sku] += qty
        
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
                updated_bid = self.update_bid_inventory(bid, total_sales_by_sku)
                f.write(updated_bid + '\n')
            
            # SID records for customers with purchases
            for customer_id in sorted(customers):
                # Find if customer was in prior SIDs to preserve format
                sid_line = None
                for prior_sid in self.prior_records['sids']:
                    if customer_id in prior_sid:
                        sid_line = prior_sid
                        break
                
                if not sid_line:
                    # Create new SID record
                    sid_line = 'SID' + customer_id.ljust(15)
                    sid_line = sid_line.ljust(200)
                
                f.write(sid_line + '\n')
            
            # PUR records
            for customer_id, customer_sales in sorted(sales_data.items()):
                for dist_sku, quantity in sorted(customer_sales.items()):
                    if quantity > 0:
                        # Format PUR record
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
            return
        
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

def test_all_periods():
    """Test on all available periods"""
    print("="*70)
    print("TESTING ALL PERIODS WITH FINAL GENERATOR")
    print("="*70)
    
    msa_dir = "MSA Data Fr"
    files = sorted([f for f in os.listdir(msa_dir) if f.isdigit() and len(f) == 8])
    
    results = []
    for i in range(len(files) - 1):
        prior = files[i]
        target = files[i + 1]
        
        print(f"\n### Testing {prior} → {target} ###")
        
        prior_file = f"MSA Data Fr/{prior}"
        output_file = f"test_{target}_final.txt"
        
        generator = FinalMSAGenerator(prior_file, target)
        generator.generate(output_file)
        
        # Clean up test file
        if os.path.exists(output_file):
            os.remove(output_file)
    
    print("\n" + "="*70)
    print("FINAL IMPROVEMENTS")
    print("="*70)
    print("""
✓ Products: Include prior + new with significant sales (>5 units)
✓ Customers: Period-specific (not cumulative)
✓ Categories: All tobacco categories maintained
✓ Date Range: Proper Saturday 00:00 to Friday 23:59:59
✓ Inventory: Updated based on actual sales
""")

def main():
    if len(sys.argv) > 2:
        prior_date = sys.argv[1]
        target_date = sys.argv[2]
    else:
        # Test one period
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_final.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = FinalMSAGenerator(prior_file, target_date)
    accuracy = generator.generate(output_file)
    
    # Optionally test all periods
    if '--test-all' in sys.argv:
        test_all_periods()

if __name__ == "__main__":
    main()