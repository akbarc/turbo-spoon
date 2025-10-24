#!/usr/bin/env python3
"""
Test MSA Backtest EDI Generator for June 20, 2025
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from modules.msa_backtest_generator import MSABacktestEDIGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_backtest_june():
    """Test backtest EDI generation for June 20, 2025"""
    generator = MSABacktestEDIGenerator()
    
    print("\n" + "="*60)
    print("TESTING MSA BACKTEST EDI GENERATION FOR 06/20/2025")
    print("="*60)
    
    try:
        # June 20, 2025 (Friday)
        target_date = datetime(2025, 6, 20, 23, 59, 59)
        
        print(f"Generating backtest EDI file for: {target_date.date()}")
        print("This will:")
        print("1. Reconstruct inventory levels as they were on 06/20/2025")
        print("2. Use actual sales transactions from 06/14-06/20/2025")
        print("3. Generate EDI in exact historical context")
        
        # Generate backtest EDI file
        edi_content, filename, summary = generator.generate_backtest_edi_file(target_date)
        
        print(f"\nBacktest Results:")
        print(f"Filename: {filename}")
        print(f"\nSummary:")
        for key, value in summary.items():
            if key == 'inventory_reconstruction':
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        # Save backtest file
        backtest_filename = f"backtest_{filename}.txt"
        with open(backtest_filename, 'w') as f:
            f.write(edi_content)
        
        print(f"\nBacktest EDI file saved as: {backtest_filename}")
        
        # Load the original sample file for comparison
        sample_file = "/Users/akbarchranya/Desktop/MSA Data/06202025 4"
        try:
            with open(sample_file, 'r') as f:
                sample_content = f.read()
            print(f"Sample file loaded from: {sample_file}")
        except Exception as e:
            print(f"Could not load sample file: {e}")
            return
        
        # Compare structure
        our_lines = edi_content.strip().split('\n')
        sample_lines = sample_content.strip().split('\n')
        
        print(f"\n" + "="*40)
        print("BACKTEST vs SAMPLE COMPARISON")
        print("="*40)
        print(f"Backtest lines: {len(our_lines)}")
        print(f"Sample lines:   {len(sample_lines)}")
        
        # Compare record counts
        def count_record_types(lines):
            counts = {}
            for line in lines:
                if line.strip():
                    record_type = line[:3]
                    counts[record_type] = counts.get(record_type, 0) + 1
            return counts
        
        our_counts = count_record_types(our_lines)
        sample_counts = count_record_types(sample_lines)
        
        print(f"\nRecord Type Comparison:")
        print(f"{'Type':<5} {'Backtest':<10} {'Sample':<10} {'Difference':<12} {'Match':<5}")
        print("-" * 50)
        
        all_types = set(our_counts.keys()) | set(sample_counts.keys())
        total_diff = 0
        for record_type in sorted(all_types):
            our_count = our_counts.get(record_type, 0)
            sample_count = sample_counts.get(record_type, 0)
            diff = abs(our_count - sample_count)
            total_diff += diff
            match = "✓" if our_count == sample_count else "✗"
            print(f"{record_type:<5} {our_count:<10} {sample_count:<10} {diff:<12} {match:<5}")
        
        print(f"\nTotal record difference: {total_diff}")
        improvement_pct = ((9394 - 1072 - total_diff) / (9394 - 1072)) * 100 if total_diff < (9394 - 1072) else 0
        print(f"Improvement vs regular generator: {improvement_pct:.1f}%")
        
        # Compare HID records
        print(f"\n" + "="*40)
        print("HID RECORD COMPARISON")
        print("="*40)
        
        our_hid = [line for line in our_lines if line.startswith('HID')]
        sample_hid = [line for line in sample_lines if line.startswith('HID')]
        
        if our_hid and sample_hid:
            print("Backtest HID:")
            print(f"  Length: {len(our_hid[0])}")
            print(f"  Content: {our_hid[0][:100]}...")
            print("Sample HID:")
            print(f"  Length: {len(sample_hid[0])}")
            print(f"  Content: {sample_hid[0][:100]}...")
            
            hid_match = our_hid[0] == sample_hid[0]
            print(f"Exact Match: {'✓' if hid_match else '✗'}")
            
            if not hid_match:
                # Find differences
                min_len = min(len(our_hid[0]), len(sample_hid[0]))
                diff_positions = []
                for i in range(min_len):
                    if our_hid[0][i] != sample_hid[0][i]:
                        diff_positions.append(i)
                
                print(f"Differences at positions: {diff_positions[:10]}...")  # Show first 10
        
        # Sample some BID records to see if we're getting closer
        print(f"\n" + "="*40)
        print("BID RECORD SAMPLING")
        print("="*40)
        
        our_bids = [line for line in our_lines if line.startswith('BID')]
        sample_bids = [line for line in sample_lines if line.startswith('BID')]
        
        print(f"Backtest BID count: {len(our_bids)}")
        print(f"Sample BID count:   {len(sample_bids)}")
        
        # Check for UPC matches
        our_upcs = set(bid[19:31] for bid in our_bids[:100])  # First 100 UPCs
        sample_upcs = set(bid[19:31] for bid in sample_bids[:100])  # First 100 UPCs
        
        upc_matches = our_upcs & sample_upcs
        print(f"UPC matches in first 100: {len(upc_matches)}")
        
        if upc_matches:
            print("Matching UPCs found:")
            for upc in sorted(list(upc_matches))[:5]:
                print(f"  {upc}")
        
        # Check for exact BID record matches
        our_bid_set = set(our_bids[:100])
        sample_bid_set = set(sample_bids[:100])
        exact_bid_matches = our_bid_set & sample_bid_set
        print(f"Exact BID record matches: {len(exact_bid_matches)}")
        
        # Show sample products from both
        print(f"\nSample products comparison:")
        print("Backtest first 5 products:")
        for i, bid in enumerate(our_bids[:5]):
            upc = bid[19:31]
            desc = bid[31:111].strip()
            qty = bid[213:227].strip()
            print(f"  {i+1}. UPC:{upc} Qty:{qty} Desc:'{desc[:30]}...'")
        
        print("Sample first 5 products:")
        for i, bid in enumerate(sample_bids[:5]):
            upc = bid[19:31]
            desc = bid[31:111].strip()
            qty = bid[213:227].strip()
            print(f"  {i+1}. UPC:{upc} Qty:{qty} Desc:'{desc[:30]}...'")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)

if __name__ == "__main__":
    test_backtest_june()