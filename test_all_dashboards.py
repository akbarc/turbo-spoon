#!/usr/bin/env python3
"""
Comprehensive Dashboard Testing Script
Tests all API endpoints and dashboard functionality
"""

import requests
import json
from datetime import datetime, timedelta
from colorama import init, Fore, Style
import sys

init(autoreset=True)

BASE_URL = "http://localhost:8080"

class DashboardTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test_endpoint(self, name, url, expected_keys=None, method='GET', data=None):
        """Test a single endpoint"""
        try:
            print(f"\n{Fore.CYAN}Testing: {name}{Style.RESET_ALL}")
            print(f"  URL: {url}")

            if method == 'GET':
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)

            # Check HTTP status
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

            # Try to parse JSON
            try:
                json_data = response.json()
            except:
                raise Exception("Response is not valid JSON")

            # Check expected keys
            if expected_keys:
                missing_keys = [k for k in expected_keys if k not in json_data]
                if missing_keys:
                    raise Exception(f"Missing keys: {missing_keys}")

            # Check for error in response
            if isinstance(json_data, dict) and json_data.get('error'):
                raise Exception(f"API returned error: {json_data['error']}")

            print(f"  {Fore.GREEN}✓ PASSED{Style.RESET_ALL}")
            if isinstance(json_data, dict):
                print(f"  Response keys: {list(json_data.keys())}")
            self.passed += 1
            return True

        except Exception as e:
            print(f"  {Fore.RED}✗ FAILED: {str(e)}{Style.RESET_ALL}")
            self.failed += 1
            self.errors.append({
                'name': name,
                'url': url,
                'error': str(e)
            })
            return False

    def test_executive_dashboard(self):
        """Test Executive Dashboard endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING EXECUTIVE DASHBOARD")
        print(f"{'='*80}{Style.RESET_ALL}")

        # Executive summary with different periods
        self.test_endpoint(
            "Executive Summary - Today",
            f"{BASE_URL}/api/business-overview/executive-summary?period=today",
            expected_keys=['revenue', 'profit', 'inventory', 'cashflow']
        )

        self.test_endpoint(
            "Executive Summary - Week",
            f"{BASE_URL}/api/business-overview/executive-summary?period=week",
            expected_keys=['revenue', 'profit', 'inventory', 'cashflow']
        )

        self.test_endpoint(
            "Executive Summary - Month",
            f"{BASE_URL}/api/business-overview/executive-summary?period=month",
            expected_keys=['revenue', 'profit', 'inventory', 'cashflow']
        )

        # Sales Performance
        self.test_endpoint(
            "Sales Performance",
            f"{BASE_URL}/api/business-overview/sales-performance",
            expected_keys=['categories', 'top_products']
        )

        # Inventory Health
        self.test_endpoint(
            "Inventory Health",
            f"{BASE_URL}/api/business-overview/inventory-health",
            expected_keys=['total_items']
        )

        # Performance Trends
        self.test_endpoint(
            "Performance Trends",
            f"{BASE_URL}/api/business-overview/performance-trends",
            expected_keys=['daily_trends']
        )

    def test_ar_dashboard(self):
        """Test AR Dashboard endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING AR DASHBOARD")
        print(f"{'='*80}{Style.RESET_ALL}")

        # AR Aging Optimized
        self.test_endpoint(
            "AR Aging Optimized",
            f"{BASE_URL}/api/financial/ar-aging-optimized",
            expected_keys=['aging_summary', 'ar_records']
        )

        # NSF Details
        self.test_endpoint(
            "NSF Details",
            f"{BASE_URL}/api/financial/nsf-details"
        )

    def test_pos_dashboard(self):
        """Test POS Operations Dashboard endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING POS OPERATIONS DASHBOARD")
        print(f"{'='*80}{Style.RESET_ALL}")

        today = datetime.now().strftime('%Y-%m-%d')

        # Daily Summary
        self.test_endpoint(
            "POS Daily Summary",
            f"{BASE_URL}/api/pos/daily-summary?date={today}",
            expected_keys=['summary', 'top_categories', 'payment_methods']
        )

        # Various report types
        report_types = [
            'daily_sales',
            'category_sales',
            'item_sales',
            'cashier_performance',
            'payment_methods'
        ]

        for report_type in report_types:
            self.test_endpoint(
                f"POS Report - {report_type}",
                f"{BASE_URL}/api/pos/run-report?report_type={report_type}&start_date={today}&end_date={today}",
                expected_keys=['data', 'success']
            )

    def test_inventory_endpoints(self):
        """Test Inventory endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING INVENTORY ENDPOINTS")
        print(f"{'='*80}{Style.RESET_ALL}")

        self.test_endpoint(
            "Low Stock Items",
            f"{BASE_URL}/api/inventory-health/low-stock"
        )

        self.test_endpoint(
            "Deadstock Items",
            f"{BASE_URL}/api/inventory-health/deadstock"
        )

        self.test_endpoint(
            "Overstock Items",
            f"{BASE_URL}/api/inventory-health/overstock"
        )

        self.test_endpoint(
            "Inventory Velocity - Hot",
            f"{BASE_URL}/api/inventory-health/velocity?view=hot"
        )

        self.test_endpoint(
            "Inventory Velocity - Cold",
            f"{BASE_URL}/api/inventory-health/velocity?view=cold"
        )

        self.test_endpoint(
            "Category Values",
            f"{BASE_URL}/api/inventory-health/category-values"
        )

    def test_sales_ops(self):
        """Test Sales Operations endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING SALES OPERATIONS")
        print(f"{'='*80}{Style.RESET_ALL}")

        self.test_endpoint(
            "Sales Ops Overview",
            f"{BASE_URL}/api/sales-ops/overview"
        )

    def test_gp_analysis(self):
        """Test GP Analysis endpoints"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TESTING GP ANALYSIS")
        print(f"{'='*80}{Style.RESET_ALL}")

        self.test_endpoint(
            "GP Executive Summary",
            f"{BASE_URL}/api/gp/executive-summary"
        )

        self.test_endpoint(
            "GP Trending",
            f"{BASE_URL}/api/gp/trending"
        )

        self.test_endpoint(
            "GP Categories",
            f"{BASE_URL}/api/gp/categories"
        )

    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}{Style.RESET_ALL}")

        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n{Fore.GREEN}Passed: {self.passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.failed}{Style.RESET_ALL}")
        print(f"Total: {total}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.errors:
            print(f"\n{Fore.RED}FAILED TESTS:{Style.RESET_ALL}")
            for error in self.errors:
                print(f"\n  {Fore.RED}✗ {error['name']}{Style.RESET_ALL}")
                print(f"    URL: {error['url']}")
                print(f"    Error: {error['error']}")

        return self.failed == 0

def main():
    print(f"{Fore.CYAN}{'='*80}")
    print(f"GEORGIA DASHBOARD - COMPREHENSIVE TEST SUITE")
    print(f"{'='*80}{Style.RESET_ALL}")
    print(f"\nTesting server at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = DashboardTester()

    # Run all tests
    tester.test_executive_dashboard()
    tester.test_ar_dashboard()
    tester.test_pos_dashboard()
    tester.test_inventory_endpoints()
    tester.test_sales_ops()
    tester.test_gp_analysis()

    # Print summary
    success = tester.print_summary()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
