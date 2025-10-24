#!/usr/bin/env python3
"""
Accurate MSA Generator - Matches exact format of actual files
Uses Distributor SKUs in PUR records as per MULTICAT specification
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# Tobacco category IDs
TOBACCO_CATEGORIES = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

class MSAGenerator:
    def __init__(self, prior_file, target_date):
        self.prior_file = prior_file
        self.target_date = target_date
        self.prior_records = None
        self.sku_to_distributor_sku = {}  # Maps POS SKU to Distributor SKU
        self.distributor_sku_to_upc = {}  # Maps Distributor SKU to full UPC
        
    def parse_msa_file(self, filepath):
        """Parse MSA file with exact format preservation"""
        records = {
            'header': None,
            'bids': [],
            'bid_by_upc': {},
            'sids': [],
            'purs': [],
            'pur_skus': set()  # Track unique distributor SKUs in PURs
        }
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                
                record_type = line[:3]
                
                if record_type == 'HID':
                    records['header'] = line.rstrip('\r\n')
                    
                elif record_type == 'BID':
                    upc = line[3:18].strip() if len(line) > 18 else ''
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
                    
                elif record_type == 'PUR':
                    # Extract distributor SKU from exact position
                    distributor_sku = line[27:41].strip() if len(line) > 41 else ''
                    if distributor_sku:
                        records['pur_skus'].add(distributor_sku)
                    
                    records['purs'].append({
                        'raw': line.rstrip('\r\n'),
                        'customer_id': line[3:11].strip() if len(line) > 11 else '',
                        'distributor_sku': distributor_sku
                    })
        
        return records
    
    def build_sku_mappings(self):
        """Build mapping between POS SKUs and Distributor SKUs"""
        print("Building SKU mappings...")
        
        # Analyze distributor SKUs from prior file
        for dist_sku in self.prior_records['pur_skus']:
            # Try to find corresponding BID record
            for upc, bid in self.prior_records['bid_by_upc'].items():
                # Check if distributor SKU matches end of UPC
                if upc.endswith(dist_sku) or dist_sku in upc:
                    self.distributor_sku_to_upc[dist_sku] = upc
                    break
        
        print(f"Mapped {len(self.distributor_sku_to_upc)} distributor SKUs to UPCs")
        
        # Now map to POS items
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        category_list = ','.join(str(c) for c in TOBACCO_CATEGORIES)
        query = f"""
        SELECT ItemLookupCode, Description, CategoryID, ID as ItemID
        FROM Item
        WHERE CategoryID IN ({category_list})
        """
        cursor.execute(query)
        
        for item in cursor:
            pos_sku = item['ItemLookupCode']
            
            # Try to match with distributor SKUs
            # Strategy: POS SKU might match distributor SKU directly or with padding
            pos_clean = pos_sku.lstrip('0')
            
            for dist_sku in self.prior_records['pur_skus']:
                dist_clean = dist_sku.lstrip('0')
                
                # Direct match
                if pos_clean == dist_clean:
                    self.sku_to_distributor_sku[pos_sku] = dist_sku
                    break
                # Check if POS SKU is contained in distributor SKU
                elif pos_clean in dist_sku:
                    self.sku_to_distributor_sku[pos_sku] = dist_sku
                    break
                # Check last N digits match
                elif len(pos_clean) >= 8 and len(dist_clean) >= 8:
                    if pos_clean[-8:] == dist_clean[-8:]:
                        self.sku_to_distributor_sku[pos_sku] = dist_sku
                        break
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        print(f"Mapped {len(self.sku_to_distributor_sku)} POS SKUs to distributor SKUs")
    
    def get_sales_data(self, start_date, end_date):
        """Get sales data from POS"""
        conn = connection_pool.get_connection()
        cursor = conn.cursor(as_dict=True)
        
        # Get items that we can map
        mapped_items = []
        for pos_sku, dist_sku in self.sku_to_distributor_sku.items():
            cursor.execute("SELECT ID FROM Item WHERE ItemLookupCode = %s", pos_sku)
            result = cursor.fetchone()
            if result:
                mapped_items.append(result['ID'])
        
        if not mapped_items:
            print("No mapped items found")
            return {}
        
        # Get sales for mapped items
        placeholders = ','.join(['%s'] * len(mapped_items))
        query = f"""
        SELECT 
            t.CustomerID,
            i.ItemLookupCode,
            SUM(te.Quantity) as Quantity
        FROM TransactionEntry te
        JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
        JOIN Item i ON te.ItemID = i.ID
        WHERE t.Time >= %s AND t.Time <= %s
        AND te.ItemID IN ({placeholders})
        GROUP BY t.CustomerID, i.ItemLookupCode
        """
        
        params = [start_date, end_date] + mapped_items
        cursor.execute(query, params)
        
        # Organize sales by customer and distributor SKU
        sales = defaultdict(lambda: defaultdict(float))
        
        for row in cursor:
            customer_id = self.format_customer_id(row['CustomerID'])
            pos_sku = row['ItemLookupCode']
            
            if pos_sku in self.sku_to_distributor_sku:
                dist_sku = self.sku_to_distributor_sku[pos_sku]
                sales[customer_id][dist_sku] += abs(row['Quantity'])
        
        cursor.close()
        connection_pool.return_connection(conn)
        
        return sales
    
    def format_customer_id(self, customer_id):
        """Format customer ID for MSA"""
        if not customer_id:
            return '00000000'
        
        # Ensure 8 digits
        cust_str = str(customer_id).zfill(8)
        
        # Rotate if starts with 0
        if cust_str.startswith('0'):
            cust_str = cust_str[1:] + '0'
        
        return cust_str
    
    def format_pur_record(self, customer_id, distributor_sku, quantity=1):
        """Format PUR record matching exact structure"""
        # PUR + customer(8) + padding(19) + distributor_sku(14) + padding + quantity data
        line = 'PUR'
        line += customer_id[:8].ljust(8)  # Customer ID (8 chars)
        line += '0' + ' ' * 18  # Field pattern from actual files
        line += distributor_sku[:14].ljust(14)  # Distributor SKU (14 chars)
        line += ' ' * 61  # Padding to position 102
        
        # Quantity section (matches actual format)
        # Format: 001XXXXXXXX.XXXXXXXXXXXX.XX
        qty_str = f"001{int(quantity):08d}.000010000000.00"
        line += qty_str
        
        # Ensure exactly 130 characters
        return line[:130].ljust(130)
    
    def update_bid_inventory(self, bid_record, sales_data):
        """Update BID record inventory based on sales"""
        # Extract UPC
        upc = bid_record['upc']
        
        # Find distributor SKU for this UPC
        dist_sku = None
        for ds, u in self.distributor_sku_to_upc.items():
            if u == upc:
                dist_sku = ds
                break
        
        if not dist_sku:
            # No sales possible, return unchanged
            return bid_record['raw']
        
        # Calculate total sales
        total_sales = 0
        for customer_sales in sales_data.values():
            if dist_sku in customer_sales:
                total_sales += customer_sales[dist_sku]
        
        # Update inventory
        try:
            current_inv = int(bid_record['quantity']) if bid_record['quantity'] else 0
        except:
            current_inv = 0
        
        new_inv = max(0, current_inv - int(total_sales))
        
        # Format updated BID record
        line = bid_record['raw']
        if len(line) >= 210:
            # Replace inventory field (positions 199-210)
            inv_str = str(new_inv).zfill(11)
            line = line[:199] + inv_str + line[210:]
        
        return line
    
    def generate(self, output_file):
        """Generate complete MSA file"""
        print(f"Generating MSA file: {output_file}")
        
        # Parse prior file
        self.prior_records = self.parse_msa_file(self.prior_file)
        
        # Build SKU mappings
        self.build_sku_mappings()
        
        # Calculate date range
        target_dt = datetime.strptime(f"2025{self.target_date[:4]}", '%Y%m%d')
        if target_dt.weekday() == 4:  # Friday
            start_dt = target_dt - timedelta(days=6)
        else:
            days_since_sat = (target_dt.weekday() + 2) % 7
            start_dt = target_dt - timedelta(days=days_since_sat)
        
        # Get sales data
        sales_data = self.get_sales_data(
            start_dt.strftime('%Y-%m-%d'),
            target_dt.strftime('%Y-%m-%d 23:59:59')
        )
        
        print(f"Found sales for {len(sales_data)} customers")
        
        # Generate output
        with open(output_file, 'w') as f:
            # Header - update date
            if self.prior_records['header']:
                header = self.prior_records['header']
                # Replace date (typically position 18-25)
                old_date = f"2025{self.prior_file.split('/')[-1][:4]}"
                new_date = f"2025{self.target_date[:4]}"
                header = header.replace(old_date, new_date)
                f.write(header + '\n')
            
            # BID records - update inventory
            for bid in self.prior_records['bids']:
                updated_bid = self.update_bid_inventory(bid, sales_data)
                f.write(updated_bid + '\n')
            
            # SID records - include ALL from prior
            for sid in self.prior_records['sids']:
                f.write(sid + '\n')
            
            # PUR records - generate from sales
            for customer_id, customer_sales in sorted(sales_data.items()):
                for dist_sku, quantity in sorted(customer_sales.items()):
                    if quantity > 0:
                        pur_line = self.format_pur_record(customer_id, dist_sku, quantity)
                        f.write(pur_line + '\n')
        
        print(f"Generated: {output_file}")
        
        # Validate
        self.validate(output_file)
    
    def validate(self, generated_file):
        """Validate against actual file if it exists"""
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
        bid_acc = (1 - abs(len(gen['bids']) - len(act['bids'])) / len(act['bids'])) * 100
        sid_acc = (1 - abs(len(gen['sids']) - len(act['sids'])) / len(act['sids'])) * 100
        pur_acc = (1 - abs(len(gen['purs']) - len(act['purs'])) / len(act['purs'])) * 100
        
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
    output_file = f"generated_msa_{target_date}_accurate.txt"
    
    if not os.path.exists(prior_file):
        print(f"Prior file not found: {prior_file}")
        return
    
    generator = MSAGenerator(prior_file, target_date)
    generator.generate(output_file)

if __name__ == "__main__":
    main()