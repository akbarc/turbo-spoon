import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pymssql
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import re
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSchemaManager:
    """Manages comprehensive database schema knowledge"""
    
    def __init__(self):
        self.schema = self._load_schema_knowledge()
        self.business_rules = self._load_business_rules()
        self.common_patterns = self._load_query_patterns()
    
    def _load_schema_knowledge(self) -> Dict[str, Any]:
        """Load comprehensive schema knowledge from documentation"""
        return {
            'tables': {
                'Transaction': {
                    'alias': 't',
                    'primary_key': 'TransactionNumber',
                    'schema': '[dbo].[Transaction]',  # Must be bracketed
                    'columns': {
                        'TransactionNumber': {'type': 'int', 'is_pk': True},
                        'Time': {'type': 'datetime', 'note': 'NOT Date - use Time'},
                        'CustomerID': {'type': 'int', 'fk': 'Customer.ID'},
                        'CashierID': {'type': 'int'},
                        'Total': {'type': 'money'},
                        'SalesTax': {'type': 'money'},
                        'BatchNumber': {'type': 'int'},
                        'StoreID': {'type': 'int'},
                        'Comment': {'type': 'nvarchar(255)', 'note': 'Cannot GROUP BY'},
                        'ReferenceNumber': {'type': 'nvarchar(50)'},
                        'Status': {'type': 'int'},
                        'CreatedDateTime': {'type': 'datetime'},
                        'ModifiedDateTime': {'type': 'datetime'}
                    },
                    'sample_joins': [
                        't.CustomerID = c.ID',
                        't.TransactionNumber = te.TransactionNumber'
                    ]
                },
                'TransactionEntry': {
                    'alias': 'te',
                    'primary_key': 'ID',
                    'schema': 'dbo.TransactionEntry',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True},
                        'TransactionNumber': {'type': 'int', 'fk': 'Transaction.TransactionNumber'},
                        'ItemID': {'type': 'int', 'fk': 'Item.ID'},
                        'Price': {'type': 'money', 'note': 'Selling price per unit'},
                        'Cost': {'type': 'money', 'note': 'Cost price - needs tobacco uplifts'},
                        'Quantity': {'type': 'float'},
                        'SalesTax': {'type': 'money'},
                        'TransactionTime': {'type': 'datetime', 'note': 'NOT Time - use TransactionTime'},
                        'Comment': {'type': 'text', 'note': 'Cannot GROUP BY'}
                    },
                    'business_logic': {
                        'revenue_calculation': 'Price * Quantity',
                        'cost_adjustments': 'Apply tobacco uplifts for categories 23 and 49'
                    }
                },
                'Customer': {
                    'alias': 'c',
                    'primary_key': 'ID',
                    'schema': 'dbo.Customer',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True, 'note': 'NOT CustomerID!'},
                        'FirstName': {'type': 'nvarchar(50)'},
                        'LastName': {'type': 'nvarchar(50)'},
                        'Company': {'type': 'nvarchar(100)', 'note': 'Priority over names'},
                        'AccountNumber': {'type': 'nvarchar(50)'},
                        'Address': {'type': 'nvarchar(255)'},
                        'City': {'type': 'nvarchar(50)'},
                        'State': {'type': 'nvarchar(10)'},
                        'Zip': {'type': 'nvarchar(15)'},
                        'PhoneNumber': {'type': 'nvarchar(25)'},
                        'EmailAddress': {'type': 'nvarchar(100)'},
                        'AccountBalance': {'type': 'money'},
                        'CreditLimit': {'type': 'money'},
                        'TotalSales': {'type': 'money'},
                        'LastVisit': {'type': 'datetime'},
                        'TotalVisits': {'type': 'int'},
                        'Notes': {'type': 'text', 'note': 'Cannot GROUP BY'},
                        'TaxExempt': {'type': 'bit'}
                    },
                    'display_logic': 'ISNULL(Company, FirstName + \' \' + LastName)'
                },
                'Item': {
                    'alias': 'i',
                    'primary_key': 'ID',
                    'schema': 'dbo.Item',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True, 'note': 'NOT ItemID!'},
                        'ItemLookupCode': {'type': 'nvarchar(50)', 'note': 'Barcode/SKU'},
                        'Description': {'type': 'nvarchar(255)'},
                        'Price': {'type': 'money'},
                        'Cost': {'type': 'money'},
                        'CategoryID': {'type': 'int', 'fk': 'Category.ID'},
                        'Notes': {'type': 'text', 'note': 'Cannot GROUP BY'}
                    }
                },
                'Category': {
                    'alias': 'cat',
                    'primary_key': 'ID',
                    'schema': 'dbo.Category',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True},
                        'Name': {'type': 'nvarchar(100)'},
                        'Code': {'type': 'nvarchar(50)'}
                    },
                    'tobacco_categories': {
                        23: {'name': 'CIGARS', 'uplift': 0.23},
                        49: {'name': 'LT-TAX-COLLECTED', 'uplift': 0.10}
                    }
                },
                'Payment': {
                    'alias': 'p',
                    'primary_key': 'ID',
                    'schema': 'dbo.Payment',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True},
                        'CustomerID': {'type': 'int', 'fk': 'Customer.ID'},
                        'Time': {'type': 'datetime', 'note': 'NOT Date - use Time'},
                        'Amount': {'type': 'money'},
                        'Comment': {'type': 'text', 'note': 'Cannot GROUP BY, contains check numbers'},
                        'BatchID': {'type': 'int'},
                        'CreatedBy': {'type': 'nvarchar(50)'},
                        'CreatedDate': {'type': 'datetime'}
                    },
                    'warnings': [
                        'NO CheckNumber column - use Comment field',
                        'NO PaymentNumber column',
                        'NO Date column - use Time'
                    ]
                },
                'AccountReceivable': {
                    'alias': 'ar',
                    'primary_key': 'ID',
                    'schema': 'dbo.AccountReceivable',
                    'columns': {
                        'ID': {'type': 'int', 'is_pk': True},
                        'CustomerID': {'type': 'int', 'fk': 'Customer.ID'},
                        'Date': {'type': 'datetime', 'note': 'Date is correct here, not Time'},
                        'OriginalAmount': {'type': 'money'},
                        'TransactionNumber': {'type': 'int', 'fk': 'Transaction.TransactionNumber'}
                    }
                }
            },
            'sql_server_constraints': {
                'version': 'SQL Server 2008 R2',
                'no_window_functions': True,
                'no_format_function': True,
                'parameterization': '%s not ?',
                'text_columns_no_group_by': [
                    'Customer.Notes', 'Transaction.Comment', 
                    'TransactionEntry.Comment', 'Payment.Comment', 'Item.Notes'
                ]
            }
        }
    
    def _load_business_rules(self) -> Dict[str, Any]:
        """Load business logic and rules"""
        return {
            'tobacco_uplifts': {
                'categories': {
                    23: {'name': 'CIGARS', 'uplift_percent': 23},
                    49: {'name': 'LT-TAX-COLLECTED', 'uplift_percent': 10}
                },
                'formula': 'adjusted_cost = cost * (1 + uplift_percent/100)'
            },
            'revenue_calculation': 'SUM(te.Price * te.Quantity)',
            'cost_calculation': '''
                CASE 
                    WHEN cat.ID = 23 THEN te.Cost * 1.23  -- CIGARS +23%
                    WHEN cat.ID = 49 THEN te.Cost * 1.10  -- LT-TAX-COLLECTED +10%
                    ELSE te.Cost 
                END
            ''',
            'customer_display': 'ISNULL(c.Company, c.FirstName + \' \' + c.LastName)',
            'date_ranges': {
                'today': "CAST(t.Time as DATE) = CAST(GETDATE() as DATE)",
                'week': "t.Time >= DATEADD(week, -1, GETDATE())",
                'month': "t.Time >= DATEADD(month, -1, GETDATE())",
                'year': "t.Time >= DATEADD(year, -1, GETDATE())"
            }
        }
    
    def _load_query_patterns(self) -> Dict[str, Any]:
        """Load common query patterns and templates"""
        return {
            'sales_summary': '''
                SELECT 
                    SUM(te.Price * te.Quantity) as Revenue,
                    COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                    COUNT(te.ID) as ItemsSold,
                    AVG(t.Total) as AvgOrderValue
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE {date_filter}
            ''',
            'top_items': '''
                SELECT TOP {limit}
                    i.Description,
                    SUM(te.Quantity) as TotalQuantity,
                    SUM(te.Price * te.Quantity) as TotalRevenue
                FROM dbo.TransactionEntry te
                JOIN dbo.Item i ON te.ItemID = i.ID
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE {date_filter}
                GROUP BY i.ID, i.Description
                ORDER BY TotalQuantity DESC
            ''',
            'customer_list': '''
                SELECT TOP {limit}
                    c.ID,
                    {customer_display} as CustomerName,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.LastVisit,
                    c.TotalSales
                FROM dbo.Customer c
                WHERE {filter_condition}
                ORDER BY {order_by}
            ''',
            'daily_trends': '''
                SELECT 
                    CAST(t.Time as DATE) as Date,
                    SUM(te.Price * te.Quantity) as Revenue,
                    COUNT(DISTINCT t.TransactionNumber) as Transactions
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE t.Time >= DATEADD(day, -{days}, GETDATE())
                GROUP BY CAST(t.Time as DATE)
                ORDER BY Date DESC
            '''
        }
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive table information"""
        return self.schema['tables'].get(table_name)
    
    def validate_column(self, table_name: str, column_name: str) -> bool:
        """Validate if column exists in table"""
        table_info = self.get_table_info(table_name)
        if not table_info:
            return False
        return column_name in table_info['columns']
    
    def get_join_pattern(self, from_table: str, to_table: str) -> Optional[str]:
        """Get proper join pattern between tables"""
        join_patterns = {
            ('Transaction', 'TransactionEntry'): 't.TransactionNumber = te.TransactionNumber',
            ('TransactionEntry', 'Item'): 'te.ItemID = i.ID',
            ('Item', 'Category'): 'i.CategoryID = cat.ID',
            ('Transaction', 'Customer'): 't.CustomerID = c.ID',
            ('Payment', 'Customer'): 'p.CustomerID = c.ID',
            ('AccountReceivable', 'Customer'): 'ar.CustomerID = c.ID'
        }
        
        return join_patterns.get((from_table, to_table)) or join_patterns.get((to_table, from_table))

class DatabaseManager:
    """Manages database connections with automatic fallback to backup"""
    
    def __init__(self):
        self.primary_config = {
            'server': os.getenv('DB_SERVER', '10.1.10.105'),
            'database': os.getenv('DB_DATABASE', 'GAWDB'),
            'username': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD')
        }
        self.backup_db_path = 'backup/gawdb_backup.sqlite'
        self.connection = None
        self.is_primary = True
        
    def connect(self):
        """Establish database connection with automatic fallback"""
        try:
            # Try primary SQL Server connection first
            self.connection = pymssql.connect(
                server=self.primary_config['server'],
                user=self.primary_config['username'],
                password=self.primary_config['password'],
                database=self.primary_config['database'],
                tds_version='7.0',
                timeout=10
            )
            self.is_primary = True
            logger.info("Connected to primary SQL Server database")
            return True
            
        except Exception as e:
            logger.warning(f"Primary database connection failed: {e}")
            return self._fallback_to_backup()
    
    def _fallback_to_backup(self):
        """Fallback to SQLite backup database"""
        try:
            if os.path.exists(self.backup_db_path):
                self.connection = sqlite3.connect(self.backup_db_path)
                self.is_primary = False
                logger.info("Connected to backup SQLite database")
                return True
            else:
                logger.error("No backup database available")
                return False
        except Exception as e:
            logger.error(f"Backup database connection failed: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> List[Tuple]:
        """Execute query with error handling"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def get_table_info(self, table_name: str) -> Dict:
        """Get table structure and sample data"""
        try:
            if self.is_primary:
                # SQL Server query
                structure_query = """
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """
                structure = self.execute_query(structure_query, (table_name,))
            else:
                # SQLite query
                structure_query = f"PRAGMA table_info({table_name})"
                structure = self.execute_query(structure_query)
            
            # Get sample data
            sample_query = f"SELECT TOP 5 * FROM [{table_name}]" if self.is_primary else f"SELECT * FROM {table_name} LIMIT 5"
            sample_data = self.execute_query(sample_query)
            
            return {
                'structure': structure,
                'sample_data': sample_data,
                'row_count': self._get_row_count(table_name)
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {}
    
    def _get_row_count(self, table_name: str) -> int:
        """Get total row count for table"""
        try:
            # Handle Transaction table special case
            if table_name == 'Transaction':
                result = self.execute_query("SELECT COUNT(*) FROM [dbo].[Transaction]")
            else:
                result = self.execute_query(f"SELECT COUNT(*) FROM {table_name}")
            return result[0][0] if result else 0
        except:
            return 0
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

class EnhancedAIQueryProcessor:
    """Enhanced AI query processor with deep database understanding"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.schema_manager = DatabaseSchemaManager()
        self.query_cache = {}
        
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query with enhanced understanding"""
        try:
            # Analyze query intent with schema knowledge
            intent = self._analyze_intent_enhanced(user_query)
            
            # Generate SQL with proper schema understanding
            sql_query = self._generate_sql_enhanced(user_query, intent)
            
            if not sql_query:
                return {
                    'error': 'Could not understand the query. Please try rephrasing.',
                    'suggestions': self._get_intelligent_suggestions(),
                    'schema_help': self._get_schema_help(user_query)
                }
            
            # Validate SQL before execution
            validation_result = self._validate_sql(sql_query)
            if not validation_result['valid']:
                return {
                    'error': f'SQL validation failed: {validation_result["error"]}',
                    'generated_sql': sql_query,
                    'suggestions': self._get_fix_suggestions(validation_result['error'])
                }
            
            # Execute query
            results = self.db.execute_query(sql_query)
            
            # Format results with business logic
            formatted_results = self._format_results_enhanced(results, intent, sql_query)
            
            return {
                'sql': sql_query,
                'results': formatted_results,
                'intent': intent,
                'row_count': len(results),
                'execution_info': {
                    'database_type': 'SQL Server' if self.db.is_primary else 'SQLite Backup',
                    'query_validated': True,
                    'business_rules_applied': intent.get('business_rules', [])
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced query processing failed: {e}")
            return {
                'error': f'Query processing error: {str(e)}',
                'suggestions': self._get_intelligent_suggestions(),
                'debug_info': str(e)
            }
    
    def _analyze_intent_enhanced(self, query: str) -> Dict[str, Any]:
        """Enhanced intent analysis with schema understanding"""
        query_lower = query.lower()
        
        intent = {
            'type': 'unknown',
            'entities': {
                'tables': [],
                'columns': [],
                'aggregation': None,
                'time_filter': None,
                'conditions': [],
                'business_context': None
            },
            'business_rules': []
        }
        
        # Detect query type with more precision
        if any(word in query_lower for word in ['show', 'list', 'display', 'get', 'find']):
            intent['type'] = 'select'
        elif any(word in query_lower for word in ['total', 'sum', 'count', 'average', 'revenue']):
            intent['type'] = 'aggregate'
        elif any(word in query_lower for word in ['top', 'best', 'highest', 'most']):
            intent['type'] = 'ranking'
        elif any(word in query_lower for word in ['trend', 'over time', 'growth', 'change', 'daily', 'weekly']):
            intent['type'] = 'trend'
        elif any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            intent['type'] = 'compare'
        
        # Enhanced entity detection
        if any(word in query_lower for word in ['sale', 'sales', 'revenue', 'income', 'transaction']):
            intent['entities']['tables'].extend(['Transaction', 'TransactionEntry'])
            intent['entities']['business_context'] = 'sales'
            if 'tobacco' in query_lower or 'cigar' in query_lower:
                intent['business_rules'].append('tobacco_uplifts')
        
        if any(word in query_lower for word in ['customer', 'client', 'buyer', 'account']):
            intent['entities']['tables'].append('Customer')
            intent['entities']['business_context'] = 'customers'
        
        if any(word in query_lower for word in ['item', 'product', 'inventory', 'stock', 'sku']):
            intent['entities']['tables'].extend(['Item', 'Category'])
            intent['entities']['business_context'] = 'inventory'
        
        if any(word in query_lower for word in ['payment', 'check', 'cash', 'credit']):
            intent['entities']['tables'].append('Payment')
            intent['entities']['business_context'] = 'payments'
        
        # Enhanced time detection
        time_patterns = {
            'today': ['today', 'this day'],
            'week': ['week', 'this week', 'weekly', '7 day'],
            'month': ['month', 'this month', 'monthly', '30 day'],
            'year': ['year', 'this year', 'yearly', 'annual']
        }
        
        for period, keywords in time_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['entities']['time_filter'] = period
                break
        
        # Detect specific aggregations
        if 'top' in query_lower:
            # Extract number if present
            import re
            numbers = re.findall(r'\btop\s+(\d+)', query_lower)
            intent['entities']['limit'] = int(numbers[0]) if numbers else 10
        
        return intent
    
    def _generate_sql_enhanced(self, query: str, intent: Dict) -> str:
        """Generate SQL with enhanced schema knowledge"""
        try:
            business_context = intent['entities'].get('business_context')
            query_type = intent['type']
            time_filter = intent['entities'].get('time_filter')
            
            # Use business-specific templates
            if business_context == 'sales':
                return self._generate_sales_query(query, intent, time_filter)
            elif business_context == 'customers':
                return self._generate_customer_query(query, intent)
            elif business_context == 'inventory':
                return self._generate_inventory_query(query, intent)
            elif business_context == 'payments':
                return self._generate_payment_query(query, intent, time_filter)
            elif query_type == 'trend':
                return self._generate_trend_query_enhanced(query, intent)
            else:
                return self._generate_general_query(query, intent)
                
        except Exception as e:
            logger.error(f"Enhanced SQL generation failed: {e}")
            return ""
    
    def _generate_sales_query(self, query: str, intent: Dict, time_filter: str) -> str:
        """Generate sales-specific queries"""
        query_lower = query.lower()
        date_condition = self.schema_manager.business_rules['date_ranges'].get(time_filter, "1=1")
        
        if intent['type'] == 'aggregate':
            if 'revenue' in query_lower or 'total' in query_lower:
                return f"""
                    SELECT 
                        SUM(te.Price * te.Quantity) as TotalRevenue,
                        COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                        COUNT(te.ID) as ItemsSold,
                        AVG(t.Total) as AvgOrderValue
                    FROM [dbo].[Transaction] t
                    JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                    WHERE {date_condition}
                """
        
        elif intent['type'] == 'ranking' and 'item' in query_lower:
            limit = intent['entities'].get('limit', 10)
            return f"""
                SELECT TOP {limit}
                    i.Description,
                    SUM(te.Quantity) as TotalQuantity,
                    SUM(te.Price * te.Quantity) as TotalRevenue,
                    cat.Name as Category
                FROM dbo.TransactionEntry te
                JOIN dbo.Item i ON te.ItemID = i.ID
                JOIN dbo.Category cat ON i.CategoryID = cat.ID
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE {date_condition}
                GROUP BY i.ID, i.Description, cat.Name
                ORDER BY TotalQuantity DESC
            """
        
        elif intent['type'] == 'select':
            return f"""
                SELECT TOP 20
                    t.TransactionNumber,
                    t.Time as TransactionTime,
                    {self.schema_manager.business_rules['customer_display']} as CustomerName,
                    t.Total,
                    t.SalesTax
                FROM [dbo].[Transaction] t
                LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
                WHERE {date_condition}
                ORDER BY t.Time DESC
            """
        
        return ""
    
    def _generate_customer_query(self, query: str, intent: Dict) -> str:
        """Generate customer-specific queries"""
        query_lower = query.lower()
        customer_display = self.schema_manager.business_rules['customer_display']
        
        if 'recent' in query_lower or 'new' in query_lower:
            return f"""
                SELECT TOP 20
                    c.ID,
                    {customer_display} as CustomerName,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.LastVisit,
                    c.TotalSales,
                    c.AccountBalance
                FROM dbo.Customer c
                WHERE c.LastVisit >= DATEADD(month, -1, GETDATE())
                ORDER BY c.LastVisit DESC
            """
        
        elif 'top' in query_lower or 'best' in query_lower:
            limit = intent['entities'].get('limit', 10)
            return f"""
                SELECT TOP {limit}
                    c.ID,
                    {customer_display} as CustomerName,
                    c.TotalSales,
                    c.TotalVisits,
                    c.AccountBalance,
                    c.LastVisit
                FROM dbo.Customer c
                WHERE c.TotalSales > 0
                ORDER BY c.TotalSales DESC
            """
        
        else:
            return f"""
                SELECT TOP 20
                    c.ID,
                    {customer_display} as CustomerName,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.LastVisit,
                    c.TotalSales
                FROM dbo.Customer c
                ORDER BY c.ID DESC
            """
    
    def _generate_inventory_query(self, query: str, intent: Dict) -> str:
        """Generate inventory-specific queries"""
        query_lower = query.lower()
        
        if 'category' in query_lower:
            return """
                SELECT 
                    cat.Name as CategoryName,
                    COUNT(i.ID) as ItemCount,
                    AVG(i.Price) as AvgPrice,
                    AVG(i.Cost) as AvgCost
                FROM dbo.Item i
                JOIN dbo.Category cat ON i.CategoryID = cat.ID
                GROUP BY cat.ID, cat.Name
                ORDER BY ItemCount DESC
            """
        
        elif 'tobacco' in query_lower or 'cigar' in query_lower:
            return """
                SELECT 
                    i.Description,
                    i.ItemLookupCode,
                    i.Price,
                    i.Cost,
                    cat.Name as Category
                FROM dbo.Item i
                JOIN dbo.Category cat ON i.CategoryID = cat.ID
                WHERE cat.Name LIKE '%CIG%' OR cat.Name LIKE '%TOB%'
                ORDER BY i.Description
            """
        
        else:
            return """
                SELECT TOP 20
                    i.Description,
                    i.ItemLookupCode,
                    i.Price,
                    i.Cost,
                    cat.Name as Category
                FROM dbo.Item i
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                ORDER BY i.ID DESC
            """
    
    def _generate_payment_query(self, query: str, intent: Dict, time_filter: str) -> str:
        """Generate payment-specific queries"""
        date_condition = self.schema_manager.business_rules['date_ranges'].get(time_filter, "1=1")
        customer_display = self.schema_manager.business_rules['customer_display']
        
        return f"""
            SELECT TOP 20
                p.ID as PaymentID,
                {customer_display} as CustomerName,
                p.Time as PaymentTime,
                p.Amount,
                p.Comment as PaymentDetails
            FROM dbo.Payment p
            LEFT JOIN dbo.Customer c ON p.CustomerID = c.ID
            WHERE {date_condition.replace('t.Time', 'p.Time')}
            ORDER BY p.Time DESC
        """
    
    def _generate_trend_query_enhanced(self, query: str, intent: Dict) -> str:
        """Generate enhanced trend analysis queries"""
        days = 30
        if 'week' in query.lower():
            days = 7
        elif 'month' in query.lower():
            days = 30
        elif 'year' in query.lower():
            days = 365
        
        return f"""
            SELECT 
                CAST(t.Time as DATE) as Date,
                SUM(te.Price * te.Quantity) as Revenue,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                COUNT(te.ID) as ItemsSold,
                AVG(t.Total) as AvgOrderValue
            FROM [dbo].[Transaction] t
            JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= DATEADD(day, -{days}, GETDATE())
            GROUP BY CAST(t.Time as DATE)
            ORDER BY Date DESC
        """
    
    def _generate_general_query(self, query: str, intent: Dict) -> str:
        """Generate general queries when context is unclear"""
        return """
            SELECT 
                'System Status' as Metric,
                COUNT(*) as Value,
                'Today' as Period
            FROM [dbo].[Transaction]
            WHERE CAST(Time as DATE) = CAST(GETDATE() as DATE)
        """
    
    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate SQL query against schema knowledge"""
        try:
            # Check for common SQL Server 2008 R2 incompatibilities
            if 'FORMAT(' in sql.upper():
                return {'valid': False, 'error': 'FORMAT() function not supported in SQL Server 2008 R2'}
            
            if 'OVER(' in sql.upper() and 'ORDER BY' in sql.upper():
                return {'valid': False, 'error': 'Window functions with ORDER BY not supported'}
            
            # Check for proper table bracketing
            if 'dbo.Transaction' in sql and '[dbo].[Transaction]' not in sql:
                return {'valid': False, 'error': 'Transaction table must be bracketed: [dbo].[Transaction]'}
            
            # Check for text columns in GROUP BY
            text_columns = self.schema_manager.schema['sql_server_constraints']['text_columns_no_group_by']
            for col in text_columns:
                if col in sql and 'GROUP BY' in sql.upper():
                    return {'valid': False, 'error': f'{col} cannot be used in GROUP BY (text/ntext type)'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def _format_results_enhanced(self, results: List[Tuple], intent: Dict, sql: str) -> Dict:
        """Enhanced result formatting with business logic"""
        if not results:
            return {'data': [], 'summary': 'No results found', 'business_insights': []}
        
        # Convert to structured data
        formatted_data = []
        column_count = len(results[0]) if results else 0
        
        # Try to get column names from SQL if possible
        column_names = []
        if 'SELECT' in sql.upper():
            # Simple column name extraction
            select_part = sql.upper().split('SELECT')[1].split('FROM')[0]
            # This is a basic extraction - could be enhanced
            column_names = [f'Column_{i}' for i in range(column_count)]
        
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                col_name = column_names[i] if i < len(column_names) else f'Column_{i}'
                row_dict[col_name] = self._format_cell_value_enhanced(value, col_name)
            formatted_data.append(row_dict)
        
        # Generate business insights
        insights = self._generate_business_insights(formatted_data, intent)
        
        return {
            'data': formatted_data,
            'summary': f'Found {len(results)} results',
            'total_rows': len(results),
            'business_insights': insights,
            'data_quality': self._assess_data_quality(formatted_data)
        }
    
    def _format_cell_value_enhanced(self, value, column_name: str):
        """Enhanced cell value formatting with business logic"""
        if value is None:
            return None
        
        # Handle currency values
        if any(word in column_name.lower() for word in ['revenue', 'total', 'amount', 'price', 'cost', 'balance']):
            if isinstance(value, (int, float)):
                return f"${value:,.2f}"
        
        # Handle dates
        if isinstance(value, str) and ('time' in column_name.lower() or 'date' in column_name.lower()):
            try:
                if 'T' in value:
                    return datetime.fromisoformat(value.replace('T', ' ')).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return value
            except:
                return value
        
        # Handle numbers
        if isinstance(value, (int, float)):
            if column_name.lower() in ['quantity', 'count', 'itemssold', 'transactions']:
                return f"{value:,}"
            elif value > 1000:
                return f"{value:,.2f}"
        
        return str(value)
    
    def _generate_business_insights(self, data: List[Dict], intent: Dict) -> List[str]:
        """Generate business insights from query results"""
        insights = []
        
        if not data:
            return insights
        
        business_context = intent['entities'].get('business_context')
        
        if business_context == 'sales' and len(data) > 0:
            # Sales insights
            revenue_cols = [k for k in data[0].keys() if 'revenue' in k.lower()]
            if revenue_cols:
                try:
                    total_revenue = sum(float(row[revenue_cols[0]].replace('$', '').replace(',', '')) 
                                      for row in data if row[revenue_cols[0]])
                    insights.append(f"Total revenue analyzed: ${total_revenue:,.2f}")
                except:
                    pass
        
        elif business_context == 'customers' and len(data) > 0:
            insights.append(f"Customer analysis shows {len(data)} records")
            
        return insights
    
    def _assess_data_quality(self, data: List[Dict]) -> Dict[str, Any]:
        """Assess data quality of results"""
        if not data:
            return {'completeness': 0, 'issues': []}
        
        total_fields = len(data) * len(data[0])
        null_fields = sum(1 for row in data for value in row.values() if value is None)
        
        completeness = ((total_fields - null_fields) / total_fields) * 100 if total_fields > 0 else 0
        
        issues = []
        if completeness < 90:
            issues.append(f"Data completeness: {completeness:.1f}% (some null values)")
        
        return {'completeness': completeness, 'issues': issues}
    
    def _get_intelligent_suggestions(self) -> List[str]:
        """Get intelligent query suggestions based on schema"""
        return [
            "Show me today's sales revenue",
            "What are the top 10 selling items this week?",
            "List recent customers with their last visit dates", 
            "Show sales trends over the last 30 days",
            "What's our total revenue this month?",
            "Display tobacco category sales with proper cost adjustments",
            "List customers with outstanding account balances",
            "Show daily transaction counts for this week",
            "What are the most profitable product categories?",
            "Display recent payments with customer details"
        ]
    
    def _get_schema_help(self, user_query: str) -> Dict[str, Any]:
        """Provide schema-specific help based on user query"""
        help_info = {
            'available_tables': list(self.schema_manager.schema['tables'].keys()),
            'common_joins': [
                'Transaction ↔ TransactionEntry (sales data)',
                'TransactionEntry ↔ Item (product details)', 
                'Item ↔ Category (product categories)',
                'Transaction ↔ Customer (customer data)',
                'Payment ↔ Customer (payment history)'
            ],
            'business_rules': [
                'Tobacco categories 23 (CIGARS) and 49 (LT-TAX-COLLECTED) require cost uplifts',
                'Revenue = Price × Quantity',
                'Customer display uses Company name or FirstName + LastName'
            ]
        }
        
        return help_info
    
    def _get_fix_suggestions(self, error: str) -> List[str]:
        """Get suggestions to fix SQL errors"""
        suggestions = []
        
        if 'bracket' in error.lower():
            suggestions.append("Use [dbo].[Transaction] instead of dbo.Transaction")
        if 'group by' in error.lower():
            suggestions.append("Remove text/ntext columns from GROUP BY clause")
        if 'format' in error.lower():
            suggestions.append("Use CAST(field AS DATE) instead of FORMAT() function")
        if 'window' in error.lower():
            suggestions.append("Avoid window functions with ORDER BY in SQL Server 2008 R2")
        
        return suggestions

class AnalyticsEngine:
    """Advanced analytics and insights engine with schema knowledge"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.schema_manager = DatabaseSchemaManager()
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get key dashboard metrics using proper schema"""
        try:
            metrics = {}
            
            # Today's sales with proper SQL
            today_sales = self.db.execute_query("""
                SELECT 
                    COALESCE(SUM(te.Price * te.Quantity), 0) as TodayRevenue,
                    COUNT(DISTINCT t.TransactionNumber) as TodayTransactions
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE CAST(t.Time as DATE) = CAST(GETDATE() as DATE)
            """)
            
            if today_sales:
                metrics['today_revenue'] = float(today_sales[0][0] or 0)
                metrics['today_transactions'] = int(today_sales[0][1] or 0)
            
            # Weekly comparison with proper joins
            weekly_sales = self.db.execute_query("""
                SELECT 
                    COALESCE(SUM(te.Price * te.Quantity), 0) as WeekRevenue,
                    COUNT(DISTINCT t.TransactionNumber) as WeekTransactions
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE t.Time >= DATEADD(week, -1, GETDATE())
            """)
            
            if weekly_sales:
                metrics['week_revenue'] = float(weekly_sales[0][0] or 0)
                metrics['week_transactions'] = int(weekly_sales[0][1] or 0)
            
            # Top items with proper schema
            top_items = self.db.execute_query("""
                SELECT TOP 5
                    i.Description,
                    SUM(te.Quantity) as TotalQuantity
                FROM dbo.TransactionEntry te
                JOIN dbo.Item i ON te.ItemID = i.ID
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= DATEADD(week, -1, GETDATE())
                GROUP BY i.ID, i.Description
                ORDER BY TotalQuantity DESC
            """)
            
            metrics['top_items'] = [{'name': item[0], 'quantity': int(item[1])} for item in top_items]
            
            # Customer count using proper Customer.ID
            customer_count = self.db.execute_query("""
                SELECT COUNT(DISTINCT ID) FROM dbo.Customer
            """)
            
            if customer_count:
                metrics['total_customers'] = int(customer_count[0][0] or 0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {}
    
    def get_sales_trends(self, days: int = 30) -> List[Dict]:
        """Get sales trend data with proper schema"""
        try:
            query = f"""
                SELECT 
                    CAST(t.Time as DATE) as Date,
                    SUM(te.Price * te.Quantity) as Revenue,
                    COUNT(DISTINCT t.TransactionNumber) as Transactions
                FROM [dbo].[Transaction] t
                JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
                WHERE t.Time >= DATEADD(day, -{days}, GETDATE())
                GROUP BY CAST(t.Time as DATE)
                ORDER BY Date
            """
            
            results = self.db.execute_query(query)
            
            return [
                {
                    'date': str(row[0]),
                    'revenue': float(row[1] or 0),
                    'transactions': int(row[2] or 0)
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get sales trends: {e}")
            return []
    
    def get_business_insights(self) -> Dict[str, Any]:
        """Get advanced business insights"""
        try:
            insights = {}
            
            # Tobacco category performance with uplifts
            tobacco_performance = self.db.execute_query("""
                SELECT 
                    cat.Name as CategoryName,
                    SUM(te.Quantity) as TotalQuantity,
                    SUM(te.Price * te.Quantity) as Revenue,
                    SUM(
                        CASE 
                            WHEN cat.ID = 23 THEN te.Cost * 1.23 * te.Quantity  -- CIGARS +23%
                            WHEN cat.ID = 49 THEN te.Cost * 1.10 * te.Quantity  -- LT-TAX-COLLECTED +10%
                            ELSE te.Cost * te.Quantity 
                        END
                    ) as AdjustedCost
                FROM dbo.TransactionEntry te
                JOIN dbo.Item i ON te.ItemID = i.ID
                JOIN dbo.Category cat ON i.CategoryID = cat.ID
                JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE cat.Name LIKE '%CIG%' OR cat.Name LIKE '%TOB%'
                  AND t.Time >= DATEADD(month, -1, GETDATE())
                GROUP BY cat.ID, cat.Name
                ORDER BY Revenue DESC
            """)
            
            insights['tobacco_categories'] = [
                {
                    'category': row[0],
                    'quantity': int(row[1]),
                    'revenue': float(row[2] or 0),
                    'adjusted_cost': float(row[3] or 0)
                }
                for row in tobacco_performance
            ]
            
            # Customer activity analysis
            customer_activity = self.db.execute_query("""
                SELECT 
                    COUNT(DISTINCT c.ID) as TotalCustomers,
                    COUNT(DISTINCT CASE WHEN c.LastVisit >= DATEADD(month, -1, GETDATE()) THEN c.ID END) as ActiveCustomers,
                    AVG(c.TotalSales) as AvgLifetimeValue,
                    SUM(c.AccountBalance) as TotalAR
                FROM dbo.Customer c
            """)
            
            if customer_activity:
                row = customer_activity[0]
                insights['customer_metrics'] = {
                    'total_customers': int(row[0] or 0),
                    'active_customers': int(row[1] or 0),
                    'avg_lifetime_value': float(row[2] or 0),
                    'total_ar_balance': float(row[3] or 0)
                }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get business insights: {e}")
            return {}

# Flask Application
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Global instances
db_manager = None
query_processor = None
analytics_engine = None

def initialize_app():
    """Initialize application components"""
    global db_manager, query_processor, analytics_engine
    
    if db_manager is None:
        db_manager = DatabaseManager()
        success = db_manager.connect()
        
        if success:
            query_processor = EnhancedAIQueryProcessor(db_manager)
            analytics_engine = AnalyticsEngine(db_manager)
            logger.info("AI Assistant v2 initialized successfully")
        else:
            logger.error("Failed to connect to any database")
        
        return success
    return True

def get_db_manager():
    """Get database manager, initializing if needed"""
    if db_manager is None:
        initialize_app()
    return db_manager

def get_query_processor():
    """Get query processor, initializing if needed"""
    if query_processor is None:
        initialize_app()
    return query_processor

def get_analytics_engine():
    """Get analytics engine, initializing if needed"""
    if analytics_engine is None:
        initialize_app()
    return analytics_engine

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('ai_assistant_v2.html')

@app.route('/api/query', methods=['POST'])
def handle_query():
    """Handle natural language queries"""
    try:
        data = request.get_json()
        user_query = data.get('query', '').strip()
        
        if not user_query:
            return jsonify({'error': 'Query cannot be empty'})
        
        # Get query processor
        processor = get_query_processor()
        if not processor:
            return jsonify({'error': 'Database not connected'})
        
        # Process query
        result = processor.process_query(user_query)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Query handling failed: {e}")
        return jsonify({'error': 'Internal server error'})

@app.route('/api/metrics')
def get_metrics():
    """Get dashboard metrics"""
    try:
        engine = get_analytics_engine()
        if not engine:
            return jsonify({'error': 'Database not connected'})
        
        metrics = engine.get_dashboard_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        return jsonify({'error': 'Failed to retrieve metrics'})

@app.route('/api/trends')
def get_trends():
    """Get sales trends"""
    try:
        engine = get_analytics_engine()
        if not engine:
            return jsonify({'error': 'Database not connected'})
        
        days = request.args.get('days', 30, type=int)
        trends = engine.get_sales_trends(days)
        return jsonify(trends)
    except Exception as e:
        logger.error(f"Trends retrieval failed: {e}")
        return jsonify({'error': 'Failed to retrieve trends'})

@app.route('/api/insights')
def get_insights():
    """Get business insights"""
    try:
        engine = get_analytics_engine()
        if not engine:
            return jsonify({'error': 'Database not connected'})
        
        insights = engine.get_business_insights()
        return jsonify(insights)
    except Exception as e:
        logger.error(f"Insights retrieval failed: {e}")
        return jsonify({'error': 'Failed to retrieve insights'})

@app.route('/api/schema')
def get_schema_info():
    """Get database schema information"""
    try:
        processor = get_query_processor()
        if not processor:
            return jsonify({'error': 'Database not connected'})
        
        schema_info = {
            'tables': list(processor.schema_manager.schema['tables'].keys()),
            'business_rules': processor.schema_manager.business_rules,
            'constraints': processor.schema_manager.schema['sql_server_constraints']
        }
        
        return jsonify(schema_info)
    except Exception as e:
        logger.error(f"Schema info retrieval failed: {e}")
        return jsonify({'error': 'Failed to retrieve schema information'})

@app.route('/api/status')
def get_status():
    """Get system status"""
    db = get_db_manager()
    return jsonify({
        'database_connected': db is not None and db.connection is not None,
        'database_type': 'SQL Server' if (db and db.is_primary) else 'SQLite Backup' if db else 'Not Connected',
        'schema_loaded': query_processor is not None,
        'business_rules_loaded': query_processor is not None and len(query_processor.schema_manager.business_rules) > 0,
        'timestamp': datetime.now().isoformat()
    })

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = get_db_manager()
    if db and hasattr(db, 'connection') and db.connection:
        db.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 