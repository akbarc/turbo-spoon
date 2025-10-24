"""
Simple Customer Name Grouping Module
Groups customers by fuzzy matching first and last names only
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection
from datetime import datetime, timedelta

# Import risk predictor
try:
    from modules.customer_risk_predictor import CustomerRiskPredictor
except ImportError:
    CustomerRiskPredictor = None

logger = logging.getLogger(__name__)

class SimpleNameGrouper:
    """Simple customer grouping based on fuzzy first/last name matching only"""
    
    def __init__(self):
        self.similarity_threshold = 0.85  # 85% name similarity required
        self.risk_predictor = CustomerRiskPredictor() if CustomerRiskPredictor else None
        
    def normalize_name(self, text: str) -> str:
        """Normalize name for comparison"""
        if not text:
            return ""
        # Upper case, remove extra spaces and special chars
        text = str(text).upper().strip()
        text = re.sub(r'[^A-Z\s]', '', text)  # Keep only letters and spaces
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        return text.strip()
    
    def fuzzy_match_names(self, first1: str, last1: str, first2: str, last2: str) -> float:
        """Simple fuzzy matching for first and last names"""
        first1 = self.normalize_name(first1)
        last1 = self.normalize_name(last1)
        first2 = self.normalize_name(first2)
        last2 = self.normalize_name(last2)
        
        # Both must have at least a last name or first name
        if not (first1 or last1) or not (first2 or last2):
            return 0.0
        
        # Calculate similarity
        first_sim = 0
        if first1 and first2:
            first_sim = SequenceMatcher(None, first1, first2).ratio()
        
        last_sim = 0
        if last1 and last2:
            last_sim = SequenceMatcher(None, last1, last2).ratio()
        
        # More strict matching to prevent false positives
        # Both names must meet minimum thresholds independently
        if first1 and first2 and last1 and last2:
            # Stricter rules: Prevent Rehan/Rehman and Karim/Arif matches
            # But allow Mohammed/Mohammad (common spelling variations)
            
            # If last names are identical (100% match)
            if last_sim == 1.0:
                # Require very high first name similarity (>91%) to prevent false matches
                # This catches Rehan (90.91%) vs Rehman but allows exact/near-exact matches
                if first_sim < 0.92:
                    return 0.0
            # If last names are very similar but not identical
            elif last_sim >= 0.95:
                # Be even stricter with first names
                if first_sim < 0.85:
                    return 0.0
            else:
                # Last names don't match well enough
                return 0.0
            
            # Weight last name more heavily (60/40)
            return (first_sim * 0.4 + last_sim * 0.6)
        elif last1 and last2:
            # For last name only matching, require 95%
            return last_sim if last_sim >= 0.95 else 0.0
        elif first1 and first2:
            # For first name only matching, require 92%
            return first_sim if first_sim >= 0.92 else 0.0
        
        return 0.0
    
    def _calculate_days_since(self, date_value) -> int:
        """Safely calculate days since a date, handling NaT and various date formats"""
        try:
            if date_value is None or pd.isna(date_value):
                return 9999
                
            # Handle NaT specifically
            if hasattr(date_value, '_value') and pd.isna(date_value):
                return 9999
            
            # Handle string dates
            if isinstance(date_value, str):
                if date_value in ['', '1900-01-01', 'NaT', 'None']:
                    return 9999
                try:
                    # Try parsing as ISO format first
                    date_obj = datetime.fromisoformat(str(date_value).replace('Z', '+00:00'))
                except:
                    try:
                        # Try pandas to_datetime as fallback
                        date_obj = pd.to_datetime(date_value).to_pydatetime()
                    except:
                        return 9999
            # Handle pandas Timestamp
            elif hasattr(date_value, 'to_pydatetime'):
                try:
                    date_obj = date_value.to_pydatetime()
                except:
                    return 9999
            # Handle datetime objects
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return 9999
            
            # Check if date_obj is valid
            if pd.isna(date_obj):
                return 9999
            
            # Calculate days difference
            days_diff = (datetime.now() - date_obj).days
            return max(0, min(days_diff, 9999))  # Reasonable bounds
            
        except Exception as e:
            logger.warning(f"Error calculating days since date {date_value}: {e}")
            return 9999
    
    def _safe_calculate_days_since_payment(self, payment_info) -> int:
        """Safely calculate days since payment, handling None and NaT values"""
        try:
            if not payment_info or not payment_info.get('date'):
                return 9999
            
            date_value = payment_info['date']
            # If it's still a datetime object, use it directly
            if hasattr(date_value, 'date') or hasattr(date_value, 'isoformat'):
                days_diff = (datetime.now() - date_value).days
                return max(0, min(days_diff, 9999))
            else:
                # Otherwise use the general calculation method
                return self._calculate_days_since(date_value)
        except Exception as e:
            logger.warning(f"Error calculating days since payment: {e}")
            return 9999
    
    def _safe_calculate_days_since_transaction(self, transaction_info) -> int:
        """Safely calculate days since transaction, handling None and NaT values"""
        try:
            if not transaction_info or not transaction_info.get('date'):
                return 9999
            
            date_value = transaction_info['date']
            # If it's still a datetime object, use it directly
            if hasattr(date_value, 'date') or hasattr(date_value, 'isoformat'):
                days_diff = (datetime.now() - date_value).days
                return max(0, min(days_diff, 9999))
            else:
                # Otherwise use the general calculation method
                return self._calculate_days_since(date_value)
        except Exception as e:
            logger.warning(f"Error calculating days since transaction: {e}")
            return 9999
    
    def find_name_groups(self, days_filter: int = 30) -> List[Dict]:
        """Find customer groups based on fuzzy name matching"""
        try:
            with SQLServerConnection() as db:
                # Get all active customers with names - optimized query
                query = """
                SELECT 
                    c.ID,
                    c.FirstName,
                    c.LastName,
                    c.Company,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.AccountBalance,
                    c.CreditLimit,
                    c.LastVisit,
                    -- Get recent payment info in one query
                    recent_payment.LastPaymentDate,
                    recent_payment.LastPaymentAmount,
                    recent_payment.LastPaymentComment,
                    -- Get recent transaction info
                    recent_transaction.LastTransactionDate,
                    recent_transaction.LastTransactionAmount,
                    recent_transaction.LastTransactionComment,
                    -- Get payment totals for date range
                    payment_totals.TotalPayments,
                    payment_totals.PaymentCount,
                    -- Get sales totals for date range  
                    sales_totals.TotalSales,
                    sales_totals.SalesCount
                FROM dbo.Customer c
                LEFT JOIN (
                    SELECT 
                        p.CustomerID,
                        MAX(p.Time) as LastPaymentDate,
                        (SELECT TOP 1 p2.Amount FROM dbo.Payment p2 WHERE p2.CustomerID = p.CustomerID ORDER BY p2.Time DESC) as LastPaymentAmount,
                        (SELECT TOP 1 p2.Comment FROM dbo.Payment p2 WHERE p2.CustomerID = p.CustomerID ORDER BY p2.Time DESC) as LastPaymentComment
                    FROM dbo.Payment p
                    GROUP BY p.CustomerID
                ) recent_payment ON c.ID = recent_payment.CustomerID
                LEFT JOIN (
                    SELECT 
                        t.CustomerID,
                        MAX(t.Time) as LastTransactionDate,
                        (SELECT TOP 1 t2.Total FROM dbo.[Transaction] t2 WHERE t2.CustomerID = t.CustomerID ORDER BY t2.Time DESC) as LastTransactionAmount,
                        (SELECT TOP 1 t2.Comment FROM dbo.[Transaction] t2 WHERE t2.CustomerID = t.CustomerID ORDER BY t2.Time DESC) as LastTransactionComment
                    FROM dbo.[Transaction] t
                    GROUP BY t.CustomerID
                ) recent_transaction ON c.ID = recent_transaction.CustomerID
                LEFT JOIN (
                    SELECT 
                        p.CustomerID,
                        SUM(p.Amount) as TotalPayments,
                        COUNT(*) as PaymentCount
                    FROM dbo.Payment p
                    WHERE p.Time >= DATEADD(day, -%s, GETDATE())
                    GROUP BY p.CustomerID
                ) payment_totals ON c.ID = payment_totals.CustomerID
                LEFT JOIN (
                    SELECT 
                        t.CustomerID,
                        SUM(t.Total) as TotalSales,
                        COUNT(*) as SalesCount
                    FROM dbo.[Transaction] t
                    WHERE t.Time >= DATEADD(day, -%s, GETDATE())
                        AND t.Total > 0
                    GROUP BY t.CustomerID
                ) sales_totals ON c.ID = sales_totals.CustomerID
                WHERE (c.FirstName IS NOT NULL OR c.LastName IS NOT NULL OR c.Company IS NOT NULL)
                    AND (c.AccountBalance > 0 OR c.LastVisit >= DATEADD(month, -12, GETDATE()))
                ORDER BY c.LastName, c.FirstName
                """
                
                customers = db.execute_query(query, (days_filter, days_filter))
                
                if customers.empty:
                    return []
                
                # Group customers by similar names
                groups = []
                processed_ids = set()
                
                for i, customer1 in customers.iterrows():
                    if customer1['ID'] in processed_ids:
                        continue
                    
                    # Start a new group
                    group_members = [customer1.to_dict()]
                    processed_ids.add(customer1['ID'])
                    
                    # Find similar names
                    for j, customer2 in customers.iterrows():
                        if customer2['ID'] in processed_ids:
                            continue
                        
                        # Check name similarity
                        similarity = self.fuzzy_match_names(
                            customer1['FirstName'],
                            customer1['LastName'],
                            customer2['FirstName'],
                            customer2['LastName']
                        )
                        
                        if similarity >= self.similarity_threshold:
                            group_members.append(customer2.to_dict())
                            processed_ids.add(customer2['ID'])
                    
                    # Only create group if multiple members
                    if len(group_members) > 1:
                        # Get the most common first/last name for display
                        first_names = [m['FirstName'] for m in group_members if m['FirstName']]
                        last_names = [m['LastName'] for m in group_members if m['LastName']]
                        
                        group_first = max(set(first_names), key=first_names.count) if first_names else ''
                        group_last = max(set(last_names), key=last_names.count) if last_names else ''
                        
                        # Clean datetime and decimal fields in member data for JSON serialization
                        for member in group_members:
                            # Convert datetime fields to strings
                            for date_field in ['LastVisit', 'LastPaymentDate', 'LastTransactionDate']:
                                if date_field in member and member[date_field] is not None:
                                    date_value = member[date_field]
                                    if pd.isna(date_value):
                                        member[date_field] = None
                                    elif hasattr(date_value, 'isoformat'):
                                        member[date_field] = date_value.isoformat()
                                    elif hasattr(date_value, 'to_pydatetime'):
                                        try:
                                            member[date_field] = date_value.to_pydatetime().isoformat()
                                        except:
                                            member[date_field] = str(date_value)
                                    else:
                                        member[date_field] = str(date_value)
                            
                            # Convert Decimal fields to floats
                            for decimal_field in ['AccountBalance', 'CreditLimit', 'LastPaymentAmount', 'LastTransactionAmount', 'TotalPayments', 'TotalSales']:
                                if decimal_field in member and member[decimal_field] is not None:
                                    decimal_value = member[decimal_field]
                                    if pd.isna(decimal_value):
                                        member[decimal_field] = 0.0
                                    elif hasattr(decimal_value, '__class__') and 'Decimal' in str(type(decimal_value)):
                                        member[decimal_field] = float(decimal_value)
                                    # Also handle string decimals
                                    elif isinstance(decimal_value, str):
                                        try:
                                            member[decimal_field] = float(decimal_value)
                                        except:
                                            member[decimal_field] = 0.0
                            
                            # Convert integer fields
                            for int_field in ['PaymentCount', 'SalesCount']:
                                if int_field in member and member[int_field] is not None:
                                    int_value = member[int_field]
                                    if pd.isna(int_value):
                                        member[int_field] = 0
                                    else:
                                        try:
                                            member[int_field] = int(int_value)
                                        except:
                                            member[int_field] = 0

                        # Calculate group-level payment info
                        most_recent_payment = None
                        most_recent_transaction = None
                        
                        for member in group_members:
                            # Safe payment date handling
                            payment_date = member.get('LastPaymentDate')
                            if payment_date and not pd.isna(payment_date) and str(payment_date) != '1900-01-01':
                                try:
                                    # Convert to comparable format
                                    if hasattr(payment_date, 'to_pydatetime'):
                                        payment_dt = payment_date.to_pydatetime()
                                    else:
                                        payment_dt = payment_date
                                        
                                    if not most_recent_payment:
                                        most_recent_payment = {
                                            'date': payment_dt,  # Keep as datetime for comparison
                                            'amount': member.get('LastPaymentAmount'),
                                            'comment': member.get('LastPaymentComment'),
                                            'customer_name': member.get('FirstName', '') + ' ' + member.get('LastName', '')
                                        }
                                    else:
                                        # Compare safely - both should be datetime objects
                                        current_dt = most_recent_payment['date']
                                        
                                        if payment_dt > current_dt:
                                            most_recent_payment = {
                                                'date': payment_dt,  # Keep as datetime for comparison
                                                'amount': member.get('LastPaymentAmount'),
                                                'comment': member.get('LastPaymentComment'),
                                                'customer_name': member.get('FirstName', '') + ' ' + member.get('LastName', '')
                                            }
                                except Exception as e:
                                    logger.warning(f"Error processing payment date for member: {e}")
                                    continue
                            
                            # Safe transaction date handling
                            transaction_date = member.get('LastTransactionDate')
                            if transaction_date and not pd.isna(transaction_date) and str(transaction_date) != '1900-01-01':
                                try:
                                    # Convert to comparable format
                                    if hasattr(transaction_date, 'to_pydatetime'):
                                        transaction_dt = transaction_date.to_pydatetime()
                                    else:
                                        transaction_dt = transaction_date
                                        
                                    if not most_recent_transaction:
                                        most_recent_transaction = {
                                            'date': transaction_dt,  # Keep as datetime for comparison
                                            'amount': member.get('LastTransactionAmount'),
                                            'comment': member.get('LastTransactionComment'),
                                            'customer_name': member.get('FirstName', '') + ' ' + member.get('LastName', '')
                                        }
                                    else:
                                        # Compare safely - both should be datetime objects
                                        current_dt = most_recent_transaction['date']
                                        
                                        if transaction_dt > current_dt:
                                            most_recent_transaction = {
                                                'date': transaction_dt,  # Keep as datetime for comparison
                                                'amount': member.get('LastTransactionAmount'),
                                                'comment': member.get('LastTransactionComment'),
                                                'customer_name': member.get('FirstName', '') + ' ' + member.get('LastName', '')
                                            }
                                except Exception as e:
                                    logger.warning(f"Error processing transaction date for member: {e}")
                                    continue
                        
                        # Convert datetime objects to strings and Decimals to floats for JSON serialization
                        if most_recent_payment:
                            if most_recent_payment.get('date'):
                                most_recent_payment['date'] = most_recent_payment['date'].isoformat() if hasattr(most_recent_payment['date'], 'isoformat') else str(most_recent_payment['date'])
                            if most_recent_payment.get('amount') and hasattr(most_recent_payment['amount'], '__class__') and 'Decimal' in str(type(most_recent_payment['amount'])):
                                most_recent_payment['amount'] = float(most_recent_payment['amount'])
                        
                        if most_recent_transaction:
                            if most_recent_transaction.get('date'):
                                most_recent_transaction['date'] = most_recent_transaction['date'].isoformat() if hasattr(most_recent_transaction['date'], 'isoformat') else str(most_recent_transaction['date'])
                            if most_recent_transaction.get('amount') and hasattr(most_recent_transaction['amount'], '__class__') and 'Decimal' in str(type(most_recent_transaction['amount'])):
                                most_recent_transaction['amount'] = float(most_recent_transaction['amount'])

                        # Calculate group totals for payments and sales
                        total_payments = sum(float(m.get('TotalPayments') or 0) for m in group_members)
                        total_sales = sum(float(m.get('TotalSales') or 0) for m in group_members)
                        total_payment_count = sum(int(m.get('PaymentCount') or 0) for m in group_members)
                        total_sales_count = sum(int(m.get('SalesCount') or 0) for m in group_members)
                        
                        groups.append({
                            'group_id': f"NAME_{customer1['ID']}",
                            'display_name': f"{group_first} {group_last}".strip(),
                            'first_name': group_first,
                            'last_name': group_last,
                            'members': group_members,
                            'member_count': len(group_members),
                            'total_balance': sum(float(m['AccountBalance'] or 0) for m in group_members),
                            'most_recent_payment': most_recent_payment,
                            'most_recent_transaction': most_recent_transaction,
                            'days_since_last_payment': self._safe_calculate_days_since_payment(most_recent_payment),
                            'days_since_last_transaction': self._safe_calculate_days_since_transaction(most_recent_transaction),
                            # New payment and sales metrics
                            'total_payments': total_payments,
                            'total_sales': total_sales,
                            'payment_count': total_payment_count,
                            'sales_count': total_sales_count,
                            'days_filter': days_filter
                        })
                
                # Sort by total balance
                groups.sort(key=lambda x: x['total_balance'], reverse=True)
                
                logger.info(f"Found {len(groups)} name-based customer groups")
                return groups
                
        except Exception as e:
            logger.error(f"Error finding name groups: {e}")
            return []
    
    def get_group_details(self, customer_ids: List[int], days_filter: int = 30) -> Dict:
        """Get comprehensive details for a customer group"""
        try:
            if not customer_ids:
                return {}
            
            with SQLServerConnection() as db:
                id_list = ','.join(str(id) for id in customer_ids)
                
                # Get customer details
                customer_query = f"""
                SELECT 
                    ID,
                    FirstName,
                    LastName,
                    Company,
                    PhoneNumber,
                    EmailAddress,
                    AccountBalance,
                    CreditLimit,
                    LastVisit,
                    AccountOpened,
                    TotalSales,
                    TotalVisits
                FROM dbo.Customer
                WHERE ID IN ({id_list})
                ORDER BY AccountBalance DESC
                """
                customers = db.execute_query(customer_query)
                
                # Get AR metrics
                ar_query = f"""
                SELECT 
                    COUNT(*) as total_invoices,
                    SUM(Balance) as total_ar,
                    AVG(Balance) as avg_invoice,
                    MIN(Date) as oldest_invoice,
                    MAX(Date) as newest_invoice,
                    AVG(DATEDIFF(day, Date, GETDATE())) as avg_days_outstanding,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN Balance ELSE 0 END) as over_90_balance
                FROM dbo.AccountReceivable
                WHERE CustomerID IN ({id_list})
                    AND Balance > 0
                """
                ar_metrics = db.execute_query(ar_query)
                
                # Get payment patterns
                payment_query = f"""
                WITH PaymentData AS (
                    SELECT 
                        CustomerID,
                        Time as PaymentDate,
                        Amount,
                        DATEPART(weekday, Time) as DayOfWeek,
                        DATEPART(day, Time) as DayOfMonth
                    FROM dbo.Payment
                    WHERE CustomerID IN ({id_list})
                        AND Time >= DATEADD(month, -6, GETDATE())
                )
                SELECT 
                    COUNT(*) as payment_count,
                    SUM(Amount) as total_payments,
                    AVG(Amount) as avg_payment,
                    MAX(PaymentDate) as last_payment,
                    -- Most common payment day
                    (SELECT TOP 1 DayOfWeek 
                     FROM PaymentData 
                     GROUP BY DayOfWeek 
                     ORDER BY COUNT(*) DESC) as common_day_of_week,
                    -- Payment timing
                    AVG(CASE WHEN DayOfMonth <= 10 THEN 1.0 ELSE 0 END) * 100 as pct_early_month,
                    AVG(CASE WHEN DayOfMonth > 20 THEN 1.0 ELSE 0 END) * 100 as pct_late_month
                FROM PaymentData
                """
                payment_patterns = db.execute_query(payment_query)
                
                # Get configurable sales periods
                sales_query = f"""
                SELECT 
                    SUM(CASE WHEN Time >= DATEADD(day, -{days_filter}, GETDATE()) THEN Total ELSE 0 END) as sales_period,
                    SUM(CASE WHEN Time >= DATEADD(day, -30, GETDATE()) THEN Total ELSE 0 END) as sales_30_days,
                    SUM(CASE WHEN Time >= DATEADD(day, -90, GETDATE()) THEN Total ELSE 0 END) as sales_90_days,
                    COUNT(CASE WHEN Time >= DATEADD(day, -{days_filter}, GETDATE()) THEN 1 END) as transactions_period,
                    COUNT(CASE WHEN Time >= DATEADD(day, -30, GETDATE()) THEN 1 END) as transactions_30_days,
                    COUNT(CASE WHEN Time >= DATEADD(day, -90, GETDATE()) THEN 1 END) as transactions_90_days
                FROM [dbo].[Transaction]
                WHERE CustomerID IN ({id_list})
                    AND Total > 0
                """
                sales_metrics = db.execute_query(sales_query)
                
                # Get detailed payment history
                payment_history_query = f"""
                SELECT TOP 50
                    p.CustomerID,
                    p.Time as PaymentDate,
                    p.Amount,
                    p.Comment,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName
                FROM dbo.Payment p
                INNER JOIN dbo.Customer c ON p.CustomerID = c.ID
                WHERE p.CustomerID IN ({id_list})
                    AND p.Time >= DATEADD(day, -{days_filter * 2}, GETDATE())
                ORDER BY p.Time DESC
                """
                payment_history = db.execute_query(payment_history_query)
                
                # Get payment totals for the specified period
                payment_totals_query = f"""
                SELECT 
                    SUM(CASE WHEN Time >= DATEADD(day, -{days_filter}, GETDATE()) THEN Amount ELSE 0 END) as payments_period,
                    COUNT(CASE WHEN Time >= DATEADD(day, -{days_filter}, GETDATE()) THEN 1 END) as payment_count_period
                FROM dbo.Payment
                WHERE CustomerID IN ({id_list})
                """
                payment_totals = db.execute_query(payment_totals_query)
                
                # Get risk analysis for each customer
                risk_assessments = []
                group_risk_stats = {
                    'low_risk': 0,
                    'medium_risk': 0,
                    'high_risk': 0,
                    'critical_risk': 0,
                    'total_risk_score': 0,
                    'avg_risk_score': 0,
                    'highest_risk_customer': None,
                    'risk_factors': []
                }
                
                if self.risk_predictor:
                    for customer_id in customer_ids:
                        try:
                            risk_assessment = self.risk_predictor.calculate_risk_score(customer_id)
                            risk_assessments.append(risk_assessment)
                            
                            # Update group stats
                            risk_level = risk_assessment.get('risk_level', 'LOW')
                            if risk_level == 'LOW':
                                group_risk_stats['low_risk'] += 1
                            elif risk_level == 'MEDIUM':
                                group_risk_stats['medium_risk'] += 1
                            elif risk_level == 'HIGH':
                                group_risk_stats['high_risk'] += 1
                            elif risk_level == 'CRITICAL':
                                group_risk_stats['critical_risk'] += 1
                            
                            risk_score = risk_assessment.get('risk_score', 0)
                            if risk_score:
                                group_risk_stats['total_risk_score'] += risk_score
                                
                                # Track highest risk customer
                                if (not group_risk_stats['highest_risk_customer'] or 
                                    risk_score > group_risk_stats['highest_risk_customer'].get('risk_score', 0)):
                                    group_risk_stats['highest_risk_customer'] = risk_assessment
                            
                            # Collect unique risk factors
                            red_flags = risk_assessment.get('red_flags', [])
                            for flag in red_flags:
                                if flag not in group_risk_stats['risk_factors']:
                                    group_risk_stats['risk_factors'].append(flag)
                                    
                        except Exception as e:
                            logger.error(f"Error getting risk assessment for customer {customer_id}: {e}")
                            continue
                    
                    # Calculate averages
                    total_customers = len(risk_assessments)
                    if total_customers > 0:
                        group_risk_stats['avg_risk_score'] = round(
                            group_risk_stats['total_risk_score'] / total_customers, 3
                        )
                        
                        # Determine overall group risk level
                        high_risk_pct = (group_risk_stats['high_risk'] + group_risk_stats['critical_risk']) / total_customers
                        if high_risk_pct >= 0.5:
                            group_risk_stats['overall_risk_level'] = 'HIGH'
                        elif high_risk_pct >= 0.25 or group_risk_stats['critical_risk'] > 0:
                            group_risk_stats['overall_risk_level'] = 'MEDIUM'
                        else:
                            group_risk_stats['overall_risk_level'] = 'LOW'
                    else:
                        group_risk_stats['overall_risk_level'] = 'UNKNOWN'

                # Build response
                result = {
                    'customers': customers.to_dict('records') if not customers.empty else [],
                    'ar_metrics': ar_metrics.iloc[0].to_dict() if not ar_metrics.empty else {},
                    'payment_patterns': payment_patterns.iloc[0].to_dict() if not payment_patterns.empty else {},
                    'sales_metrics': sales_metrics.iloc[0].to_dict() if not sales_metrics.empty else {},
                    'payment_history': payment_history.to_dict('records') if not payment_history.empty else [],
                    'payment_totals': payment_totals.iloc[0].to_dict() if not payment_totals.empty else {},
                    'risk_assessments': risk_assessments,
                    'group_risk_stats': group_risk_stats,
                    'days_filter': days_filter,
                    'summary': {
                        'total_customers': len(customers),
                        'total_ar': float(customers['AccountBalance'].sum()),
                        'total_credit_limit': float(customers['CreditLimit'].sum()),
                        'avg_ar_per_customer': float(customers['AccountBalance'].mean())
                    }
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting group details: {e}")
            return {}
    
    def export_all_groups_detailed(self, days_filter: int = 30) -> List[Dict]:
        """Export comprehensive data for all customer groups with payment/invoice details"""
        try:
            with SQLServerConnection() as db:
                # Get all customers with comprehensive details in one optimized query
                query = """
                SELECT 
                    c.ID,
                    c.FirstName,
                    c.LastName,
                    c.Company,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.AccountBalance,
                    c.CreditLimit,
                    c.LastVisit,
                    c.TotalSales,
                    c.TotalVisits,
                    
                    -- Last Payment Details
                    last_payment.PaymentDate as LastPaymentDate,
                    last_payment.PaymentAmount as LastPaymentAmount,
                    last_payment.PaymentComment as LastPaymentComment,
                    
                    -- Last Invoice/Sale Details
                    last_transaction.TransactionDate as LastInvoiceDate,
                    last_transaction.TransactionAmount as LastInvoiceAmount,
                    last_transaction.TransactionComment as LastInvoiceComment,
                    last_transaction.TransactionNumber as LastInvoiceNumber,
                    
                    -- Group Classification (prioritize human names, normalize spacing)
                    CASE 
                        WHEN c.LastName IS NOT NULL AND LEN(LTRIM(RTRIM(c.LastName))) > 0 THEN
                            UPPER(LTRIM(RTRIM(ISNULL(c.FirstName, '') + ' ' + c.LastName)))
                        WHEN c.FirstName IS NOT NULL AND LEN(LTRIM(RTRIM(c.FirstName))) > 0 THEN
                            UPPER(LTRIM(RTRIM(c.FirstName)))
                        WHEN c.Company IS NOT NULL AND LEN(c.Company) > 0 THEN
                            -- Extract likely person names from company names
                            CASE 
                                WHEN c.Company LIKE '% %' AND LEN(c.Company) < 30 THEN
                                    UPPER(LTRIM(RTRIM(c.Company)))
                                ELSE
                                    UPPER(LEFT(LTRIM(RTRIM(c.Company)), 25))
                            END
                        ELSE 
                            'CUSTOMER_' + CAST(c.ID as varchar)
                    END as GroupKey,
                    
                    -- Days calculations
                    CASE 
                        WHEN last_payment.PaymentDate IS NULL THEN 9999
                        ELSE DATEDIFF(day, last_payment.PaymentDate, GETDATE())
                    END as DaysSinceLastPayment,
                    
                    CASE 
                        WHEN last_transaction.TransactionDate IS NULL THEN 9999
                        ELSE DATEDIFF(day, last_transaction.TransactionDate, GETDATE())
                    END as DaysSinceLastSale
                    
                FROM dbo.Customer c
                
                -- Get most recent payment with details
                LEFT JOIN (
                    SELECT 
                        p1.CustomerID,
                        p1.Time as PaymentDate,
                        p1.Amount as PaymentAmount,
                        p1.Comment as PaymentComment
                    FROM dbo.Payment p1
                    WHERE p1.Time = (
                        SELECT MAX(p2.Time) 
                        FROM dbo.Payment p2 
                        WHERE p2.CustomerID = p1.CustomerID
                    )
                ) last_payment ON c.ID = last_payment.CustomerID
                
                -- Get most recent transaction with details
                LEFT JOIN (
                    SELECT 
                        t1.CustomerID,
                        t1.Time as TransactionDate,
                        t1.Total as TransactionAmount,
                        t1.Comment as TransactionComment,
                        t1.TransactionNumber
                    FROM dbo.[Transaction] t1
                    WHERE t1.Time = (
                        SELECT MAX(t2.Time) 
                        FROM dbo.[Transaction] t2 
                        WHERE t2.CustomerID = t1.CustomerID
                    )
                ) last_transaction ON c.ID = last_transaction.CustomerID
                
                WHERE (c.AccountBalance > 0 OR c.LastVisit >= DATEADD(month, -24, GETDATE()))
                    AND (c.FirstName IS NOT NULL OR c.LastName IS NOT NULL OR c.Company IS NOT NULL)
                
                ORDER BY 
                    CASE 
                        WHEN c.LastName IS NOT NULL AND LEN(LTRIM(RTRIM(c.LastName))) > 0 THEN
                            UPPER(LTRIM(RTRIM(ISNULL(c.FirstName, '') + ' ' + c.LastName)))
                        WHEN c.FirstName IS NOT NULL AND LEN(LTRIM(RTRIM(c.FirstName))) > 0 THEN
                            UPPER(LTRIM(RTRIM(c.FirstName)))
                        WHEN c.Company IS NOT NULL AND LEN(c.Company) > 0 THEN
                            CASE 
                                WHEN c.Company LIKE '% %' AND LEN(c.Company) < 30 THEN
                                    UPPER(LTRIM(RTRIM(c.Company)))
                                ELSE
                                    UPPER(LEFT(LTRIM(RTRIM(c.Company)), 25))
                            END
                        ELSE 
                            'CUSTOMER_' + CAST(c.ID as varchar)
                    END,
                    c.AccountBalance DESC
                """
                
                logger.info("Executing comprehensive customer export query...")
                customers = db.execute_query(query)
                
                if customers.empty:
                    return []
                
                # Group customers by GroupKey and clean up group names
                groups_dict = {}
                for _, customer in customers.iterrows():
                    group_key = customer['GroupKey']
                    
                    # Clean and improve group name display
                    display_name = self._clean_group_name(group_key, customer)
                    
                    if group_key not in groups_dict:
                        groups_dict[group_key] = {
                            'group_name': display_name,
                            'customers': [],
                            'total_ar_balance': 0,
                            'total_credit_limit': 0,
                            'customer_count': 0,
                            'total_lifetime_sales': 0,
                            'most_recent_payment_date': None,
                            'most_recent_sale_date': None,
                            'combined_days_since_payment': 0,
                            'combined_days_since_sale': 0
                        }
                    
                    # Convert customer record to dict with safe type conversion
                    customer_dict = {}
                    for key, value in customer.items():
                        if pd.isna(value):
                            customer_dict[key] = None
                        elif hasattr(value, '__class__') and 'Decimal' in str(type(value)):
                            customer_dict[key] = float(value)
                        else:
                            customer_dict[key] = value
                    
                    groups_dict[group_key]['customers'].append(customer_dict)
                    groups_dict[group_key]['total_ar_balance'] += float(customer.get('AccountBalance', 0) or 0)
                    groups_dict[group_key]['total_credit_limit'] += float(customer.get('CreditLimit', 0) or 0)
                    groups_dict[group_key]['customer_count'] += 1
                    groups_dict[group_key]['total_lifetime_sales'] += float(customer.get('TotalSales', 0) or 0)
                    
                    # Track most recent dates
                    if customer.get('LastPaymentDate') and customer['LastPaymentDate'] != '1900-01-01':
                        if (not groups_dict[group_key]['most_recent_payment_date'] or 
                            customer['LastPaymentDate'] > groups_dict[group_key]['most_recent_payment_date']):
                            groups_dict[group_key]['most_recent_payment_date'] = customer['LastPaymentDate']
                    
                    if customer.get('LastInvoiceDate') and customer['LastInvoiceDate'] != '1900-01-01':
                        if (not groups_dict[group_key]['most_recent_sale_date'] or 
                            customer['LastInvoiceDate'] > groups_dict[group_key]['most_recent_sale_date']):
                            groups_dict[group_key]['most_recent_sale_date'] = customer['LastInvoiceDate']
                
                # Convert to list and sort by total AR balance
                export_data = list(groups_dict.values())
                export_data.sort(key=lambda x: x['total_ar_balance'], reverse=True)
                
                logger.info(f"Prepared export data for {len(export_data)} customer groups with {sum(g['customer_count'] for g in export_data)} total customers")
                return export_data
                
        except Exception as e:
            logger.error(f"Error exporting group details: {e}")
            return []
    
    def _clean_group_name(self, group_key: str, customer_sample: dict) -> str:
        """Clean and improve group name for better readability"""
        try:
            # Remove extra spaces
            cleaned = ' '.join(group_key.split())
            
            # If it looks like a proper name (has space and reasonable length)
            if ' ' in cleaned and len(cleaned) < 40:
                # Capitalize properly for names
                words = cleaned.split()
                cleaned_words = []
                for word in words:
                    if len(word) > 0:
                        # Don't over-capitalize single letters or short words
                        if len(word) == 1:
                            cleaned_words.append(word.upper())
                        else:
                            cleaned_words.append(word.title())
                return ' '.join(cleaned_words)
            
            # For single words or longer strings, keep them as title case
            if len(cleaned) > 0:
                return cleaned.title()
            
            # Fallback to original
            return group_key
            
        except Exception as e:
            logger.warning(f"Error cleaning group name '{group_key}': {e}")
            return group_key