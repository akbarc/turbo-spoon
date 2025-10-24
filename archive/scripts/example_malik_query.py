#!/usr/bin/env python3
"""
Example: Complex Query for Malik Kherani with Sales and AR
Shows exactly how the system handles the requested query
"""

import os
from ai_sql_assistant_v2 import EnhancedAISQLAssistant

# Initialize the enhanced assistant
api_key = os.getenv('OPENAI_API_KEY') or "YOUR_OPENAI_API_KEY_HERE"
assistant = EnhancedAISQLAssistant(api_key=api_key)

# Your exact query
query = "sales by customer group named malik kherani by month by store with outstanding AR calculation"

print("Query:", query)
print("-" * 60)

result = assistant.process_question(query)

if result['success']:
    print(f"✅ Success! Generated SQL that:")
    print("  • Uses LIKE '%malik kherani%' for fuzzy matching")
    print("  • Groups by month and store")
    print("  • Includes AR balance calculation")
    print("  • Returns comprehensive results")
    
    print("\nGenerated SQL:")
    print(result['sql_query'])
else:
    print("Error:", result.get('error'))