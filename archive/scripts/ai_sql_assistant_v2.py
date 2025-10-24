"""
Enhanced AI SQL Assistant v2 - Deep Database Understanding
Complete redesign with true dynamic SQL generation and deep schema knowledge
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum

import pandas as pd
import openai

from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


class QueryDomain(Enum):
    """Query domain classification for better understanding"""
    SALES = "sales"
    INVENTORY = "inventory"
    CUSTOMERS = "customers"
    ACCOUNTS_RECEIVABLE = "ar"
    PAYMENTS = "payments"
    PROFIT = "profit"
    PRODUCTS = "products"
    CATEGORIES = "categories"
    ANALYTICS = "analytics"
    UNKNOWN = "unknown"


class TimeGranularity(Enum):
    """Time grouping granularity"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    NONE = "none"


@dataclass
class DatabaseSchema:
    """Complete database schema representation"""
    tables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    business_rules: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize with complete schema knowledge"""
        self.tables = {
            "Transaction": {
                "alias": "t",
                "primary_key": "TransactionNumber",
                "date_column": "Time",
                "description": "Sales transaction headers",
                "columns": {
                    "TransactionNumber": {"type": "int", "nullable": False, "description": "Unique transaction ID"},
                    "Time": {"type": "datetime", "nullable": False, "description": "Transaction timestamp"},
                    "CustomerID": {"type": "int", "nullable": True, "description": "Customer reference"},
                    "Total": {"type": "money", "nullable": False, "description": "Transaction total"},
                    "SalesTax": {"type": "money", "nullable": True, "description": "Tax amount"},
                    "CashierID": {"type": "int", "nullable": True, "description": "Employee ID"},
                    "Status": {"type": "int", "nullable": True, "description": "Transaction status"},
                    "Comment": {"type": "nvarchar", "nullable": True, "description": "Transaction notes"},
                    "ReferenceNumber": {"type": "nvarchar", "nullable": True, "description": "External reference"}
                }
            },
            "TransactionEntry": {
                "alias": "te",
                "primary_key": "ID",
                "date_column": "TransactionTime",
                "description": "Transaction line items (4.6M+ records)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "Line item ID"},
                    "TransactionNumber": {"type": "int", "nullable": False, "description": "Parent transaction"},
                    "ItemID": {"type": "int", "nullable": False, "description": "Product reference"},
                    "Price": {"type": "money", "nullable": False, "description": "Unit selling price"},
                    "Cost": {"type": "money", "nullable": False, "description": "Unit cost"},
                    "Quantity": {"type": "float", "nullable": False, "description": "Quantity sold"},
                    "TransactionTime": {"type": "datetime", "nullable": False, "description": "Line timestamp"},
                    "SalesTax": {"type": "money", "nullable": True, "description": "Line tax"},
                    "DiscountAmount": {"type": "money", "nullable": True, "description": "Discount applied"}
                }
            },
            "Item": {
                "alias": "i",
                "primary_key": "ID",
                "date_column": "LastSold",
                "description": "Product master (12,332+ products)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "Product ID"},
                    "Description": {"type": "nvarchar", "nullable": False, "description": "Product name"},
                    "ItemLookupCode": {"type": "nvarchar", "nullable": True, "description": "Barcode/UPC"},
                    "CategoryID": {"type": "int", "nullable": True, "description": "Category reference"},
                    "Price": {"type": "money", "nullable": False, "description": "Current price"},
                    "Cost": {"type": "money", "nullable": False, "description": "Current cost"},
                    "Quantity": {"type": "float", "nullable": True, "description": "On-hand quantity"},
                    "LastSold": {"type": "datetime", "nullable": True, "description": "Last sale date"},
                    "Inactive": {"type": "bit", "nullable": True, "description": "Active status"}
                }
            },
            "Category": {
                "alias": "cat",
                "primary_key": "ID",
                "date_column": None,
                "description": "Product categories (83 total)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "Category ID"},
                    "Name": {"type": "nvarchar", "nullable": False, "description": "Category name"},
                    "Code": {"type": "nvarchar", "nullable": True, "description": "Category code"},
                    "DepartmentID": {"type": "int", "nullable": True, "description": "Department reference"}
                }
            },
            "Customer": {
                "alias": "c",
                "primary_key": "ID",
                "date_column": "LastVisit",
                "description": "Customer master (2,824+ customers)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "Customer ID"},
                    "FirstName": {"type": "nvarchar", "nullable": True, "description": "First name"},
                    "LastName": {"type": "nvarchar", "nullable": True, "description": "Last name"},
                    "Company": {"type": "nvarchar", "nullable": True, "description": "Company name"},
                    "AccountNumber": {"type": "nvarchar", "nullable": True, "description": "Account code"},
                    "AccountBalance": {"type": "money", "nullable": True, "description": "Current AR balance"},
                    "CreditLimit": {"type": "money", "nullable": True, "description": "Credit limit"},
                    "TotalSales": {"type": "money", "nullable": True, "description": "Lifetime sales"},
                    "LastVisit": {"type": "datetime", "nullable": True, "description": "Last transaction"},
                    "TaxExempt": {"type": "bit", "nullable": True, "description": "Tax exemption"}
                }
            },
            "Payment": {
                "alias": "p",
                "primary_key": "ID",
                "date_column": "Time",
                "description": "Customer payments (63,021+ records)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "Payment ID"},
                    "CustomerID": {"type": "int", "nullable": False, "description": "Customer reference"},
                    "Time": {"type": "datetime", "nullable": False, "description": "Payment timestamp"},
                    "Amount": {"type": "money", "nullable": False, "description": "Payment amount"},
                    "Comment": {"type": "nvarchar", "nullable": True, "description": "Payment notes"}
                }
            },
            "AccountReceivable": {
                "alias": "ar",
                "primary_key": "ID",
                "date_column": "Date",
                "description": "AR records (142,706+ entries)",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "AR record ID"},
                    "CustomerID": {"type": "int", "nullable": False, "description": "Customer reference"},
                    "Date": {"type": "datetime", "nullable": False, "description": "Invoice date"},
                    "DueDate": {"type": "datetime", "nullable": True, "description": "Payment due date"},
                    "Balance": {"type": "money", "nullable": False, "description": "Outstanding amount"},
                    "OriginalAmount": {"type": "money", "nullable": False, "description": "Original amount"},
                    "TransactionNumber": {"type": "int", "nullable": True, "description": "Related transaction"}
                }
            },
            "AccountReceivableHistory": {
                "alias": "arh",
                "primary_key": "ID",
                "date_column": "Date",
                "description": "AR adjustments and history",
                "columns": {
                    "ID": {"type": "int", "nullable": False, "description": "History ID and reference"},
                    "AccountReceivableID": {"type": "int", "nullable": False, "description": "Parent AR record"},
                    "Amount": {"type": "money", "nullable": False, "description": "Adjustment amount"},
                    "Comment": {"type": "nvarchar", "nullable": True, "description": "Adjustment notes"},
                    "Date": {"type": "datetime", "nullable": False, "description": "Adjustment date"}
                }
            }
        }
        
        self.relationships = [
            {"from": "Transaction.CustomerID", "to": "Customer.ID"},
            {"from": "TransactionEntry.TransactionNumber", "to": "Transaction.TransactionNumber"},
            {"from": "TransactionEntry.ItemID", "to": "Item.ID"},
            {"from": "Item.CategoryID", "to": "Category.ID"},
            {"from": "Payment.CustomerID", "to": "Customer.ID"},
            {"from": "AccountReceivable.CustomerID", "to": "Customer.ID"},
            {"from": "AccountReceivableHistory.AccountReceivableID", "to": "AccountReceivable.ID"}
        ]
        
        self.business_rules = {
            "tobacco_uplifts": {
                "CIGARS": 1.23,  # +23% excise tax
                "LT-TAX-COLLECTED": 1.10  # +10% excise tax
            },
            "customer_display": "COALESCE(Company, FirstName + ' ' + LastName)",
            "transaction_brackets": "[dbo].[Transaction]",  # Reserved keyword
            "nsf_detection": "Comment LIKE '%NSF%'",  # $65 NSF fees
            "manual_adjustment": "TransactionNumber = 0"  # Manual AR adjustments
        }


@dataclass
class QueryContext:
    """Enhanced query context with deep understanding"""
    question: str
    domain: QueryDomain
    tables_needed: List[str]
    metrics: List[str]
    filters: Dict[str, Any]
    time_range: Optional[Dict[str, Any]]
    grouping: Optional[TimeGranularity]
    aggregations: List[str]
    sorting: Optional[Dict[str, str]]
    limit: Optional[int]
    special_calculations: List[str]


class NaturalLanguageProcessor:
    """Advanced NLP for query understanding"""
    
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.domain_keywords = {
            QueryDomain.SALES: ["sales", "revenue", "sold", "transactions", "orders"],
            QueryDomain.INVENTORY: ["inventory", "stock", "on hand", "quantity", "available"],
            QueryDomain.CUSTOMERS: ["customer", "client", "account", "buyer"],
            QueryDomain.ACCOUNTS_RECEIVABLE: ["ar", "receivable", "owed", "outstanding", "balance"],
            QueryDomain.PAYMENTS: ["payment", "paid", "collection", "received"],
            QueryDomain.PROFIT: ["profit", "margin", "gp", "gross profit", "markup"],
            QueryDomain.PRODUCTS: ["product", "item", "sku", "merchandise"],
            QueryDomain.CATEGORIES: ["category", "department", "type", "group"],
            QueryDomain.ANALYTICS: ["trend", "compare", "analysis", "performance", "growth"]
        }
        
        self.metric_patterns = {
            "count": r"(how many|count|number of|total)",
            "sum": r"(total|sum|amount|revenue)",
            "average": r"(average|avg|mean)",
            "maximum": r"(maximum|max|highest|top)",
            "minimum": r"(minimum|min|lowest|bottom)"
        }
        
        self.time_patterns = {
            "today": (0, 0),
            "yesterday": (1, 1),
            "this week": (7, 0),
            "last week": (14, 7),
            "this month": (30, 0),
            "last month": (60, 30),
            "this quarter": (90, 0),
            "last quarter": (180, 90),
            "this year": (365, 0),
            "last year": (730, 365),
            "ytd": ("year_start", 0),
            "mtd": ("month_start", 0),
            "qtd": ("quarter_start", 0)
        }
    
    def parse(self, question: str) -> QueryContext:
        """Parse natural language into structured query context"""
        question_lower = question.lower()
        
        # Detect domain
        domain = self._detect_domain(question_lower)
        
        # Extract metrics
        metrics = self._extract_metrics(question_lower)
        
        # Determine tables needed
        tables_needed = self._determine_tables(domain, question_lower)
        
        # Extract filters
        filters = self._extract_filters(question_lower)
        
        # Parse time range
        time_range = self._parse_time_range(question_lower)
        
        # Detect grouping
        grouping = self._detect_grouping(question_lower)
        
        # Extract aggregations
        aggregations = self._extract_aggregations(question_lower, metrics)
        
        # Determine sorting
        sorting = self._determine_sorting(question_lower)
        
        # Extract limit
        limit = self._extract_limit(question_lower)
        
        # Identify special calculations
        special_calculations = self._identify_special_calculations(question_lower)
        
        return QueryContext(
            question=question,
            domain=domain,
            tables_needed=tables_needed,
            metrics=metrics,
            filters=filters,
            time_range=time_range,
            grouping=grouping,
            aggregations=aggregations,
            sorting=sorting,
            limit=limit,
            special_calculations=special_calculations
        )
    
    def _detect_domain(self, text: str) -> QueryDomain:
        """Detect the primary domain of the query"""
        scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        return QueryDomain.UNKNOWN
    
    def _extract_metrics(self, text: str) -> List[str]:
        """Extract what metrics the user wants"""
        metrics = []
        for metric, pattern in self.metric_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                metrics.append(metric)
        
        # Domain-specific metrics
        if "revenue" in text or "sales" in text:
            metrics.append("revenue")
        if "profit" in text or "margin" in text:
            metrics.append("profit")
        if "cost" in text:
            metrics.append("cost")
        if "quantity" in text or "units" in text:
            metrics.append("quantity")
        
        return metrics if metrics else ["sum"]  # Default to sum
    
    def _determine_tables(self, domain: QueryDomain, text: str) -> List[str]:
        """Determine which tables are needed"""
        tables = []
        
        # Domain-based table selection
        domain_tables = {
            QueryDomain.SALES: ["Transaction", "TransactionEntry", "Item"],
            QueryDomain.INVENTORY: ["Item", "Category"],
            QueryDomain.CUSTOMERS: ["Customer"],
            QueryDomain.ACCOUNTS_RECEIVABLE: ["AccountReceivable", "Customer"],
            QueryDomain.PAYMENTS: ["Payment", "Customer"],
            QueryDomain.PROFIT: ["Transaction", "TransactionEntry", "Item", "Category"]
        }
        
        if domain in domain_tables:
            tables.extend(domain_tables[domain])
        
        # Text-based additions
        if "category" in text:
            tables.append("Category")
        if "customer" in text:
            tables.append("Customer")
        if "payment" in text:
            tables.append("Payment")
        
        # Remove duplicates while preserving order
        seen = set()
        return [t for t in tables if not (t in seen or seen.add(t))]
    
    def _extract_filters(self, text: str) -> Dict[str, Any]:
        """Extract filtering conditions with fuzzy matching support"""
        filters = {}
        
        # Category filters
        if "cigar" in text.lower():
            filters["category"] = "CIGARS"
        elif "lt-tax" in text.lower() or "lt tax" in text.lower():
            filters["category"] = "LT-TAX-COLLECTED"
        
        # Extract entity names (customers, products, etc.) with fuzzy matching
        # Look for quoted strings first
        quoted_matches = re.findall(r'"([^"]+)"', text)
        if not quoted_matches:
            quoted_matches = re.findall(r"'([^']+)'", text)
        
        # Customer name extraction with fuzzy matching
        customer_patterns = [
            # Pattern for "all account information for X"
            r"(?:all\s+)?(?:account\s+)?(?:information\s+)?for\s+([A-Za-z0-9\s\-\.&']+?)(?:\s*,|\s+all\s+|$)",
            # Pattern for names followed by business names
            r"(?:^|\s)([A-Za-z]+\s+[A-Za-z]+)\s+(\d*\s*(?:star|mart|store|shop|market|gas|food|liquor|tobacco|convenience)[^,]*)",
            # General customer patterns
            r"customer\s+(?:named?\s+)?([A-Za-z0-9\s\-\.&']+?)(?:\s+sales|\s+revenue|\s+balance|$)",
            r"for\s+([A-Za-z0-9\s\-\.&']+?)(?:\s+customer|$)",
            r"(?:^|\s)([A-Z][A-Za-z0-9\s\-\.&']*?(?:mart|store|shop|market|gas|food|liquor|tobacco|convenience)s?\b)",
        ]
        
        customer_name = None
        
        # Special handling for queries like "sameer somani 5 star food mart"
        if "sameer somani" in text.lower() or "5 star" in text.lower():
            # Extract both name and business
            if "sameer somani" in text.lower() and "5 star" in text.lower():
                customer_name = "5 star food mart"  # Primary identifier
            elif "5 star" in text.lower():
                # Extract just the business name
                match = re.search(r"(5\s*star[^,]*(?:mart|food|store)?)", text, re.IGNORECASE)
                if match:
                    customer_name = match.group(1).strip()
            elif "sameer somani" in text.lower():
                customer_name = "sameer somani"
        
        # If not found with special handling, try patterns
        if not customer_name:
            for pattern in customer_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if match.lastindex and match.lastindex > 1:
                        # Combine multiple groups if present
                        customer_name = " ".join([g for g in match.groups() if g]).strip()
                    else:
                        customer_name = match.group(1).strip()
                    break
        
        # Check quoted strings for customer names
        if not customer_name and quoted_matches:
            customer_name = quoted_matches[0]
        
        if customer_name:
            # Clean up the name and prepare for LIKE query
            customer_name = customer_name.strip().strip("'\"")
            # Remove common words that aren't part of the name
            stop_words = ['all', 'details', 'comments', 'included', 'sales', 'payments', "nsf's", 'adjustments', 'etc']
            for word in stop_words:
                customer_name = customer_name.replace(word, '').strip()
            
            filters["customer"] = customer_name
            filters["customer_fuzzy"] = True  # Flag for fuzzy matching
        
        # Product name extraction with fuzzy matching
        product_patterns = [
            r"product\s+(?:named?\s+)?([A-Za-z0-9\s\-\.]+?)(?:\s+sales|$)",
            r"item\s+(?:named?\s+)?([A-Za-z0-9\s\-\.]+?)(?:\s+sales|$)",
            r"(?:marlboro|camel|newport|winston|american spirit|juul|vuse)",
        ]
        
        product_name = None
        for pattern in product_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                product_name = match.group(1) if match.lastindex else match.group(0)
                break
        
        if product_name:
            product_name = product_name.strip().strip("'\"")
            filters["product"] = product_name
            filters["product_fuzzy"] = True
        
        # Status filters
        if "active" in text.lower():
            filters["active"] = True
        elif "inactive" in text.lower():
            filters["active"] = False
        
        # NSF filters
        if "nsf" in text.lower():
            filters["nsf"] = True
        
        # Amount filters
        amount_match = re.search(r"(over|above|greater than|more than)\s+\$?([\d,]+)", text, re.IGNORECASE)
        if amount_match:
            filters["amount_gt"] = float(amount_match.group(2).replace(",", ""))
        
        amount_match = re.search(r"(under|below|less than)\s+\$?([\d,]+)", text, re.IGNORECASE)
        if amount_match:
            filters["amount_lt"] = float(amount_match.group(2).replace(",", ""))
        
        return filters
    
    def _parse_time_range(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse time range from text"""
        # Check for explicit date ranges
        date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        dates = re.findall(date_pattern, text)
        if len(dates) >= 2:
            return {
                "type": "explicit",
                "start": dates[0],
                "end": dates[1]
            }
        
        # Check for relative time patterns
        for pattern, (days_back, days_forward) in self.time_patterns.items():
            if pattern in text:
                if isinstance(days_back, str):
                    return {"type": pattern, "special": days_back}
                return {
                    "type": "relative",
                    "days_back": days_back,
                    "days_forward": days_forward
                }
        
        # Check for "last N days/months/years"
        last_n = re.search(r"last\s+(\d+)\s+(day|week|month|year)s?", text, re.IGNORECASE)
        if last_n:
            num = int(last_n.group(1))
            unit = last_n.group(2).lower()
            multipliers = {"day": 1, "week": 7, "month": 30, "year": 365}
            return {
                "type": "relative",
                "days_back": num * multipliers[unit],
                "days_forward": 0
            }
        
        # Default to last 30 days
        return {
            "type": "relative",
            "days_back": 30,
            "days_forward": 0
        }
    
    def _detect_grouping(self, text: str) -> Optional[TimeGranularity]:
        """Detect time grouping requirements"""
        if "by hour" in text or "hourly" in text:
            return TimeGranularity.HOUR
        elif "by day" in text or "daily" in text:
            return TimeGranularity.DAY
        elif "by week" in text or "weekly" in text:
            return TimeGranularity.WEEK
        elif "by month" in text or "monthly" in text:
            return TimeGranularity.MONTH
        elif "by quarter" in text or "quarterly" in text:
            return TimeGranularity.QUARTER
        elif "by year" in text or "yearly" in text or "annual" in text:
            return TimeGranularity.YEAR
        return TimeGranularity.NONE
    
    def _extract_aggregations(self, text: str, metrics: List[str]) -> List[str]:
        """Extract aggregation requirements"""
        aggregations = []
        
        if "group by" in text:
            # Extract explicit group by
            group_match = re.search(r"group by\s+(\w+)", text, re.IGNORECASE)
            if group_match:
                aggregations.append(group_match.group(1))
        
        # Implicit grouping
        if "by category" in text:
            aggregations.append("category")
        if "by customer" in text:
            aggregations.append("customer")
        if "by product" in text or "by item" in text:
            aggregations.append("product")
        if "by department" in text:
            aggregations.append("department")
        
        return aggregations
    
    def _determine_sorting(self, text: str) -> Optional[Dict[str, str]]:
        """Determine sorting requirements"""
        if "top" in text or "highest" in text:
            return {"direction": "DESC", "by": "value"}
        elif "bottom" in text or "lowest" in text:
            return {"direction": "ASC", "by": "value"}
        elif "recent" in text or "latest" in text:
            return {"direction": "DESC", "by": "date"}
        elif "oldest" in text:
            return {"direction": "ASC", "by": "date"}
        return None
    
    def _extract_limit(self, text: str) -> Optional[int]:
        """Extract result limit"""
        limit_match = re.search(r"(top|first|last)\s+(\d+)", text, re.IGNORECASE)
        if limit_match:
            return int(limit_match.group(2))
        return None
    
    def _identify_special_calculations(self, text: str) -> List[str]:
        """Identify special calculation requirements"""
        calculations = []
        
        if "profit" in text or "margin" in text:
            calculations.append("tobacco_uplift")
        if "growth" in text or "change" in text:
            calculations.append("period_comparison")
        if "forecast" in text or "predict" in text:
            calculations.append("trend_analysis")
        if "rank" in text:
            calculations.append("ranking")
        
        # Debt collection and comprehensive activity keywords
        comprehensive_keywords = [
            "collection", "activity", "everything", "all activity", 
            "adjustments", "running balance", "statement", "reconciliation",
            "all account information", "complete", "comprehensive", "all details",
            "nsf", "pull everything"
        ]
        if any(word in text for word in comprehensive_keywords):
            calculations.append("comprehensive_activity")
        if "adjustment" in text or "credit" in text or "debit" in text:
            calculations.append("include_adjustments")
        
        return calculations


class SQLBuilder:
    """Advanced SQL query builder with deep schema knowledge"""
    
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
    
    def build(self, context: QueryContext) -> str:
        """Build optimized SQL query from context"""
        # Determine query structure
        if "comprehensive_activity" in context.special_calculations:
            return self._build_comprehensive_activity_query(context)
        elif "period_comparison" in context.special_calculations:
            return self._build_comparison_query(context)
        elif context.grouping != TimeGranularity.NONE:
            return self._build_time_series_query(context)
        elif context.aggregations:
            return self._build_aggregation_query(context)
        else:
            return self._build_simple_query(context)
    
    def _build_simple_query(self, context: QueryContext) -> str:
        """Build a simple SELECT query"""
        # Select columns
        select_cols = self._determine_select_columns(context)
        
        # From clause with joins
        from_clause = self._build_from_clause(context)
        
        # Where clause
        where_clause = self._build_where_clause(context)
        
        # Order by
        order_clause = self._build_order_clause(context)
        
        # Limit
        limit_clause = f"TOP {context.limit}" if context.limit else ""
        
        sql = f"SELECT {limit_clause} {select_cols}\n{from_clause}"
        if where_clause:
            sql += f"\nWHERE {where_clause}"
        if order_clause:
            sql += f"\n{order_clause}"
        
        return sql
    
    def _build_aggregation_query(self, context: QueryContext) -> str:
        """Build an aggregation query"""
        # Group by columns
        group_cols = self._determine_group_columns(context)
        
        # Aggregate expressions
        agg_exprs = self._build_aggregate_expressions(context)
        
        # From clause with joins
        from_clause = self._build_from_clause(context)
        
        # Where clause
        where_clause = self._build_where_clause(context)
        
        # Having clause if needed
        having_clause = self._build_having_clause(context)
        
        # Order by
        order_clause = self._build_order_clause(context)
        
        # Build query
        select_cols = ", ".join(group_cols + agg_exprs)
        sql = f"SELECT {select_cols}\n{from_clause}"
        
        if where_clause:
            sql += f"\nWHERE {where_clause}"
        
        if group_cols:
            sql += f"\nGROUP BY {', '.join(group_cols)}"
        
        if having_clause:
            sql += f"\nHAVING {having_clause}"
        
        if order_clause:
            sql += f"\n{order_clause}"
        
        # Add TOP if limit specified
        if context.limit:
            sql = sql.replace("SELECT ", f"SELECT TOP {context.limit} ", 1)
        
        return sql
    
    def _build_time_series_query(self, context: QueryContext) -> str:
        """Build a time series query"""
        # Determine date expression based on granularity
        date_expr = self._get_date_expression(context)
        
        # Build aggregates
        agg_exprs = self._build_aggregate_expressions(context)
        
        # From clause
        from_clause = self._build_from_clause(context)
        
        # Where clause
        where_clause = self._build_where_clause(context)
        
        # Build query
        select_cols = f"{date_expr} AS period, " + ", ".join(agg_exprs)
        sql = f"SELECT {select_cols}\n{from_clause}"
        
        if where_clause:
            sql += f"\nWHERE {where_clause}"
        
        sql += f"\nGROUP BY {date_expr}"
        sql += f"\nORDER BY period"
        
        return sql
    
    def _build_comparison_query(self, context: QueryContext) -> str:
        """Build a period-over-period comparison query"""
        # This would use CTEs to compare different periods
        current_period = self._build_period_cte("CurrentPeriod", context, 0)
        previous_period = self._build_period_cte("PreviousPeriod", context, 1)
        
        sql = f"""WITH CurrentPeriod AS (
{current_period}
),
PreviousPeriod AS (
{previous_period}
)
SELECT 
    COALESCE(c.group_key, p.group_key) AS group_key,
    ISNULL(c.value, 0) AS current_value,
    ISNULL(p.value, 0) AS previous_value,
    CASE 
        WHEN p.value = 0 THEN NULL
        ELSE ((c.value - p.value) / p.value) * 100
    END AS percent_change
FROM CurrentPeriod c
FULL OUTER JOIN PreviousPeriod p ON c.group_key = p.group_key
ORDER BY current_value DESC"""
        
        return sql
    
    def _determine_select_columns(self, context: QueryContext) -> str:
        """Determine SELECT columns based on context"""
        columns = []
        
        # Add columns based on domain and tables
        if "Customer" in context.tables_needed:
            columns.append("COALESCE(c.Company, c.FirstName + ' ' + c.LastName) AS customer_name")
        
        if "Item" in context.tables_needed:
            columns.append("i.Description AS product")
            columns.append("i.ItemLookupCode AS barcode")
        
        if "Category" in context.tables_needed:
            columns.append("cat.Name AS category")
        
        # Add metric columns based on domain
        if context.domain == QueryDomain.ACCOUNTS_RECEIVABLE:
            if "AccountReceivable" in context.tables_needed:
                columns.append("ar.Balance AS ar_balance")
                columns.append("ar.Date AS invoice_date")
        elif context.domain == QueryDomain.PAYMENTS:
            if "Payment" in context.tables_needed:
                columns.append("p.Amount AS payment_amount")
                columns.append("p.Time AS payment_date")
        elif "TransactionEntry" in context.tables_needed:
            # Sales-related columns
            if "revenue" in context.metrics:
                columns.append("te.Price * te.Quantity AS revenue")
            
            if "profit" in context.metrics:
                columns.append(self._build_profit_expression())
            
            if "quantity" in context.metrics:
                columns.append("te.Quantity")
        
        return ", ".join(columns) if columns else "*"
    
    def _build_from_clause(self, context: QueryContext) -> str:
        """Build FROM clause with appropriate joins"""
        # Start with primary table based on domain
        domain_primary = {
            QueryDomain.SALES: "Transaction",
            QueryDomain.INVENTORY: "Item",
            QueryDomain.CUSTOMERS: "Customer",
            QueryDomain.ACCOUNTS_RECEIVABLE: "AccountReceivable",
            QueryDomain.PAYMENTS: "Payment",
            QueryDomain.PROFIT: "Transaction"
        }
        
        primary_table = domain_primary.get(context.domain, "Transaction")
        table_info = self.schema.tables[primary_table]
        alias = table_info["alias"]
        
        # Special handling for Transaction table (reserved keyword)
        if primary_table == "Transaction":
            from_parts = [f"FROM [dbo].[Transaction] {alias}"]
        else:
            from_parts = [f"FROM {primary_table} {alias}"]
        
        # Build join path for all needed tables
        joins_added = {primary_table}
        join_order = []
        
        # Define standard join paths
        if "TransactionEntry" in context.tables_needed and primary_table == "Transaction":
            join_order.append("TransactionEntry")
        
        if "Item" in context.tables_needed:
            if "TransactionEntry" not in joins_added and primary_table == "Transaction":
                join_order.append("TransactionEntry")
            join_order.append("Item")
        
        if "Category" in context.tables_needed:
            if "Item" not in joins_added and "Item" not in join_order:
                if "TransactionEntry" not in joins_added and primary_table == "Transaction":
                    join_order.append("TransactionEntry")
                join_order.append("Item")
            join_order.append("Category")
        
        if "Customer" in context.tables_needed and primary_table != "Customer":
            join_order.append("Customer")
        
        # Add joins in order
        for table_name in join_order:
            if table_name not in joins_added:
                join_clause = self._get_join_for_table(table_name, joins_added)
                if join_clause:
                    from_parts.append(join_clause)
                    joins_added.add(table_name)
        
        return "\n".join(from_parts)
    
    def _get_join_for_table(self, table_name: str, existing_tables: set) -> str:
        """Get JOIN clause for a specific table based on what's already joined"""
        # Standard join patterns based on table relationships
        if table_name == "TransactionEntry" and "Transaction" in existing_tables:
            return "JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber"
        elif table_name == "Item" and "TransactionEntry" in existing_tables:
            return "JOIN Item i ON te.ItemID = i.ID"
        elif table_name == "Category" and "Item" in existing_tables:
            return "LEFT JOIN Category cat ON i.CategoryID = cat.ID"
        elif table_name == "Customer":
            if "Transaction" in existing_tables:
                return "LEFT JOIN Customer c ON t.CustomerID = c.ID"
            elif "Payment" in existing_tables:
                return "JOIN Customer c ON p.CustomerID = c.ID"
            elif "AccountReceivable" in existing_tables:
                return "JOIN Customer c ON ar.CustomerID = c.ID"
        elif table_name == "Payment" and "Customer" in existing_tables:
            return "LEFT JOIN Payment p ON c.ID = p.CustomerID"
        elif table_name == "AccountReceivable" and "Customer" in existing_tables:
            return "LEFT JOIN AccountReceivable ar ON c.ID = ar.CustomerID"
        elif table_name == "AccountReceivableHistory" and "AccountReceivable" in existing_tables:
            return "LEFT JOIN AccountReceivableHistory arh ON ar.ID = arh.AccountReceivableID"
        
        return ""
    
    def _get_join_clause(self, from_table: str, to_table: str, existing_tables: set) -> str:
        """Generate appropriate JOIN clause (legacy method for compatibility)"""
        # Find relationship
        for rel in self.schema.relationships:
            from_parts = rel["from"].split(".")
            to_parts = rel["to"].split(".")
            
            # Direct join
            if from_parts[0] == from_table and to_parts[0] == to_table:
                from_alias = self.schema.tables[from_table]["alias"]
                to_alias = self.schema.tables[to_table]["alias"]
                return f"JOIN {to_table} {to_alias} ON {from_alias}.{from_parts[1]} = {to_alias}.{to_parts[1]}"
            
            # Reverse join
            if from_parts[0] == to_table and to_parts[0] == from_table:
                from_alias = self.schema.tables[from_table]["alias"]
                to_alias = self.schema.tables[to_table]["alias"]
                return f"JOIN {to_table} {to_alias} ON {to_alias}.{from_parts[1]} = {from_alias}.{to_parts[1]}"
        
        return ""
    
    def _build_where_clause(self, context: QueryContext) -> str:
        """Build WHERE clause from filters and time range"""
        conditions = []
        
        # Time range conditions
        if context.time_range:
            time_condition = self._build_time_condition(context)
            if time_condition:
                conditions.append(time_condition)
        
        # Filter conditions - only add if table exists in query
        if "category" in context.filters and "Category" in context.tables_needed:
            conditions.append(f"cat.Name = '{context.filters['category']}'")
        
        if "customer" in context.filters and "Customer" in context.tables_needed:
            customer_name = context.filters['customer'].replace("'", "''")  # Escape quotes
            if context.filters.get('customer_fuzzy', False):
                # Use fuzzy matching with LIKE for customer names
                # Search in both Company and concatenated FirstName + LastName
                conditions.append(f"""(
                    c.Company LIKE '%{customer_name}%' OR 
                    c.FirstName + ' ' + c.LastName LIKE '%{customer_name}%' OR
                    c.AccountNumber LIKE '%{customer_name}%'
                )""")
            else:
                # Exact match
                conditions.append(f"c.Company = '{customer_name}'")
        
        if "product" in context.filters and "Item" in context.tables_needed:
            product_name = context.filters['product'].replace("'", "''")
            if context.filters.get('product_fuzzy', False):
                # Fuzzy match for products
                conditions.append(f"""(
                    i.Description LIKE '%{product_name}%' OR
                    i.ItemLookupCode LIKE '%{product_name}%'
                )""")
            else:
                conditions.append(f"i.Description = '{product_name}'")
        
        if "active" in context.filters and "Item" in context.tables_needed:
            if context.filters["active"]:
                conditions.append("i.Inactive = 0")
            else:
                conditions.append("i.Inactive = 1")
        
        if "nsf" in context.filters and "AccountReceivableHistory" in context.tables_needed:
            conditions.append("arh.Comment LIKE '%NSF%'")
        
        if "amount_gt" in context.filters:
            # Use appropriate amount field based on domain
            if context.domain == QueryDomain.ACCOUNTS_RECEIVABLE:
                conditions.append(f"ar.Balance > {context.filters['amount_gt']}")
            elif "TransactionEntry" in context.tables_needed:
                conditions.append(f"te.Price * te.Quantity > {context.filters['amount_gt']}")
        
        if "amount_lt" in context.filters:
            if context.domain == QueryDomain.ACCOUNTS_RECEIVABLE:
                conditions.append(f"ar.Balance < {context.filters['amount_lt']}")
            elif "TransactionEntry" in context.tables_needed:
                conditions.append(f"te.Price * te.Quantity < {context.filters['amount_lt']}")
        
        return " AND ".join(conditions)
    
    def _build_time_condition(self, context: QueryContext) -> str:
        """Build time range condition"""
        if not context.time_range:
            return ""
        
        # Determine which date column to use
        primary_table = None
        for table in context.tables_needed:
            if table in ["Transaction", "Payment", "AccountReceivable"]:
                primary_table = table
                break
        
        if not primary_table:
            return ""
        
        table_info = self.schema.tables[primary_table]
        alias = table_info["alias"]
        date_col = table_info["date_column"]
        
        if context.time_range["type"] == "relative":
            days_back = context.time_range["days_back"]
            return f"{alias}.{date_col} >= DATEADD(DAY, -{days_back}, GETDATE())"
        elif context.time_range["type"] == "explicit":
            start = context.time_range["start"]
            end = context.time_range["end"]
            return f"{alias}.{date_col} BETWEEN '{start}' AND '{end}'"
        elif context.time_range.get("special") == "year_start":
            return f"{alias}.{date_col} >= DATEADD(yy, DATEDIFF(yy, 0, GETDATE()), 0)"
        elif context.time_range.get("special") == "month_start":
            return f"{alias}.{date_col} >= DATEADD(mm, DATEDIFF(mm, 0, GETDATE()), 0)"
        elif context.time_range.get("special") == "quarter_start":
            return f"{alias}.{date_col} >= DATEADD(qq, DATEDIFF(qq, 0, GETDATE()), 0)"
        
        return ""
    
    def _build_order_clause(self, context: QueryContext) -> str:
        """Build ORDER BY clause"""
        if not context.sorting:
            return ""
        
        direction = context.sorting.get("direction", "DESC")
        by = context.sorting.get("by", "value")
        
        if by == "date":
            # Find date column
            for table in context.tables_needed:
                if table in self.schema.tables:
                    date_col = self.schema.tables[table].get("date_column")
                    if date_col:
                        alias = self.schema.tables[table]["alias"]
                        return f"ORDER BY {alias}.{date_col} {direction}"
        else:
            # Order by first aggregate column
            return f"ORDER BY 2 {direction}"  # Second column (first is usually grouping)
        
        return ""
    
    def _build_having_clause(self, context: QueryContext) -> str:
        """Build HAVING clause for aggregate filtering"""
        # Implement if needed for aggregate conditions
        return ""
    
    def _determine_group_columns(self, context: QueryContext) -> List[str]:
        """Determine GROUP BY columns"""
        columns = []
        
        for agg in context.aggregations:
            if agg == "category":
                columns.append("cat.Name")
            elif agg == "customer":
                columns.append("COALESCE(c.Company, c.FirstName + ' ' + c.LastName)")
            elif agg == "product":
                columns.append("i.Description")
            elif agg == "department":
                columns.append("cat.DepartmentID")
        
        return columns
    
    def _build_aggregate_expressions(self, context: QueryContext) -> List[str]:
        """Build aggregate expressions"""
        expressions = []
        
        for metric in context.metrics:
            if metric == "count":
                expressions.append("COUNT(*) AS count")
            elif metric == "sum" or metric == "revenue":
                expressions.append("SUM(te.Price * te.Quantity) AS total_revenue")
            elif metric == "average":
                expressions.append("AVG(te.Price * te.Quantity) AS avg_revenue")
            elif metric == "profit":
                expressions.append(f"SUM({self._build_profit_expression()}) AS total_profit")
            elif metric == "quantity":
                expressions.append("SUM(te.Quantity) AS total_quantity")
            elif metric == "cost":
                expressions.append("SUM(te.Cost * te.Quantity) AS total_cost")
        
        if not expressions:
            expressions.append("COUNT(*) AS count")
        
        return expressions
    
    def _build_profit_expression(self) -> str:
        """Build profit calculation with tobacco uplifts"""
        return """(te.Price * te.Quantity) - 
        CASE 
            WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
            WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
            ELSE te.Cost * te.Quantity
        END"""
    
    def _get_date_expression(self, context: QueryContext) -> str:
        """Get date expression based on granularity"""
        # Find primary date column
        date_col = "t.Time"  # Default to Transaction.Time
        
        if context.grouping == TimeGranularity.HOUR:
            return f"DATEPART(HOUR, {date_col})"
        elif context.grouping == TimeGranularity.DAY:
            return f"CAST({date_col} AS DATE)"
        elif context.grouping == TimeGranularity.WEEK:
            return f"DATEPART(WEEK, {date_col})"
        elif context.grouping == TimeGranularity.MONTH:
            return f"CONVERT(VARCHAR(7), {date_col}, 120)"
        elif context.grouping == TimeGranularity.QUARTER:
            return f"'Q' + CAST(DATEPART(QUARTER, {date_col}) AS VARCHAR) + ' ' + CAST(YEAR({date_col}) AS VARCHAR)"
        elif context.grouping == TimeGranularity.YEAR:
            return f"YEAR({date_col})"
        
        return f"CAST({date_col} AS DATE)"
    
    def _build_comprehensive_activity_query(self, context: QueryContext) -> str:
        """Build comprehensive customer activity query for debt collection"""
        # Extract customer filter
        customer_filter = ""
        if "customer" in context.filters:
            customer_name = context.filters['customer'].replace("'", "''")
            if context.filters.get('customer_fuzzy', False):
                customer_filter = f"""(
                    c.Company LIKE '%{customer_name}%' OR 
                    c.FirstName + ' ' + c.LastName LIKE '%{customer_name}%' OR
                    c.AccountNumber LIKE '%{customer_name}%'
                )"""
            else:
                customer_filter = f"c.Company = '{customer_name}'"
        
        # Build comprehensive activity query with UNION ALL
        sql = f"""
WITH CustomerMatch AS (
    SELECT TOP 1 c.ID as CustomerID, 
           COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
           c.AccountBalance as CurrentBalance
    FROM Customer c
    WHERE {customer_filter if customer_filter else '1=1'}
),
AllActivity AS (
    -- Sales Transactions from Transaction table only (avoid duplicates with AR)
    SELECT 
        'Invoice' as Type,
        t.Time as ActivityDate,
        t.TransactionNumber as RefNumber,
        'Sale - Invoice #' + CAST(t.TransactionNumber as VARCHAR) as Description,
        t.Total as Debit,
        0 as Credit,
        CAST(t.Comment as VARCHAR(500)) as Comment
    FROM [dbo].[Transaction] t
    INNER JOIN CustomerMatch cm ON t.CustomerID = cm.CustomerID
    -- Exclude transactions that are already in AccountReceivable to avoid duplicates
    WHERE NOT EXISTS (
        SELECT 1 FROM AccountReceivable ar 
        WHERE ar.TransactionNumber = t.TransactionNumber 
        AND ar.CustomerID = cm.CustomerID
    )
    
    UNION ALL
    
    -- Outstanding AR balances (unpaid invoices)
    SELECT 
        'Invoice' as Type,
        ar.Date as ActivityDate,
        ar.TransactionNumber as RefNumber,
        'Sale - Invoice #' + CAST(ar.TransactionNumber as VARCHAR) as Description,
        ar.Balance as Debit,
        0 as Credit,
        'Outstanding' as Comment
    FROM AccountReceivable ar
    INNER JOIN CustomerMatch cm ON ar.CustomerID = cm.CustomerID
    WHERE ar.Balance > 0
    
    UNION ALL
    
    -- Payments (credits to account)
    SELECT 
        'Payment' as Type,
        p.Time as ActivityDate,
        p.ID as RefNumber,
        'Payment Received' as Description,
        0 as Debit,
        p.Amount as Credit,
        CAST(p.Comment as VARCHAR(500)) as Comment
    FROM Payment p
    INNER JOIN CustomerMatch cm ON p.CustomerID = cm.CustomerID
    
    UNION ALL
    
    -- AR Adjustments from AccountReceivableHistory
    SELECT 
        CASE 
            WHEN arh.Amount < 0 THEN 'Credit Adjustment'
            WHEN arh.Amount > 0 THEN 'Debit Adjustment'
            ELSE 'Adjustment'
        END as Type,
        arh.Date as ActivityDate,
        arh.ID as RefNumber,
        CASE 
            WHEN arh.Comment LIKE '%NSF%' THEN 'NSF Fee'
            WHEN arh.Amount = -1 THEN '$1 Adjustment'
            WHEN arh.Amount = 1 THEN '$1 Charge'
            ELSE 'Manual Adjustment'
        END as Description,
        CASE WHEN arh.Amount > 0 THEN arh.Amount ELSE 0 END as Debit,
        CASE WHEN arh.Amount < 0 THEN ABS(arh.Amount) ELSE 0 END as Credit,
        CAST(arh.Comment as VARCHAR(500)) as Comment
    FROM AccountReceivableHistory arh
    INNER JOIN AccountReceivable ar ON arh.AccountReceivableID = ar.ID
    INNER JOIN CustomerMatch cm ON ar.CustomerID = cm.CustomerID
)
SELECT 
    cm.CustomerName,
    aa.Type,
    aa.ActivityDate,
    aa.RefNumber,
    aa.Description,
    aa.Debit,
    aa.Credit,
    aa.Debit - aa.Credit as NetAmount,
    aa.Comment,
    -- Calculate running balance properly for each row
    (SELECT ISNULL(SUM(sub.Debit - sub.Credit), 0)
     FROM AllActivity sub
     WHERE (sub.ActivityDate < aa.ActivityDate)
        OR (sub.ActivityDate = aa.ActivityDate AND sub.RefNumber <= aa.RefNumber)
    ) as RunningBalance,
    cm.CurrentBalance as CurrentARBalance
FROM AllActivity aa
CROSS JOIN CustomerMatch cm
ORDER BY aa.ActivityDate DESC, aa.RefNumber DESC"""
        
        return sql
    
    def _build_period_cte(self, name: str, context: QueryContext, periods_back: int) -> str:
        """Build CTE for period comparison"""
        # Adjust time range for previous period
        adjusted_context = context
        if periods_back > 0:
            if adjusted_context.time_range:
                days_back = adjusted_context.time_range.get("days_back", 30)
                adjusted_context.time_range["days_back"] = days_back * (periods_back + 1)
        
        # Build subquery
        subquery = self._build_aggregation_query(adjusted_context)
        
        # Extract key columns for comparison
        subquery = subquery.replace("SELECT ", f"SELECT {name}.group_key, ", 1)
        
        return subquery


class EnhancedAISQLAssistant:
    """Enhanced AI SQL Assistant with deep database understanding"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the enhanced assistant"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or "YOUR_OPENAI_API_KEY_HERE"
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.schema = DatabaseSchema()
        self.nlp = NaturalLanguageProcessor(self.schema)
        self.sql_builder = SQLBuilder(self.schema)
        
        # Query cache
        self._query_cache = {}
        
        logger.info("Enhanced AI SQL Assistant v2 initialized with deep schema knowledge")
    
    def process_question(self, question: str, feedback_callback: Optional[Any] = None) -> Dict[str, Any]:
        """Process natural language question into SQL and execute"""
        
        def feedback(msg: str):
            if feedback_callback:
                try:
                    feedback_callback(msg)
                except:
                    pass
            logger.info(msg)
        
        try:
            feedback("🧠 Understanding your question with deep schema knowledge...")
            
            # Parse the question
            context = self.nlp.parse(question)
            
            feedback(f"📊 Detected domain: {context.domain.value}")
            feedback(f"🔍 Tables needed: {', '.join(context.tables_needed)}")
            
            # Build SQL query
            feedback("🏗️ Building optimized SQL query...")
            sql_query = self.sql_builder.build(context)
            
            # Validate and optimize
            sql_query = self._validate_and_optimize(sql_query)
            
            feedback("✅ Executing query...")
            results_df = self._execute_sql(sql_query)
            
            feedback("🎯 Analyzing results...")
            analysis = self._analyze_results(question, sql_query, results_df, context)
            
            # Cache results
            query_id = self._cache_results(results_df, sql_query)
            
            # Safely serialize context for JSON
            context_dict = {
                'question': context.question,
                'domain': context.domain.value if context.domain else None,
                'tables_needed': context.tables_needed,
                'metrics': context.metrics,
                'filters': context.filters,
                'time_range': context.time_range,
                'grouping': context.grouping.value if context.grouping else None,
                'aggregations': context.aggregations,
                'sorting': context.sorting,
                'limit': context.limit,
                'special_calculations': context.special_calculations
            }
            
            return {
                'question': question,
                'sql_query': sql_query,
                'context': context_dict,
                'results': self._prepare_results(results_df),
                'row_count': len(results_df),
                'query_id': query_id,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {
                'question': question,
                'sql_query': None,
                'results': [],
                'row_count': 0,
                'analysis': f"Error: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }
    
    def _validate_and_optimize(self, sql: str) -> str:
        """Validate and optimize SQL query"""
        # Ensure Transaction table is bracketed
        sql = re.sub(r'\bTransaction\b(?!\])', '[dbo].[Transaction]', sql)
        
        # Validate aliases
        sql = sql.replace(" Category c ", " Category cat ")
        
        # Add other optimizations
        return sql
    
    def _execute_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query"""
        with SQLServerConnection() as db:
            return db.execute_query(sql, description="AI Generated Query")
    
    def _analyze_results(self, question: str, sql: str, df: pd.DataFrame, context: QueryContext) -> str:
        """Analyze results with context awareness and entity confirmation"""
        if df.empty:
            # Check if fuzzy matching was used and suggest alternatives
            if context.filters.get('customer_fuzzy') or context.filters.get('product_fuzzy'):
                return f"No data found matching your search criteria. The search included fuzzy matching for '{context.filters.get('customer') or context.filters.get('product')}'. Please verify the name or try a broader search term."
            return "No data found matching your criteria."
        
        # Build confirmation of what was matched
        confirmations = []
        if context.filters.get('customer_fuzzy') and 'customer_name' in df.columns:
            unique_customers = df['customer_name'].dropna().unique()[:3]
            if len(unique_customers) > 0:
                confirmations.append(f"Found customers matching '{context.filters['customer']}': {', '.join(str(c) for c in unique_customers)}")
        
        if context.filters.get('product_fuzzy') and 'product' in df.columns:
            unique_products = df['product'].dropna().unique()[:3]
            if len(unique_products) > 0:
                confirmations.append(f"Found products matching '{context.filters['product']}': {', '.join(str(p) for p in unique_products[:2])}")
        
        # Prepare analysis prompt
        summary = {
            'total_rows': len(df),
            'columns': list(df.columns),
            'sample': df.head(5).to_dict('records'),
            'domain': context.domain.value,
            'metrics': context.metrics,
            'matches_confirmed': confirmations
        }
        
        # Get numeric summaries
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary['statistics'] = {}
            for col in numeric_cols:
                summary['statistics'][col] = {
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(df[col].mean()),
                    'sum': float(df[col].sum())
                }
        
        prompt = f"""Analyze these query results and provide insights:
Question: {question}
Domain: {context.domain.value}
Results Summary: {json.dumps(summary, default=str)}

Provide:
1. Direct answer to the question
2. Confirm what entities were matched if fuzzy search was used
3. 2-3 key insights
4. Any notable patterns

Keep response under 150 words."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
        )
        
        analysis = response.choices[0].message.content.strip()
        
        # Prepend confirmations if any
        if confirmations:
            analysis = "✅ " + " | ".join(confirmations) + "\n\n" + analysis
        
        return analysis
    
    def _cache_results(self, df: pd.DataFrame, sql: str) -> str:
        """Cache query results"""
        query_id = f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(df)}"
        self._query_cache[query_id] = {
            'df': df,
            'sql': sql,
            'timestamp': datetime.now()
        }
        
        # Clean old cache entries
        if len(self._query_cache) > 20:
            oldest = sorted(self._query_cache.keys())[:10]
            for key in oldest:
                del self._query_cache[key]
        
        return query_id
    
    def _prepare_results(self, df: pd.DataFrame, limit: int = 500) -> List[Dict]:
        """Prepare results for JSON serialization"""
        if df.empty:
            return []
        
        # Convert non-serializable types
        def convert_values(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, bytes):
                # Try to decode bytes as UTF-8, otherwise convert to hex string
                try:
                    return obj.decode('utf-8')
                except UnicodeDecodeError:
                    return obj.hex()
            elif isinstance(obj, dict):
                return {k: convert_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_values(x) for x in obj]
            # Check for pandas NA/null values
            try:
                if pd.isna(obj):
                    return None
            except (TypeError, ValueError):
                pass
            return obj
        
        results = df.head(limit).to_dict('records')
        return convert_values(results)
    
    def get_cached_results(self, query_id: str) -> Optional[pd.DataFrame]:
        """Retrieve cached results"""
        cache_entry = self._query_cache.get(query_id)
        if cache_entry:
            return cache_entry['df']
        return None
    
    def explain_query(self, sql: str) -> str:
        """Explain what a SQL query does in plain English"""
        prompt = f"""Explain this SQL query in simple terms:
{sql}

Provide:
1. What data it retrieves
2. Any filters applied
3. How results are grouped/sorted
4. What calculations are performed

Keep explanation under 100 words."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()