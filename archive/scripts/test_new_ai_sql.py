#!/usr/bin/env python3
"""
Test the new simplified AI SQL Assistant
"""

from ai_sql_assistant import AISQLAssistant
import json

def test_queries():
    """Test various query types with the new assistant."""
    
    print("=" * 80)
    print("TESTING NEW AI SQL ASSISTANT V3")
    print("=" * 80)
    
    # Initialize assistant
    assistant = AISQLAssistant()
    
    # Test queries
    test_questions = [
        "total sales last 30 days",
        "top 5 customers by sales this month",
        "sales by category trailing 12 months",
        "customers with balance over $5000",
        "best selling products today",
        "total revenue YTD by month"
    ]
    
    results = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nTest {i}: {question}")
        print("-" * 60)
        
        try:
            result = assistant.process_business_question(question)
            
            if result['success']:
                print(f"✅ Success!")
                print(f"   SQL: {result['sql_query'][:100]}...")
                print(f"   Results: {result['row_count']} rows")
                print(f"   Analysis: {result['analysis']}")
                results.append({
                    'question': question,
                    'status': 'SUCCESS',
                    'rows': result['row_count'],
                    'analysis': result['analysis']
                })
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                results.append({
                    'question': question,
                    'status': 'FAILED',
                    'error': result.get('error', 'Unknown error')
                })
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                'question': question,
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    print(f"\nSuccess Rate: {success_count}/{len(test_questions)} ({success_count/len(test_questions)*100:.0f}%)")
    
    print("\nDetailed Results:")
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        print(f"{status_icon} {r['question'][:50]:<50} {r['status']}")
        if r['status'] == 'SUCCESS':
            print(f"   → {r.get('analysis', 'No analysis')}")
        else:
            print(f"   → Error: {r.get('error', 'Unknown')[:60]}")
    
    # Save results
    with open('ai_sql_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n✅ Test results saved to ai_sql_test_results.json")

if __name__ == "__main__":
    test_queries()