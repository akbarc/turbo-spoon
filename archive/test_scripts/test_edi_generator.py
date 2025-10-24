#!/usr/bin/env python3
"""
Test MSA EDI Generator
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from modules.msa_edi_generator import MSAEDIGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_edi_generation():
    """Test EDI generation"""
    generator = MSAEDIGenerator()
    
    print("\n" + "="*60)
    print("TESTING MSA EDI GENERATION")
    print("="*60)
    
    try:
        # Find last Friday
        today = datetime.now()
        days_since_friday = (today.weekday() - 4) % 7
        if days_since_friday == 0:
            # Today is Friday, use last Friday
            last_friday = today - timedelta(days=7)
        else:
            last_friday = today - timedelta(days=days_since_friday)
        
        last_friday = last_friday.replace(hour=23, minute=59, second=59)
        
        print(f"\nGenerating EDI file for week ending: {last_friday.date()}")
        
        # Generate EDI file
        edi_content, filename, summary = generator.generate_edi_file(last_friday)
        
        print(f"\nFilename: {filename}")
        print(f"\nSummary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Save test file
        test_filename = f"test_{filename}.txt"
        
        with open(test_filename, 'w') as f:
            f.write(edi_content)
        
        print(f"\nEDI file saved as: {test_filename}")
        print(f"File size: {len(edi_content)} characters")
        
        # Show sample of the file
        lines = edi_content.split('\n')
        print(f"\nEDI file structure ({len(lines)} lines):")
        
        hid_lines = [i for i, line in enumerate(lines) if line.startswith('HID')]
        bid_lines = [i for i, line in enumerate(lines) if line.startswith('BID')]
        sid_lines = [i for i, line in enumerate(lines) if line.startswith('SID')]
        pur_lines = [i for i, line in enumerate(lines) if line.startswith('PUR')]
        tot_lines = [i for i, line in enumerate(lines) if line.startswith('TOT')]
        
        print(f"  HID records: {len(hid_lines)} (lines {hid_lines})")
        print(f"  BID records: {len(bid_lines)} (lines {bid_lines[0] if bid_lines else 'none'}-{bid_lines[-1] if bid_lines else 'none'})")
        print(f"  SID records: {len(sid_lines)} (lines {sid_lines[0] if sid_lines else 'none'}-{sid_lines[-1] if sid_lines else 'none'})")
        print(f"  PUR records: {len(pur_lines)} (lines {pur_lines[0] if pur_lines else 'none'}-{pur_lines[-1] if pur_lines else 'none'})")
        print(f"  TOT records: {len(tot_lines)} (lines {tot_lines})")
        
        # Show samples of each record type
        print("\nSample records:")
        
        # HID sample
        if hid_lines:
            print(f"\nHID (Header):")
            hid_line = lines[hid_lines[0]]
            print(f"  Length: {len(hid_line)} chars")
            print(f"  Content: {hid_line[:100]}...")
        
        # BID sample
        if bid_lines:
            print(f"\nBID (Product) - showing first 3:")
            for i in range(min(3, len(bid_lines))):
                bid_line = lines[bid_lines[i]]
                # Extract key parts
                item_code = bid_line[5:19]
                upc = bid_line[19:31]
                description = bid_line[31:111].strip()
                quantity = bid_line[213:227]
                print(f"  {i+1}. Item:{item_code} UPC:{upc} Desc:'{description[:30]}...' Qty:{quantity}")
        
        # SID sample  
        if sid_lines:
            print(f"\nSID (Customers) - showing first 3:")
            for i in range(min(3, len(sid_lines))):
                sid_line = lines[sid_lines[i]]
                customer_id = sid_line[3:15].strip()
                store_name = sid_line[30:62].strip()
                city = sid_line[135:160].strip()
                print(f"  {i+1}. ID:{customer_id} Store:'{store_name}' City:'{city}'")
        
        # PUR sample
        if pur_lines:
            print(f"\nPUR (Transactions) - showing first 5:")
            for i in range(min(5, len(pur_lines))):
                pur_line = lines[pur_lines[i]]
                customer_id = pur_line[3:15].strip()
                upc = pur_line[30:44]
                quantity = pur_line[127:135]
                price = pur_line[141:156]
                print(f"  {i+1}. Customer:{customer_id} UPC:{upc} Qty:{quantity} Price:{price}")
        
        # TOT sample
        if tot_lines:
            print(f"\nTOT (Totals):")
            tot_line = lines[tot_lines[0]]
            print(f"  Length: {len(tot_line)} chars")
            print(f"  Content: {tot_line}")
        
        # Validation checks
        print(f"\n" + "-"*40)
        print("VALIDATION CHECKS")
        print("-"*40)
        
        # Check line lengths
        expected_length = 468  # Based on EDI format
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            if line.strip():  # Skip empty lines
                print(f"Line {i+1}: {len(line)} chars ({'✓' if len(line) >= 200 else '✗'})")
        
        print(f"\nTotal characters: {len(edi_content):,}")
        print(f"Total lines: {len(lines)}")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)

if __name__ == "__main__":
    test_edi_generation()