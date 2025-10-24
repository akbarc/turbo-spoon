#!/usr/bin/env python3
"""
Test script to reproduce the AI SQL assistant's weekly sales calculation 
that might be producing unrealistic $15M+ figures
"""

import sys
import os
sys.path.append('/Users/akbarchranya/georgiadashboard')

from ai_sql_assistant import AISQLAssistant
from database_pymssql import quick_query
import json

def test_ai_weekly_sales():
    """Test AI SQL Assistant with weekly sales questions"""
    print("=" * 80)
    print("TESTING AI SQL ASSISTANT - WEEKLY SALES QUERIES")
    print("=" * 80)
    
    try:
        # Initialize AI SQL Assistant
        print("\n1. INITIALIZING AI SQL ASSISTANT...")
        assistant = AISQLAssistant()
        print("✅ AI SQL Assistant initialized")
        
        # Test questions that might produce unrealistic figures
        test_questions = [
            "Compare this week's sales to last week",
            "What are this week's sales figures?", 
            "Show me weekly sales for the past month",
            "How much did we sell this week compared to last week?",
            "What are the total sales for the current week?"
        ]
        
        print(f"\n2. TESTING {len(test_questions)} WEEKLY SALES QUESTIONS...")
        print("-" * 60)
        
        for i, question in enumerate(test_questions, 1):
            print(f"\nQUESTION {i}: {question}")
            print("-" * 40)
            
            try:
                # Process the question through AI
                def feedback_callback(message):
                    print(f"  {message}")
                
                result = assistant.process_business_question(question, feedback_callback)
                
                if result['success']:
                    print(f"✅ SQL Generated: {result['sql_query']}")
                    print(f"📊 Results: {result['row_count']} rows returned")
                    
                    # Check for unrealistic figures
                    if result['results']:
                        print("💰 Key financial figures found:")
                        for row in result['results'][:5]:  # Show first 5 rows
                            for key, value in row.items():
                                if isinstance(value, (int, float)) and value > 1000000:  # Values over $1M
                                    print(f"    🚨 HIGH VALUE: {key} = ${value:,.2f}")
                                elif 'sales' in key.lower() or 'total' in key.lower() or 'revenue' in key.lower():
                                    print(f"    💵 {key} = ${value:,.2f}")
                    
                    print(f"🧠 AI Analysis: {result['analysis']}")
                    
                    # Manual verification with simple query
                    print("🔍 MANUAL VERIFICATION:")
                    verification_query = """
                    SELECT 
                        'This Week (Last 7 Days)' as Period,
                        COUNT(*) as TransactionCount,
                        SUM(COALESCE(te.Price * te.Quantity, 0)) as TotalSales
                    FROM [dbo].[Transaction] t
                    LEFT JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                    WHERE t.Time >= DATEADD(day, -7, GETDATE())
                    """
                    
                    verification_df = quick_query(verification_query)
                    if not verification_df.empty:
                        actual_sales = verification_df.iloc[0]['TotalSales']
                        actual_transactions = verification_df.iloc[0]['TransactionCount']
                        print(f"    Manual check: ${actual_sales:,.2f} from {actual_transactions:,} transactions")
                        
                        # Compare with AI result
                        ai_totals = []
                        for row in result['results']:
                            for key, value in row.items():
                                if 'sales' in key.lower() and isinstance(value, (int, float)):
                                    ai_totals.append(value)
                        
                        if ai_totals:
                            max_ai_total = max(ai_totals)
                            if max_ai_total > actual_sales * 2:  # AI result is more than double manual check
                                print(f"    ⚠️ DISCREPANCY: AI max figure (${max_ai_total:,.2f}) vs Manual (${actual_sales:,.2f})")
                            else:
                                print(f"    ✅ Results consistent with manual check")
                else:
                    print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Error processing question: {e}")
                
            print("-" * 40)
            
        print("\n" + "=" * 80)
        print("AI WEEKLY SALES TEST COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_weekly_sales()