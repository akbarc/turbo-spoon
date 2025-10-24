#!/usr/bin/env python3
"""
Test MSA EDI Generator for specific date (06/20/2025) to compare with sample
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from modules.msa_edi_generator import MSAEDIGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_specific_date():
    """Test EDI generation for June 20, 2025"""
    generator = MSAEDIGenerator()
    
    print("\n" + "="*60)
    print("TESTING MSA EDI GENERATION FOR 06/20/2025")
    print("="*60)
    
    try:
        # June 20, 2025 (Friday)
        target_date = datetime(2025, 6, 20, 23, 59, 59)
        
        print(f"Generating EDI file for: {target_date.date()}")
        
        # Generate EDI file
        edi_content, filename, summary = generator.generate_edi_file(target_date)
        
        print(f"\nFilename: {filename}")
        print(f"Expected: 06202025")
        print(f"Match: {'✓' if filename == '06202025' else '✗'}")
        
        # Save our generated file
        test_filename = f"generated_{filename}.txt"
        with open(test_filename, 'w') as f:
            f.write(edi_content)
        
        print(f"\nGenerated file saved as: {test_filename}")
        
        # Read the sample file
        sample_file = "/Users/akbarchranya/Desktop/MSA Data/06202025 4"
        try:
            with open(sample_file, 'r') as f:
                sample_content = f.read()
            print(f"Sample file loaded from: {sample_file}")
        except Exception as e:
            print(f"Could not load sample file: {e}")
            return
        
        # Compare basic structure
        our_lines = edi_content.strip().split('\n')
        sample_lines = sample_content.strip().split('\n')
        
        print(f"\n" + "="*40)
        print("STRUCTURE COMPARISON")
        print("="*40)
        print(f"Generated lines: {len(our_lines)}")
        print(f"Sample lines:    {len(sample_lines)}")
        
        # Analyze record types
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
        print(f"{'Type':<5} {'Generated':<10} {'Sample':<10} {'Match':<5}")
        print("-" * 35)
        
        all_types = set(our_counts.keys()) | set(sample_counts.keys())
        for record_type in sorted(all_types):
            our_count = our_counts.get(record_type, 0)
            sample_count = sample_counts.get(record_type, 0)
            match = "✓" if our_count == sample_count else "✗"
            print(f"{record_type:<5} {our_count:<10} {sample_count:<10} {match:<5}")
        
        # Compare HID records
        print(f"\n" + "="*40)
        print("HID RECORD COMPARISON")
        print("="*40)
        
        our_hid = [line for line in our_lines if line.startswith('HID')]
        sample_hid = [line for line in sample_lines if line.startswith('HID')]
        
        if our_hid and sample_hid:
            print("Generated HID:")
            print(f"  {our_hid[0]}")
            print("Sample HID:")
            print(f"  {sample_hid[0]}")
            print(f"Match: {'✓' if our_hid[0] == sample_hid[0] else '✗'}")
            
            # Compare key fields
            hid_fields = [
                ("Wholesaler ID", 3, 14),
                ("Trans Type", 14, 17),
                ("Date", 17, 25),
                ("Company", 25, 57),
                ("Address", 57, 120),
                ("City", 120, 145),
                ("State", 145, 147),
                ("ZIP", 147, 152)
            ]
            
            print(f"\nHID Field Comparison:")
            for field_name, start, end in hid_fields:
                our_value = our_hid[0][start:end].strip()
                sample_value = sample_hid[0][start:end].strip()
                match = "✓" if our_value == sample_value else "✗"
                print(f"  {field_name:<12}: '{our_value}' vs '{sample_value}' {match}")
        
        # Compare TOT records
        print(f"\n" + "="*40)
        print("TOT RECORD COMPARISON")
        print("="*40)
        
        our_tot = [line for line in our_lines if line.startswith('TOT')]
        sample_tot = [line for line in sample_lines if line.startswith('TOT')]
        
        if our_tot and sample_tot:
            print("Generated TOT:")
            print(f"  {our_tot[0]}")
            print("Sample TOT:")
            print(f"  {sample_tot[0]}")
            print(f"Match: {'✓' if our_tot[0] == sample_tot[0] else '✗'}")
        
        # Sample a few BID records
        print(f"\n" + "="*40)
        print("BID RECORD SAMPLES")
        print("="*40)
        
        our_bids = [line for line in our_lines if line.startswith('BID')][:5]
        sample_bids = [line for line in sample_lines if line.startswith('BID')][:5]
        
        print("First 5 BID records comparison:")
        for i, (our_bid, sample_bid) in enumerate(zip(our_bids, sample_bids)):
            # Extract UPC for comparison
            our_upc = our_bid[19:31]
            sample_upc = sample_bid[19:31] 
            print(f"  {i+1}. Generated UPC: {our_upc}")
            print(f"     Sample UPC:    {sample_upc}")
            print(f"     Match: {'✓' if our_upc == sample_upc else '✗'}")
            print()
        
        # Check if any BID records match exactly
        our_bid_set = set(our_bids)
        sample_bid_set = set(sample_bids)
        exact_matches = our_bid_set & sample_bid_set
        print(f"Exact BID matches: {len(exact_matches)} out of {min(len(our_bids), len(sample_bids))}")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)

if __name__ == "__main__":
    test_specific_date()