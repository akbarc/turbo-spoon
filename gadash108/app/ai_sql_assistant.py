#!/usr/bin/env python3
"""
AI SQL Assistant - Complete Rewrite (V3)
Simplified and actually works!
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import pandas as pd
import openai
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


class AISQLAssistant:
    """
    Completely redesigned SQL Assistant that actually works.
    Focus on simplicity and accuracy over complex rules.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            # Fallback API key if environment variable not set
            self.api_key = "YOUR_OPENAI_API_KEY_HERE"
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self._query_cache = {}
        
        # Load actual schema from database
        self.schema = self._load_database_schema()
    
    def _load_database_schema(self) -> Dict[str, List[str]]:
        """Load the actual database schema."""
        schema = {}
        try:
            with SQLServerConnection() as db:
                # Get key tables and their columns
                query = """
                SELECT 
                    t.TABLE_NAME,
                    c.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLES t
                JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                WHERE t.TABLE_SCHEMA = 'dbo' 
                    AND t.TABLE_TYPE = 'BASE TABLE'
                    AND t.TABLE_NAME IN (
                        'Customer', 'Transaction', 'TransactionEntry', 
                        'Item', 'Category', 'Supplier',
                        'AccountReceivable', 'AccountReceivableHistory', 
                        'Payment', 'Department'
                    )
                ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
                """
                df = db.execute_query(query, description="Load schema")
                
                for _, row in df.iterrows():
                    table = row['TABLE_NAME']
                    column = row['COLUMN_NAME']
                    if table not in schema:
                        schema[table] = []
                    schema[table].append(column)
                    
            logger.info(f"Loaded schema for {len(schema)} tables")
        except Exception as e:
            logger.warning(f"Using fallback schema: {e}")
            # Fallback to known schema
            schema = {
                'Customer': ['ID', 'FirstName', 'LastName', 'Company'],
                'Transaction': ['TransactionNumber', 'Time', 'CustomerID', 'Total'],
                'TransactionEntry': ['ID', 'TransactionNumber', 'ItemID', 'Quantity', 'Price', 'Cost', 'TransactionTime'],
                'Item': ['ID', 'ItemLookupCode', 'Description', 'CategoryID', 'SupplierID'],
                'Category': ['ID', 'Name'],
                'AccountReceivable': ['ID', 'CustomerID', 'Date', 'Balance', 'Amount'],
                'Payment': ['ID', 'CustomerID', 'Time', 'Amount'],
                'Supplier': ['ID', 'SupplierName']
            }
        
        return schema
    
    def _build_prompt(self, question: str) -> str:
        """Build a simple, effective prompt."""
        # Extract time context
        time_context = self._get_time_context(question)
        
        schema_text = "Key Tables:\n"
        for table, cols in self.schema.items():
            schema_text += f"• {table}: {', '.join(cols[:8])}\n"
        
        prompt = f"""Generate a SQL Server 2008 R2 query for this question: {question}

{schema_text}

Critical Rules:
1. Use [dbo].[Transaction] (with brackets - it's a reserved word)
2. Date columns: Transaction.Time, Payment.Time, AccountReceivable.Date
3. Join path for sales: [Transaction] -> TransactionEntry -> Item -> Category
4. Customer name: COALESCE(Company, FirstName + ' ' + LastName)
5. Use TOP not LIMIT
6. No window functions (OVER/PARTITION BY)
{time_context}

Return ONLY the SQL query."""
        
        return prompt
    
    def _get_time_context(self, question: str) -> str:
        """Extract time period context."""
        q = question.lower()
        
        if 'today' in q:
            return "\nTime filter: WHERE t.Time >= CAST(GETDATE() AS DATE)"
        elif 'yesterday' in q:
            return "\nTime filter: WHERE CAST(t.Time AS DATE) = DATEADD(DAY, -1, CAST(GETDATE() AS DATE))"
        elif 'last 12 months' in q or 'trailing 12' in q:
            return "\nTime filter: WHERE t.Time >= DATEADD(MONTH, -12, GETDATE())"
        elif 'last 30 days' in q or 'past 30' in q or 'last month' in q:
            return "\nTime filter: WHERE t.Time >= DATEADD(DAY, -30, GETDATE())"
        elif 'ytd' in q or 'year to date' in q or 'this year' in q:
            return "\nTime filter: WHERE t.Time >= CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01'"
        elif re.search(r'last (\d+) days', q):
            days = re.search(r'last (\d+) days', q).group(1)
            return f"\nTime filter: WHERE t.Time >= DATEADD(DAY, -{days}, GETDATE())"
        elif re.search(r'last (\d+) months', q):
            months = re.search(r'last (\d+) months', q).group(1)
            return f"\nTime filter: WHERE t.Time >= DATEADD(MONTH, -{months}, GETDATE())"
        
        # Default for queries that likely need time context
        if any(word in q for word in ['sales', 'revenue', 'transactions', 'total', 'sum']):
            return "\nTime filter (default): WHERE t.Time >= DATEADD(DAY, -30, GETDATE())"
        
        return ""
    
    def generate_sql(self, question: str) -> str:
        """Generate SQL from natural language."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and effective
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate only SQL queries, no explanations."},
                    {"role": "user", "content": self._build_prompt(question)}
                ],
                temperature=0.1,
                max_tokens=600
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            # Safety check
            if any(kw in sql.upper() for kw in ['DELETE', 'UPDATE', 'INSERT', 'DROP', 'ALTER', 'TRUNCATE']):
                raise ValueError("Only SELECT queries allowed")
            
            # Quick fixes for common issues
            sql = self._apply_quick_fixes(sql)
            
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            raise
    
    def _apply_quick_fixes(self, sql: str) -> str:
        """Apply quick fixes for common issues."""
        # Fix Transaction references
        sql = re.sub(r'\bFROM\s+Transaction\b', 'FROM [dbo].[Transaction]', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bJOIN\s+Transaction\b', 'JOIN [dbo].[Transaction]', sql, flags=re.IGNORECASE)
        
        # Fix date columns
        sql = sql.replace('Transaction.Date', 'Transaction.Time')
        sql = sql.replace('t.Date', 't.Time')
        sql = sql.replace('Payment.Date', 'Payment.Time')
        
        return sql
    
    def execute_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return results."""
        try:
            with SQLServerConnection() as db:
                return db.execute_query(sql, description="AI Query")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Execution error: {error_msg}")
            
            # Try to auto-fix and retry once
            if 'syntax' in error_msg.lower() or 'Transaction' in error_msg:
                fixed_sql = sql.replace(' Transaction ', ' [dbo].[Transaction] ')
                fixed_sql = fixed_sql.replace('FROM Transaction', 'FROM [dbo].[Transaction]')
                fixed_sql = fixed_sql.replace('JOIN Transaction', 'JOIN [dbo].[Transaction]')
                
                try:
                    with SQLServerConnection() as db:
                        return db.execute_query(fixed_sql, description="AI Query (Fixed)")
                except:
                    pass
            
            raise
    
    def analyze_results(self, question: str, sql: str, df: pd.DataFrame) -> str:
        """Quick analysis of results."""
        if df.empty:
            return "No data found."
        
        analysis = []
        
        # Row count
        analysis.append(f"{len(df):,} results")
        
        # Sum numeric columns
        for col in df.select_dtypes(include=['number']).columns[:3]:
            if any(kw in col.lower() for kw in ['amount', 'total', 'sales', 'revenue', 'balance']):
                total = df[col].sum()
                if total > 100:
                    analysis.append(f"{col}: ${total:,.2f}")
                else:
                    analysis.append(f"{col}: {total:,.2f}")
        
        return " | ".join(analysis) if analysis else "Query executed successfully"
    
    def process_business_question(self, question: str, feedback_callback=None) -> Dict[str, Any]:
        """Main entry point - process a business question."""
        def feedback(msg):
            if feedback_callback:
                try:
                    feedback_callback(msg)
                except:
                    pass
            logger.info(msg)
        
        try:
            # Generate SQL
            feedback("🤖 Generating SQL...")
            sql_query = self.generate_sql(question)
            
            # Execute
            feedback("⚡ Running query...")
            results_df = self.execute_query(sql_query)
            
            # Analyze
            feedback("📊 Analyzing...")
            analysis = self.analyze_results(question, sql_query, results_df)
            
            # Cache
            cache_id = f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._query_cache[cache_id] = {'df': results_df, 'sql': sql_query}
            
            # Format results
            def convert_for_json(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                if isinstance(obj, (datetime, pd.Timestamp)):
                    return obj.isoformat()
                return obj
            
            # Convert DataFrame for JSON
            results_json = []
            for _, row in results_df.head(500).iterrows():
                results_json.append({k: convert_for_json(v) for k, v in row.to_dict().items()})
            
            return {
                'success': True,
                'question': question,
                'sql_query': sql_query,
                'results': results_json,
                'row_count': len(results_df),
                'display_count': min(len(results_df), 500),
                'analysis': analysis,
                'query_id': cache_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Process error: {e}")
            return {
                'success': False,
                'question': question,
                'sql_query': None,
                'results': [],
                'row_count': 0,
                'analysis': f"Error: {str(e)}",
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_cached_results(self, query_id: str) -> Optional[pd.DataFrame]:
        """Get cached results by ID."""
        if query_id in self._query_cache:
            return self._query_cache[query_id]['df']
        return None
    
    def process_followup(self, previous_sql: str, instruction: str, feedback_callback=None) -> Dict[str, Any]:
        """Process a follow-up question."""
        # For now, just treat as new question
        # Could enhance to modify previous SQL based on instruction
        return self.process_business_question(instruction, feedback_callback)