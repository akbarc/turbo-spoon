#!/usr/bin/env python3
"""
Test script to verify date filter fix works correctly for all report types
"""

import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:5003"

# Test date range
end_date = datetime.now().date()
start_date = end_date - timedelta(days=7)

# Report types to test, organized by their date column
test_reports = {
    "Transaction Reports (t.Time)": [
        'daily_sales',
        'category_sales',
        'customer_sales',
        'cashier_performance',
        'hourly_sales',
        'sales_by_category',
        'top_customers'
    ],
    "Excise Reports (pue.TransactionTime)": [
        'pu_excise_summary',
        'excise_by_category',
        'excise_transactions',
        'daily_excise'
    ],
    "DailySales Reports (Date)": [
        'daily_sales_pos',
        'daily_sales_table'
    ],
    "AR Reports (arh.Date)": [
        'ar_history'
    ],
    "Cash Drawer (b.OpenDate)": [
        'cash_drawer_report'
    ],
    "No Date Filter": [
        'ar_aging',
        'inventory_valuation',
        'inventory_list',
        'reorder_report',
        'physical_count_worksheet'
    ]
}

def test_report(report_type, use_dates=True):
    """Test a single report type"""
    params = {
        'report_type': report_type,
    }

    if use_dates:
        params['start_date'] = str(start_date)
        params['end_date'] = str(end_date)

    try:
        response = requests.get(f"{BASE_URL}/api/pos/reports", params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            row_count = data.get('row_count', 0)
            return {
                'status': 'SUCCESS',
                'rows': row_count,
                'message': f'{row_count} rows returned'
            }
        else:
            error = response.json().get('error', 'Unknown error')
            return {
                'status': 'FAILED',
                'error': error
            }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'SKIPPED',
            'error': 'Server not running'
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'error': str(e)
        }

def main():
    print("=" * 80)
    print("DATE FILTER FIX VERIFICATION TEST")
    print("=" * 80)
    print(f"Testing with date range: {start_date} to {end_date}")
    print()

    total_tested = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for category, reports in test_reports.items():
        print(f"\n{category}")
        print("-" * 80)

        use_dates = category != "No Date Filter"

        for report_type in reports:
            total_tested += 1
            result = test_report(report_type, use_dates)

            status_symbol = {
                'SUCCESS': '✓',
                'FAILED': '✗',
                'ERROR': '⚠',
                'SKIPPED': '○'
            }.get(result['status'], '?')

            print(f"  {status_symbol} {report_type:30s} ", end='')

            if result['status'] == 'SUCCESS':
                print(f"[{result['message']}]")
                total_passed += 1
            elif result['status'] == 'SKIPPED':
                print(f"[SKIPPED - {result['error']}]")
                total_skipped += 1
            else:
                print(f"[{result['status']}]")
                print(f"     Error: {result.get('error', 'Unknown')}")
                total_failed += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Tests:  {total_tested}")
    print(f"Passed:       {total_passed} ✓")
    print(f"Failed:       {total_failed} ✗")
    print(f"Skipped:      {total_skipped} ○")

    if total_failed == 0 and total_skipped < total_tested:
        print("\n✓ All active tests PASSED! Date filter fix is working correctly.")
    elif total_skipped == total_tested:
        print("\n○ All tests SKIPPED - Server not running")
        print("  Start the server with: python3 run.py")
    else:
        print(f"\n✗ {total_failed} test(s) FAILED - Review errors above")

    print("=" * 80)

if __name__ == "__main__":
    main()
