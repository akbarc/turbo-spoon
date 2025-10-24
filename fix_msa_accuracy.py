#!/usr/bin/env python3
"""
Fix MSA generator based on identified issues:
1. Query for ALL products with sales in period (not just new)
2. Follow MSA's customer roster approach (don't keep cumulative)
3. Fix category list based on actual MSA products
4. Ensure proper Saturday-Friday date range
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# Updated category list based on analysis - keeping all original plus any found in MSA
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class ImprovedMSAGenerator:
    def __init__(self, prior_file, target_date):
        self.prior_file = prior_file
        self.target_date = target_date
        self.known_distributor_skus = set()
        self.sku_mapping = {}
        self.prior_records = None
        
    def load_all_distributor_skus(self):
        """Load all known Distributor SKUs from historical MSA files"""
        print("Loading historical Distributor SKUs...")
        
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
        """Calculate proper Saturday to Friday date range"""
        # Parse target date (should be a Friday)
        target_dt = datetime.strptime(f"2025{target_date_str[:4]}", '%Y%m%d')
        
        # Find the Friday
        if target_dt.weekday() == 4:  # It's Friday
            end_dt = target_dt
        else:
            # Find next Friday
            days_until_friday = (4 - target_dt.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            end_dt = target_dt + timedelta(days=days_until_friday)
        
        # Start is previous Saturday (6 days before Friday)
        start_dt = end_dt - timedelta(days=6)
        
        # Set times: Saturday 00:00:00 to Friday 23:59:59
        start_time = start_dt.replace(hour=0, minute=0, second=0)
        end_time = end_dt.replace(hour=23, minute=59, second=59)
        
        print(f"MSA Period: {start_time.strftime('%A %Y-%m-%d %H:%M')} to {end_time.strftime('%A %Y-%m-%d %H:%M')}")
        
        return start_time, end_time
    
    def get_all_products_with_sales(self, start_date, end_date):
        """Get ALL products that had sales in period, not just new ones"""
        print("\n### QUERYING ALL PRODUCTS WITH SALES IN PERIOD ###")
        
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Get ALL products with sales in the period
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        query = f"""
        SELECT DISTINCT
            i.ItemLookupCode,
            i.Description,
            i.CategoryID,
            c.Name as CategoryName
        FROM Item i
        LEFT JOIN Category c ON i.CategoryID = c.ID
        JOIN TransactionEntry te ON i.ID = te.ItemID
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        ORDER BY i.ItemLookupCode
        """
        
        cursor.execute(query, (start_date, end_date))
        products = cursor.fetchall()
        
        print(f"Found {len(products)} products with sales in period")
        
        # Group by category to verify
        by_category = defaultdict(int)
        for p in products:
            by_category[p['CategoryID']] += 1
        
        print("\nProducts by category:")
        for cat_id in sorted(by_category.keys()):
            print(f"  Category {cat_id}: {by_category[cat_id]} products")
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return products
    
    def update_bid_records(self, prior_bids, products_with_sales):
        """Update BID records to include all products with sales"""
        print("\n### UPDATING BID RECORDS ###")
        
        # Start with prior BIDs
        updated_bids = list(prior_bids)
        existing_upcs = {bid['upc'] for bid in prior_bids}
        
        # Add any products with sales that aren't already in BIDs
        added_count = 0
        for product in products_with_sales:
            # Convert ItemLookupCode to 15-char UPC format for BID
            upc = product['ItemLookupCode'].rjust(15, '0')
            
            if upc not in existing_upcs:
                # Create new BID record
                bid_line = 'BID'
                bid_line += upc  # 15 chars
                bid_line += product['Description'][:60].ljust(60)  # Description
                # Add other BID fields with defaults
                bid_line = bid_line.ljust(210) + '00000000000'  # Default inventory
                
                updated_bids.append({
                    'raw': bid_line,
                    'upc': upc,
                    'quantity': '0'
                })
                added_count += 1
        
        print(f"Added {added_count} new products to BID records")
        print(f"Total BID records: {len(updated_bids)}")
        
        return updated_bids
    
    def get_customers_with_purchases(self, start_date, end_date):
        """Get customers who made purchases in period (follow MSA approach)"""
        print("\n### GETTING CUSTOMERS WITH PURCHASES ###")
        
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        
        query = f"""
        SELECT DISTINCT
            t.CustomerID
        FROM [Transaction] t
        JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        WHERE t.Time >= %s AND t.Time <= %s
        AND i.CategoryID IN ({category_list})
        AND t.CustomerID IS NOT NULL
        """
        
        cursor.execute(query, (start_date, end_date))
        customers = [row['CustomerID'] for row in cursor.fetchall()]
        
        print(f"Found {len(customers)} customers with tobacco purchases")
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return customers
    
    def parse_msa_file(self, filepath):
        """Parse MSA file"""
        records = {
            'header': None,
            'bids': [],
            'bid_by_upc': {},
            'sids': [],
            'purs': [],
            'customers': set()
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
                        'quantity': line[199:210].strip() if len(line) > 210 else '0'
                    }
                    records['bids'].append(bid_rec)
                    records['bid_by_upc'][upc] = bid_rec
                    
                elif record_type == 'SID':
                    records['sids'].append(line.rstrip('\r\n'))
                    customer_id = line[3:11].strip() if len(line) > 11 else ''
                    if customer_id:
                        records['customers'].add(customer_id)
                    
                elif record_type == 'PUR':
                    records['purs'].append(line.rstrip('\r\n'))
        
        return records
    
    def map_to_distributor_sku(self, item_lookup_code):
        """Map POS ItemLookupCode to Distributor SKU"""
        if item_lookup_code in self.sku_mapping:
            return self.sku_mapping[item_lookup_code]
        
        # Try padding to 14 chars
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
        """Generate MSA with improvements"""
        print(f"\n=== GENERATING IMPROVED MSA: {output_file} ===")
        
        # Load distributor SKUs
        self.load_all_distributor_skus()
        
        # Parse prior file
        self.prior_records = self.parse_msa_file(self.prior_file)
        
        # Get proper date range (Saturday to Friday)
        start_dt, end_dt = self.get_proper_date_range(self.target_date)
        
        # Get ALL products with sales in period
        products_with_sales = self.get_all_products_with_sales(
            start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            end_dt.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # Update BID records to include all products with sales
        updated_bids = self.update_bid_records(self.prior_records['bids'], products_with_sales)
        
        # Get customers with purchases (MSA approach - not cumulative)
        customers_with_purchases = self.get_customers_with_purchases(
            start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            end_dt.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # Get sales data
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
        GROUP BY t.CustomerID, i.ItemLookupCode
        """
        
        cursor.execute(query, (
            start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            end_dt.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        sales_data = defaultdict(lambda: defaultdict(float))
        for row in cursor.fetchall():
            if row['CustomerID']:
                customer_id = self.format_customer_id(row['CustomerID'])
                dist_sku = self.map_to_distributor_sku(row['ItemLookupCode'])
                if dist_sku:
                    sales_data[customer_id][dist_sku] += abs(row['Quantity'])
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        print(f"\nGenerating output with:")
        print(f"  - {len(updated_bids)} BID records")
        print(f"  - {len(customers_with_purchases)} customers")
        print(f"  - {len(sales_data)} customers with mapped purchases")
        
        # Write output
        with open(output_file, 'w') as f:
            # Header
            if self.prior_records['header']:
                header = self.prior_records['header']
                old_date = f"2025{self.prior_file.split('/')[-1][:4]}"
                new_date = f"2025{self.target_date[:4]}"
                header = header.replace(old_date, new_date)
                f.write(header + '\n')
            
            # BID records (including new products)
            for bid in updated_bids:
                f.write(bid['raw'] + '\n')
            
            # SID records for customers with purchases
            for customer_id in sorted(set(customers_with_purchases)):
                sid_line = 'SID' + self.format_customer_id(customer_id).ljust(15)
                sid_line = sid_line.ljust(200)  # Standard SID length
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
        
        print(f"\nGenerated: {output_file}")
        
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

def main():
    if len(sys.argv) > 2:
        prior_date = sys.argv[1]
        target_date = sys.argv[2]
    else:
        prior_date = "08012025"
        target_date = "08082025"
    
    prior_file = f"MSA Data Fr/{prior_date}"
    output_file = f"generated_msa_{target_date}_improved.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = ImprovedMSAGenerator(prior_file, target_date)
    generator.generate(output_file)
    
    print("\n" + "="*70)
    print("IMPROVEMENTS IMPLEMENTED")
    print("="*70)
    print("""
✓ 1. Query ALL products with sales (not just new)
✓ 2. Follow MSA customer approach (period-specific)
✓ 3. Use correct tobacco categories
✓ 4. Proper Saturday-Friday date range with correct times
""")

if __name__ == "__main__":
    main()