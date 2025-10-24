#!/usr/bin/env python3
"""
AI SQL Assistant v3 - Complete Rewrite
Simplified, more accurate, and actually works well
"""

import os
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import pandas as pd
import openai
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


class AISQLAssistantV3:
    """
    Completely redesigned SQL Assistant that actually works.
    Focus on simplicity and accuracy over complex rules.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            # Fallback API key if needed
            self.api_key = "YOUR_OPENAI_API_KEY_HERE"
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self._query_cache = {}
        
        # Load actual schema from database
        self.schema = self._load_database_schema()
        
        # Common query patterns that work
        self.working_examples = self._load_working_examples()
    
    def _load_database_schema(self) -> Dict[str, List[str]]:
        """Load the actual database schema."""
        schema = {}
        try:
            with SQLServerConnection() as db:
                # Get all tables and columns
                query = """
                SELECT 
                    t.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE
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
            logger.error(f"Failed to load schema: {e}")
            # Fallback to known schema
            schema = self._get_fallback_schema()
        
        return schema
    
    def _get_fallback_schema(self) -> Dict[str, List[str]]:
        """Fallback schema if database query fails."""
        return {
            'Customer': ['ID', 'FirstName', 'LastName', 'Company', 'Address', 'City', 'State', 'Zip'],
            'Transaction': ['TransactionNumber', 'Time', 'CustomerID', 'Total', 'SalesTax'],
            'TransactionEntry': ['ID', 'TransactionNumber', 'ItemID', 'Quantity', 'Price', 'Cost', 'TransactionTime'],
            'Item': ['ID', 'ItemLookupCode', 'Description', 'DepartmentID', 'CategoryID', 'Price', 'Cost', 'Quantity'],
            'Category': ['ID', 'Name', 'DepartmentID'],
            'AccountReceivable': ['ID', 'CustomerID', 'Date', 'Balance', 'Amount'],
            'AccountReceivableHistory': ['ID', 'CustomerID', 'Date', 'Amount', 'Comment', 'TransactionNumber'],
            'Payment': ['ID', 'CustomerID', 'Time', 'Amount', 'Comment'],
            'Supplier': ['ID', 'SupplierName', 'ContactName', 'PhoneNumber']
        }
    
    def _load_working_examples(self) -> List[Dict[str, str]]:
        """Load examples of queries that actually work."""
        return [
            {
                "question": "total sales last 30 days",
                "sql": """
                SELECT SUM(te.Price * te.Quantity) as TotalSales
                FROM [dbo].[Transaction] t
                JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
                """
            },
            {
                "question": "sales by category",
                "sql": """
                SELECT 
                    ISNULL(cat.Name, 'UNCATEGORIZED') as Category,
                    SUM(te.Price * te.Quantity) as TotalSales
                FROM [dbo].[Transaction] t
                JOIN TransactionEntry te ON te.TransactionNumber = t.TransactionNumber
                LEFT JOIN Item i ON te.ItemID = i.ID
                LEFT JOIN Category cat ON i.CategoryID = cat.ID
                WHERE t.Time >= DATEADD(DAY, -30, GETDATE())
                GROUP BY cat.Name
                ORDER BY TotalSales DESC
                """
            },
            {
                "question": "customers with balance over 1000",
                "sql": """
                SELECT 
                    c.ID,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                    SUM(ar.Balance) as TotalBalance
                FROM AccountReceivable ar
                JOIN Customer c ON ar.CustomerID = c.ID
                GROUP BY c.ID, c.Company, c.FirstName, c.LastName
                HAVING SUM(ar.Balance) > 1000
                ORDER BY TotalBalance DESC
                """
            }
        ]
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt with schema info."""
        schema_text = "Database Schema:\n"
        for table, columns in self.schema.items():
            schema_text += f"\n{table}: {', '.join(columns[:10])}"  # First 10 columns
        
        examples_text = "\nWorking Examples:\n"
        for ex in self.working_examples[:3]:
            examples_text += f"\nQ: {ex['question']}\nSQL: {ex['sql'][:200]}...\n"
        
        return f"""You are a SQL expert for SQL Server 2008 R2.

{schema_text}

Key Rules:
1. Use [dbo].[Transaction] with brackets (reserved word)
2. Join TransactionEntry to Transaction via TransactionNumber
3. Customer name: COALESCE(c.Company, c.FirstName + ' ' + c.LastName)
4. Date columns: Transaction.Time, Payment.Time, AccountReceivable.Date
5. For categories, join: Item -> Category
6. Use TOP not LIMIT
7. No window functions (not supported in SQL Server 2008 R2)

{examples_text}

Return ONLY the SQL query, no explanations."""
    
    def generate_sql(self, question: str) -> str:
        """Generate SQL from natural language question."""
        try:
            # Check if question is about time period
            time_clause = self._extract_time_clause(question)
            
            # Add time context if found
            if time_clause:
                question_with_context = f"{question} (use: {time_clause})"
            else:
                question_with_context = question
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Faster, cheaper, often better for SQL
                messages=[
                    {"role": "system", "content": self._create_system_prompt()},
                    {"role": "user", "content": f"Generate SQL for: {question_with_context}"}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up the SQL
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            # Basic safety check
            if any(keyword in sql.upper() for keyword in ['DELETE', 'UPDATE', 'INSERT', 'DROP', 'ALTER']):
                raise ValueError("Only SELECT queries are allowed")
            
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise
    
    def _extract_time_clause(self, question: str) -> Optional[str]:
        """Extract time period from question and return SQL clause."""
        q_lower = question.lower()
        
        # Today
        if 'today' in q_lower:
            return "CAST(t.Time AS DATE) = CAST(GETDATE() AS DATE)"
        
        # Yesterday
        if 'yesterday' in q_lower:
            return "CAST(t.Time AS DATE) = CAST(DATEADD(DAY, -1, GETDATE()) AS DATE)"
        
        # Last N days
        import re
        days_match = re.search(r'last (\d+) days?|past (\d+) days?', q_lower)
        if days_match:
            days = days_match.group(1) or days_match.group(2)
            return f"t.Time >= DATEADD(DAY, -{days}, GETDATE())"
        
        # Last N months
        months_match = re.search(r'last (\d+) months?|past (\d+) months?', q_lower)
        if months_match:
            months = months_match.group(1) or months_match.group(2)
            return f"t.Time >= DATEADD(MONTH, -{months}, GETDATE())"
        
        # This month (MTD)
        if 'this month' in q_lower or 'mtd' in q_lower:
            return "t.Time >= DATEADD(DAY, 1 - DAY(GETDATE()), CAST(GETDATE() AS DATE))"
        
        # This year (YTD)
        if 'this year' in q_lower or 'ytd' in q_lower:
            return "t.Time >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR(4)) + '-01-01' AS DATETIME)"
        
        # Last month
        if 'last month' in q_lower:
            return """t.Time >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 1, 0)
                     AND t.Time < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)"""
        
        # Default to last 30 days if time-related words present
        if any(word in q_lower for word in ['recent', 'lately', 'sales', 'revenue', 'transactions']):
            return "t.Time >= DATEADD(DAY, -30, GETDATE())"
        
        return None
    
    def execute_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and return DataFrame."""
        try:
            with SQLServerConnection() as db:
                df = db.execute_query(sql, description="AI Generated Query")
                return df
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            # Try to fix common issues
            fixed_sql = self._try_fix_sql(sql, str(e))
            if fixed_sql != sql:
                logger.info("Attempting fixed query...")
                with SQLServerConnection() as db:
                    df = db.execute_query(fixed_sql, description="AI Generated Query (Fixed)")
                    return df
            raise
    
    def _try_fix_sql(self, sql: str, error: str) -> str:
        """Attempt to fix common SQL errors."""
        fixed = sql
        
        # Fix Transaction table references
        if 'Transaction' in error or 'syntax' in error.lower():
            fixed = fixed.replace(' Transaction ', ' [dbo].[Transaction] ')
            fixed = fixed.replace('FROM Transaction', 'FROM [dbo].[Transaction]')
            fixed = fixed.replace('JOIN Transaction', 'JOIN [dbo].[Transaction]')
        
        # Fix date column issues
        if 'Date' in error or 'Time' in error:
            fixed = fixed.replace('Transaction.Date', 'Transaction.Time')
            fixed = fixed.replace('t.Date', 't.Time')
            fixed = fixed.replace('Payment.Date', 'Payment.Time')
            fixed = fixed.replace('p.Date', 'p.Time')
        
        # Fix ambiguous column names
        if 'ambiguous' in error.lower():
            # Add table aliases where missing
            fixed = re.sub(r'\b(ID|Name|Time|Date)\b(?![.])', r't.\1', fixed)
        
        return fixed
    
    def analyze_results(self, question: str, df: pd.DataFrame) -> str:
        """Provide natural language analysis of results."""
        if df.empty:
            return "No data found for your query."
        
        # Create a summary
        summary_parts = []
        
        # Row count
        summary_parts.append(f"Found {len(df):,} results")
        
        # Numeric columns summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols[:3]:  # First 3 numeric columns
            if 'price' in col.lower() or 'amount' in col.lower() or 'sales' in col.lower() or 'revenue' in col.lower():
                total = df[col].sum()
                summary_parts.append(f"Total {col}: ${total:,.2f}")
            elif 'count' in col.lower() or 'quantity' in col.lower():
                total = df[col].sum()
                summary_parts.append(f"Total {col}: {total:,.0f}")
        
        # Top results if grouped
        if len(df) > 1 and len(df.columns) > 1:
            first_col = df.columns[0]
            if df[first_col].dtype == 'object':  # Likely a category/name
                top_3 = df.head(3)
                summary_parts.append(f"Top 3 {first_col}: {', '.join(top_3[first_col].astype(str))}")
        
        return " | ".join(summary_parts)
    
    def process_question(self, question: str, feedback_callback=None) -> Dict[str, Any]:
        """Main entry point - process a natural language question."""
        def feedback(msg: str):
            if feedback_callback:
                try:
                    feedback_callback(msg)
                except:
                    pass
            logger.info(msg)
        
        try:
            # Generate SQL
            feedback("🤖 Generating SQL query...")
            sql_query = self.generate_sql(question)
            
            # Execute query
            feedback("⚡ Executing query...")
            results_df = self.execute_query(sql_query)
            
            # Analyze results
            feedback("📊 Analyzing results...")
            analysis = self.analyze_results(question, results_df)
            
            # Cache results
            cache_id = f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._query_cache[cache_id] = {
                'df': results_df,
                'sql': sql_query,
                'question': question
            }
            
            # Convert for JSON serialization
            def convert_decimal(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                if isinstance(obj, pd.Timestamp):
                    return obj.isoformat()
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            results_preview = results_df.head(500).applymap(convert_decimal).to_dict('records')
            
            return {
                'success': True,
                'question': question,
                'sql_query': sql_query,
                'results': results_preview,
                'row_count': len(results_df),
                'display_count': min(len(results_df), 500),
                'analysis': analysis,
                'query_id': cache_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process question: {e}")
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
        """Get cached query results."""
        if query_id in self._query_cache:
            return self._query_cache[query_id]['df']
        return None
    
    def export_results(self, query_id: str, format: str = 'excel') -> Optional[str]:
        """Export cached results to file."""
        if query_id not in self._query_cache:
            return None
        
        df = self._query_cache[query_id]['df']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'excel':
            filename = f'query_results_{timestamp}.xlsx'
            df.to_excel(filename, index=False)
            return filename
        elif format == 'csv':
            filename = f'query_results_{timestamp}.csv'
            df.to_csv(filename, index=False)
            return filename
        
        return None


# Backwards compatibility wrapper
class AISQLAssistant:
    """Wrapper for backwards compatibility with existing code."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.v3 = AISQLAssistantV3(api_key)
    
    def process_business_question(self, question: str, feedback_callback=None) -> Dict[str, Any]:
        return self.v3.process_question(question, feedback_callback)
    
    def get_cached_results(self, query_id: str) -> Optional[pd.DataFrame]:
        return self.v3.get_cached_results(query_id)
    
    def process_followup(self, previous_sql: str, instruction: str, feedback_callback=None) -> Dict[str, Any]:
        # For followup, just process as new question
        return self.v3.process_question(instruction, feedback_callback)