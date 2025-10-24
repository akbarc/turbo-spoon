#!/usr/bin/env python3
"""
Fast Risk Analysis Module
Optimized for practical risk insights with SQL-based overviews
"""

import logging
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import pandas as pd

logger = logging.getLogger(__name__)

class FastRiskAnalysis:
    """Optimized risk analysis focused on actionable insights"""
    
    def __init__(self):
        pass
    
    def get_risk_overview(self, days_no_payment=90, balance_multiplier=2.0):
        """Get comprehensive risk overview with key categories"""
        try:
            with SQLServerConnection() as db:
                # 1. Customers with no successful payments in X days (simplified approach)
                no_payment_query = f"""
                SELECT 
                    c.ID as CustomerID,
                    CASE 
                        WHEN c.Company IS NOT NULL AND LEN(c.Company) > 0 THEN c.Company
                        ELSE c.FirstName + ' ' + c.LastName
                    END as CustomerName,
                    c.AccountBalance,
                    c.PhoneNumber,
                    CASE 
                        WHEN last_payments.LastPaymentDate IS NULL THEN 9999
                        ELSE DATEDIFF(day, last_payments.LastPaymentDate, GETDATE())
                    END as DaysSincePayment,
                    ISNULL(last_payments.LastPaymentDate, '1900-01-01') as LastPaymentDate
                FROM dbo.Customer c
                LEFT JOIN (
                    SELECT 
                        p.CustomerID,
                        MAX(p.Time) as LastPaymentDate
                    FROM dbo.Payment p
                    GROUP BY p.CustomerID
                ) last_payments ON c.ID = last_payments.CustomerID
                WHERE c.AccountBalance > 500
                AND CASE 
                    WHEN last_payments.LastPaymentDate IS NULL THEN 9999
                    ELSE DATEDIFF(day, last_payments.LastPaymentDate, GETDATE())
                END >= {days_no_payment}
                ORDER BY c.AccountBalance DESC
                """
                no_payment_customers = db.execute_query(no_payment_query)
                
                # 2. High balance relative to sales activity
                high_balance_query = f"""
                SELECT 
                    c.ID as CustomerID,
                    CASE 
                        WHEN c.Company IS NOT NULL AND LEN(c.Company) > 0 THEN c.Company
                        ELSE c.FirstName + ' ' + c.LastName
                    END as CustomerName,
                    c.AccountBalance,
                    c.PhoneNumber,
                    ISNULL(recent_sales.MonthlySales, 0) as MonthlySales,
                    CASE 
                        WHEN ISNULL(recent_sales.MonthlySales, 0) = 0 THEN 999.0
                        ELSE c.AccountBalance / ISNULL(recent_sales.MonthlySales, 1)
                    END as BalanceToMonthlySalesRatio
                FROM dbo.Customer c
                LEFT JOIN (
                    SELECT 
                        monthly_totals.CustomerID,
                        AVG(monthly_totals.MonthlyTotal) as MonthlySales
                    FROM (
                        SELECT 
                            CustomerID,
                            YEAR(Time) as SalesYear,
                            MONTH(Time) as SalesMonth,
                            SUM(Total) as MonthlyTotal
                        FROM dbo.[Transaction]
                        WHERE Time >= DATEADD(month, -6, GETDATE())
                        GROUP BY CustomerID, YEAR(Time), MONTH(Time)
                    ) monthly_totals
                    GROUP BY monthly_totals.CustomerID
                ) recent_sales ON c.ID = recent_sales.CustomerID
                WHERE c.AccountBalance > 1000
                AND CASE 
                    WHEN ISNULL(recent_sales.MonthlySales, 0) = 0 THEN 999.0
                    ELSE c.AccountBalance / ISNULL(recent_sales.MonthlySales, 1)
                END >= {balance_multiplier}
                ORDER BY CASE 
                    WHEN ISNULL(recent_sales.MonthlySales, 0) = 0 THEN 999.0
                    ELSE c.AccountBalance / ISNULL(recent_sales.MonthlySales, 1)
                END DESC, c.AccountBalance DESC
                """
                high_balance_customers = db.execute_query(high_balance_query)
                
                # 3. NSF Problem Customers (using $65 NSF fee pattern)
                nsf_problem_query = """
                SELECT 
                    c.ID as CustomerID,
                    CASE 
                        WHEN c.Company IS NOT NULL AND LEN(c.Company) > 0 THEN c.Company
                        ELSE c.FirstName + ' ' + c.LastName
                    END as CustomerName,
                    c.AccountBalance,
                    c.PhoneNumber,
                    nsf_data.NSFCount,
                    nsf_data.NSFAmount,
                    nsf_data.LastNSFDate,
                    CASE 
                        WHEN nsf_data.LastNSFDate IS NULL THEN 9999
                        ELSE DATEDIFF(day, nsf_data.LastNSFDate, GETDATE())
                    END as DaysSinceLastNSF
                FROM dbo.Customer c
                JOIN (
                    SELECT 
                        ar.CustomerID,
                        COUNT(*) as NSFCount,
                        SUM(ar.OriginalAmount) as NSFAmount,
                        MAX(ar.Date) as LastNSFDate
                    FROM dbo.AccountReceivable ar
                    WHERE ar.OriginalAmount = 65.00  -- Standard NSF fee
                    AND ar.TransactionNumber = 0     -- Manual adjustments
                    GROUP BY ar.CustomerID
                    HAVING COUNT(*) > 0
                ) nsf_data ON c.ID = nsf_data.CustomerID
                WHERE c.AccountBalance > 100
                ORDER BY nsf_data.NSFCount DESC, nsf_data.NSFAmount DESC
                """
                nsf_customers = db.execute_query(nsf_problem_query)
                
                # 4. Highest AR Balances
                highest_ar_query = """
                SELECT TOP 50
                    c.ID as CustomerID,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                    c.AccountBalance,
                    c.PhoneNumber,
                    c.CreditLimit,
                    CASE 
                        WHEN c.CreditLimit > 0 THEN (c.AccountBalance / c.CreditLimit) * 100
                        ELSE 0
                    END as CreditUtilization,
                    c.TotalSales,
                    CASE 
                        WHEN c.TotalSales > 0 THEN (c.AccountBalance / c.TotalSales) * 100
                        ELSE 0
                    END as BalanceToLifetimeSalesRatio
                FROM dbo.Customer c
                WHERE c.AccountBalance > 1000
                ORDER BY c.AccountBalance DESC
                """
                highest_ar_customers = db.execute_query(highest_ar_query)
                
                # 5. Group Risk Analysis (customers with similar names) - simplified for SQL 2008 R2
                group_risk_query = """
                SELECT 
                    CASE 
                        WHEN Company IS NOT NULL AND LEN(Company) > 0 THEN
                            UPPER(LEFT(Company, 15))
                        ELSE 
                            UPPER(ISNULL(LastName, '') + ' ' + ISNULL(FirstName, ''))
                    END as GroupKey,
                    COUNT(*) as GroupSize,
                    SUM(AccountBalance) as TotalGroupBalance,
                    AVG(AccountBalance) as AvgGroupBalance,
                    MAX(AccountBalance) as MaxGroupBalance
                FROM dbo.Customer
                WHERE AccountBalance > 100
                GROUP BY 
                    CASE 
                        WHEN Company IS NOT NULL AND LEN(Company) > 0 THEN
                            UPPER(LEFT(Company, 15))
                        ELSE 
                            UPPER(ISNULL(LastName, '') + ' ' + ISNULL(FirstName, ''))
                    END
                HAVING COUNT(*) > 1 AND SUM(AccountBalance) > 5000
                ORDER BY SUM(AccountBalance) DESC
                """
                group_risks = db.execute_query(group_risk_query)
                
                # 6. Summary Statistics
                summary_query = """
                SELECT 
                    COUNT(CASE WHEN AccountBalance > 0 THEN 1 END) as TotalARCustomers,
                    SUM(CASE WHEN AccountBalance > 0 THEN AccountBalance ELSE 0 END) as TotalARBalance,
                    COUNT(CASE WHEN AccountBalance > 10000 THEN 1 END) as HighBalanceCustomers,
                    SUM(CASE WHEN AccountBalance > 10000 THEN AccountBalance ELSE 0 END) as HighBalanceTotal,
                    AVG(CASE WHEN AccountBalance > 0 THEN AccountBalance END) as AvgARBalance
                FROM dbo.Customer
                """
                summary_stats = db.execute_query(summary_query).iloc[0] if not db.execute_query(summary_query).empty else {}
                
                # Convert all dataframes to safe dictionaries with float conversion
                def safe_dict_records(df):
                    if df.empty:
                        return []
                    records = df.to_dict('records')
                    # Convert any Decimal types to float
                    for record in records:
                        for key, value in record.items():
                            if hasattr(value, '__class__') and 'Decimal' in str(type(value)):
                                record[key] = float(value)
                            elif pd.isna(value):
                                record[key] = None
                    return records
                
                # Convert summary stats safely
                safe_summary = {}
                for key, value in dict(summary_stats).items():
                    if hasattr(value, '__class__') and 'Decimal' in str(type(value)):
                        safe_summary[key] = float(value)
                    elif pd.isna(value):
                        safe_summary[key] = None
                    else:
                        safe_summary[key] = value
                
                return {
                    'no_payment_customers': safe_dict_records(no_payment_customers),
                    'high_balance_customers': safe_dict_records(high_balance_customers),
                    'nsf_customers': safe_dict_records(nsf_customers),
                    'highest_ar_customers': safe_dict_records(highest_ar_customers),
                    'group_risks': safe_dict_records(group_risks),
                    'summary_stats': safe_summary,
                    'parameters': {
                        'days_no_payment': days_no_payment,
                        'balance_multiplier': balance_multiplier
                    },
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting risk overview: {e}")
            return {
                'error': str(e),
                'no_payment_customers': [],
                'high_balance_customers': [],
                'nsf_customers': [],
                'highest_ar_customers': [],
                'group_risks': [],
                'summary_stats': {},
                'generated_at': datetime.now().isoformat()
            }
    
    def get_customer_risk_summary(self, customer_id: int) -> dict:
        """Get quick risk summary for a specific customer"""
        try:
            with SQLServerConnection() as db:
                # Get customer basic info and key risk metrics
                query = f"""
                WITH CustomerRisk AS (
                    SELECT 
                        c.ID,
                        COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                        c.AccountBalance,
                        c.CreditLimit,
                        c.TotalSales,
                        c.PhoneNumber,
                        
                        -- Last payment (simplified)
                        (SELECT MAX(p.Time) 
                         FROM dbo.Payment p 
                         WHERE p.CustomerID = c.ID) as LastSuccessfulPayment,
                        
                        -- NSF Statistics (using $65 pattern)
                        (SELECT COUNT(*) 
                         FROM dbo.AccountReceivable ar
                         WHERE ar.CustomerID = c.ID 
                         AND ar.OriginalAmount = 65.00 
                         AND ar.TransactionNumber = 0) as NSFCount,
                        
                        (SELECT SUM(ar.OriginalAmount) 
                         FROM dbo.AccountReceivable ar
                         WHERE ar.CustomerID = c.ID 
                         AND ar.OriginalAmount = 65.00 
                         AND ar.TransactionNumber = 0) as NSFAmount,
                        
                        -- Recent sales activity (last 3 months)
                        (SELECT SUM(t.Total) 
                         FROM dbo.[Transaction] t 
                         WHERE t.CustomerID = c.ID 
                         AND t.Time >= DATEADD(month, -3, GETDATE())) as RecentSales
                         
                    FROM dbo.Customer c
                    WHERE c.ID = {customer_id}
                )
                SELECT *,
                    CASE 
                        WHEN LastSuccessfulPayment IS NULL THEN 9999
                        ELSE DATEDIFF(day, LastSuccessfulPayment, GETDATE())
                    END as DaysSinceLastPayment,
                    
                    CASE 
                        WHEN CreditLimit > 0 THEN (AccountBalance / CreditLimit) * 100
                        ELSE 0
                    END as CreditUtilization,
                    
                    CASE 
                        WHEN TotalSales > 0 THEN (AccountBalance / TotalSales) * 100
                        ELSE 0
                    END as BalanceToSalesRatio,
                    
                    CASE 
                        WHEN RecentSales > 0 THEN (AccountBalance / (RecentSales / 3.0))
                        ELSE 999.0
                    END as BalanceToMonthlySalesRatio
                    
                FROM CustomerRisk
                """
                
                result = db.execute_query(query)
                if result.empty:
                    return {'error': 'Customer not found'}
                
                customer = result.iloc[0].to_dict()
                
                # Calculate risk level
                risk_score = 0
                risk_factors = []
                
                # Days since payment factor (0-40 points)
                days_since_payment = customer['DaysSinceLastPayment']
                if days_since_payment >= 365:
                    risk_score += 40
                    risk_factors.append(f"No payment in {days_since_payment} days (CRITICAL)")
                elif days_since_payment >= 180:
                    risk_score += 30
                    risk_factors.append(f"No payment in {days_since_payment} days (HIGH)")
                elif days_since_payment >= 90:
                    risk_score += 20
                    risk_factors.append(f"No payment in {days_since_payment} days (MEDIUM)")
                elif days_since_payment >= 60:
                    risk_score += 10
                    risk_factors.append(f"No payment in {days_since_payment} days")
                
                # NSF factor (0-25 points)
                nsf_count = customer.get('NSFCount', 0) or 0
                if nsf_count >= 10:
                    risk_score += 25
                    risk_factors.append(f"Severe NSF history: {nsf_count} returns")
                elif nsf_count >= 5:
                    risk_score += 15
                    risk_factors.append(f"High NSF count: {nsf_count} returns")
                elif nsf_count >= 1:
                    risk_score += 5
                    risk_factors.append(f"NSF history: {nsf_count} returns")
                
                # Balance ratio factor (0-20 points)
                balance_ratio = customer.get('BalanceToMonthlySalesRatio', 0) or 0
                if balance_ratio >= 10:
                    risk_score += 20
                    risk_factors.append(f"Balance is {balance_ratio:.1f}x monthly sales")
                elif balance_ratio >= 5:
                    risk_score += 15
                    risk_factors.append(f"Balance is {balance_ratio:.1f}x monthly sales")
                elif balance_ratio >= 3:
                    risk_score += 10
                    risk_factors.append(f"Balance is {balance_ratio:.1f}x monthly sales")
                
                # Credit utilization factor (0-10 points)
                credit_util = customer.get('CreditUtilization', 0) or 0
                if credit_util >= 100:
                    risk_score += 10
                    risk_factors.append(f"Credit limit exceeded")
                elif credit_util >= 90:
                    risk_score += 7
                    risk_factors.append(f"High credit utilization: {credit_util:.0f}%")
                elif credit_util >= 75:
                    risk_score += 5
                    risk_factors.append(f"Credit utilization: {credit_util:.0f}%")
                
                # High balance factor (0-5 points)
                balance = customer.get('AccountBalance', 0) or 0
                if balance > 100000:
                    risk_score += 5
                    risk_factors.append(f"Very high balance: ${balance:,.0f}")
                elif balance > 50000:
                    risk_score += 3
                    risk_factors.append(f"High balance: ${balance:,.0f}")
                
                # Determine risk level
                if risk_score >= 75:
                    risk_level = "CRITICAL"
                    risk_color = "#dc2626"
                elif risk_score >= 50:
                    risk_level = "HIGH"
                    risk_color = "#ea580c"
                elif risk_score >= 25:
                    risk_level = "MEDIUM"
                    risk_color = "#d97706"
                else:
                    risk_level = "LOW"
                    risk_color = "#16a34a"
                
                return {
                    'customer_id': customer_id,
                    'customer_name': customer['CustomerName'],
                    'risk_score': min(100, risk_score),  # Cap at 100
                    'risk_level': risk_level,
                    'risk_color': risk_color,
                    'risk_factors': risk_factors,
                    'metrics': {
                        'account_balance': float(customer.get('AccountBalance', 0) or 0),
                        'days_since_payment': int(customer.get('DaysSinceLastPayment', 0) or 0),
                        'nsf_count': int(nsf_count),
                        'nsf_amount': float(customer.get('NSFAmount', 0) or 0),
                        'credit_utilization': round(float(credit_util), 1),
                        'balance_to_sales_ratio': round(float(customer.get('BalanceToSalesRatio', 0) or 0), 1),
                        'balance_to_monthly_sales_ratio': round(float(balance_ratio), 1),
                        'last_payment_date': customer.get('LastSuccessfulPayment')
                    },
                    'calculated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting customer risk summary for {customer_id}: {e}")
            return {
                'customer_id': customer_id,
                'error': str(e),
                'risk_score': -1,
                'risk_level': 'ERROR'
            }
    
    def search_customers_by_risk_criteria(self, criteria: dict) -> list:
        """Search customers based on specific risk criteria"""
        try:
            conditions = []
            params = []
            
            # Build WHERE conditions based on criteria
            if criteria.get('min_balance'):
                conditions.append("c.AccountBalance >= %s")
                params.append(criteria['min_balance'])
            
            if criteria.get('max_days_since_payment'):
                # This would require a subquery for last payment
                pass  # Implement if needed
            
            if criteria.get('min_nsf_count'):
                # This would require a subquery for NSF count
                pass  # Implement if needed
            
            # For now, return basic high-risk customers
            return self.get_risk_overview()['highest_ar_customers'][:20]
            
        except Exception as e:
            logger.error(f"Error searching customers by risk criteria: {e}")
            return []
