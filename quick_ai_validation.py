#!/usr/bin/env python3
"""
Quick validation test for Enhanced AI SQL Assistant
Tests key scenarios and compares with known good queries
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from ai_sql_assistant_v2 import EnhancedAISQLAssistant
from database_pymssql import SQLServerConnection
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def run_validation_tests():
    """Run quick validation tests"""
    print("=" * 80)
    print("ENHANCED AI SQL ASSISTANT - QUICK VALIDATION")
    print("=" * 80)
    
    # Initialize assistant
    api_key = os.getenv('OPENAI_API_KEY') or "YOUR_OPENAI_API_KEY_HERE"
    assistant = EnhancedAISQLAssistant(api_key=api_key)
    
    # Define test cases with expected SQL patterns
    test_cases = [
        {
            "name": "Simple Sales Query",
            "question": "What are total sales for today?",
            "expected_tables": ["Transaction", "TransactionEntry"],
            "validate_sql": lambda sql: all(x in sql for x in ["[dbo].[Transaction]", "TransactionEntry", "SUM"])
        },
        {
            "name": "Customer Revenue",
            "question": "Show me top 5 customers by revenue this month",
            "expected_tables": ["Transaction", "TransactionEntry", "Customer"],
            "validate_sql": lambda sql: all(x in sql for x in ["Customer", "TOP 5", "SUM"])
        },
        {
            "name": "Category Analysis",
            "question": "Sales by category for cigars",
            "expected_tables": ["Transaction", "TransactionEntry", "Item", "Category"],
            "validate_sql": lambda sql: all(x in sql for x in ["Category cat", "CIGARS"])
        },
        {
            "name": "Profit with Tobacco Uplift",
            "question": "Calculate profit for LT-TAX-COLLECTED products",
            "expected_tables": ["Transaction", "TransactionEntry", "Item", "Category"],
            "validate_sql": lambda sql: "1.10" in sql or "1.23" in sql
        },
        {
            "name": "AR Balance",
            "question": "Customers with AR balance over 1000",
            "expected_tables": ["AccountReceivable", "Customer"],
            "validate_sql": lambda sql: all(x in sql for x in ["AccountReceivable", "Balance"])
        },
        {
            "name": "Inventory Query",
            "question": "Products with low inventory",
            "expected_tables": ["Item"],
            "validate_sql": lambda sql: "Item" in sql
        },
        {
            "name": "Payment Analysis",
            "question": "Total payments received this month",
            "expected_tables": ["Payment"],
            "validate_sql": lambda sql: all(x in sql for x in ["Payment", "Time"])
        },
        {
            "name": "Time Series",
            "question": "Monthly sales trend for last 6 months",
            "expected_tables": ["Transaction", "TransactionEntry"],
            "validate_sql": lambda sql: "GROUP BY" in sql.upper()
        },
        {
            "name": "Complex Join",
            "question": "Customer sales and AR balance summary",
            "expected_tables": ["Customer", "Transaction", "AccountReceivable"],
            "validate_sql": lambda sql: "Customer" in sql
        },
        {
            "name": "Date Range",
            "question": "Sales between 01/01/2024 and 01/31/2024",
            "expected_tables": ["Transaction", "TransactionEntry"],
            "validate_sql": lambda sql: "BETWEEN" in sql or (">" in sql and "<" in sql)
        }
    ]
    
    # Run tests
    results = []
    print("\n🧪 Running validation tests...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test['name']}")
        print(f"    Question: {test['question']}")
        
        start_time = time.time()
        try:
            # Process question
            result = assistant.process_question(test['question'])
            execution_time = time.time() - start_time
            
            if result['success']:
                sql = result['sql_query']
                row_count = result['row_count']
                
                # Validate SQL structure
                sql_valid = test['validate_sql'](sql)
                
                # Test direct execution
                try:
                    with SQLServerConnection() as db:
                        df = db.execute_query(sql, description=f"Validation: {test['name']}")
                        execution_valid = True
                        actual_rows = len(df)
                except:
                    execution_valid = False
                    actual_rows = 0
                
                # Check table detection
                context = result.get('context', {})
                detected_tables = context.get('tables_needed', [])
                
                status = "✅" if sql_valid and execution_valid else "⚠️"
                print(f"    {status} Result: {row_count} rows in {execution_time:.2f}s")
                
                if not sql_valid:
                    print(f"       ❌ SQL validation failed")
                if not execution_valid:
                    print(f"       ❌ Execution failed")
                
                # Show SQL snippet
                sql_snippet = sql.replace('\n', ' ')[:100]
                print(f"    SQL: {sql_snippet}...")
                
                results.append({
                    "test": test['name'],
                    "success": result['success'],
                    "sql_valid": sql_valid,
                    "execution_valid": execution_valid,
                    "rows": row_count,
                    "time": execution_time
                })
            else:
                print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")
                results.append({
                    "test": test['name'],
                    "success": False,
                    "sql_valid": False,
                    "execution_valid": False,
                    "rows": 0,
                    "time": execution_time
                })
                
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
            results.append({
                "test": test['name'],
                "success": False,
                "sql_valid": False,
                "execution_valid": False,
                "rows": 0,
                "time": 0
            })
        
        print()
    
    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r['success'])
    sql_valid = sum(1 for r in results if r['sql_valid'])
    exec_valid = sum(1 for r in results if r['execution_valid'])
    
    print(f"\n📊 Overall Results:")
    print(f"  Query Generation: {successful}/{len(test_cases)} ({successful/len(test_cases)*100:.0f}%)")
    print(f"  SQL Validation: {sql_valid}/{len(test_cases)} ({sql_valid/len(test_cases)*100:.0f}%)")
    print(f"  Execution Success: {exec_valid}/{len(test_cases)} ({exec_valid/len(test_cases)*100:.0f}%)")
    
    avg_time = sum(r['time'] for r in results if r['success']) / max(successful, 1)
    print(f"\n⚡ Performance:")
    print(f"  Average execution time: {avg_time:.2f}s")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    print("-" * 60)
    for r in results:
        status = "✅" if r['success'] and r['sql_valid'] and r['execution_valid'] else "❌"
        print(f"{status} {r['test']:30} | Rows: {r['rows']:6} | Time: {r['time']:.2f}s")
    
    # Test complex scenarios
    print("\n" + "=" * 80)
    print("COMPLEX SCENARIO TESTS")
    print("=" * 80)
    
    complex_tests = [
        "Compare sales this month vs last month by category",
        "Which products have the highest profit margin?",
        "Customer cohort analysis by first purchase date",
        "Sales forecast based on historical trends",
        "Identify customers at risk of churn",
        "Market basket analysis for frequently bought together items"
    ]
    
    print("\n🔬 Testing complex analytical queries:\n")
    
    for i, question in enumerate(complex_tests, 1):
        print(f"[{i}] {question}")
        try:
            result = assistant.process_question(question)
            if result['success']:
                print(f"    ✅ Generated SQL with {result['row_count']} rows")
                # Show first line of analysis
                if result.get('analysis'):
                    first_line = result['analysis'].split('\n')[0][:100]
                    print(f"    Analysis: {first_line}...")
            else:
                print(f"    ❌ Failed: {result.get('error', 'Unknown')[:100]}")
        except Exception as e:
            print(f"    ❌ Exception: {str(e)[:100]}")
        print()
    
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    
    # Return overall success rate
    return exec_valid / len(test_cases) * 100


if __name__ == "__main__":
    success_rate = run_validation_tests()
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ AI Assistant is working well!")
        sys.exit(0)
    else:
        print("⚠️ AI Assistant needs improvement")
        sys.exit(1)