#!/usr/bin/env python3
"""
MSA MultiCat Format Parser to CSV
Parses fixed-width MSA tobacco data files according to the specifications
in Master_MultiCat_Format_Requirements_TOB.pdf
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Any

class MSAParser:
    """Parser for MSA MultiCat format files"""
    
    def __init__(self):
        # Define record type specifications based on the PDF
        self.record_specs = {
            'HID': {  # Header Identification Record
                'distributor_id': (4, 11),
                'project_id': (12, 15),
                'test_indicator': (16, 16),
                'time_interval': (17, 17),
                'end_date': (18, 25),
                'distributor_name': (26, 57),
                'distributor_address': (58, 147),
                'distributor_city': (148, 172),
                'distributor_state': (173, 174),
                'distributor_zip': (175, 183),
                'distributor_country': (184, 186),
                'contact_last_name': (187, 206),
                'contact_first_name': (207, 226),
                'contact_phone': (232, 241),
                'contact_fax': (247, 256),
                'contact_email': (257, 316),
                'file_creation_date': (329, 336),
                'inventory_resubmission_flag': (337, 337)
            },
            'BID': {  # Brand Identification Record
                'upc_code': (4, 17),
                'distributor_sku': (18, 31),
                'product_description': (32, 81),
                'promotion_description': (82, 131),
                'items_per_selling_unit': (132, 137),
                'promotion_indicator': (138, 138),
                'nacs_category_code': (139, 144),
                'msa_category_code': (145, 150),
                'distributor_component_shipper_flag': (177, 177),
                'manufacturer_promotion_code': (178, 187),
                'manufacturer_product_id': (188, 201),
                'state_tax_jurisdiction': (208, 209),
                'alternate_upc_1': (210, 225),
                'alternate_upc_2': (226, 241),
                'measure_code_1': (248, 250),
                'measure_value_1': (251, 261)  # Inventory
            },
            'SID': {  # Ship-To Identification Record
                'ship_to_customer_number': (4, 11),
                'ship_to_customer_shipping_number': (12, 19),
                'ship_to_customer_shipping_number_ext': (20, 27),
                'ship_to_customer_name': (28, 59),
                'ship_to_customer_store_number': (60, 67),
                'ship_to_customer_address': (68, 157),
                'ship_to_customer_city': (158, 182),
                'ship_to_customer_state': (183, 184),
                'ship_to_customer_zip': (185, 193),
                'ship_to_customer_country': (194, 196),
                'state_tax_jurisdiction': (197, 198),
                'ship_to_customer_phone': (202, 211),
                'ship_to_customer_class_of_trade': (212, 231),
                'ship_to_customer_tdlinx': (232, 238),
                'ship_to_customer_cash_carry_indicator': (239, 239),
                'bill_to_customer_number': (259, 282),
                'customer_product_promotion_acceptance': (498, 498),
                'distributor_sales_rep_id': (499, 508)
            },
            'PUR': {  # Purchase Record
                'ship_to_customer_number': (4, 11),
                'ship_to_customer_shipping_number': (12, 19),
                'ship_to_customer_shipping_number_ext': (20, 27),
                'distributor_sku': (28, 41),
                'invoice_number': (45, 74),
                'transaction_date': (75, 82),
                'measure_code_1': (103, 105),
                'measure_value_1': (106, 116),  # Quantity shipped
                'measure_code_2': (117, 119),
                'measure_value_2': (120, 130)   # Dollars sold
            },
            'TOT': {  # Total Record
                'distributor_id': (4, 11),
                'end_date': (12, 19),
                'number_of_bid_records': (20, 28),
                'number_of_sid_records': (29, 37),
                'number_of_pur_records': (38, 46),
                'measure_code_1': (87, 89),
                'measure_value_1': (90, 104),
                'measure_code_2': (105, 107),
                'measure_value_2': (108, 122),
                'measure_code_3': (123, 125),
                'measure_value_3': (126, 140)
            }
        }
    
    def parse_field(self, line: str, start: int, end: int) -> str:
        """Extract and clean a field from a fixed-width line"""
        # Adjust for 1-based indexing in the spec
        value = line[start-1:end] if len(line) >= end else line[start-1:]
        return value.strip()
    
    def parse_record(self, line: str, record_type: str) -> Dict[str, Any]:
        """Parse a single record based on its type"""
        if record_type not in self.record_specs:
            return {}
        
        spec = self.record_specs[record_type]
        record = {'record_type': record_type}
        
        for field_name, (start, end) in spec.items():
            record[field_name] = self.parse_field(line, start, end)
        
        return record
    
    def parse_file(self, filepath: str) -> Dict[str, List[Dict]]:
        """Parse an entire MSA file"""
        records = {
            'header': None,
            'brands': [],
            'customers': [],
            'purchases': [],
            'total': None
        }
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if len(line) < 3:
                    continue
                
                record_type = line[:3]
                
                if record_type == 'HID':
                    records['header'] = self.parse_record(line, 'HID')
                elif record_type == 'BID':
                    records['brands'].append(self.parse_record(line, 'BID'))
                elif record_type == 'SID':
                    records['customers'].append(self.parse_record(line, 'SID'))
                elif record_type == 'PUR':
                    records['purchases'].append(self.parse_record(line, 'PUR'))
                elif record_type == 'TOT':
                    records['total'] = self.parse_record(line, 'TOT')
        
        return records
    
    def to_csv(self, records: Dict[str, List[Dict]], output_dir: str, base_filename: str):
        """Export parsed records to CSV files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Export header information
        if records['header']:
            header_file = os.path.join(output_dir, f"{base_filename}_header.csv")
            with open(header_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records['header'].keys())
                writer.writeheader()
                writer.writerow(records['header'])
            print(f"Created: {header_file}")
        
        # Export brands
        if records['brands']:
            brands_file = os.path.join(output_dir, f"{base_filename}_brands.csv")
            with open(brands_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records['brands'][0].keys())
                writer.writeheader()
                writer.writerows(records['brands'])
            print(f"Created: {brands_file} ({len(records['brands'])} records)")
        
        # Export customers
        if records['customers']:
            customers_file = os.path.join(output_dir, f"{base_filename}_customers.csv")
            with open(customers_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records['customers'][0].keys())
                writer.writeheader()
                writer.writerows(records['customers'])
            print(f"Created: {customers_file} ({len(records['customers'])} records)")
        
        # Export purchases
        if records['purchases']:
            purchases_file = os.path.join(output_dir, f"{base_filename}_purchases.csv")
            with open(purchases_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records['purchases'][0].keys())
                writer.writeheader()
                writer.writerows(records['purchases'])
            print(f"Created: {purchases_file} ({len(records['purchases'])} records)")
        
        # Export total
        if records['total']:
            total_file = os.path.join(output_dir, f"{base_filename}_total.csv")
            with open(total_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=records['total'].keys())
                writer.writeheader()
                writer.writerow(records['total'])
            print(f"Created: {total_file}")
    
    def create_combined_report(self, records: Dict[str, List[Dict]], output_file: str):
        """Create a combined report joining brands and purchases"""
        # Create a lookup for brands by SKU
        brand_lookup = {b['distributor_sku']: b for b in records['brands']}
        
        # Create combined records
        combined = []
        for purchase in records['purchases']:
            sku = purchase.get('distributor_sku', '')
            brand = brand_lookup.get(sku, {})
            
            combined_record = {
                'distributor_sku': sku,
                'product_description': brand.get('product_description', ''),
                'upc_code': brand.get('upc_code', ''),
                'msa_category_code': brand.get('msa_category_code', ''),
                'items_per_selling_unit': brand.get('items_per_selling_unit', ''),
                'inventory': brand.get('measure_value_1', ''),
                'customer_number': purchase.get('ship_to_customer_number', ''),
                'shipping_number': purchase.get('ship_to_customer_shipping_number', ''),
                'invoice_number': purchase.get('invoice_number', ''),
                'transaction_date': purchase.get('transaction_date', ''),
                'quantity_shipped': purchase.get('measure_value_1', ''),
                'dollars_sold': purchase.get('measure_value_2', '')
            }
            combined.append(combined_record)
        
        # Write combined report
        if combined:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=combined[0].keys())
                writer.writeheader()
                writer.writerows(combined)
            print(f"Created combined report: {output_file} ({len(combined)} records)")


def main():
    """Main function to process all MSA files"""
    parser = MSAParser()
    msa_dir = "/Users/akbarchranya/georgiadashboard/MSA Data FR"
    output_dir = "/Users/akbarchranya/georgiadashboard/MSA_CSV_Output"
    
    # Get all files in the MSA Data FR directory
    files = [f for f in os.listdir(msa_dir) if os.path.isfile(os.path.join(msa_dir, f))]
    
    print(f"Found {len(files)} MSA files to process\n")
    
    for filename in sorted(files):
        filepath = os.path.join(msa_dir, filename)
        print(f"\nProcessing: {filename}")
        print("-" * 50)
        
        try:
            # Parse the file
            records = parser.parse_file(filepath)
            
            # Create output directory for this file
            file_output_dir = os.path.join(output_dir, filename)
            
            # Export to CSV files
            parser.to_csv(records, file_output_dir, filename)
            
            # Create combined report if we have both brands and purchases
            if records['brands'] and records['purchases']:
                combined_file = os.path.join(file_output_dir, f"{filename}_combined.csv")
                parser.create_combined_report(records, combined_file)
            
            # Print summary
            print(f"\nSummary for {filename}:")
            print(f"  Brands: {len(records['brands'])}")
            print(f"  Customers: {len(records['customers'])}")
            print(f"  Purchases: {len(records['purchases'])}")
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    print(f"\n\nAll files processed. Output saved to: {output_dir}")


if __name__ == "__main__":
    main()