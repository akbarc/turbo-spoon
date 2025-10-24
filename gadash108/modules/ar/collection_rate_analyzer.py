"""
Historical Collection Rate Analyzer
Tracks and analyzes AR collection performance over different time periods
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection
from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class CollectionRateAnalyzer:
    """Analyzes historical collection rates and AR performance"""
    
    def get_collection_rates(self, period='mtd'):
        """
        Get collection rates for specified period
        Periods: 'mtd', '30d', '90d', '6m', '1y', 'ytd'
        """
        try:
            with SQLServerConnection() as db:
                # Determine date range
                end_date = datetime.now()
                if period == 'mtd':
                    start_date = datetime(end_date.year, end_date.month, 1)
                elif period == '30d':
                    start_date = end_date - timedelta(days=30)
                elif period == '90d':
                    start_date = end_date - timedelta(days=90)
                elif period == '6m':
                    start_date = end_date - timedelta(days=180)
                elif period == '1y':
                    start_date = end_date - timedelta(days=365)
                elif period == 'ytd':
                    start_date = datetime(end_date.year, 1, 1)
                else:
                    start_date = end_date - timedelta(days=30)
                
                # Get collection rate data
                query = """
                WITH ARCreated AS (
                    -- New AR created in period (from sales)
                    SELECT 
                        CAST(t.Time AS DATE) as Date,
                        SUM(t.Total) as NewAR
                    FROM [dbo].[Transaction] t
                    WHERE t.Time >= %s AND t.Time < %s
                        AND t.Total > 0
                    GROUP BY CAST(t.Time AS DATE)
                ),
                Collections AS (
                    -- Payments collected in period
                    SELECT 
                        CAST(p.Time AS DATE) as Date,
                        SUM(p.Amount) as Collected
                    FROM dbo.Payment p
                    WHERE p.Time >= %s AND p.Time < %s
                        AND p.Amount > 0
                        AND UPPER(p.Comment) NOT LIKE '%%NSF%%'
                        AND UPPER(p.Comment) NOT LIKE '%%RETURN%%'
                    GROUP BY CAST(p.Time AS DATE)
                ),
                DailyMetrics AS (
                    SELECT 
                        COALESCE(a.Date, c.Date) as Date,
                        ISNULL(a.NewAR, 0) as NewAR,
                        ISNULL(c.Collected, 0) as Collected
                    FROM ARCreated a
                    FULL OUTER JOIN Collections c ON a.Date = c.Date
                )
                SELECT 
                    -- Summary metrics
                    SUM(NewAR) as TotalNewAR,
                    SUM(Collected) as TotalCollected,
                    CASE 
                        WHEN SUM(NewAR) > 0 
                        THEN CAST(100.0 * SUM(Collected) / SUM(NewAR) AS DECIMAL(5,2))
                        ELSE 0 
                    END as CollectionRate,
                    AVG(Collected) as AvgDailyCollection,
                    MAX(Collected) as MaxDailyCollection,
                    MIN(Collected) as MinDailyCollection,
                    COUNT(DISTINCT Date) as DaysInPeriod,
                    -- Weekly average
                    SUM(Collected) / NULLIF(DATEDIFF(week, MIN(Date), MAX(Date)) + 1, 0) as AvgWeeklyCollection
                FROM DailyMetrics
                """
                
                result = db.execute_query(query, (start_date, end_date, start_date, end_date))
                
                if result.empty:
                    return self._empty_metrics()
                
                summary = result.iloc[0].to_dict()
                
                # Get daily breakdown for trend analysis
                daily_query = """
                WITH DailyData AS (
                    SELECT 
                        CAST(dates.Date AS DATE) as Date,
                        ISNULL(SUM(t.Total), 0) as NewAR,
                        ISNULL((
                            SELECT SUM(p.Amount) 
                            FROM dbo.Payment p 
                            WHERE CAST(p.Time AS DATE) = CAST(dates.Date AS DATE)
                                AND p.Amount > 0
                                AND UPPER(p.Comment) NOT LIKE '%%NSF%%'
                        ), 0) as Collected
                    FROM (
                        SELECT DISTINCT CAST(Time AS DATE) as Date
                        FROM [dbo].[Transaction]
                        WHERE Time >= %s AND Time < %s
                        UNION
                        SELECT DISTINCT CAST(Time AS DATE) as Date
                        FROM dbo.Payment
                        WHERE Time >= %s AND Time < %s
                    ) dates
                    LEFT JOIN [dbo].[Transaction] t ON CAST(t.Time AS DATE) = dates.Date
                    GROUP BY dates.Date
                )
                SELECT 
                    Date,
                    NewAR,
                    Collected,
                    SUM(NewAR) OVER (ORDER BY Date) as CumulativeAR,
                    SUM(Collected) OVER (ORDER BY Date) as CumulativeCollected,
                    CASE 
                        WHEN SUM(NewAR) OVER (ORDER BY Date) > 0
                        THEN CAST(100.0 * SUM(Collected) OVER (ORDER BY Date) / 
                             SUM(NewAR) OVER (ORDER BY Date) AS DECIMAL(5,2))
                        ELSE 0
                    END as RunningCollectionRate
                FROM DailyData
                ORDER BY Date
                """
                
                daily_data = db.execute_query(daily_query, (start_date, end_date, start_date, end_date))
                
                # Get aging-based collection analysis
                aging_query = """
                SELECT 
                    CASE 
                        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 Days'
                        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 Days'
                        WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 Days'
                        ELSE 'Over 90 Days'
                    END as AgingBucket,
                    COUNT(*) as InvoiceCount,
                    SUM(ar.OriginalAmount) as OriginalAmount,
                    SUM(ar.OriginalAmount - ar.Balance) as AmountCollected,
                    SUM(ar.Balance) as Outstanding,
                    CASE 
                        WHEN SUM(ar.OriginalAmount) > 0
                        THEN CAST(100.0 * SUM(ar.OriginalAmount - ar.Balance) / 
                             SUM(ar.OriginalAmount) AS DECIMAL(5,2))
                        ELSE 0
                    END as CollectionRate
                FROM dbo.AccountReceivable ar
                WHERE ar.Date >= %s
                GROUP BY CASE 
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30 Days'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60 Days'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90 Days'
                    ELSE 'Over 90 Days'
                END
                ORDER BY CASE 
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN 1
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN 2
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN 3
                    ELSE 4
                END
                """
                
                aging_data = db.execute_query(aging_query, (start_date,))
                
                # Get customer-level collection performance
                customer_query = """
                SELECT TOP 10
                    c.ID,
                    COALESCE(c.Company, c.FirstName + ' ' + c.LastName) as CustomerName,
                    SUM(t.Total) as TotalSales,
                    ISNULL((
                        SELECT SUM(p.Amount) 
                        FROM dbo.Payment p 
                        WHERE p.CustomerID = c.ID
                            AND p.Time >= %s
                            AND p.Amount > 0
                            AND UPPER(p.Comment) NOT LIKE '%%NSF%%'
                    ), 0) as TotalCollected,
                    c.AccountBalance as CurrentBalance,
                    CASE 
                        WHEN SUM(t.Total) > 0
                        THEN CAST(100.0 * ISNULL((
                            SELECT SUM(p.Amount) 
                            FROM dbo.Payment p 
                            WHERE p.CustomerID = c.ID
                                AND p.Time >= %s
                                AND p.Amount > 0
                                AND UPPER(p.Comment) NOT LIKE '%%NSF%%'
                        ), 0) / SUM(t.Total) AS DECIMAL(5,2))
                        ELSE 0
                    END as CollectionRate
                FROM dbo.Customer c
                INNER JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
                WHERE t.Time >= %s
                GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance
                HAVING SUM(t.Total) > 0
                ORDER BY SUM(t.Total) DESC
                """
                
                customer_data = db.execute_query(customer_query, (start_date, start_date, start_date))
                
                return {
                    'period': period,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'summary': summary,
                    'daily_trend': daily_data.to_dict('records') if not daily_data.empty else [],
                    'aging_analysis': aging_data.to_dict('records') if not aging_data.empty else [],
                    'top_customers': customer_data.to_dict('records') if not customer_data.empty else [],
                    'performance_indicators': self._calculate_performance_indicators(summary)
                }
                
        except Exception as e:
            logger.error(f"Error calculating collection rates: {e}")
            return self._empty_metrics()
    
    def _calculate_performance_indicators(self, summary):
        """Calculate performance indicators based on collection metrics"""
        collection_rate = summary.get('CollectionRate', 0)
        
        indicators = {
            'status': 'Good' if collection_rate >= 80 else 'Fair' if collection_rate >= 60 else 'Poor',
            'trend': 'Improving' if collection_rate >= 75 else 'Stable' if collection_rate >= 50 else 'Declining',
            'efficiency_score': min(100, collection_rate * 1.1),  # Slight boost for good performance
            'recommendations': []
        }
        
        if collection_rate < 60:
            indicators['recommendations'].append("Consider implementing stricter credit policies")
            indicators['recommendations'].append("Increase collection follow-up frequency")
        elif collection_rate < 80:
            indicators['recommendations'].append("Review credit limits for high-risk customers")
            indicators['recommendations'].append("Consider offering early payment discounts")
        else:
            indicators['recommendations'].append("Maintain current collection practices")
            indicators['recommendations'].append("Consider rewarding prompt payers")
        
        return indicators
    
    def _empty_metrics(self):
        """Return empty metrics structure"""
        return {
            'period': 'unknown',
            'summary': {
                'TotalNewAR': 0,
                'TotalCollected': 0,
                'CollectionRate': 0,
                'AvgDailyCollection': 0
            },
            'daily_trend': [],
            'aging_analysis': [],
            'top_customers': [],
            'performance_indicators': {
                'status': 'Unknown',
                'trend': 'Unknown',
                'efficiency_score': 0,
                'recommendations': []
            }
        }