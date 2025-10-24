#!/usr/bin/env python3
"""
Validate the MSA generator against ALL available MSA files to get comprehensive accuracy metrics
"""

from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from database_pymssql import connection_pool

# Import our sustainable generator
from generate_msa_sustainable import SustainableMSAGenerator

def get_msa_file_pairs():
    """Find all consecutive MSA file pairs for testing"""
    msa_dir = "MSA Data Fr"
    files = []
    
    # Get all MSA files with dates
    for filename in os.listdir(msa_dir):
        filepath = os.path.join(msa_dir, filename)
        if os.path.isfile(filepath) and filename.isdigit() and len(filename) == 8:
            files.append(filename)
    
    # Sort by date
    files.sort()
    
    # Create pairs of consecutive files
    pairs = []
    for i in range(len(files) - 1):
        pairs.append((files[i], files[i + 1]))
    
    return pairs

def test_generator_on_pair(prior_date, target_date):
    """Test generator on a specific date pair"""
    prior_file = f"MSA Data Fr/{prior_date}"
    actual_file = f"MSA Data Fr/{target_date}"
    
    if not os.path.exists(prior_file) or not os.path.exists(actual_file):
        return None
    
    # Generate MSA file
    output_file = f"test_generated_{target_date}.txt"
    
    try:
        generator = SustainableMSAGenerator(prior_file, target_date)
        
        # Load distributor SKUs
        generator.load_all_distributor_skus()
        
        # Parse prior file
        generator.prior_records = generator.parse_msa_file(prior_file)
        
        # Calculate date range
        target_dt = datetime.strptime(f"2025{target_date[:4]}", '%Y%m%d')
        if target_dt.weekday() == 4:  # Friday
            start_dt = target_dt - timedelta(days=6)
        else:
            days_since_sat = (target_dt.weekday() + 2) % 7
            start_dt = target_dt - timedelta(days=days_since_sat)
        
        # Get sales data
        sales_data = generator.get_sales_data(
            start_dt.strftime('%Y-%m-%d'),
            target_dt.strftime('%Y-%m-%d 23:59:59')
        )
        
        # Generate output
        with open(output_file, 'w') as f:
            # Header
            if generator.prior_records['header']:
                header = generator.prior_records['header']
                old_date = f"2025{prior_date[:4]}"
                new_date = f"2025{target_date[:4]}"
                header = header.replace(old_date, new_date)
                f.write(header + '\n')
            
            # BID records
            for bid in generator.prior_records['bids']:
                f.write(bid['raw'] + '\n')
            
            # SID records
            for sid in generator.prior_records['sids']:
                f.write(sid + '\n')
            
            # PUR records
            for customer_id, customer_sales in sorted(sales_data.items()):
                for dist_sku, quantity in sorted(customer_sales.items()):
                    if quantity > 0:
                        pur_line = generator.format_pur_record(customer_id, dist_sku, quantity)
                        f.write(pur_line + '\n')
        
        # Validate against actual
        gen = generator.parse_msa_file(output_file)
        act = generator.parse_msa_file(actual_file)
        
        # Calculate metrics
        metrics = {
            'bid_gen': len(gen['bids']),
            'bid_act': len(act['bids']),
            'sid_gen': len(gen['sids']),
            'sid_act': len(act['sids']),
            'pur_gen': len(gen['purs']),
            'pur_act': len(act['purs']),
            'mapped_skus': len(generator.sku_mapping),
            'known_skus': len(generator.known_distributor_skus)
        }
        
        # Calculate accuracy
        bid_acc = max(0, 100 * (1 - abs(metrics['bid_gen'] - metrics['bid_act']) / max(1, metrics['bid_act'])))
        sid_acc = max(0, 100 * (1 - abs(metrics['sid_gen'] - metrics['sid_act']) / max(1, metrics['sid_act'])))
        pur_acc = max(0, 100 * (1 - abs(metrics['pur_gen'] - metrics['pur_act']) / max(1, metrics['pur_act'])))
        
        metrics['bid_accuracy'] = bid_acc
        metrics['sid_accuracy'] = sid_acc
        metrics['pur_accuracy'] = pur_acc
        metrics['overall_accuracy'] = (bid_acc + sid_acc + pur_acc) / 3
        
        # Clean up test file
        os.remove(output_file)
        
        return metrics
        
    except Exception as e:
        print(f"Error testing {prior_date} → {target_date}: {e}")
        if os.path.exists(output_file):
            os.remove(output_file)
        return None

def analyze_all_files():
    """Test generator on all available MSA file pairs"""
    print("="*70)
    print("COMPREHENSIVE MSA GENERATOR VALIDATION")
    print("="*70)
    
    pairs = get_msa_file_pairs()
    print(f"\nFound {len(pairs)} consecutive MSA file pairs to test")
    
    # Test each pair
    results = []
    
    for i, (prior, target) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] Testing {prior} → {target}")
        
        metrics = test_generator_on_pair(prior, target)
        if metrics:
            results.append({
                'prior': prior,
                'target': target,
                'metrics': metrics
            })
            print(f"  BID: {metrics['bid_accuracy']:.1f}% ({metrics['bid_gen']}/{metrics['bid_act']})")
            print(f"  SID: {metrics['sid_accuracy']:.1f}% ({metrics['sid_gen']}/{metrics['sid_act']})")
            print(f"  PUR: {metrics['pur_accuracy']:.1f}% ({metrics['pur_gen']}/{metrics['pur_act']})")
            print(f"  Overall: {metrics['overall_accuracy']:.1f}%")
    
    return results

def calculate_statistics(results):
    """Calculate overall statistics from all test results"""
    print("\n" + "="*70)
    print("OVERALL ACCURACY STATISTICS")
    print("="*70)
    
    if not results:
        print("No results to analyze")
        return
    
    # Aggregate metrics
    bid_accuracies = [r['metrics']['bid_accuracy'] for r in results]
    sid_accuracies = [r['metrics']['sid_accuracy'] for r in results]
    pur_accuracies = [r['metrics']['pur_accuracy'] for r in results]
    overall_accuracies = [r['metrics']['overall_accuracy'] for r in results]
    
    def stats(values):
        if not values:
            return 0, 0, 0
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        return avg, min_val, max_val
    
    print("\n### ACCURACY SUMMARY ###")
    print(f"Tested {len(results)} MSA file pairs")
    print()
    
    # BID accuracy
    avg, min_val, max_val = stats(bid_accuracies)
    print(f"BID Records:")
    print(f"  Average: {avg:.1f}%")
    print(f"  Range: {min_val:.1f}% - {max_val:.1f}%")
    
    # SID accuracy
    avg, min_val, max_val = stats(sid_accuracies)
    print(f"\nSID Records:")
    print(f"  Average: {avg:.1f}%")
    print(f"  Range: {min_val:.1f}% - {max_val:.1f}%")
    
    # PUR accuracy
    avg, min_val, max_val = stats(pur_accuracies)
    print(f"\nPUR Records:")
    print(f"  Average: {avg:.1f}%")
    print(f"  Range: {min_val:.1f}% - {max_val:.1f}%")
    
    # Overall accuracy
    avg, min_val, max_val = stats(overall_accuracies)
    print(f"\nOVERALL:")
    print(f"  Average: {avg:.1f}%")
    print(f"  Range: {min_val:.1f}% - {max_val:.1f}%")
    
    # Best and worst performing periods
    best = max(results, key=lambda x: x['metrics']['overall_accuracy'])
    worst = min(results, key=lambda x: x['metrics']['overall_accuracy'])
    
    print(f"\n### BEST PERFORMING PERIOD ###")
    print(f"{best['prior']} → {best['target']}: {best['metrics']['overall_accuracy']:.1f}%")
    
    print(f"\n### WORST PERFORMING PERIOD ###")
    print(f"{worst['prior']} → {worst['target']}: {worst['metrics']['overall_accuracy']:.1f}%")
    
    # Consistency analysis
    print("\n### CONSISTENCY ANALYSIS ###")
    variance = sum((x - avg) ** 2 for x in overall_accuracies) / len(overall_accuracies)
    std_dev = variance ** 0.5
    print(f"Standard Deviation: {std_dev:.1f}%")
    
    if std_dev < 2:
        print("✓ EXCELLENT consistency - very stable across all periods")
    elif std_dev < 5:
        print("✓ GOOD consistency - stable performance")
    else:
        print("⚠ Some variability in performance across periods")
    
    # SKU mapping coverage
    if results:
        avg_mapped = sum(r['metrics']['mapped_skus'] for r in results) / len(results)
        avg_known = sum(r['metrics']['known_skus'] for r in results) / len(results)
        print(f"\n### SKU MAPPING COVERAGE ###")
        print(f"Average SKUs mapped: {avg_mapped:.0f}/{avg_known:.0f} ({avg_mapped/avg_known*100:.1f}%)")

def identify_patterns(results):
    """Identify patterns in accuracy over time"""
    print("\n" + "="*70)
    print("PATTERN ANALYSIS")
    print("="*70)
    
    # Group by month
    by_month = defaultdict(list)
    for r in results:
        month = r['target'][:2]  # First 2 digits are month
        by_month[month].append(r['metrics']['overall_accuracy'])
    
    print("\n### ACCURACY BY MONTH ###")
    months = ['06', '07', '08']
    month_names = {'06': 'June', '07': 'July', '08': 'August'}
    
    for month in months:
        if month in by_month:
            avg = sum(by_month[month]) / len(by_month[month])
            print(f"{month_names[month]}: {avg:.1f}% (n={len(by_month[month])})")
    
    # Check for trends
    if len(results) > 1:
        first_half = results[:len(results)//2]
        second_half = results[len(results)//2:]
        
        first_avg = sum(r['metrics']['overall_accuracy'] for r in first_half) / len(first_half)
        second_avg = sum(r['metrics']['overall_accuracy'] for r in second_half) / len(second_half)
        
        print("\n### TREND ANALYSIS ###")
        print(f"First half average: {first_avg:.1f}%")
        print(f"Second half average: {second_avg:.1f}%")
        
        if second_avg > first_avg + 2:
            print("✓ Improving trend - accuracy getting better over time")
        elif second_avg < first_avg - 2:
            print("⚠ Declining trend - accuracy decreasing over time")
        else:
            print("✓ Stable performance - no significant trend")

def main():
    print("Starting comprehensive MSA generator validation...")
    print("This will test the generator against all available MSA files.")
    print()
    
    # Connect to database first
    try:
        conn = connection_pool.get_connection()
        connection_pool.return_connection(conn)
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return
    
    # Run validation
    results = analyze_all_files()
    
    if results:
        calculate_statistics(results)
        identify_patterns(results)
        
        print("\n" + "="*70)
        print("FINAL ASSESSMENT")
        print("="*70)
        
        avg_overall = sum(r['metrics']['overall_accuracy'] for r in results) / len(results)
        
        if avg_overall >= 95:
            print(f"✓✓✓ EXCELLENT - {avg_overall:.1f}% average accuracy")
            print("The generator is production-ready and highly reliable.")
        elif avg_overall >= 90:
            print(f"✓✓ VERY GOOD - {avg_overall:.1f}% average accuracy")
            print("The generator performs well and is suitable for production use.")
        elif avg_overall >= 85:
            print(f"✓ GOOD - {avg_overall:.1f}% average accuracy")
            print("The generator is functional but could benefit from improvements.")
        else:
            print(f"⚠ NEEDS IMPROVEMENT - {avg_overall:.1f}% average accuracy")
            print("The generator requires further optimization.")
    else:
        print("\nNo results generated. Check database connection and MSA files.")

if __name__ == "__main__":
    main()