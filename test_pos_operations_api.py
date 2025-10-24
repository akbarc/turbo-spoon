#!/usr/bin/env python3
"""
Test script for POS Operations API endpoints
Tests all endpoints and validates response structure
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app
from app.main import app, init_database

def test_endpoint(client, endpoint, params=None, expected_keys=None):
    """Test a single endpoint and validate response"""
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint}")
    print(f"Params: {params}")

    try:
        response = client.get(endpoint, query_string=params)

        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Response: {response.get_json()}")
            return False

        data = response.get_json()

        # Check for expected keys
        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in data]
            if missing_keys:
                print(f"❌ FAILED: Missing keys: {missing_keys}")
                return False

        # Check for cache metadata
        if '_cache' in data:
            cache_info = data['_cache']
            print(f"Cache: hit={cache_info.get('hit')}, age={cache_info.get('age_seconds')}s, ttl={cache_info.get('ttl_seconds')}s")

        # Pretty print first level of response
        summary = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                if isinstance(value, dict):
                    summary[key] = f"<dict with {len(value)} keys>"
                else:
                    summary[key] = f"<list with {len(value)} items>"
            else:
                summary[key] = value

        print(f"Response Summary: {json.dumps(summary, indent=2, default=str)}")
        print("✅ PASSED")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all endpoint tests"""
    print("="*60)
    print("POS Operations API Test Suite")
    print("="*60)

    # Initialize database
    print("\nInitializing database...")
    if not init_database():
        print("❌ Database initialization failed")
        return 1

    print("✅ Database initialized")

    # Create test client
    app.config['TESTING'] = True
    client = app.test_client()

    # Track results
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }

    # Test 1: Operations Summary (today)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/operations-summary',
        params={'date': datetime.now().strftime('%Y-%m-%d')},
        expected_keys=['date', 'metrics', 'comparison', 'payment_methods']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 2: Operations Summary (no comparison)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/operations-summary',
        params={'compare': 'false'},
        expected_keys=['date', 'metrics', 'comparison']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 3: Daily Metrics (7 days)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/daily-metrics',
        params={'days': 7},
        expected_keys=['period', 'daily_data', 'aggregates']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 4: Daily Metrics (30 days)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/daily-metrics',
        params={'days': 30},
        expected_keys=['period', 'daily_data', 'aggregates']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 5: Top Performers (default)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/top-performers',
        params={},
        expected_keys=['period', 'top_items', 'top_categories', 'top_cashiers']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 6: Top Performers (custom date range)
    results['total'] += 1
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    if test_endpoint(
        client,
        '/api/pos/top-performers',
        params={
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'limit': 20
        },
        expected_keys=['period', 'top_items', 'top_categories', 'top_cashiers']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 7: Operational Alerts
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/alerts',
        params={},
        expected_keys=['date', 'alert_count', 'alerts', 'summary']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 8: Hourly Breakdown
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/hourly-breakdown',
        params={'date': datetime.now().strftime('%Y-%m-%d')},
        expected_keys=['date', 'hourly_data', 'peak_hour', 'total_sales', 'total_transactions']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 9: Transaction Velocity (60 minutes)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/transaction-velocity',
        params={'minutes': 60},
        expected_keys=['time_window', 'current_metrics', 'velocity', 'comparison']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 10: Transaction Velocity (30 minutes)
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/transaction-velocity',
        params={'minutes': 30},
        expected_keys=['time_window', 'current_metrics', 'velocity']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 11: Cache Stats
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/cache/stats',
        params={},
        expected_keys=['total_entries', 'cache_entries', 'total_size_bytes']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 12: Test cache hit (call operations-summary again)
    print("\n" + "="*60)
    print("Testing cache hit (calling operations-summary again)")
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/operations-summary',
        params={'date': datetime.now().strftime('%Y-%m-%d')},
        expected_keys=['date', 'metrics', '_cache']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 13: Clear Cache
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/cache/clear',
        params={},
        expected_keys=['success', 'message']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 14: Verify cache cleared
    results['total'] += 1
    if test_endpoint(
        client,
        '/api/pos/cache/stats',
        params={},
        expected_keys=['total_entries']
    ):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # Test 15: Error handling - invalid date format
    print("\n" + "="*60)
    print("Testing error handling (invalid date)")
    results['total'] += 1
    response = client.get('/api/pos/operations-summary', query_string={'date': 'invalid-date'})
    if response.status_code == 400:
        print("✅ PASSED: Correctly returned 400 for invalid date")
        results['passed'] += 1
    else:
        print(f"❌ FAILED: Expected 400, got {response.status_code}")
        results['failed'] += 1

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests:  {results['total']}")
    print(f"✅ Passed:    {results['passed']}")
    print(f"❌ Failed:    {results['failed']}")

    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    if results['failed'] == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {results['failed']} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
