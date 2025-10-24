#!/usr/bin/env python3
"""
Unified Analytics Engine
Handles all business intelligence calculations and data analysis
"""

import logging
import os
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
from database_pymssql import (SQLServerConnection, PYMSSQL_AVAILABLE, 
                              DatabaseConnectionError, DatabaseQueryError, 
                              ConnectionPoolError, DatabaseTimeoutError)

logger = logging.getLogger(__name__)


class UnifiedAnalyticsEngine:
    """
    Unified analytics engine with direct SQL Server connection
    
    This class handles all the business intelligence calculations including:
    - Sales analytics and trends
    - Profit analysis by items, categories, and customers
    - Accounts receivable analysis and aging
    - Inventory management and risk assessment
    - Customer behavior analysis
    - Historical performance tracking
    """
    
    def __init__(self):
        """Initialize the analytics engine with database connection"""
        self.connection_timeout = 10
        self.max_retries = 2
        self.db = SQLServerConnection()
        
        # Initialize direct database connection
        try:
            if self.db.connect():
                logger.info("✅ Connected to live SQL Server database")
            else:
                raise DatabaseConnectionError("Failed to establish initial database connection")
        except (DatabaseConnectionError, ConnectionPoolError) as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise DatabaseConnectionError(f"Cannot start dashboard - database unavailable: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during database initialization: {e}")
            raise DatabaseConnectionError(f"Cannot start dashboard - unexpected error: {e}")
    
    def safe_execute_query(self, query, params=None, description="Query", use_cache=True):
        """
        Execute query with direct database connection and error handling
        
        Args:
            query (str): SQL query to execute
            params (list): Query parameters for safe parameterized queries
            description (str): Description of the query for logging
            use_cache (bool): Whether to use caching (currently unused)
            
        Returns:
            pd.DataFrame: Query results as a pandas DataFrame
            
        Raises:
            Exception: If query fails after all retries
        """
        max_retries = 3  # Increased from 2 to 3 for better reliability
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                logger.info(f"🔍 Executing: {description}")
                
                # Use direct database connection
                if not self.db.connection:
                    self.db.connect()
                
                # Handle parameter substitution for pymssql
                if params:
                    # Use cursor execute with parameters for proper SQL Server parameterization
                    cursor = self.db.connection.cursor()
                    cursor.execute(query, params)
                    
                    # Convert cursor results to DataFrame
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    data = cursor.fetchall()
                    result = pd.DataFrame(data, columns=columns)
                    cursor.close()
                else:
                    result = pd.read_sql(query, self.db.connection)
                
                if not result.empty:
                    logger.info(f"✅ {description} successful: {len(result)} rows")
                    return result
                else:
                    logger.warning(f"⚠️ {description} returned no data")
                    return pd.DataFrame()
                    
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # Check for connection-related errors - expand detection
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    'timeout', 'dead', 'not connected', 'connection', 'unknown error', 
                    'datastream processing', 'bad token', 'out of sync'
                ])
                
                if is_connection_error:
                    if retry_count <= max_retries:
                        logger.warning(f"🔄 Database connection issue detected, retrying ({retry_count}/{max_retries}): {e}")
                        
                        # Force reconnection with exponential backoff and better cleanup
                        time.sleep(2 ** (retry_count - 1))
                        try:
                            # More aggressive connection cleanup
                            if hasattr(self.db, 'connection') and self.db.connection:
                                try:
                                    self.db.connection.close()
                                except:
                                    pass  # Ignore close errors
                        except:
                            pass
                        
                        # Clear connection and force new one
                        self.db.connection = None
                        
                        # Try to reconnect with a small delay
                        time.sleep(0.5)
                        if self.db.connect():
                            logger.info("🔌 Database reconnection successful")
                            continue
                        else:
                            logger.error("❌ Database reconnection failed")
                            continue
                
                logger.error(f"❌ {description} failed: {e}")
                
                # For "Unknown error", return empty result instead of crashing
                if "unknown error" in error_msg.lower():
                    logger.warning(f"⚠️ Returning empty result for {description} due to database connectivity issue")
                    return pd.DataFrame()
                
                raise Exception(f"Database query failed for {description}: {e}")
        
        # If we get here, all retries failed
        logger.error(f"❌ All retries exhausted for {description}")
        return pd.DataFrame()
    
    def to_json_safe(self, obj):
        """Convert pandas/numpy types to JSON-safe types"""
        if obj is None or pd.isna(obj):
            return 0
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj.item())
        elif isinstance(obj, (int, float)):
            return float(obj)
        elif isinstance(obj, str):
            return obj
        elif hasattr(obj, 'item'):  # Handle numpy scalars
            try:
                return float(obj.item())
            except:
                return 0
        else:
            # Try to convert to float for money/decimal types
            try:
                return float(obj)
            except:
                return 0
    
    def validate_limit(self, limit, max_limit=1000, default=50):
        """Validate and sanitize limit parameter to prevent SQL injection"""
        try:
            limit_int = int(limit)
            # Ensure limit is within safe bounds
            if limit_int < 1:
                return default
            elif limit_int > max_limit:
                return max_limit
            return limit_int
        except (ValueError, TypeError):
            return default
    
    def get_date_range(self, period):
        """Get start and end dates for a period
        
        Args:
            period (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            
        Returns:
            tuple: (start_date, end_date) as formatted strings
            
        Raises:
            ValueError: If period is 'custom' (should use explicit dates instead)
        """
        # Custom dates should be handled separately and not call this method
        if period == 'custom':
            raise ValueError("Custom date ranges should use explicit start_date and end_date parameters, not get_date_range('custom')")
        
        now = datetime.now()
        
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == '7d':
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '30d':
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'mtd':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'ytd':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == '90d':
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '1y':
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to today
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
        return start_date.strftime('%Y-%m-%d %H:%M:%S'), end_date.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_comparison_date_range(self, period):
        """Get the comparison period date range for trend calculations
        
        Args:
            period (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            
        Returns:
            tuple: (start_date, end_date) as formatted strings for comparison period
        """
        now = datetime.now()
        
        if period == 'today':
            # Compare to yesterday
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '7d':
            # Compare to previous 7 days
            end_date = (now - timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '30d':
            # Compare to previous 30 days
            end_date = (now - timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=60)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'mtd':
            # Compare to same period last month
            last_month_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Take same number of days as current MTD
            current_day = now.day
            start_date = last_month_start
            end_date = (last_month_start + timedelta(days=current_day-1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'ytd':
            # Compare to same period last year
            last_year = now.year - 1
            start_date = now.replace(year=last_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(year=last_year, hour=23, minute=59, second=59, microsecond=999999)
        elif period == '90d':
            # Compare to previous 90 days
            end_date = (now - timedelta(days=90)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=180)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == '1y':
            # Compare to previous year
            end_date = (now - timedelta(days=365)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=730)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to yesterday for today comparison
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
        return start_date.strftime('%Y-%m-%d %H:%M:%S'), end_date.strftime('%Y-%m-%d %H:%M:%S')
    
    def calculate_trend_percentage(self, current_value, previous_value):
        """Calculate percentage change between current and previous values
        
        Args:
            current_value (float): Current period value
            previous_value (float): Previous period value for comparison
            
        Returns:
            float: Percentage change rounded to 1 decimal place
        """
        if previous_value == 0:
            return 100.0 if current_value > 0 else 0.0
        
        percentage = ((current_value - previous_value) / previous_value) * 100
        return round(percentage, 1)
    
    # =================
    # SALES ANALYTICS
    # =================
    
    def get_sales_summary(self, time_filter='today'):
        """Get sales summary with time filtering and trend calculations
        
        Args:
            time_filter (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            
        Returns:
            dict: Sales summary data with trends
        """
        start_date, end_date = self.get_date_range(time_filter)
        comp_start_date, comp_end_date = self.get_comparison_date_range(time_filter)
        
        query = """
            SELECT 
            COALESCE(SUM(te.Price * te.Quantity), 0) as TotalRevenue,
            COALESCE(SUM(te.Quantity), 0) as TotalUnits,
            COALESCE(COUNT(DISTINCT t.TransactionNumber), 0) as TotalInvoices
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE t.Time >= %s AND t.Time <= %s
        """
        
        # Get current period data
        use_cache = time_filter not in ['today']
        df = self.safe_execute_query(query, [start_date, end_date], f"Sales Summary ({time_filter})", use_cache)
        
        # Get comparison period data
        comp_df = self.safe_execute_query(query, [comp_start_date, comp_end_date], f"Sales Summary Comparison ({time_filter})", use_cache)
        
        if not df.empty:
            total_revenue = self.to_json_safe(df.iloc[0]['TotalRevenue'])
            total_units = self.to_json_safe(df.iloc[0]['TotalUnits'])
            total_invoices = self.to_json_safe(df.iloc[0]['TotalInvoices'])
            
            # Calculate average invoice value correctly: Total Revenue ÷ Number of Invoices
            avg_invoice_value = total_revenue / total_invoices if total_invoices > 0 else 0
            
            # Calculate trends vs comparison period
            revenue_trend = 0
            units_trend = 0
            invoices_trend = 0
            avg_invoice_trend = 0
            
            if not comp_df.empty:
                comp_revenue = self.to_json_safe(comp_df.iloc[0]['TotalRevenue'])
                comp_units = self.to_json_safe(comp_df.iloc[0]['TotalUnits'])
                comp_invoices = self.to_json_safe(comp_df.iloc[0]['TotalInvoices'])
                comp_avg_invoice = comp_revenue / comp_invoices if comp_invoices > 0 else 0
                
                revenue_trend = self.calculate_trend_percentage(total_revenue, comp_revenue)
                units_trend = self.calculate_trend_percentage(total_units, comp_units)
                invoices_trend = self.calculate_trend_percentage(total_invoices, comp_invoices)
                avg_invoice_trend = self.calculate_trend_percentage(avg_invoice_value, comp_avg_invoice)
            
            return {
                'total_revenue': total_revenue,
                'total_units': total_units,
                'total_invoices': total_invoices,
                'avg_invoice_value': avg_invoice_value,
                'avg_transaction_value': avg_invoice_value,  # For frontend compatibility
                'revenue_trend': revenue_trend,
                'units_trend': units_trend,
                'invoices_trend': invoices_trend,
                'avg_invoice_trend': avg_invoice_trend,
                'status': 'success'
            }
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    def get_sales_summary_custom(self, start_date, end_date):
        """Get sales summary with custom date range - FIXED: Avg invoice = Total Revenue ÷ Total Invoices
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            dict: Sales summary data
        """
        query = """
            SELECT 
            COALESCE(SUM(te.Price * te.Quantity), 0) as TotalRevenue,
            COALESCE(SUM(te.Quantity), 0) as TotalUnits,
            COALESCE(COUNT(DISTINCT t.TransactionNumber), 0) as TotalInvoices
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        WHERE CAST(t.Time as DATE) >= %s AND CAST(t.Time as DATE) <= %s
        """
        
        # Custom date ranges can be cached since they're typically historical
        df = self.safe_execute_query(query, [start_date, end_date], f"Sales Summary (Custom: {start_date} to {end_date})", True)
        
        if not df.empty:
            total_revenue = self.to_json_safe(df.iloc[0]['TotalRevenue'])
            total_invoices = self.to_json_safe(df.iloc[0]['TotalInvoices'])
            
            # Calculate average invoice value correctly: Total Revenue ÷ Number of Invoices
            avg_invoice_value = total_revenue / total_invoices if total_invoices > 0 else 0
            
            return {
                'total_revenue': total_revenue,
                'total_units': self.to_json_safe(df.iloc[0]['TotalUnits']),
                'total_invoices': total_invoices,
                'avg_invoice_value': avg_invoice_value,
                'avg_transaction_value': avg_invoice_value,  # For frontend compatibility
                'status': 'success'
            }
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    # =================
    # PROFIT ANALYTICS
    # =================
    
    def get_profit_summary(self, time_filter='today'):
        """Get profit summary with tobacco cost uplifts and trend calculations
        
        Args:
            time_filter (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            
        Returns:
            dict: Profit summary data with trends
        """
        start_date, end_date = self.get_date_range(time_filter)
        comp_start_date, comp_end_date = self.get_comparison_date_range(time_filter)
        
        query = """
        SELECT 
            COALESCE(SUM(te.Price * te.Quantity), 0) as TotalRevenue,
            COALESCE(SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23  -- CIGARS +23% excise tax
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- LT-TAX-COLLECTED +10% excise tax
                    ELSE te.Cost * te.Quantity
                END
            ), 0) as TotalAdjustedCost,
            COALESCE(SUM(te.Quantity), 0) as TotalUnits
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        """
        
        # Get current period data
        df = self.safe_execute_query(query, [start_date, end_date], f"Profit Summary ({time_filter})")
        
        # Get comparison period data
        comp_df = self.safe_execute_query(query, [comp_start_date, comp_end_date], f"Profit Summary Comparison ({time_filter})")
        
        if not df.empty:
            revenue = self.to_json_safe(df.iloc[0]['TotalRevenue'])
            cost = self.to_json_safe(df.iloc[0]['TotalAdjustedCost'])
            gross_profit = revenue - cost
            gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
            
            # Calculate trends vs comparison period
            profit_trend = 0
            margin_trend = 0
            
            if not comp_df.empty:
                comp_revenue = self.to_json_safe(comp_df.iloc[0]['TotalRevenue'])
                comp_cost = self.to_json_safe(comp_df.iloc[0]['TotalAdjustedCost'])
                comp_gross_profit = comp_revenue - comp_cost
                comp_gross_margin = (comp_gross_profit / comp_revenue * 100) if comp_revenue > 0 else 0
                
                profit_trend = self.calculate_trend_percentage(gross_profit, comp_gross_profit)
                margin_trend = self.calculate_trend_percentage(gross_margin, comp_gross_margin)
            
            return {
                'total_revenue': revenue,
                'total_cost': cost,
                'gross_profit': gross_profit,
                'gross_margin': gross_margin,
                'total_units': self.to_json_safe(df.iloc[0]['TotalUnits']),
                'profit_trend': profit_trend,
                'margin_trend': margin_trend,
                'status': 'success'
            }
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    def get_profit_summary_custom(self, start_date, end_date):
        """Get profit summary with custom date range and tobacco cost uplifts
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            dict: Profit summary data
        """
        query = """
        SELECT 
            COALESCE(SUM(te.Price * te.Quantity), 0) as TotalRevenue,
            COALESCE(SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23  -- CIGARS +23% excise tax
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- LT-TAX-COLLECTED +10% excise tax
                    ELSE te.Cost * te.Quantity
                END
            ), 0) as TotalAdjustedCost,
            COALESCE(SUM(te.Quantity), 0) as TotalUnits
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE CAST(t.Time as DATE) >= %s AND CAST(t.Time as DATE) <= %s
        """
        
        df = self.safe_execute_query(query, [start_date, end_date], f"Profit Summary (Custom: {start_date} to {end_date})")
        
        if not df.empty:
            revenue = self.to_json_safe(df.iloc[0]['TotalRevenue'])
            cost = self.to_json_safe(df.iloc[0]['TotalAdjustedCost'])
            gross_profit = revenue - cost
            gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
            
            return {
                'total_revenue': revenue,
                'total_cost': cost,
                'gross_profit': gross_profit,
                'gross_margin': gross_margin,
                'total_units': self.to_json_safe(df.iloc[0]['TotalUnits']),
                'status': 'success'
            }
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    # =================
    # COMPREHENSIVE PROFIT ANALYSIS
    # =================
    # 
    # IMPORTANT: Cost uplifts for excise tax compliance:
    # - CIGARS category: +23% cost uplift
    # - LT-TAX-COLLECTED category: +10% cost uplift
    # These uplifts are applied to all profit calculations to account for tobacco excise taxes.
    
    def get_profit_analysis_by_item(self, time_filter='30d', limit=50):
        """Get detailed profit analysis by individual items
        
        Args:
            time_filter (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            limit (int): Maximum number of items to return
            
        Returns:
            dict: List of items with profit analysis data
        """
        start_date, end_date = self.get_date_range(time_filter)
        safe_limit = self.validate_limit(limit, max_limit=1000, default=50)
        
        query = """
        SELECT TOP %s
            i.ID as ItemID,
            i.ItemLookupCode,
            i.Description as ItemName,
            COALESCE(c.Name, 'Uncategorized') as CategoryName,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23  -- CIGARS +23% excise tax
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- LT-TAX-COLLECTED +10% excise tax
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalCost,
            SUM(te.Price * te.Quantity) - SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalProfit,
            AVG(te.Price) as AvgSellPrice,
            AVG(te.Cost) as AvgCost,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY i.ID, i.ItemLookupCode, i.Description, c.Name
        ORDER BY TotalProfit DESC
        """
        
        df = self.safe_execute_query(query, [safe_limit, start_date, end_date], f"Profit Analysis by Item ({time_filter})")
        
        if not df.empty:
            items = []
            for _, row in df.iterrows():
                revenue = self.to_json_safe(row['TotalRevenue'])
                cost = self.to_json_safe(row['TotalCost'])
                profit = self.to_json_safe(row['TotalProfit'])
                margin_percent = (profit / revenue * 100) if revenue > 0 else 0
                
                items.append({
                    'item_id': self.to_json_safe(row['ItemID']),
                    'item_code': row['ItemLookupCode'] or '',
                    'item_name': row['ItemName'],
                    'category': row['CategoryName'],
                    'units_sold': self.to_json_safe(row['UnitsSold']),
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percent': round(margin_percent, 2),
                    'avg_sell_price': self.to_json_safe(row['AvgSellPrice']),
                    'avg_cost': self.to_json_safe(row['AvgCost']),
                    'transaction_count': self.to_json_safe(row['TransactionCount']),
                    'unique_customers': self.to_json_safe(row['UniqueCustomers'])
                })
                
            return {'items': items, 'status': 'success'}
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    def get_profit_analysis_by_category(self, time_filter='30d'):
        """Get detailed profit analysis by category with business-friendly consolidation
        
        Args:
            time_filter (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            
        Returns:
            dict: List of categories with profit analysis data
        """
        start_date, end_date = self.get_date_range(time_filter)
        
        # Get raw category data first
        query = """
        SELECT 
            COALESCE(c.Name, 'Uncategorized') as CategoryName,
            COUNT(DISTINCT i.ID) as ItemCount,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(
                CASE 
                    WHEN c.Name IN ('CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'LITTLE CIGAR-GA') THEN te.Cost * te.Quantity * 1.23  -- CIGARS +23% excise tax
                    WHEN c.Name IN ('LT-TAX-COLLECTED', 'LT-TAX PAID', 'LT-RYO-TAX COLLECTED') THEN te.Cost * te.Quantity * 1.10  -- LT-TAX +10% excise tax
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalCost,
            SUM(te.Price * te.Quantity) - SUM(
                CASE 
                    WHEN c.Name IN ('CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'LITTLE CIGAR-GA') THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name IN ('LT-TAX-COLLECTED', 'LT-TAX PAID', 'LT-RYO-TAX COLLECTED') THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalProfit,
            AVG(te.Price) as AvgSellPrice,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY c.Name
        ORDER BY TotalRevenue DESC
        """
        
        df = self.safe_execute_query(query, [start_date, end_date], f"Profit Analysis by Category ({time_filter})")
        
        if not df.empty:
            # Consolidate categories based on business logic
            consolidated_categories = self._consolidate_categories(df)
            return {'categories': consolidated_categories, 'status': 'success'}
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    def _consolidate_categories(self, df):
        """Consolidate categories based on business logic
        
        Args:
            df (pd.DataFrame): Raw category data from database
            
        Returns:
            list: Consolidated category data
        """
        # Define consolidation mappings
        category_mappings = {
            # Cigar categories (23% cost uplift group)
            'Cigars & Cigar Products': ['CIGARS', 'CIGAR GA', 'LIT CIGARS 003251', 'LITTLE CIGAR-GA'],
            
            # Tax categories (10% cost uplift group) 
            'Little Cigars (Tax Collected)': ['LT-TAX-COLLECTED', 'LT-TAX PAID', 'LT-RYO-TAX COLLECTED'],
            
            # E-cig categories
            'Electronic Cigarettes & Pods': ['ELECTRONIC CIG', 'ECIG - PODS', 'ECIG - DISP D8', 'ECIG - PODS D8'],
            
            # Keep major categories as-is
            'Cigarettes': ['CIGARETTE'],
            'Drinks & Beverages': ['DRINKS', 'JUICES'],
            'Food & Snacks': ['FOOD', 'CANDYS', 'COOKIES', 'FROZEN'],
            'Health & Wellness': ['KRATOM', 'CBD/HEMP', 'MEDICINE', 'VITAMINS'],
            'Accessories & Hardware': ['CELLUAR ACCESSORIES', 'AUTOMOTIVE', 'HARDWARE', 'BATTERY'],
            'Personal Care': ['COSMETICS & BEAUTY', 'PERFUMES', 'CLEANING PRODUCTS'],
            'Smoking Accessories': ['LIGHTERS', 'CIG ROLLING PAPER', 'BLUNT WRAP'],
            'Other Tobacco Products': ['T7 SMOKELESS GA', 'NICOTINE POUCHES']
        }
        
        # Initialize consolidated data
        consolidated = {}
        other_revenue = 0
        other_cost = 0
        other_profit = 0
        other_units = 0
        other_items = 0
        other_transactions = 0
        other_customers = set()
        
        # Process each row
        for _, row in df.iterrows():
            category_name = row['CategoryName']
            revenue = self.to_json_safe(row['TotalRevenue'])
            
            # Find which consolidated category this belongs to
            assigned_to = None
            for consolidated_name, original_categories in category_mappings.items():
                if category_name in original_categories:
                    assigned_to = consolidated_name
                    break
            
            # If revenue < $10k or not assigned, put in "Other"
            if revenue < 10000 or assigned_to is None:
                other_revenue += revenue
                other_cost += self.to_json_safe(row['TotalCost'])
                other_profit += self.to_json_safe(row['TotalProfit'])
                other_units += self.to_json_safe(row['UnitsSold'])
                other_items += self.to_json_safe(row['ItemCount'])
                other_transactions += self.to_json_safe(row['TransactionCount'])
                other_customers.add(category_name)  # Track unique categories in Other
            else:
                # Add to consolidated category
                if assigned_to not in consolidated:
                    consolidated[assigned_to] = {
                        'category_name': assigned_to,
                        'revenue': 0,
                        'cost': 0,
                        'profit': 0,
                        'units_sold': 0,
                        'item_count': 0,
                        'transaction_count': 0,
                        'unique_customers': 0,
                        'avg_sell_price': 0,
                        'price_sum': 0,
                        'price_count': 0
                    }
                
                consolidated[assigned_to]['revenue'] += revenue
                consolidated[assigned_to]['cost'] += self.to_json_safe(row['TotalCost'])
                consolidated[assigned_to]['profit'] += self.to_json_safe(row['TotalProfit'])
                consolidated[assigned_to]['units_sold'] += self.to_json_safe(row['UnitsSold'])
                consolidated[assigned_to]['item_count'] += self.to_json_safe(row['ItemCount'])
                consolidated[assigned_to]['transaction_count'] += self.to_json_safe(row['TransactionCount'])
                consolidated[assigned_to]['unique_customers'] += self.to_json_safe(row['UniqueCustomers'])
                
                # Track for average price calculation
                if pd.notna(row['AvgSellPrice']):
                    consolidated[assigned_to]['price_sum'] += float(row['AvgSellPrice']) * self.to_json_safe(row['UnitsSold'])
                    consolidated[assigned_to]['price_count'] += self.to_json_safe(row['UnitsSold'])
        
        # Add "Other" category if it has data
        if other_revenue > 0:
            consolidated['Other (Small Categories)'] = {
                'category_name': 'Other (Small Categories)',
                'revenue': other_revenue,
                'cost': other_cost,
                'profit': other_profit,
                'units_sold': other_units,
                'item_count': other_items,
                'transaction_count': other_transactions,
                'unique_customers': len(other_customers),
                'avg_sell_price': other_revenue / other_units if other_units > 0 else 0
            }
        
        # Format final results
        result_categories = []
        for category_data in consolidated.values():
            revenue = category_data['revenue']
            cost = category_data['cost']
            profit = category_data['profit']
            margin_percent = round((profit / revenue * 100), 2) if revenue > 0 else 0
            
            # Calculate average price
            avg_price = 0
            if category_data.get('price_count', 0) > 0:
                avg_price = category_data['price_sum'] / category_data['price_count']
            elif category_data.get('avg_sell_price'):
                avg_price = category_data['avg_sell_price']
            
            result_categories.append({
                'category_name': category_data['category_name'],
                'item_count': category_data['item_count'],
                'units_sold': category_data['units_sold'],
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'margin_percent': round(margin_percent, 2),
                'avg_sell_price': avg_price,
                'transaction_count': category_data['transaction_count'],
                'unique_customers': category_data['unique_customers']
            })
        
        # Sort by profit descending
        result_categories.sort(key=lambda x: x['profit'], reverse=True)
        return result_categories
    
    def get_profit_analysis_by_customer(self, time_filter='30d', limit=50):
        """Get detailed profit analysis by customer
        
        Args:
            time_filter (str): Time period filter ('today', '7d', '30d', 'mtd', 'ytd', '90d', '1y')
            limit (int): Maximum number of customers to return
            
        Returns:
            dict: List of customers with profit analysis data
        """
        start_date, end_date = self.get_date_range(time_filter)
        safe_limit = self.validate_limit(limit, max_limit=1000, default=50)
        
        query = """
        SELECT TOP %s
            c.ID as CustomerID,
            COALESCE(c.AccountNumber, '') as AccountNumber,
            COALESCE(c.FirstName + ' ' + c.LastName, 'Unknown Customer') as CustomerName,
            SUM(te.Quantity) as UnitsPurchased,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalCost,
            SUM(te.Price * te.Quantity) - SUM(
                CASE 
                    WHEN cat.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN cat.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalProfit,
            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
            AVG(te.Price * te.Quantity) as AvgTransactionValue
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Customer c ON t.CustomerID = c.ID
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= %s AND t.Time <= %s
        GROUP BY c.ID, c.AccountNumber, c.FirstName, c.LastName
        ORDER BY TotalProfit DESC
        """
        
        df = self.safe_execute_query(query, [safe_limit, start_date, end_date], f"Profit Analysis by Customer ({time_filter})")
        
        if not df.empty:
            customers = []
            for _, row in df.iterrows():
                revenue = self.to_json_safe(row['TotalRevenue'])
                cost = self.to_json_safe(row['TotalCost'])
                profit = self.to_json_safe(row['TotalProfit'])
                margin_percent = (profit / revenue * 100) if revenue > 0 else 0
                
                customers.append({
                    'customer_id': self.to_json_safe(row['CustomerID']),
                    'account_number': row['AccountNumber'] or '',
                    'customer_name': row['CustomerName'],
                    'units_purchased': self.to_json_safe(row['UnitsPurchased']),
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percent': round(margin_percent, 2),
                    'transaction_count': self.to_json_safe(row['TransactionCount']),
                    'avg_transaction_value': self.to_json_safe(row['AvgTransactionValue'])
                })
                
            return {'customers': customers, 'status': 'success'}
        else:
            return {'error': 'No data available', 'status': 'no_data'}
    
    def get_items_by_category_profit(self, category_name, time_filter='30d', limit=25):
        """Get items within a specific category sorted by profit
        
        Args:
            category_name (str): Name of the category to filter by
            time_filter (str): Time period filter
            limit (int): Maximum number of items to return
            
        Returns:
            dict: List of items in the category with profit data
        """
        start_date, end_date = self.get_date_range(time_filter)
        safe_limit = self.validate_limit(limit, max_limit=500, default=25)
        
        query = """
        SELECT TOP %s
            i.ID as ItemID,
            i.ItemLookupCode,
            i.Description as ItemName,
            SUM(te.Quantity) as UnitsSold,
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalCost,
            SUM(te.Price * te.Quantity) - SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as TotalProfit,
            AVG(te.Price) as AvgSellPrice
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s AND COALESCE(c.Name, 'Uncategorized') LIKE %s
        GROUP BY i.ID, i.ItemLookupCode, i.Description
        ORDER BY TotalProfit DESC
        """
        
        category_pattern = f'%{category_name}%'
        df = self.safe_execute_query(query, [safe_limit, start_date, end_date, category_pattern], 
                                   f"Items by Category Profit ({category_name}, {time_filter})")
        
        if not df.empty:
            items = []
            for _, row in df.iterrows():
                revenue = self.to_json_safe(row['TotalRevenue'])
                cost = self.to_json_safe(row['TotalCost'])
                profit = self.to_json_safe(row['TotalProfit'])
                margin_percent = (profit / revenue * 100) if revenue > 0 else 0
                
                items.append({
                    'item_id': self.to_json_safe(row['ItemID']),
                    'item_code': row['ItemLookupCode'] or '',
                    'item_name': row['ItemName'],
                    'units_sold': self.to_json_safe(row['UnitsSold']),
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percent': round(margin_percent, 2),
                    'avg_sell_price': self.to_json_safe(row['AvgSellPrice'])
                })
                
            return {'items': items, 'category': category_name, 'status': 'success'}
        else:
            return {'error': 'No data available for category', 'category': category_name, 'status': 'no_data'}
    
    # =================
    # ACCOUNTS RECEIVABLE ANALYTICS
    # =================
    
    def get_ar_summary(self):
        """Get accounts receivable summary with key metrics
        
        Returns:
            dict: AR summary with total outstanding, average age, etc.
        """
        query = """
        SELECT 
            COUNT(*) as TotalAccounts,
            SUM(CASE WHEN ar.Balance > 0 THEN 1 ELSE 0 END) as AccountsWithBalance,
            COALESCE(SUM(ar.Balance), 0) as TotalOutstanding,
            COALESCE(AVG(CASE WHEN ar.Balance > 0 THEN ar.Balance ELSE NULL END), 0) as AvgOutstandingBalance,
            COALESCE(MAX(ar.Balance), 0) as MaxOutstanding,
            COALESCE(SUM(CASE WHEN DATEDIFF(day, ar.LastPaymentDate, GETDATE()) <= 30 THEN ar.Balance ELSE 0 END), 0) as Current30Days,
            COALESCE(SUM(CASE WHEN DATEDIFF(day, ar.LastPaymentDate, GETDATE()) BETWEEN 31 AND 60 THEN ar.Balance ELSE 0 END), 0) as Days31to60,
            COALESCE(SUM(CASE WHEN DATEDIFF(day, ar.LastPaymentDate, GETDATE()) BETWEEN 61 AND 90 THEN ar.Balance ELSE 0 END), 0) as Days61to90,
            COALESCE(SUM(CASE WHEN DATEDIFF(day, ar.LastPaymentDate, GETDATE()) > 90 THEN ar.Balance ELSE 0 END), 0) as Over90Days
        FROM dbo.Customer ar
        """
        
        df = self.safe_execute_query(query, [], "AR Summary")
        
        if not df.empty:
            total_outstanding = self.to_json_safe(df.iloc[0]['TotalOutstanding'])
            
            return {
                'total_accounts': self.to_json_safe(df.iloc[0]['TotalAccounts']),
                'accounts_with_balance': self.to_json_safe(df.iloc[0]['AccountsWithBalance']),
                'total_outstanding': total_outstanding,
                'avg_outstanding_balance': self.to_json_safe(df.iloc[0]['AvgOutstandingBalance']),
                'max_outstanding': self.to_json_safe(df.iloc[0]['MaxOutstanding']),
                'aging': {
                    'current_30_days': self.to_json_safe(df.iloc[0]['Current30Days']),
                    'days_31_to_60': self.to_json_safe(df.iloc[0]['Days31to60']),
                    'days_61_to_90': self.to_json_safe(df.iloc[0]['Days61to90']),
                    'over_90_days': self.to_json_safe(df.iloc[0]['Over90Days'])
                },
                'status': 'success'
            }
        else:
            return {'error': 'No AR data available', 'status': 'no_data'}
    
    def get_ar_metrics(self, period='30d'):
        """Get AR performance metrics for a specific period
        
        Args:
            period (str): Time period for analysis
            
        Returns:
            dict: AR metrics including collection efficiency
        """
        start_date, end_date = self.get_date_range(period)
        
        query = """
        SELECT 
            COUNT(DISTINCT c.ID) as ActiveAccounts,
            COALESCE(SUM(CASE WHEN c.Balance > 0 THEN c.Balance ELSE 0 END), 0) as TotalOutstanding,
            COALESCE(AVG(CASE WHEN c.Balance > 0 THEN 
                DATEDIFF(day, c.LastPaymentDate, GETDATE()) ELSE NULL END), 0) as AvgDaysOutstanding,
            COALESCE(SUM(CASE WHEN t.Time >= %s AND t.Time <= %s THEN t.Total ELSE 0 END), 0) as PeriodSales,
            COALESCE(SUM(CASE WHEN t.Time >= %s AND t.Time <= %s THEN 
                CASE WHEN t.TransactionTypeID = 1 THEN t.Total ELSE 0 END ELSE 0 END), 0) as PeriodPayments
        FROM dbo.Customer c
        LEFT JOIN dbo.[Transaction] t ON c.ID = t.CustomerID
        """
        
        df = self.safe_execute_query(query, [start_date, end_date, start_date, end_date], f"AR Metrics ({period})")
        
        if not df.empty:
            total_outstanding = self.to_json_safe(df.iloc[0]['TotalOutstanding'])
            period_sales = self.to_json_safe(df.iloc[0]['PeriodSales'])
            collection_ratio = (period_sales / total_outstanding) if total_outstanding > 0 else 0
            
            return {
                'active_accounts': self.to_json_safe(df.iloc[0]['ActiveAccounts']),
                'total_outstanding': total_outstanding,
                'avg_days_outstanding': self.to_json_safe(df.iloc[0]['AvgDaysOutstanding']),
                'period_sales': period_sales,
                'period_payments': self.to_json_safe(df.iloc[0]['PeriodPayments']),
                'collection_ratio': round(collection_ratio, 3),
                'status': 'success'
            }
        else:
            return {'error': 'No AR metrics available', 'status': 'no_data'}
    
    def get_ar_aging(self, period='30d'):
        """Get detailed AR aging analysis
        
        Args:
            period (str): Period for aging analysis
            
        Returns:
            dict: Detailed aging buckets with customer breakdown
        """
        query = """
        SELECT 
            c.ID as CustomerID,
            COALESCE(c.FirstName + ' ' + c.LastName, 'Unknown') as CustomerName,
            c.AccountNumber,
            c.Balance as OutstandingBalance,
            COALESCE(DATEDIFF(day, c.LastPaymentDate, GETDATE()), 0) as DaysOutstanding,
            c.LastPaymentDate,
            CASE 
                WHEN DATEDIFF(day, c.LastPaymentDate, GETDATE()) <= 30 THEN 'Current (0-30 days)'
                WHEN DATEDIFF(day, c.LastPaymentDate, GETDATE()) BETWEEN 31 AND 60 THEN '31-60 days'
                WHEN DATEDIFF(day, c.LastPaymentDate, GETDATE()) BETWEEN 61 AND 90 THEN '61-90 days'
                ELSE 'Over 90 days'
            END as AgingBucket
        FROM dbo.Customer c
        WHERE c.Balance > 0
        ORDER BY c.Balance DESC
        """
        
        df = self.safe_execute_query(query, [], f"AR Aging ({period})")
        
        if not df.empty:
            aging_buckets = {}
            customers = []
            
            for _, row in df.iterrows():
                bucket = row['AgingBucket']
                balance = self.to_json_safe(row['OutstandingBalance'])
                
                if bucket not in aging_buckets:
                    aging_buckets[bucket] = {'count': 0, 'total_balance': 0}
                
                aging_buckets[bucket]['count'] += 1
                aging_buckets[bucket]['total_balance'] += balance
                
                customers.append({
                    'customer_id': self.to_json_safe(row['CustomerID']),
                    'customer_name': row['CustomerName'],
                    'account_number': row['AccountNumber'] or '',
                    'outstanding_balance': balance,
                    'days_outstanding': self.to_json_safe(row['DaysOutstanding']),
                    'last_payment_date': str(row['LastPaymentDate']) if row['LastPaymentDate'] else None,
                    'aging_bucket': bucket
                })
            
            return {
                'aging_buckets': aging_buckets,
                'customers': customers,
                'total_customers': len(customers),
                'status': 'success'
            }
        else:
            return {'error': 'No AR aging data available', 'status': 'no_data'}
    
    def get_collection_trends(self, period='30d'):
        """Get collection performance trends
        
        Args:
            period (str): Period for trend analysis
            
        Returns:
            dict: Collection trends and performance metrics
        """
        start_date, end_date = self.get_date_range(period)
        
        query = """
        SELECT 
            CAST(t.Time as DATE) as PaymentDate,
            COUNT(*) as PaymentCount,
            SUM(CASE WHEN t.TransactionTypeID = 1 THEN t.Total ELSE 0 END) as DailyPayments,
            AVG(CASE WHEN t.TransactionTypeID = 1 THEN t.Total ELSE NULL END) as AvgPaymentAmount
        FROM dbo.[Transaction] t
        WHERE t.Time >= %s AND t.Time <= %s AND t.TransactionTypeID = 1
        GROUP BY CAST(t.Time as DATE)
        ORDER BY PaymentDate DESC
        """
        
        df = self.safe_execute_query(query, [start_date, end_date], f"Collection Trends ({period})")
        
        if not df.empty:
            trends = []
            total_payments = 0
            
            for _, row in df.iterrows():
                daily_payments = self.to_json_safe(row['DailyPayments'])
                total_payments += daily_payments
                
                trends.append({
                    'date': str(row['PaymentDate']),
                    'payment_count': self.to_json_safe(row['PaymentCount']),
                    'daily_payments': daily_payments,
                    'avg_payment_amount': self.to_json_safe(row['AvgPaymentAmount'])
                })
            
            return {
                'trends': trends,
                'total_payments': total_payments,
                'avg_daily_payments': total_payments / len(trends) if trends else 0,
                'status': 'success'
            }
        else:
            return {'error': 'No collection trend data available', 'status': 'no_data'}
    
    def get_overdue_customers(self, period='30d', limit=15):
        """Get list of overdue customers
        
        Args:
            period (str): Period to define overdue threshold
            limit (int): Maximum customers to return
            
        Returns:
            dict: List of overdue customers with details
        """
        safe_limit = self.validate_limit(limit, max_limit=100, default=15)
        
        query = """
        SELECT TOP %s
            c.ID as CustomerID,
            COALESCE(c.FirstName + ' ' + c.LastName, 'Unknown') as CustomerName,
            c.AccountNumber,
            c.Balance as OutstandingBalance,
            DATEDIFF(day, c.LastPaymentDate, GETDATE()) as DaysOverdue,
            c.LastPaymentDate,
            c.Phone1,
            c.Email
        FROM dbo.Customer c
        WHERE c.Balance > 0 AND DATEDIFF(day, c.LastPaymentDate, GETDATE()) > 30
        ORDER BY c.Balance DESC, DaysOverdue DESC
        """
        
        df = self.safe_execute_query(query, [safe_limit], f"Overdue Customers ({period})")
        
        if not df.empty:
            customers = []
            for _, row in df.iterrows():
                customers.append({
                    'customer_id': self.to_json_safe(row['CustomerID']),
                    'customer_name': row['CustomerName'],
                    'account_number': row['AccountNumber'] or '',
                    'outstanding_balance': self.to_json_safe(row['OutstandingBalance']),
                    'days_overdue': self.to_json_safe(row['DaysOverdue']),
                    'last_payment_date': str(row['LastPaymentDate']) if row['LastPaymentDate'] else None,
                    'phone': row['Phone1'] or '',
                    'email': row['Email'] or ''
                })
            
            return {'customers': customers, 'status': 'success'}
        else:
            return {'error': 'No overdue customers found', 'status': 'no_data'}
    
    def get_recent_payments(self, period='30d', limit=15):
        """Get recent payment transactions
        
        Args:
            period (str): Period to look for recent payments
            limit (int): Maximum payments to return
            
        Returns:
            dict: List of recent payment transactions
        """
        start_date, end_date = self.get_date_range(period)
        safe_limit = self.validate_limit(limit, max_limit=100, default=15)
        
        query = """
        SELECT TOP %s
            t.TransactionNumber,
            t.Time as PaymentDate,
            t.Total as PaymentAmount,
            COALESCE(c.FirstName + ' ' + c.LastName, 'Unknown') as CustomerName,
            c.AccountNumber,
            c.ID as CustomerID
        FROM dbo.[Transaction] t
        JOIN dbo.Customer c ON t.CustomerID = c.ID
        WHERE t.Time >= %s AND t.Time <= %s AND t.TransactionTypeID = 1
        ORDER BY t.Time DESC
        """
        
        df = self.safe_execute_query(query, [safe_limit, start_date, end_date], f"Recent Payments ({period})")
        
        if not df.empty:
            payments = []
            for _, row in df.iterrows():
                payments.append({
                    'transaction_number': row['TransactionNumber'],
                    'payment_date': str(row['PaymentDate']),
                    'payment_amount': self.to_json_safe(row['PaymentAmount']),
                    'customer_name': row['CustomerName'],
                    'account_number': row['AccountNumber'] or '',
                    'customer_id': self.to_json_safe(row['CustomerID'])
                })
            
            return {'payments': payments, 'status': 'success'}
        else:
            return {'error': 'No recent payments found', 'status': 'no_data'}
    
    # =================
    # HISTORICAL ANALYSIS
    # =================
    
    def get_historical_trends(self, start_year='2012', end_year=None):
        """Get comprehensive historical trends with enhanced business analytics
        
        Args:
            start_year (str): Starting year for analysis
            end_year (str): Ending year for analysis (defaults to current year)
            
        Returns:
            dict: Historical trends data with sales, profit, and AR metrics
        """
        if end_year is None:
            end_year = str(datetime.now().year)
            
        try:
            start_year = int(start_year)
            end_year = int(end_year)
        except ValueError:
            return {'error': 'Invalid year parameters', 'status': 'error'}
        
        # Get historical sales and profit data
        sales_profit_data = self._get_historical_sales_profit(start_year, end_year)
        ar_data = self._get_historical_ar_data(start_year, end_year)
        
        return {
            'sales_profit_data': sales_profit_data,
            'ar_data': ar_data,
            'start_year': start_year,
            'end_year': end_year,
            'status': 'success'
        }
    
    def _get_historical_sales_profit(self, start_year, end_year):
        """Get historical sales and profit data by year and month
        
        Args:
            start_year (int): Starting year
            end_year (int): Ending year
            
        Returns:
            list: Monthly sales and profit data
        """
        query = """
        SELECT 
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            SUM(te.Price * te.Quantity) as MonthlyRevenue,
            SUM(
                CASE 
                    WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23
                    WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10
                    ELSE te.Cost * te.Quantity
                END
            ) as MonthlyCost,
            COUNT(DISTINCT t.TransactionNumber) as MonthlyTransactions
        FROM [dbo].[Transaction] t
        JOIN dbo.TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        JOIN dbo.Item i ON te.ItemID = i.ID
        LEFT JOIN dbo.Category c ON i.CategoryID = c.ID
        WHERE YEAR(t.Time) >= %s AND YEAR(t.Time) <= %s
        GROUP BY YEAR(t.Time), MONTH(t.Time)
        ORDER BY YEAR(t.Time), MONTH(t.Time)
        """
        
        df = self.safe_execute_query(query, [start_year, end_year], f"Historical Sales/Profit ({start_year}-{end_year})")
        
        monthly_data = []
        if not df.empty:
            for _, row in df.iterrows():
                revenue = self.to_json_safe(row['MonthlyRevenue'])
                cost = self.to_json_safe(row['MonthlyCost'])
                profit = revenue - cost
                
                monthly_data.append({
                    'year': self.to_json_safe(row['Year']),
                    'month': self.to_json_safe(row['Month']),
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percent': round((profit / revenue * 100), 2) if revenue > 0 else 0,
                    'transactions': self.to_json_safe(row['MonthlyTransactions'])
                })
        
        return monthly_data
    
    def _get_historical_ar_data(self, start_year, end_year):
        """Get historical accounts receivable data
        
        Args:
            start_year (int): Starting year
            end_year (int): Ending year
            
        Returns:
            list: Historical AR metrics by year
        """
        # Simplified AR historical data - in a real implementation, 
        # this would need historical AR snapshots
        query = """
        SELECT 
            YEAR(GETDATE()) as Year,
            COUNT(*) as TotalCustomers,
            SUM(CASE WHEN Balance > 0 THEN Balance ELSE 0 END) as TotalOutstanding,
            AVG(CASE WHEN Balance > 0 THEN Balance ELSE NULL END) as AvgBalance
        FROM dbo.Customer
        """
        
        df = self.safe_execute_query(query, [], "Historical AR Data")
        
        ar_data = []
        if not df.empty:
            ar_data.append({
                'year': self.to_json_safe(df.iloc[0]['Year']),
                'total_customers': self.to_json_safe(df.iloc[0]['TotalCustomers']),
                'total_outstanding': self.to_json_safe(df.iloc[0]['TotalOutstanding']),
                'avg_balance': self.to_json_safe(df.iloc[0]['AvgBalance'])
            })
        
        return ar_data
    
    def _generate_historical_analytics(self, sales_data, ar_data, inventory_data, start_year, end_year):
        """Generate comprehensive historical analytics from raw data
        
        Args:
            sales_data (list): Historical sales data
            ar_data (list): Historical AR data
            inventory_data (list): Historical inventory data
            start_year (int): Start year
            end_year (int): End year
            
        Returns:
            dict: Processed historical analytics
        """
        # This is a simplified implementation
        # The actual method in app.py is much more complex
        
        analytics = {
            'summary': {
                'total_years': end_year - start_year + 1,
                'total_months': len(sales_data),
                'avg_monthly_revenue': sum(item['revenue'] for item in sales_data) / len(sales_data) if sales_data else 0,
                'avg_monthly_profit': sum(item['profit'] for item in sales_data) / len(sales_data) if sales_data else 0
            },
            'yearly_trends': [],
            'monthly_trends': sales_data,
            'ar_trends': ar_data
        }
        
        # Group by year for yearly trends
        yearly_data = {}
        for item in sales_data:
            year = item['year']
            if year not in yearly_data:
                yearly_data[year] = {'revenue': 0, 'cost': 0, 'profit': 0, 'transactions': 0, 'months': 0}
            
            yearly_data[year]['revenue'] += item['revenue']
            yearly_data[year]['cost'] += item['cost']
            yearly_data[year]['profit'] += item['profit']
            yearly_data[year]['transactions'] += item['transactions']
            yearly_data[year]['months'] += 1
        
        for year, data in yearly_data.items():
            analytics['yearly_trends'].append({
                'year': year,
                'revenue': data['revenue'],
                'cost': data['cost'],
                'profit': data['profit'],
                'margin_percent': round((data['profit'] / data['revenue'] * 100), 2) if data['revenue'] > 0 else 0,
                'transactions': data['transactions'],
                'avg_monthly_revenue': data['revenue'] / data['months'] if data['months'] > 0 else 0
            })
        
        return analytics