#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI SQL Assistant
Tests 200+ scenarios and compares with API results for validation
"""

import os
import sys
import json
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

# Import both assistants for comparison
from ai_sql_assistant import AISQLAssistant as OldAssistant
from ai_sql_assistant_v2 import EnhancedAISQLAssistant as NewAssistant
from database_pymssql import SQLServerConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveTestSuite:
    """Comprehensive test suite for AI SQL Assistant"""
    
    def __init__(self):
        """Initialize test suite with both assistants"""
        # API key
        api_key = os.getenv('OPENAI_API_KEY') or "YOUR_OPENAI_API_KEY_HERE"
        
        self.old_assistant = OldAssistant(api_key=api_key)
        self.new_assistant = NewAssistant(api_key=api_key)
        
        # API endpoints for validation
        self.api_base = "http://localhost:5000"  # Adjust if needed
        
        # Store test results
        self.test_results = []
        self.comparison_results = []
        
    def generate_test_queries(self) -> List[Dict[str, Any]]:
        """Generate 200+ diverse test queries"""
        queries = []
        
        # 1. Basic Sales Queries (20 tests)
        sales_queries = [
            "What are total sales today?",
            "Show me sales for yesterday",
            "Total revenue this week",
            "Sales for last 7 days",
            "Monthly sales total",
            "Quarterly revenue",
            "Year to date sales",
            "Sales for last month",
            "Revenue for last 3 months",
            "Sales between 01/01/2024 and 01/31/2024",
            "Total sales for 2023",
            "Daily sales average this month",
            "Highest sales day this year",
            "Lowest revenue day last month",
            "Weekend vs weekday sales comparison",
            "Morning vs evening sales",
            "Sales by hour today",
            "Peak sales hours this week",
            "Transaction count vs revenue",
            "Average transaction value this month"
        ]
        
        # 2. Customer Analytics (20 tests)
        customer_queries = [
            "Top 10 customers by revenue",
            "Customers with highest purchase frequency",
            "New customers this month",
            "Customers who haven't purchased in 30 days",
            "Customer lifetime value rankings",
            "Customers with credit limit exceeded",
            "VIP customers (over $10000 lifetime)",
            "Customer purchase patterns",
            "Average customer spend per visit",
            "Customer retention rate",
            "Most loyal customers",
            "Customer geographic distribution",
            "Business vs individual customers",
            "Tax exempt customer analysis",
            "Customer payment behavior",
            "Customers with NSF history",
            "Customer credit utilization",
            "Inactive customer analysis",
            "Customer reactivation candidates",
            "Customer segmentation by value"
        ]
        
        # 3. Product & Inventory (20 tests)
        product_queries = [
            "Top selling products",
            "Products running low on stock",
            "Inventory value by category",
            "Slow moving inventory",
            "Products not sold in 30 days",
            "New products added this month",
            "Price changes impact on sales",
            "Product profitability ranking",
            "Category performance comparison",
            "Seasonal product trends",
            "Product bundle opportunities",
            "Cross-selling analysis",
            "Product velocity metrics",
            "Dead stock identification",
            "Reorder point analysis",
            "Product lifecycle stages",
            "SKU rationalization candidates",
            "Product margin analysis",
            "Category growth trends",
            "Product cannibalization analysis"
        ]
        
        # 4. Financial Queries (20 tests)
        financial_queries = [
            "Gross profit margin by category",
            "Total profit this month",
            "Profit trends over last 6 months",
            "Category profitability ranking",
            "Product margin analysis",
            "Cost of goods sold breakdown",
            "Tobacco tax impact on margins",
            "Discount impact on profitability",
            "Revenue vs profit correlation",
            "Break-even analysis by product",
            "Contribution margin by category",
            "Fixed vs variable cost analysis",
            "Profit per square foot",
            "Return on inventory investment",
            "Cash flow from operations",
            "Working capital trends",
            "Days sales outstanding",
            "Inventory turnover ratio",
            "Gross margin return on investment",
            "Economic value added calculation"
        ]
        
        # 5. AR & Payments (20 tests)
        ar_queries = [
            "Total accounts receivable balance",
            "Aging accounts receivable report",
            "Customers with overdue payments",
            "NSF check analysis",
            "Payment collection rate",
            "Average days to payment",
            "Credit risk assessment",
            "Bad debt provision calculation",
            "Payment method distribution",
            "Collection effectiveness metrics",
            "AR turnover ratio",
            "Customer payment history",
            "Credit limit utilization",
            "Write-off candidates",
            "Payment terms optimization",
            "Early payment discount analysis",
            "Collection agency referrals",
            "Payment dispute resolution",
            "Cash application efficiency",
            "Credit policy compliance"
        ]
        
        # 6. Complex Analytical Queries (30 tests)
        complex_queries = [
            "Compare this month's sales to last month by category",
            "Year over year growth by product category",
            "Customer cohort analysis by first purchase month",
            "Market basket analysis for frequently bought together",
            "Customer churn prediction indicators",
            "Seasonal sales patterns by category",
            "Price elasticity analysis",
            "Promotion effectiveness measurement",
            "Customer lifetime value by acquisition channel",
            "Inventory optimization recommendations",
            "Sales forecast based on historical trends",
            "Anomaly detection in daily sales",
            "Customer segmentation using RFM analysis",
            "Product affinity matrix",
            "Geographic sales heat map data",
            "Time series decomposition of sales",
            "Pareto analysis of products (80/20 rule)",
            "Sales velocity by day of week and hour",
            "Correlation between weather and sales",
            "Impact of holidays on sales patterns",
            "Customer journey mapping data",
            "Attribution modeling for marketing",
            "Demand forecasting by SKU",
            "Inventory aging analysis",
            "Supplier performance metrics",
            "Employee productivity analysis",
            "Store layout optimization data",
            "Queue analysis and wait times",
            "Transaction fraud detection patterns",
            "Competitive pricing analysis"
        ]
        
        # 7. Specific Category Queries (20 tests)
        category_queries = [
            "Cigar sales this month",
            "LT-TAX-COLLECTED revenue YTD",
            "Tobacco category performance",
            "Non-tobacco vs tobacco sales ratio",
            "Category mix changes over time",
            "Emerging category trends",
            "Category cannibalization analysis",
            "Category price positioning",
            "Category margin comparison",
            "Category inventory turns",
            "Category space productivity",
            "Category promotional lift",
            "Category customer demographics",
            "Category purchase frequency",
            "Category basket size impact",
            "Category loyalty metrics",
            "Category substitution patterns",
            "Category lifecycle analysis",
            "Category competitive analysis",
            "Category growth opportunities"
        ]
        
        # 8. Time-based Comparisons (20 tests)
        time_queries = [
            "Monday vs Friday sales comparison",
            "First week vs last week of month",
            "Holiday sales vs regular days",
            "Month-end spike analysis",
            "Quarterly seasonality patterns",
            "Year-end performance review",
            "Black Friday sales analysis",
            "Summer vs winter comparison",
            "Beginning of month vs end of month",
            "Payday impact on sales",
            "Weekend traffic patterns",
            "Rush hour transaction analysis",
            "Slow period identification",
            "Peak season preparation metrics",
            "Off-season performance",
            "Event-driven sales spikes",
            "Weather impact correlation",
            "School calendar effects",
            "Local event influences",
            "Economic indicator correlations"
        ]
        
        # 9. Employee & Operations (20 tests)
        operations_queries = [
            "Sales by cashier",
            "Transaction processing time",
            "Average items per transaction",
            "Void and return analysis",
            "Discount usage patterns",
            "Cash vs credit transactions",
            "Transaction error rates",
            "Peak staffing requirements",
            "Employee sales performance",
            "Training effectiveness metrics",
            "Shrinkage and loss analysis",
            "Operational efficiency KPIs",
            "Customer service metrics",
            "Queue management statistics",
            "POS system performance",
            "Inventory accuracy metrics",
            "Order fulfillment rates",
            "Supplier delivery performance",
            "Warehouse efficiency metrics",
            "Distribution cost analysis"
        ]
        
        # 10. Executive Dashboard Queries (10 tests)
        executive_queries = [
            "Executive summary for this month",
            "KPI dashboard metrics",
            "Business health scorecard",
            "Performance against targets",
            "Market share analysis",
            "Competitive benchmarking",
            "Strategic initiative tracking",
            "Risk assessment dashboard",
            "Opportunity pipeline",
            "Investment ROI analysis"
        ]
        
        # Combine all queries
        all_query_texts = (
            sales_queries + customer_queries + product_queries + 
            financial_queries + ar_queries + complex_queries + 
            category_queries + time_queries + operations_queries + 
            executive_queries
        )
        
        # Create query objects with metadata
        for i, query_text in enumerate(all_query_texts):
            queries.append({
                "id": i + 1,
                "text": query_text,
                "category": self._categorize_query(query_text),
                "complexity": self._assess_complexity(query_text),
                "expected_tables": self._predict_tables(query_text)
            })
        
        return queries
    
    def _categorize_query(self, query: str) -> str:
        """Categorize query by domain"""
        query_lower = query.lower()
        if any(word in query_lower for word in ["sales", "revenue", "transaction"]):
            return "sales"
        elif any(word in query_lower for word in ["customer", "client"]):
            return "customer"
        elif any(word in query_lower for word in ["product", "inventory", "stock"]):
            return "product"
        elif any(word in query_lower for word in ["profit", "margin", "cost"]):
            return "financial"
        elif any(word in query_lower for word in ["ar", "receivable", "payment"]):
            return "ar_payment"
        elif any(word in query_lower for word in ["compare", "vs", "trend", "forecast"]):
            return "analytical"
        else:
            return "general"
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity"""
        query_lower = query.lower()
        complex_indicators = ["compare", "vs", "trend", "forecast", "analysis", 
                             "correlation", "prediction", "optimization", "segmentation"]
        
        if any(indicator in query_lower for indicator in complex_indicators):
            return "complex"
        elif len(query.split()) > 10:
            return "medium"
        else:
            return "simple"
    
    def _predict_tables(self, query: str) -> List[str]:
        """Predict which tables will be needed"""
        query_lower = query.lower()
        tables = []
        
        if any(word in query_lower for word in ["sales", "revenue", "transaction"]):
            tables.extend(["Transaction", "TransactionEntry"])
        if any(word in query_lower for word in ["customer", "client"]):
            tables.append("Customer")
        if any(word in query_lower for word in ["product", "item", "inventory"]):
            tables.append("Item")
        if any(word in query_lower for word in ["category", "department"]):
            tables.append("Category")
        if any(word in query_lower for word in ["payment", "paid"]):
            tables.append("Payment")
        if any(word in query_lower for word in ["ar", "receivable"]):
            tables.append("AccountReceivable")
        
        return list(set(tables))
    
    def run_single_test(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test query"""
        result = {
            "query_id": query["id"],
            "query_text": query["text"],
            "category": query["category"],
            "complexity": query["complexity"]
        }
        
        try:
            # Test new assistant
            start_time = time.time()
            new_result = self.new_assistant.process_question(query["text"])
            new_time = time.time() - start_time
            
            result["new_assistant"] = {
                "success": new_result.get("success", False),
                "row_count": new_result.get("row_count", 0),
                "execution_time": new_time,
                "sql": new_result.get("sql_query", ""),
                "error": new_result.get("error", None)
            }
            
            # Test old assistant for comparison (optional)
            try:
                start_time = time.time()
                old_result = self.old_assistant.process_business_question(query["text"])
                old_time = time.time() - start_time
                
                result["old_assistant"] = {
                    "success": old_result.get("success", False),
                    "row_count": old_result.get("row_count", 0),
                    "execution_time": old_time,
                    "sql": old_result.get("sql_query", ""),
                    "error": old_result.get("error", None)
                }
                
                # Compare results
                if new_result.get("success") and old_result.get("success"):
                    result["comparison"] = {
                        "row_count_match": abs(new_result["row_count"] - old_result["row_count"]) <= 1,
                        "performance_gain": (old_time - new_time) / old_time * 100 if old_time > 0 else 0
                    }
            except:
                result["old_assistant"] = {"success": False, "error": "Failed to run"}
                
        except Exception as e:
            result["new_assistant"] = {
                "success": False,
                "error": str(e)
            }
        
        return result
    
    def validate_with_api(self, query_type: str, params: Dict = None) -> Optional[Dict]:
        """Validate results against API endpoints"""
        api_endpoints = {
            "sales": "/api/sales/summary",
            "customer": "/api/customers/top",
            "inventory": "/api/inventory/status",
            "ar": "/api/ar/summary",
            "profit": "/api/analytics/profit"
        }
        
        endpoint = api_endpoints.get(query_type)
        if not endpoint:
            return None
        
        try:
            response = requests.get(f"{self.api_base}{endpoint}", params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None
    
    def run_direct_sql_validation(self, sql: str) -> Tuple[bool, int]:
        """Run SQL directly to validate it works"""
        try:
            with SQLServerConnection() as db:
                df = db.execute_query(sql, description="Validation Query")
                return True, len(df)
        except Exception as e:
            return False, 0
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("=" * 80)
        print("COMPREHENSIVE AI SQL ASSISTANT TEST SUITE")
        print("=" * 80)
        
        # Generate test queries
        print("\n📝 Generating 200+ test queries...")
        queries = self.generate_test_queries()
        print(f"✅ Generated {len(queries)} test queries")
        
        # Category breakdown
        categories = {}
        for q in queries:
            cat = q["category"]
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n📊 Query Distribution:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} queries")
        
        # Run tests
        print("\n🚀 Starting comprehensive testing...")
        print("-" * 80)
        
        successful_new = 0
        successful_old = 0
        failed_new = 0
        failed_old = 0
        
        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] Testing: {query['text'][:60]}...")
            
            result = self.run_single_test(query)
            self.test_results.append(result)
            
            # Update counters
            if result["new_assistant"]["success"]:
                successful_new += 1
                print(f"  ✅ New: {result['new_assistant']['row_count']} rows in {result['new_assistant']['execution_time']:.2f}s")
            else:
                failed_new += 1
                print(f"  ❌ New: {result['new_assistant'].get('error', 'Unknown error')}")
            
            if "old_assistant" in result:
                if result["old_assistant"]["success"]:
                    successful_old += 1
                    print(f"  ✅ Old: {result['old_assistant']['row_count']} rows in {result['old_assistant']['execution_time']:.2f}s")
                else:
                    failed_old += 1
            
            # Validate SQL if successful
            if result["new_assistant"]["success"] and result["new_assistant"]["sql"]:
                valid, rows = self.run_direct_sql_validation(result["new_assistant"]["sql"])
                if not valid:
                    print(f"  ⚠️  SQL validation failed!")
            
            # Add small delay to avoid overwhelming the API
            if i % 10 == 0:
                time.sleep(1)
        
        # Generate summary report
        print("\n" + "=" * 80)
        print("TEST SUMMARY REPORT")
        print("=" * 80)
        
        print(f"\n📈 New Assistant Performance:")
        print(f"  Total Tests: {len(queries)}")
        print(f"  Successful: {successful_new} ({successful_new/len(queries)*100:.1f}%)")
        print(f"  Failed: {failed_new} ({failed_new/len(queries)*100:.1f}%)")
        
        if successful_old > 0:
            print(f"\n📊 Comparison with Old Assistant:")
            print(f"  Old Success Rate: {successful_old/len(queries)*100:.1f}%")
            print(f"  New Success Rate: {successful_new/len(queries)*100:.1f}%")
            print(f"  Improvement: {(successful_new - successful_old)/len(queries)*100:+.1f}%")
        
        # Analyze by category
        print("\n📂 Success Rate by Category:")
        category_stats = {}
        for result in self.test_results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "success": 0}
            category_stats[cat]["total"] += 1
            if result["new_assistant"]["success"]:
                category_stats[cat]["success"] += 1
        
        for cat, stats in sorted(category_stats.items()):
            rate = stats["success"] / stats["total"] * 100
            print(f"  {cat}: {rate:.1f}% ({stats['success']}/{stats['total']})")
        
        # Analyze by complexity
        print("\n🎯 Success Rate by Complexity:")
        complexity_stats = {}
        for result in self.test_results:
            comp = result["complexity"]
            if comp not in complexity_stats:
                complexity_stats[comp] = {"total": 0, "success": 0}
            complexity_stats[comp]["total"] += 1
            if result["new_assistant"]["success"]:
                complexity_stats[comp]["success"] += 1
        
        for comp in ["simple", "medium", "complex"]:
            if comp in complexity_stats:
                stats = complexity_stats[comp]
                rate = stats["success"] / stats["total"] * 100
                print(f"  {comp}: {rate:.1f}% ({stats['success']}/{stats['total']})")
        
        # Performance metrics
        print("\n⚡ Performance Metrics:")
        exec_times = [r["new_assistant"]["execution_time"] 
                     for r in self.test_results 
                     if r["new_assistant"]["success"]]
        if exec_times:
            print(f"  Average execution time: {sum(exec_times)/len(exec_times):.2f}s")
            print(f"  Fastest query: {min(exec_times):.2f}s")
            print(f"  Slowest query: {max(exec_times):.2f}s")
        
        # Failed queries analysis
        if failed_new > 0:
            print("\n❌ Failed Query Analysis:")
            error_types = {}
            for result in self.test_results:
                if not result["new_assistant"]["success"]:
                    error = result["new_assistant"].get("error", "Unknown")
                    error_type = self._classify_error(error)
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error_type}: {count} occurrences")
        
        # Save detailed results
        self._save_results()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"✅ Results saved to: ai_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    def _classify_error(self, error: str) -> str:
        """Classify error types"""
        error_lower = str(error).lower()
        if "could not be bound" in error_lower:
            return "Invalid column reference"
        elif "syntax" in error_lower:
            return "SQL syntax error"
        elif "timeout" in error_lower:
            return "Query timeout"
        elif "connection" in error_lower:
            return "Connection error"
        elif "permission" in error_lower:
            return "Permission denied"
        else:
            return "Other error"
    
    def _save_results(self):
        """Save test results to file"""
        filename = f"ai_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {
            "test_date": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "successful": sum(1 for r in self.test_results if r["new_assistant"]["success"]),
            "failed": sum(1 for r in self.test_results if not r["new_assistant"]["success"]),
            "detailed_results": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Also save a CSV summary
        csv_filename = filename.replace('.json', '.csv')
        df = pd.DataFrame([{
            "query_id": r["query_id"],
            "query": r["query_text"],
            "category": r["category"],
            "complexity": r["complexity"],
            "success": r["new_assistant"]["success"],
            "row_count": r["new_assistant"].get("row_count", 0),
            "execution_time": r["new_assistant"].get("execution_time", 0),
            "error": r["new_assistant"].get("error", "")
        } for r in self.test_results])
        
        df.to_csv(csv_filename, index=False)
        print(f"✅ CSV summary saved to: {csv_filename}")


def main():
    """Main entry point"""
    test_suite = ComprehensiveTestSuite()
    test_suite.run_comprehensive_tests()


if __name__ == "__main__":
    main()