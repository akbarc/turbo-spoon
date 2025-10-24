"""
Comprehensive Customer Analytics Module
Provides detailed insights into customer sales, payments, receivables, and patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

class PaymentBehavior(Enum):
    """Customer payment behavior classifications"""
    EXCELLENT = "Excellent"  # Pays early or on time consistently
    GOOD = "Good"  # Mostly on time, occasional delays
    FAIR = "Fair"  # Regular delays but eventually pays
    POOR = "Poor"  # Significant delays, collection issues
    RISK = "High Risk"  # Major collection problems, NSF history

class CustomerSegment(Enum):
    """Customer business segments"""
    VIP = "VIP"  # High value, loyal customers
    GROWTH = "Growth"  # Growing purchase volume
    STABLE = "Stable"  # Consistent purchasing
    DECLINING = "Declining"  # Decreasing activity
    DORMANT = "Dormant"  # No recent activity
    NEW = "New"  # Recently acquired

@dataclass
class CustomerMetrics:
    """Core customer metrics"""
    customer_id: int
    name: str
    segment: CustomerSegment
    payment_behavior: PaymentBehavior
    risk_score: float  # 0-100, higher is riskier
    credit_recommendation: float
    lifetime_value: float
    days_to_pay_avg: float
    payment_consistency: float  # Standard deviation of payment days
    nsf_count: int
    nsf_rate: float
    collection_probability: float  # Probability of collecting outstanding AR

class CustomerAnalytics:
    """Comprehensive customer analytics engine"""
    
    def __init__(self):
        self.db = SQLServerConnection()
        
    def get_customer_360_view(self, customer_id: int) -> Dict[str, Any]:
        """
        Get complete 360-degree view of a customer
        Includes all metrics, history, patterns, and predictions
        """
        try:
            # Core customer information
            customer_info = self._get_customer_info(customer_id)
            
            # Sales analytics
            sales_metrics = self._get_sales_metrics(customer_id)
            
            # Payment analytics
            payment_metrics = self._get_payment_metrics(customer_id)
            
            # Receivables analytics
            receivables_metrics = self._get_receivables_metrics(customer_id)
            
            # Pattern detection
            patterns = self._detect_patterns(customer_id)
            
            # Risk assessment
            risk_assessment = self._assess_risk(customer_id)
            
            # Predictions
            predictions = self._generate_predictions(customer_id)
            
            # Recommendations
            recommendations = self._generate_recommendations(customer_id)
            
            return {
                'customer': customer_info,
                'sales': sales_metrics,
                'payments': payment_metrics,
                'receivables': receivables_metrics,
                'patterns': patterns,
                'risk': risk_assessment,
                'predictions': predictions,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting customer 360 view: {e}")
            return {}
    
    def _get_customer_info(self, customer_id: int) -> Dict:
        """Get basic customer information"""
        with self.db:
            query = """
            SELECT 
                c.ID,
                c.Company,
                c.FirstName,
                c.LastName,
                c.PhoneNumber,
                c.Email,
                c.Address,
                c.City,
                c.State,
                c.Zip,
                c.AccountBalance,
                c.CreditLimit,
                c.TotalSales,
                c.LastVisit,
                c.DateCreated,
                DATEDIFF(day, c.DateCreated, GETDATE()) as customer_age_days,
                c.SalesmanID,
                s.Name as SalesmanName,
                -- Customer classification
                CASE 
                    WHEN c.TotalSales > 1000000 THEN 'Enterprise'
                    WHEN c.TotalSales > 500000 THEN 'Large'
                    WHEN c.TotalSales > 100000 THEN 'Medium'
                    WHEN c.TotalSales > 10000 THEN 'Small'
                    ELSE 'Micro'
                END as customer_size,
                -- Activity status
                CASE
                    WHEN DATEDIFF(day, c.LastVisit, GETDATE()) <= 30 THEN 'Active'
                    WHEN DATEDIFF(day, c.LastVisit, GETDATE()) <= 90 THEN 'Recent'
                    WHEN DATEDIFF(day, c.LastVisit, GETDATE()) <= 180 THEN 'Inactive'
                    ELSE 'Dormant'
                END as activity_status
            FROM dbo.Customer c
            LEFT JOIN dbo.Salesman s ON c.SalesmanID = s.ID
            WHERE c.ID = %s
            """
            
            result = self.db.execute_query(query, [customer_id])
            if not result.empty:
                return result.iloc[0].to_dict()
            return {}
    
    def _get_sales_metrics(self, customer_id: int) -> Dict:
        """Get comprehensive sales metrics for customer"""
        with self.db:
            # Overall sales metrics
            overall_query = """
            WITH SalesMetrics AS (
                SELECT 
                    COUNT(DISTINCT t.ID) as total_transactions,
                    COUNT(DISTINCT CAST(t.Time as DATE)) as active_days,
                    SUM(t.Total) as total_revenue,
                    AVG(t.Total) as avg_transaction_value,
                    MAX(t.Total) as max_transaction_value,
                    MIN(t.Total) as min_transaction_value,
                    STDEV(t.Total) as transaction_value_std,
                    MAX(t.Time) as last_purchase_date,
                    MIN(t.Time) as first_purchase_date,
                    DATEDIFF(day, MIN(t.Time), MAX(t.Time)) as customer_lifetime_days
                FROM dbo.[Transaction] t
                WHERE t.CustomerID = %s
                    AND t.Status = 1
            ),
            MonthlyTrend AS (
                SELECT 
                    YEAR(Time) as year,
                    MONTH(Time) as month,
                    SUM(Total) as monthly_revenue,
                    COUNT(*) as monthly_transactions
                FROM dbo.[Transaction]
                WHERE CustomerID = %s
                    AND Status = 1
                    AND Time >= DATEADD(month, -12, GETDATE())
                GROUP BY YEAR(Time), MONTH(Time)
            ),
            ProductMix AS (
                SELECT TOP 10
                    td.ItemID,
                    i.Description as ItemName,
                    COUNT(*) as purchase_count,
                    SUM(td.Quantity) as total_quantity,
                    SUM(td.Total) as product_revenue,
                    AVG(td.Price) as avg_price
                FROM dbo.TransactionDetail td
                JOIN dbo.[Transaction] t ON td.TransactionID = t.ID
                LEFT JOIN dbo.Inventory i ON td.ItemID = i.ID
                WHERE t.CustomerID = %s
                    AND t.Status = 1
                GROUP BY td.ItemID, i.Description
                ORDER BY SUM(td.Total) DESC
            ),
            CategoryMix AS (
                SELECT TOP 5
                    i.Category,
                    COUNT(DISTINCT td.ItemID) as unique_items,
                    SUM(td.Quantity) as total_quantity,
                    SUM(td.Total) as category_revenue
                FROM dbo.TransactionDetail td
                JOIN dbo.[Transaction] t ON td.TransactionID = t.ID
                LEFT JOIN dbo.Inventory i ON td.ItemID = i.ID
                WHERE t.CustomerID = %s
                    AND t.Status = 1
                GROUP BY i.Category
                ORDER BY SUM(td.Total) DESC
            )
            SELECT 
                sm.*,
                -- Purchase frequency
                CASE 
                    WHEN sm.customer_lifetime_days > 0 
                    THEN sm.total_transactions * 30.0 / sm.customer_lifetime_days
                    ELSE 0
                END as transactions_per_month,
                -- Growth rate (comparing last 3 months to previous 3 months)
                (
                    SELECT 
                        CASE 
                            WHEN SUM(CASE WHEN Time >= DATEADD(month, -6, GETDATE()) 
                                          AND Time < DATEADD(month, -3, GETDATE()) 
                                     THEN Total ELSE 0 END) > 0
                            THEN (
                                SUM(CASE WHEN Time >= DATEADD(month, -3, GETDATE()) 
                                        THEN Total ELSE 0 END) - 
                                SUM(CASE WHEN Time >= DATEADD(month, -6, GETDATE()) 
                                          AND Time < DATEADD(month, -3, GETDATE()) 
                                        THEN Total ELSE 0 END)
                            ) * 100.0 / 
                            SUM(CASE WHEN Time >= DATEADD(month, -6, GETDATE()) 
                                      AND Time < DATEADD(month, -3, GETDATE()) 
                                THEN Total ELSE 0 END)
                            ELSE 0
                        END
                    FROM dbo.[Transaction]
                    WHERE CustomerID = %s AND Status = 1
                ) as quarterly_growth_rate
            FROM SalesMetrics sm
            """
            
            result = self.db.execute_query(overall_query, [customer_id] * 5)
            
            # Get monthly trend data
            trend_query = """
            SELECT 
                YEAR(Time) as year,
                MONTH(Time) as month,
                SUM(Total) as revenue,
                COUNT(*) as transactions,
                AVG(Total) as avg_transaction
            FROM dbo.[Transaction]
            WHERE CustomerID = %s
                AND Status = 1
                AND Time >= DATEADD(month, -12, GETDATE())
            GROUP BY YEAR(Time), MONTH(Time)
            ORDER BY year, month
            """
            trend_data = self.db.execute_query(trend_query, [customer_id])
            
            # Get product preferences
            product_query = """
            SELECT TOP 10
                i.Description as product,
                i.Category,
                COUNT(*) as purchase_count,
                SUM(td.Quantity) as total_quantity,
                SUM(td.Total) as revenue,
                MAX(t.Time) as last_purchased
            FROM dbo.TransactionDetail td
            JOIN dbo.[Transaction] t ON td.TransactionID = t.ID
            LEFT JOIN dbo.Inventory i ON td.ItemID = i.ID
            WHERE t.CustomerID = %s
                AND t.Status = 1
            GROUP BY i.Description, i.Category
            ORDER BY SUM(td.Total) DESC
            """
            products = self.db.execute_query(product_query, [customer_id])
            
            return {
                'overview': result.iloc[0].to_dict() if not result.empty else {},
                'monthly_trend': trend_data.to_dict('records'),
                'top_products': products.to_dict('records'),
                'seasonality': self._detect_seasonality(customer_id)
            }
    
    def _get_payment_metrics(self, customer_id: int) -> Dict:
        """Get comprehensive payment metrics and behavior analysis"""
        with self.db:
            query = """
            WITH PaymentHistory AS (
                SELECT 
                    p.ID,
                    p.Time as payment_date,
                    p.Amount,
                    p.Type,
                    p.Number as check_number,
                    p.Comment,
                    -- Find the invoice this payment applies to
                    ar.Date as invoice_date,
                    DATEDIFF(day, ar.Date, p.Time) as days_to_pay,
                    -- Payment characteristics
                    CASE 
                        WHEN p.Comment LIKE '%NSF%' OR p.Comment LIKE '%RETURN%' THEN 1
                        ELSE 0
                    END as is_nsf,
                    CASE
                        WHEN p.Comment LIKE '%PD%' OR p.Comment LIKE '%POST%DATE%' THEN 1
                        ELSE 0
                    END as is_postdated,
                    DATEPART(dw, p.Time) as payment_day_of_week,
                    DATEPART(day, p.Time) as payment_day_of_month
                FROM dbo.Payment p
                LEFT JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                    AND ar.Date <= p.Time
                    AND ar.Date >= DATEADD(day, -120, p.Time)
                WHERE p.CustomerID = %s
            ),
            PaymentStats AS (
                SELECT 
                    COUNT(*) as total_payments,
                    COUNT(DISTINCT CAST(payment_date as DATE)) as payment_days,
                    SUM(Amount) as total_paid,
                    AVG(Amount) as avg_payment,
                    MAX(Amount) as max_payment,
                    MIN(Amount) as min_payment,
                    STDEV(Amount) as payment_std,
                    AVG(days_to_pay) as avg_days_to_pay,
                    STDEV(days_to_pay) as payment_timing_consistency,
                    MAX(payment_date) as last_payment_date,
                    SUM(is_nsf) as nsf_count,
                    SUM(CASE WHEN is_nsf = 1 THEN Amount ELSE 0 END) as nsf_amount,
                    SUM(is_postdated) as postdated_count,
                    -- Payment timing analysis
                    AVG(CASE WHEN days_to_pay <= 30 THEN 1.0 ELSE 0 END) * 100 as pct_on_time,
                    AVG(CASE WHEN days_to_pay > 30 AND days_to_pay <= 60 THEN 1.0 ELSE 0 END) * 100 as pct_30_60_days,
                    AVG(CASE WHEN days_to_pay > 60 AND days_to_pay <= 90 THEN 1.0 ELSE 0 END) * 100 as pct_60_90_days,
                    AVG(CASE WHEN days_to_pay > 90 THEN 1.0 ELSE 0 END) * 100 as pct_over_90_days,
                    -- Payment patterns
                    MODE() WITHIN GROUP (ORDER BY payment_day_of_week) as most_common_payment_day,
                    MODE() WITHIN GROUP (ORDER BY payment_day_of_month) as most_common_day_of_month
                FROM PaymentHistory
            ),
            RecentTrend AS (
                SELECT 
                    AVG(days_to_pay) as recent_avg_days_to_pay,
                    COUNT(*) as recent_payment_count
                FROM (
                    SELECT TOP 10 days_to_pay
                    FROM PaymentHistory
                    WHERE days_to_pay IS NOT NULL
                    ORDER BY payment_date DESC
                ) recent
            )
            SELECT 
                ps.*,
                rt.recent_avg_days_to_pay,
                rt.recent_payment_count,
                -- Payment behavior score (0-100, 100 is best)
                CASE
                    WHEN ps.avg_days_to_pay IS NULL THEN 50
                    WHEN ps.avg_days_to_pay <= 10 THEN 100
                    WHEN ps.avg_days_to_pay <= 30 THEN 90
                    WHEN ps.avg_days_to_pay <= 45 THEN 75
                    WHEN ps.avg_days_to_pay <= 60 THEN 60
                    WHEN ps.avg_days_to_pay <= 90 THEN 40
                    ELSE 20
                END - (ps.nsf_count * 10) as payment_score,
                -- Trend indicator
                CASE
                    WHEN rt.recent_avg_days_to_pay < ps.avg_days_to_pay - 5 THEN 'Improving'
                    WHEN rt.recent_avg_days_to_pay > ps.avg_days_to_pay + 5 THEN 'Deteriorating'
                    ELSE 'Stable'
                END as payment_trend
            FROM PaymentStats ps
            CROSS JOIN RecentTrend rt
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            # Get payment method preferences
            method_query = """
            SELECT 
                Type as payment_method,
                COUNT(*) as count,
                SUM(Amount) as total_amount,
                AVG(Amount) as avg_amount,
                MAX(Time) as last_used
            FROM dbo.Payment
            WHERE CustomerID = %s
            GROUP BY Type
            ORDER BY COUNT(*) DESC
            """
            methods = self.db.execute_query(method_query, [customer_id])
            
            # Get NSF/returns detail
            nsf_query = """
            SELECT 
                Time as date,
                Amount,
                Comment,
                CASE 
                    WHEN Comment LIKE '%NSF%' THEN 'NSF'
                    WHEN Comment LIKE '%RETURN%' THEN 'Returned'
                    ELSE 'Other'
                END as return_type
            FROM dbo.Payment
            WHERE CustomerID = %s
                AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')
            ORDER BY Time DESC
            """
            nsf_detail = self.db.execute_query(nsf_query, [customer_id])
            
            return {
                'summary': result.iloc[0].to_dict() if not result.empty else {},
                'payment_methods': methods.to_dict('records'),
                'nsf_returns': nsf_detail.to_dict('records'),
                'behavior_classification': self._classify_payment_behavior(result.iloc[0] if not result.empty else {})
            }
    
    def _get_receivables_metrics(self, customer_id: int) -> Dict:
        """Get detailed receivables analysis"""
        with self.db:
            # Current AR aging
            aging_query = """
            SELECT 
                SUM(Balance) as total_ar,
                COUNT(*) as open_invoices,
                MIN(Date) as oldest_invoice_date,
                MAX(Date) as newest_invoice_date,
                AVG(DATEDIFF(day, Date, GETDATE())) as avg_invoice_age,
                -- Aging buckets
                SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN Balance ELSE 0 END) as current_ar,
                SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 30 AND DATEDIFF(day, Date, GETDATE()) <= 60 
                    THEN Balance ELSE 0 END) as ar_31_60,
                SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 60 AND DATEDIFF(day, Date, GETDATE()) <= 90 
                    THEN Balance ELSE 0 END) as ar_61_90,
                SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 AND DATEDIFF(day, Date, GETDATE()) <= 120 
                    THEN Balance ELSE 0 END) as ar_91_120,
                SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 120 THEN Balance ELSE 0 END) as ar_over_120,
                -- Aging percentages
                CASE WHEN SUM(Balance) > 0 THEN
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN Balance ELSE 0 END) * 100.0 / SUM(Balance)
                ELSE 0 END as pct_current,
                CASE WHEN SUM(Balance) > 0 THEN
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN Balance ELSE 0 END) * 100.0 / SUM(Balance)
                ELSE 0 END as pct_over_90
            FROM dbo.AccountReceivable
            WHERE CustomerID = %s
                AND Balance > 0
            """
            aging = self.db.execute_query(aging_query, [customer_id])
            
            # Invoice detail
            invoice_query = """
            SELECT 
                ID as invoice_id,
                Date as invoice_date,
                Total as invoice_amount,
                Balance as outstanding_balance,
                DATEDIFF(day, Date, GETDATE()) as age_days,
                CASE 
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN 'Current'
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 60 THEN '31-60 days'
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 90 THEN '61-90 days'
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 120 THEN '91-120 days'
                    ELSE 'Over 120 days'
                END as aging_bucket,
                -- Collection probability based on age
                CASE 
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN 0.95
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 60 THEN 0.85
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 90 THEN 0.70
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 120 THEN 0.50
                    WHEN DATEDIFF(day, Date, GETDATE()) <= 180 THEN 0.30
                    ELSE 0.10
                END as collection_probability
            FROM dbo.AccountReceivable
            WHERE CustomerID = %s
                AND Balance > 0
            ORDER BY Date DESC
            """
            invoices = self.db.execute_query(invoice_query, [customer_id])
            
            # Historical collection patterns
            collection_query = """
            WITH Collections AS (
                SELECT 
                    ar.ID,
                    ar.Date as invoice_date,
                    ar.Total as invoice_amount,
                    p.Time as payment_date,
                    p.Amount as payment_amount,
                    DATEDIFF(day, ar.Date, p.Time) as days_to_collect
                FROM dbo.AccountReceivable ar
                JOIN dbo.Payment p ON ar.CustomerID = p.CustomerID
                    AND p.Time >= ar.Date
                    AND p.Time <= DATEADD(day, 180, ar.Date)
                WHERE ar.CustomerID = %s
                    AND ar.Balance = 0  -- Fully paid invoices
            )
            SELECT 
                AVG(days_to_collect) as avg_collection_days,
                STDEV(days_to_collect) as collection_consistency,
                MIN(days_to_collect) as fastest_collection,
                MAX(days_to_collect) as slowest_collection,
                COUNT(*) as collected_invoices
            FROM Collections
            """
            collection_patterns = self.db.execute_query(collection_query, [customer_id])
            
            return {
                'aging_summary': aging.iloc[0].to_dict() if not aging.empty else {},
                'open_invoices': invoices.to_dict('records'),
                'collection_patterns': collection_patterns.iloc[0].to_dict() if not collection_patterns.empty else {},
                'collection_forecast': self._forecast_collections(customer_id)
            }
    
    def _detect_patterns(self, customer_id: int) -> Dict:
        """Detect behavioral patterns in customer data"""
        with self.db:
            # Purchase patterns
            purchase_pattern_query = """
            WITH PurchasePatterns AS (
                SELECT 
                    DATEPART(year, Time) as year,
                    DATEPART(month, Time) as month,
                    DATEPART(week, Time) as week,
                    DATEPART(dw, Time) as day_of_week,
                    DATEPART(day, Time) as day_of_month,
                    COUNT(*) as transactions,
                    SUM(Total) as revenue
                FROM dbo.[Transaction]
                WHERE CustomerID = %s
                    AND Status = 1
                    AND Time >= DATEADD(month, -12, GETDATE())
                GROUP BY 
                    DATEPART(year, Time),
                    DATEPART(month, Time),
                    DATEPART(week, Time),
                    DATEPART(dw, Time),
                    DATEPART(day, Time)
            )
            SELECT 
                -- Day of week patterns
                (SELECT TOP 1 day_of_week FROM PurchasePatterns 
                 GROUP BY day_of_week ORDER BY SUM(revenue) DESC) as best_sales_day,
                (SELECT TOP 1 day_of_week FROM PurchasePatterns 
                 GROUP BY day_of_week ORDER BY COUNT(*) DESC) as most_frequent_day,
                -- Monthly patterns
                (SELECT TOP 1 day_of_month FROM PurchasePatterns 
                 WHERE day_of_month <= 10 
                 GROUP BY day_of_month ORDER BY SUM(revenue) DESC) as best_early_month_day,
                (SELECT TOP 1 day_of_month FROM PurchasePatterns 
                 WHERE day_of_month > 20 
                 GROUP BY day_of_month ORDER BY SUM(revenue) DESC) as best_late_month_day,
                -- Seasonal patterns
                (SELECT TOP 1 month FROM PurchasePatterns 
                 GROUP BY month ORDER BY SUM(revenue) DESC) as best_month,
                (SELECT TOP 1 month FROM PurchasePatterns 
                 GROUP BY month ORDER BY SUM(revenue) ASC) as worst_month
            """
            patterns = self.db.execute_query(purchase_pattern_query, [customer_id])
            
            # Order frequency pattern
            frequency_query = """
            WITH OrderGaps AS (
                SELECT 
                    Time,
                    LAG(Time) OVER (ORDER BY Time) as prev_order_date,
                    DATEDIFF(day, LAG(Time) OVER (ORDER BY Time), Time) as days_between_orders
                FROM dbo.[Transaction]
                WHERE CustomerID = %s
                    AND Status = 1
                    AND Time >= DATEADD(month, -6, GETDATE())
            )
            SELECT 
                AVG(days_between_orders) as avg_order_frequency,
                STDEV(days_between_orders) as frequency_consistency,
                MIN(days_between_orders) as min_gap,
                MAX(days_between_orders) as max_gap,
                -- Regularity score (lower is more regular)
                CASE 
                    WHEN AVG(days_between_orders) > 0 
                    THEN STDEV(days_between_orders) / AVG(days_between_orders)
                    ELSE NULL
                END as regularity_coefficient
            FROM OrderGaps
            WHERE days_between_orders IS NOT NULL
            """
            frequency = self.db.execute_query(frequency_query, [customer_id])
            
            return {
                'purchase_patterns': patterns.iloc[0].to_dict() if not patterns.empty else {},
                'order_frequency': frequency.iloc[0].to_dict() if not frequency.empty else {},
                'seasonality_index': self._calculate_seasonality_index(customer_id),
                'loyalty_indicators': self._calculate_loyalty_indicators(customer_id)
            }
    
    def _assess_risk(self, customer_id: int) -> Dict:
        """Comprehensive risk assessment"""
        with self.db:
            # Get all risk factors
            risk_query = """
            WITH RiskFactors AS (
                SELECT 
                    c.ID,
                    c.AccountBalance,
                    c.CreditLimit,
                    -- AR risk factors
                    (SELECT COUNT(*) FROM dbo.AccountReceivable 
                     WHERE CustomerID = c.ID AND Balance > 0 
                     AND DATEDIFF(day, Date, GETDATE()) > 90) as invoices_over_90,
                    (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                     WHERE CustomerID = c.ID AND Balance > 0 
                     AND DATEDIFF(day, Date, GETDATE()) > 90) as ar_over_90,
                    -- Payment risk factors
                    (SELECT COUNT(*) FROM dbo.Payment 
                     WHERE CustomerID = c.ID 
                     AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count,
                    (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                     FROM dbo.Payment p
                     JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                     WHERE p.CustomerID = c.ID) as avg_days_to_pay,
                    -- Business risk factors
                    DATEDIFF(day, c.LastVisit, GETDATE()) as days_since_last_visit,
                    (SELECT COUNT(*) FROM dbo.[Transaction] 
                     WHERE CustomerID = c.ID 
                     AND Time >= DATEADD(month, -3, GETDATE())) as recent_transactions,
                    -- Credit utilization
                    CASE 
                        WHEN c.CreditLimit > 0 
                        THEN c.AccountBalance * 100.0 / c.CreditLimit 
                        ELSE NULL 
                    END as credit_utilization
                FROM dbo.Customer c
                WHERE c.ID = %s
            )
            SELECT 
                *,
                -- Calculate risk score (0-100, higher is riskier)
                (
                    -- NSF risk (0-30 points)
                    CASE 
                        WHEN nsf_count = 0 THEN 0
                        WHEN nsf_count = 1 THEN 10
                        WHEN nsf_count = 2 THEN 20
                        ELSE 30
                    END +
                    -- Payment timing risk (0-25 points)
                    CASE 
                        WHEN avg_days_to_pay IS NULL THEN 10
                        WHEN avg_days_to_pay <= 30 THEN 0
                        WHEN avg_days_to_pay <= 60 THEN 10
                        WHEN avg_days_to_pay <= 90 THEN 20
                        ELSE 25
                    END +
                    -- AR aging risk (0-25 points)
                    CASE 
                        WHEN ar_over_90 IS NULL OR ar_over_90 = 0 THEN 0
                        WHEN ar_over_90 < 10000 THEN 10
                        WHEN ar_over_90 < 50000 THEN 20
                        ELSE 25
                    END +
                    -- Activity risk (0-20 points)
                    CASE 
                        WHEN recent_transactions >= 10 THEN 0
                        WHEN recent_transactions >= 5 THEN 5
                        WHEN recent_transactions >= 1 THEN 10
                        ELSE 20
                    END
                ) as risk_score,
                -- Risk classification
                CASE 
                    WHEN nsf_count > 2 OR ISNULL(ar_over_90, 0) > 100000 THEN 'High Risk'
                    WHEN nsf_count > 0 OR ISNULL(ar_over_90, 0) > 50000 THEN 'Medium Risk'
                    WHEN ISNULL(ar_over_90, 0) > 10000 OR ISNULL(avg_days_to_pay, 0) > 60 THEN 'Low Risk'
                    ELSE 'Minimal Risk'
                END as risk_level
            FROM RiskFactors
            """
            
            risk_data = self.db.execute_query(risk_query, [customer_id])
            
            return {
                'risk_assessment': risk_data.iloc[0].to_dict() if not risk_data.empty else {},
                'credit_recommendation': self._calculate_credit_recommendation(customer_id),
                'collection_strategy': self._recommend_collection_strategy(customer_id)
            }
    
    def _generate_predictions(self, customer_id: int) -> Dict:
        """Generate predictive analytics for customer"""
        with self.db:
            # Get historical data for predictions
            history_query = """
            WITH MonthlyData AS (
                SELECT 
                    YEAR(Time) as year,
                    MONTH(Time) as month,
                    SUM(Total) as revenue,
                    COUNT(*) as transactions
                FROM dbo.[Transaction]
                WHERE CustomerID = %s
                    AND Status = 1
                    AND Time >= DATEADD(month, -24, GETDATE())
                GROUP BY YEAR(Time), MONTH(Time)
            )
            SELECT 
                AVG(revenue) as avg_monthly_revenue,
                STDEV(revenue) as revenue_std,
                AVG(transactions) as avg_monthly_transactions,
                -- Calculate trend
                (SELECT TOP 1 revenue FROM MonthlyData ORDER BY year DESC, month DESC) as last_month_revenue,
                (SELECT AVG(revenue) FROM (SELECT TOP 3 revenue FROM MonthlyData ORDER BY year DESC, month DESC) recent) as last_3_months_avg,
                (SELECT AVG(revenue) FROM (SELECT TOP 6 revenue FROM MonthlyData ORDER BY year DESC, month DESC) recent) as last_6_months_avg
            FROM MonthlyData
            """
            history = self.db.execute_query(history_query, [customer_id])
            
            if not history.empty:
                data = history.iloc[0]
                
                # Simple predictions based on trends
                trend_factor = 1.0
                last_3_avg = data.get('last_3_months_avg')
                last_6_avg = data.get('last_6_months_avg')
                if last_3_avg is not None and last_6_avg is not None and last_6_avg > 0:
                    trend_factor = last_3_avg / last_6_avg
                
                next_month_revenue = float(data['avg_monthly_revenue'] or 0) * trend_factor
                next_quarter_revenue = next_month_revenue * 3
                
                # Payment prediction
                payment_query = """
                SELECT 
                    AVG(DATEDIFF(day, ar.Date, p.Time)) as avg_payment_days
                FROM dbo.Payment p
                JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                WHERE p.CustomerID = %s
                    AND p.Time >= DATEADD(month, -6, GETDATE())
                """
                payment_data = self.db.execute_query(payment_query, [customer_id])
                avg_payment_days = payment_data.iloc[0]['avg_payment_days'] if not payment_data.empty else 45
                
                # Get current AR
                ar_query = "SELECT SUM(Balance) as total_ar FROM dbo.AccountReceivable WHERE CustomerID = %s AND Balance > 0"
                ar_data = self.db.execute_query(ar_query, [customer_id])
                current_ar = float(ar_data.iloc[0]['total_ar'] or 0) if not ar_data.empty else 0
                
                return {
                    'next_month_revenue': next_month_revenue,
                    'next_quarter_revenue': next_quarter_revenue,
                    'expected_payment_date': (datetime.now() + timedelta(days=int(avg_payment_days or 45))).date().isoformat(),
                    'collection_amount_30_days': current_ar * 0.6,  # Assume 60% collection in 30 days
                    'collection_amount_60_days': current_ar * 0.85,  # 85% in 60 days
                    'churn_risk': self._calculate_churn_risk(customer_id),
                    'growth_potential': 'High' if trend_factor > 1.1 else 'Medium' if trend_factor > 0.9 else 'Low'
                }
            
            return {}
    
    def _generate_recommendations(self, customer_id: int) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        with self.db:
            # Get customer data for recommendations
            query = """
            SELECT 
                c.AccountBalance,
                c.CreditLimit,
                c.TotalSales,
                (SELECT AVG(Total) FROM dbo.[Transaction] 
                 WHERE CustomerID = c.ID AND Time >= DATEADD(month, -3, GETDATE())) as recent_avg_transaction,
                (SELECT COUNT(*) FROM dbo.Payment 
                 WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count,
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND Balance > 0 AND DATEDIFF(day, Date, GETDATE()) > 90) as ar_over_90,
                DATEDIFF(day, c.LastVisit, GETDATE()) as days_inactive
            FROM dbo.Customer c
            WHERE c.ID = %s
            """
            data = self.db.execute_query(query, [customer_id])
            
            if not data.empty:
                customer = data.iloc[0]
                
                # Credit limit recommendations
                if customer.get('CreditLimit') and customer['CreditLimit'] > 0:
                    utilization = customer['AccountBalance'] / customer['CreditLimit']
                    if utilization > 0.9:
                        recommendations.append({
                            'type': 'credit_limit',
                            'priority': 'high',
                            'action': 'Review credit limit - currently at ' + f"{utilization*100:.0f}% utilization",
                            'impact': 'May improve sales by removing purchasing constraints'
                        })
                
                # Collection recommendations
                if customer.get('ar_over_90') and customer['ar_over_90'] > 0:
                    recommendations.append({
                        'type': 'collection',
                        'priority': 'urgent',
                        'action': f"Escalate collection efforts - ${customer['ar_over_90']:,.2f} over 90 days",
                        'impact': 'Reduce bad debt risk and improve cash flow'
                    })
                
                # NSF handling
                if customer.get('nsf_count') and customer['nsf_count'] > 0:
                    recommendations.append({
                        'type': 'payment_terms',
                        'priority': 'high',
                        'action': 'Consider requiring certified funds or ACH payments',
                        'impact': 'Reduce NSF occurrences and processing costs'
                    })
                
                # Engagement recommendations
                if customer.get('days_inactive') and customer['days_inactive'] > 90:
                    recommendations.append({
                        'type': 'engagement',
                        'priority': 'medium',
                        'action': f"Re-engagement needed - no activity for {customer['days_inactive']} days",
                        'impact': 'Prevent customer churn and restore revenue stream'
                    })
                
                # Sales opportunities
                if customer['recent_avg_transaction']:
                    # Check for upsell opportunities based on historical patterns
                    recommendations.append({
                        'type': 'sales',
                        'priority': 'low',
                        'action': 'Review purchase history for cross-sell opportunities',
                        'impact': 'Potential to increase average transaction value'
                    })
        
        return recommendations
    
    def _detect_seasonality(self, customer_id: int) -> Dict:
        """Detect seasonal patterns in customer purchases"""
        with self.db:
            query = """
            WITH MonthlyRevenue AS (
                SELECT 
                    MONTH(Time) as month,
                    SUM(Total) as revenue,
                    COUNT(*) as transactions
                FROM dbo.[Transaction]
                WHERE CustomerID = %s
                    AND Status = 1
                    AND Time >= DATEADD(year, -2, GETDATE())
                GROUP BY MONTH(Time)
            )
            SELECT 
                month,
                revenue,
                transactions,
                revenue / NULLIF((SELECT AVG(revenue) FROM MonthlyRevenue), 0) as seasonality_index
            FROM MonthlyRevenue
            ORDER BY month
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            if not result.empty:
                # Find peak and low seasons
                peak_month = result.loc[result['seasonality_index'].idxmax()]
                low_month = result.loc[result['seasonality_index'].idxmin()]
                
                return {
                    'has_seasonality': (peak_month['seasonality_index'] - low_month['seasonality_index']) > 0.5,
                    'peak_month': int(peak_month['month']),
                    'peak_index': float(peak_month['seasonality_index']),
                    'low_month': int(low_month['month']),
                    'low_index': float(low_month['seasonality_index']),
                    'monthly_indices': result.to_dict('records')
                }
            
            return {'has_seasonality': False}
    
    def _classify_payment_behavior(self, payment_data: Dict) -> str:
        """Classify customer payment behavior"""
        if not payment_data:
            return PaymentBehavior.RISK.value
        
        avg_days = payment_data.get('avg_days_to_pay', 999) if payment_data.get('avg_days_to_pay') is not None else 999
        nsf_count = payment_data.get('nsf_count', 0) if payment_data.get('nsf_count') is not None else 0
        payment_score = payment_data.get('payment_score', 0) if payment_data.get('payment_score') is not None else 0
        
        if nsf_count > 2 or avg_days > 90:
            return PaymentBehavior.RISK.value
        elif nsf_count > 0 or avg_days > 60:
            return PaymentBehavior.POOR.value
        elif avg_days > 45:
            return PaymentBehavior.FAIR.value
        elif avg_days > 30:
            return PaymentBehavior.GOOD.value
        else:
            return PaymentBehavior.EXCELLENT.value
    
    def _calculate_seasonality_index(self, customer_id: int) -> float:
        """Calculate seasonality strength (0-1, higher means more seasonal)"""
        seasonality = self._detect_seasonality(customer_id)
        if seasonality.get('has_seasonality'):
            return min((seasonality['peak_index'] - seasonality['low_index']) / 2, 1.0)
        return 0.0
    
    def _calculate_loyalty_indicators(self, customer_id: int) -> Dict:
        """Calculate customer loyalty metrics"""
        with self.db:
            query = """
            SELECT 
                DATEDIFF(day, MIN(Time), MAX(Time)) as customer_lifetime_days,
                COUNT(DISTINCT CAST(Time as DATE)) as active_days,
                COUNT(*) as total_transactions,
                DATEDIFF(day, MAX(Time), GETDATE()) as days_since_last_purchase,
                -- Consistency score
                COUNT(DISTINCT YEAR(Time) * 100 + MONTH(Time)) as active_months,
                DATEDIFF(month, MIN(Time), MAX(Time)) + 1 as total_months
            FROM dbo.[Transaction]
            WHERE CustomerID = %s AND Status = 1
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            if not result.empty:
                data = result.iloc[0]
                
                # Calculate loyalty score
                lifetime_score = min(data['customer_lifetime_days'] / 365, 1.0) * 30  # Max 30 points for tenure
                frequency_score = min(data['total_transactions'] / 100, 1.0) * 30  # Max 30 points for frequency
                consistency_score = (data['active_months'] / data['total_months']) * 20 if data['total_months'] > 0 else 0
                recency_score = max(0, 20 - (data['days_since_last_purchase'] / 10))  # Lose points for inactivity
                
                total_score = lifetime_score + frequency_score + consistency_score + recency_score
                
                return {
                    'loyalty_score': total_score,
                    'loyalty_level': 'Platinum' if total_score >= 80 else 'Gold' if total_score >= 60 else 'Silver' if total_score >= 40 else 'Bronze',
                    'lifetime_days': int(data['customer_lifetime_days']),
                    'purchase_consistency': float(data['active_months'] / data['total_months']) if data['total_months'] > 0 else 0,
                    'days_since_last_purchase': int(data['days_since_last_purchase'])
                }
            
            return {'loyalty_score': 0, 'loyalty_level': 'New'}
    
    def _forecast_collections(self, customer_id: int) -> Dict:
        """Forecast expected collections based on historical patterns"""
        with self.db:
            # Get historical collection rates
            query = """
            WITH CollectionRates AS (
                SELECT 
                    CASE 
                        WHEN DATEDIFF(day, ar.Date, p.Time) <= 30 THEN '0-30'
                        WHEN DATEDIFF(day, ar.Date, p.Time) <= 60 THEN '31-60'
                        WHEN DATEDIFF(day, ar.Date, p.Time) <= 90 THEN '61-90'
                        ELSE '90+'
                    END as collection_period,
                    COUNT(*) as invoice_count
                FROM dbo.AccountReceivable ar
                JOIN dbo.Payment p ON ar.CustomerID = p.CustomerID
                    AND p.Time >= ar.Date
                WHERE ar.CustomerID = %s
                    AND ar.Balance = 0
                GROUP BY CASE 
                    WHEN DATEDIFF(day, ar.Date, p.Time) <= 30 THEN '0-30'
                    WHEN DATEDIFF(day, ar.Date, p.Time) <= 60 THEN '31-60'
                    WHEN DATEDIFF(day, ar.Date, p.Time) <= 90 THEN '61-90'
                    ELSE '90+'
                END
            ),
            CurrentAR AS (
                SELECT 
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) <= 30 THEN Balance ELSE 0 END) as ar_0_30,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 30 AND DATEDIFF(day, Date, GETDATE()) <= 60 
                        THEN Balance ELSE 0 END) as ar_31_60,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 60 AND DATEDIFF(day, Date, GETDATE()) <= 90 
                        THEN Balance ELSE 0 END) as ar_61_90,
                    SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN Balance ELSE 0 END) as ar_90_plus
                FROM dbo.AccountReceivable
                WHERE CustomerID = %s AND Balance > 0
            )
            SELECT * FROM CurrentAR
            """
            
            ar_data = self.db.execute_query(query, [customer_id, customer_id])
            
            if not ar_data.empty:
                current = ar_data.iloc[0]
                
                # Apply historical collection rates (simplified)
                forecast = {
                    'next_30_days': float(current['ar_0_30'] or 0) * 0.8 + float(current['ar_31_60'] or 0) * 0.5,
                    'next_60_days': float(current['ar_0_30'] or 0) * 0.95 + float(current['ar_31_60'] or 0) * 0.8 + float(current['ar_61_90'] or 0) * 0.4,
                    'next_90_days': float(current['ar_0_30'] or 0) + float(current['ar_31_60'] or 0) * 0.9 + float(current['ar_61_90'] or 0) * 0.7 + float(current['ar_90_plus'] or 0) * 0.3,
                    'confidence': 'High' if current['ar_90_plus'] == 0 else 'Medium' if current['ar_90_plus'] < 10000 else 'Low'
                }
                
                return forecast
            
            return {}
    
    def _calculate_credit_recommendation(self, customer_id: int) -> float:
        """Calculate recommended credit limit based on payment history and sales volume"""
        with self.db:
            query = """
            SELECT 
                c.CreditLimit as current_limit,
                c.AccountBalance as current_balance,
                (SELECT AVG(Total) FROM (
                    SELECT TOP 3 SUM(Total) as Total
                    FROM dbo.[Transaction]
                    WHERE CustomerID = c.ID AND Status = 1
                    GROUP BY YEAR(Time), MONTH(Time)
                    ORDER BY YEAR(Time) DESC, MONTH(Time) DESC
                ) recent) as avg_monthly_purchases,
                (SELECT MAX(Total) FROM dbo.[Transaction] 
                 WHERE CustomerID = c.ID AND Status = 1) as max_transaction,
                (SELECT COUNT(*) FROM dbo.Payment 
                 WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count,
                (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                 FROM dbo.Payment p
                 JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                 WHERE p.CustomerID = c.ID) as avg_payment_days
            FROM dbo.Customer c
            WHERE c.ID = %s
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            if not result.empty:
                data = result.iloc[0]
                
                # Base recommendation on monthly purchases
                base_limit = float(data['avg_monthly_purchases'] or 0) * 1.5
                
                # Adjust based on payment behavior
                if data['nsf_count'] > 0:
                    base_limit *= 0.7  # Reduce for NSF history
                if data['avg_payment_days'] and data['avg_payment_days'] > 60:
                    base_limit *= 0.8  # Reduce for slow payment
                elif data['avg_payment_days'] and data['avg_payment_days'] < 30:
                    base_limit *= 1.2  # Increase for good payment
                
                # Round to nearest thousand
                return round(base_limit / 1000) * 1000
            
            return 0
    
    def _recommend_collection_strategy(self, customer_id: int) -> str:
        """Recommend collection strategy based on customer profile"""
        with self.db:
            query = """
            SELECT 
                c.AccountBalance,
                c.TotalSales,
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND DATEDIFF(day, Date, GETDATE()) > 90) as ar_over_90,
                (SELECT COUNT(*) FROM dbo.[Transaction] 
                 WHERE CustomerID = c.ID AND Time >= DATEADD(month, -3, GETDATE())) as recent_activity,
                (SELECT COUNT(*) FROM dbo.Payment 
                 WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count
            FROM dbo.Customer c
            WHERE c.ID = %s
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            if not result.empty:
                data = result.iloc[0]
                
                if data.get('ar_over_90') and data['ar_over_90'] > 50000:
                    return "Escalate to management - consider legal action if no response within 7 days"
                elif data.get('nsf_count', 0) > 1:
                    return "Require certified funds or wire transfer for future orders"
                elif data.get('recent_activity', 0) == 0:
                    return "Combine collection efforts with re-engagement campaign"
                elif data.get('ar_over_90') and data['ar_over_90'] > 10000:
                    return "Increase contact frequency - call twice weekly until payment plan established"
                else:
                    return "Standard collection process - monthly statements with follow-up calls"
            
            return "Unable to determine strategy - manual review recommended"
    
    def _calculate_churn_risk(self, customer_id: int) -> str:
        """Calculate customer churn risk"""
        with self.db:
            query = """
            SELECT 
                DATEDIFF(day, MAX(Time), GETDATE()) as days_since_last_purchase,
                COUNT(*) as total_transactions,
                AVG(DATEDIFF(day, LAG(Time) OVER (ORDER BY Time), Time)) as avg_days_between_purchases
            FROM dbo.[Transaction]
            WHERE CustomerID = %s AND Status = 1
            GROUP BY CustomerID
            """
            
            result = self.db.execute_query(query, [customer_id])
            
            if not result.empty:
                data = result.iloc[0]
                
                avg_days = data.get('avg_days_between_purchases')
                days_since = data.get('days_since_last_purchase', 0)
                
                if avg_days and avg_days > 0:
                    expected_days = avg_days * 2
                    
                    if days_since and days_since > expected_days * 2:
                        return 'High'
                    elif days_since and days_since > expected_days:
                        return 'Medium'
                    else:
                        return 'Low'
            
            return 'Unknown'
    
    def get_bulk_customer_metrics(self, customer_ids: List[int] = None) -> pd.DataFrame:
        """Get metrics for multiple customers at once for dashboard views"""
        with self.db:
            id_filter = ""
            params = []
            if customer_ids:
                placeholders = ','.join(['%s'] * len(customer_ids))
                id_filter = f"WHERE c.ID IN ({placeholders})"
                params = customer_ids
            
            query = f"""
            SELECT 
                c.ID as customer_id,
                c.Company as company,
                COALESCE(c.FirstName + ' ' + c.LastName, '') as contact_name,
                c.AccountBalance as ar_balance,
                c.CreditLimit as credit_limit,
                c.TotalSales as lifetime_sales,
                -- Payment metrics
                (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                 FROM dbo.Payment p
                 JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                 WHERE p.CustomerID = c.ID) as avg_days_to_pay,
                (SELECT COUNT(*) FROM dbo.Payment 
                 WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count,
                -- AR aging
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND Balance > 0 
                 AND DATEDIFF(day, Date, GETDATE()) <= 30) as ar_current,
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND Balance > 0 
                 AND DATEDIFF(day, Date, GETDATE()) > 30 
                 AND DATEDIFF(day, Date, GETDATE()) <= 60) as ar_31_60,
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND Balance > 0 
                 AND DATEDIFF(day, Date, GETDATE()) > 60 
                 AND DATEDIFF(day, Date, GETDATE()) <= 90) as ar_61_90,
                (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                 WHERE CustomerID = c.ID AND Balance > 0 
                 AND DATEDIFF(day, Date, GETDATE()) > 90) as ar_over_90,
                -- Activity
                DATEDIFF(day, c.LastVisit, GETDATE()) as days_since_last_visit,
                (SELECT COUNT(*) FROM dbo.[Transaction] 
                 WHERE CustomerID = c.ID 
                 AND Time >= DATEADD(month, -3, GETDATE())) as recent_transactions,
                -- Risk score
                (
                    CASE WHEN (SELECT COUNT(*) FROM dbo.Payment WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) > 0 THEN 30 ELSE 0 END +
                    CASE 
                        WHEN (SELECT AVG(DATEDIFF(day, ar.Date, p.Time)) FROM dbo.Payment p JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID WHERE p.CustomerID = c.ID) > 90 THEN 25
                        WHEN (SELECT AVG(DATEDIFF(day, ar.Date, p.Time)) FROM dbo.Payment p JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID WHERE p.CustomerID = c.ID) > 60 THEN 15
                        WHEN (SELECT AVG(DATEDIFF(day, ar.Date, p.Time)) FROM dbo.Payment p JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID WHERE p.CustomerID = c.ID) > 30 THEN 5
                        ELSE 0
                    END +
                    CASE WHEN (SELECT SUM(Balance) FROM dbo.AccountReceivable WHERE CustomerID = c.ID AND Balance > 0 AND DATEDIFF(day, Date, GETDATE()) > 90) > 50000 THEN 25 ELSE 0 END
                ) as risk_score
            FROM dbo.Customer c
            {id_filter}
            ORDER BY c.AccountBalance DESC
            """
            
            return self.db.execute_query(query, params)

# Helper functions for integration with other modules
def get_customer_analytics_summary(customer_id: int) -> Dict:
    """Quick helper to get customer summary for dashboards"""
    analytics = CustomerAnalytics()
    return analytics.get_customer_360_view(customer_id)

def get_customer_risk_scores(customer_ids: List[int] = None) -> pd.DataFrame:
    """Get risk scores for multiple customers"""
    analytics = CustomerAnalytics()
    return analytics.get_bulk_customer_metrics(customer_ids)