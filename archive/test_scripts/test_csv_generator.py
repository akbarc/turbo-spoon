#!/usr/bin/env python3
"""
Test MSA CSV Generator
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from modules.msa_csv_generator import MSACSVGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_csv_generation():
    """Test CSV generation"""
    generator = MSACSVGenerator()
    
    print("\n" + "="*60)
    print("TESTING MSA CSV GENERATION")
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
        
        print(f"\nGenerating CSV files for week ending: {last_friday.date()}")
        
        # Generate CSV files
        sales_csv, items_csv, date_string, summary = generator.generate_csv_files(last_friday)
        
        print(f"\nDate String: {date_string}")
        print(f"\nSummary:")
        for key, value in summary.items():
            if key != 'categories_included':
                print(f"  {key}: {value}")
        
        # Save test files
        sales_filename = f"test_Sales - {date_string}.csv"
        items_filename = f"test_Items- {date_string}.csv"
        
        with open(sales_filename, 'w') as f:
            f.write(sales_csv)
        print(f"\nSales CSV saved as: {sales_filename}")
        print(f"Sales CSV preview (first 500 chars):")
        print(sales_csv[:500])
        
        with open(items_filename, 'w') as f:
            f.write(items_csv)
        print(f"\nItems CSV saved as: {items_filename}")
        print(f"Items CSV preview (first 500 chars):")
        print(items_csv[:500])
        
        # Test ZIP generation
        print("\n" + "-"*40)
        print("Testing ZIP file generation...")
        
        zip_buffer, zip_filename, summary = generator.generate_zip_file(last_friday)
        
        # Save ZIP file
        test_zip_filename = f"test_{zip_filename}"
        with open(test_zip_filename, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        print(f"ZIP file saved as: {test_zip_filename}")
        print(f"ZIP file size: {len(zip_buffer.getvalue())} bytes")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)

if __name__ == "__main__":
    test_csv_generation()