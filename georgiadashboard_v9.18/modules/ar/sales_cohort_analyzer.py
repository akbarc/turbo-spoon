"""
Sales Cohort Collection Analysis System
Tracks how sales from specific periods convert to collections over time
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
from dataclasses import dataclass
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

@dataclass
class CohortMetrics:
    """Metrics for a sales cohort"""
    cohort_week: str
    sales_amount: float
    collections_by_week: Dict[int, float]  # Week offset -> amount collected
    cumulative_collection_rate: Dict[int, float]  # Week offset -> cumulative %
    dso: float
    total_collected: float
    total_outstanding: float
    collection_velocity: float  # % collected in first 30 days

class SalesCohortAnalyzer:
    """Analyzes collection patterns by sales cohort"""
    
    def __init__(self, lookback_weeks: int = 52, max_collection_weeks: int = 26, 
                 start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        Initialize the analyzer
        
        Args:
            lookback_weeks: How many weeks of history to analyze
            max_collection_weeks: Maximum weeks to track collections after sale
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
        """
        self.lookback_weeks = lookback_weeks
        self.max_collection_weeks = max_collection_weeks
        self.start_date = start_date
        self.end_date = end_date
        
    def get_sales_cohorts(self) -> pd.DataFrame:
        """
        Get weekly sales cohorts with their collection patterns
        Track collections from customers who made purchases in each week
        """
        with SQLServerConnection() as db:
            # Build date filter clause - SQL Server 2008 R2 uses %s for parameters
            if self.start_date and self.end_date:
                date_filter = "Time >= %s AND Time <= %s"
                params = [self.start_date, self.end_date]
            else:
                date_filter = "Time >= DATEADD(week, -%s, GETDATE()) AND Time < GETDATE()"
                params = [self.lookback_weeks]
            
            # Track sales cohorts and subsequent collections from those customers
            query = f"""
            WITH WeeklySales AS (
                -- Group sales by week and customer
                SELECT 
                    DATEPART(year, Time) as SalesYear,
                    DATEPART(week, Time) as SalesWeek,
                    MIN(CAST(Time as DATE)) as WeekStartDate,
                    MAX(CAST(Time as DATE)) as WeekEndDate,
                    CustomerID,
                    SUM(Total) as CustomerSales
                FROM [Transaction]
                WHERE {date_filter}
                    AND Total > 0  -- Only positive sales
                GROUP BY DATEPART(year, Time), DATEPART(week, Time), CustomerID
            ),
            WeeklySalesTotals AS (
                -- Total sales per week
                SELECT 
                    SalesYear,
                    SalesWeek,
                    MIN(WeekStartDate) as WeekStartDate,
                    MAX(WeekEndDate) as WeekEndDate,
                    COUNT(DISTINCT CustomerID) as CustomerCount,
                    SUM(CustomerSales) as TotalSales
                FROM WeeklySales
                GROUP BY SalesYear, SalesWeek
            ),
            WeeklyCollections AS (
                -- Track collections from customers who bought in each week
                SELECT 
                    ws.SalesYear,
                    ws.SalesWeek,
                    DATEDIFF(week, ws.WeekStartDate, CAST(p.Time as DATE)) as WeeksAfterSale,
                    SUM(p.Amount * (ws.CustomerSales / cs.TotalCustomerSales)) as CollectionAmount
                FROM WeeklySales ws
                INNER JOIN (
                    -- Get total sales per customer for proportional allocation
                    SELECT CustomerID, SUM(CustomerSales) as TotalCustomerSales
                    FROM WeeklySales
                    GROUP BY CustomerID
                ) cs ON cs.CustomerID = ws.CustomerID
                INNER JOIN Payment p ON p.CustomerID = ws.CustomerID
                WHERE p.Time >= ws.WeekStartDate
                    AND DATEDIFF(week, ws.WeekStartDate, CAST(p.Time as DATE)) >= 0
                    AND DATEDIFF(week, ws.WeekStartDate, CAST(p.Time as DATE)) <= %s
                GROUP BY ws.SalesYear, ws.SalesWeek, ws.WeekStartDate,
                         DATEDIFF(week, ws.WeekStartDate, CAST(p.Time as DATE))
            )
            SELECT 
                wst.*,
                wc.WeeksAfterSale,
                ISNULL(wc.CollectionAmount, 0) as CollectionAmount,
                ISNULL(wc.CollectionAmount, 0) / NULLIF(wst.TotalSales, 0) as CollectionRate
            FROM WeeklySalesTotals wst
            LEFT JOIN WeeklyCollections wc
                ON wst.SalesYear = wc.SalesYear 
                AND wst.SalesWeek = wc.SalesWeek
            ORDER BY wst.WeekStartDate DESC, wc.WeeksAfterSale
            """
            
            # Add max_collection_weeks parameter
            params.append(self.max_collection_weeks)
            
            df = db.execute_query(query, params)
            
            # Convert Decimal types to float
            for col in df.columns:
                if df[col].dtype == object:
                    try:
                        df[col] = df[col].apply(lambda x: float(x) if hasattr(x, 'real') else x)
                    except:
                        pass
                        
            return df
    
    def analyze_collection_patterns(self) -> Dict[str, Any]:
        """
        Analyze collection patterns across all cohorts
        """
        cohorts_df = self.get_sales_cohorts()
        
        if cohorts_df.empty:
            logger.warning("No cohort data available")
            return {}
        
        # Group by cohort and analyze
        cohort_metrics = {}
        
        for (year, week), group in cohorts_df.groupby(['SalesYear', 'SalesWeek']):
            cohort_key = f"{year}-W{week:02d}"
            sales_amount = group['TotalSales'].iloc[0] if not group.empty else 0
            
            # Collections by week offset
            collections = {}
            cumulative = 0
            cumulative_rates = {}
            
            for _, row in group.iterrows():
                if pd.notna(row['WeeksAfterSale']) and pd.notna(row['CollectionAmount']):
                    week_offset = int(row['WeeksAfterSale'])
                    amount = float(row['CollectionAmount'])
                    collections[week_offset] = amount
                    cumulative += amount
                    cumulative_rates[week_offset] = (cumulative / sales_amount * 100) if sales_amount > 0 else 0
            
            # Calculate metrics
            total_collected = sum(collections.values())
            # Collection velocity = % collected in first 4 weeks (weeks 0, 1, 2, 3)
            collection_velocity = sum(v for k, v in collections.items() if k < 4) / sales_amount * 100 if sales_amount > 0 else 0
            
            # Calculate DSO (weighted average days to collect)
            weighted_days = sum(week * 7 * amount for week, amount in collections.items())
            dso = weighted_days / total_collected if total_collected > 0 else 0
            
            cohort_metrics[cohort_key] = CohortMetrics(
                cohort_week=cohort_key,
                sales_amount=sales_amount,
                collections_by_week=collections,
                cumulative_collection_rate=cumulative_rates,
                dso=dso,
                total_collected=total_collected,
                total_outstanding=sales_amount - total_collected,
                collection_velocity=collection_velocity
            )
        
        # Calculate average patterns
        avg_pattern = self._calculate_average_pattern(cohort_metrics)
        
        # Identify trends
        trends = self._analyze_trends(cohort_metrics)
        
        # Generate predictions
        predictions = self._generate_predictions(avg_pattern, cohorts_df)
        
        return {
            'cohort_metrics': cohort_metrics,
            'average_pattern': avg_pattern,
            'trends': trends,
            'predictions': predictions,
            'summary': self._generate_summary(cohort_metrics)
        }
    
    def _calculate_average_pattern(self, cohort_metrics: Dict[str, CohortMetrics]) -> Dict[int, float]:
        """
        Calculate the average collection pattern across all cohorts
        """
        week_collections = defaultdict(list)
        
        for cohort in cohort_metrics.values():
            for week, rate in cohort.cumulative_collection_rate.items():
                week_collections[week].append(rate)
        
        avg_pattern = {}
        for week, rates in week_collections.items():
            avg_pattern[week] = np.mean(rates)
        
        return dict(sorted(avg_pattern.items()))
    
    def _analyze_trends(self, cohort_metrics: Dict[str, CohortMetrics]) -> Dict[str, Any]:
        """
        Analyze trends in collection patterns
        """
        # Sort cohorts by date
        sorted_cohorts = sorted(cohort_metrics.items(), key=lambda x: x[0])
        
        if len(sorted_cohorts) < 4:
            return {}
        
        # Compare recent vs historical
        recent_cohorts = sorted_cohorts[-4:]  # Last 4 weeks
        historical_cohorts = sorted_cohorts[-12:-4]  # Previous 8 weeks
        
        recent_velocity = np.mean([c[1].collection_velocity for c in recent_cohorts])
        historical_velocity = np.mean([c[1].collection_velocity for c in historical_cohorts]) if historical_cohorts else recent_velocity
        
        recent_dso = np.mean([c[1].dso for c in recent_cohorts if c[1].dso > 0])
        historical_dso = np.mean([c[1].dso for c in historical_cohorts if c[1].dso > 0]) if historical_cohorts else recent_dso
        
        return {
            'velocity_trend': 'improving' if recent_velocity > historical_velocity else 'declining',
            'velocity_change': recent_velocity - historical_velocity,
            'dso_trend': 'improving' if recent_dso < historical_dso else 'worsening',
            'dso_change': recent_dso - historical_dso,
            'recent_velocity': recent_velocity,
            'historical_velocity': historical_velocity,
            'recent_dso': recent_dso,
            'historical_dso': historical_dso
        }
    
    def _generate_predictions(self, avg_pattern: Dict[int, float], cohorts_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate cash flow predictions based on historical patterns
        """
        # Get recent sales that haven't fully collected yet
        recent_sales = self._get_recent_uncollected_sales()
        
        predictions = {}
        for week_offset in range(1, 9):  # Predict next 8 weeks
            week_date = datetime.now() + timedelta(weeks=week_offset)
            week_key = week_date.strftime('%Y-W%U')
            
            expected_collections = 0
            
            # For each recent sales week, calculate expected collections
            for sales_week, sales_data in recent_sales.items():
                weeks_since_sale = week_offset + sales_data['weeks_ago']
                
                if weeks_since_sale in avg_pattern:
                    # Expected collection rate for this week
                    if weeks_since_sale - 1 in avg_pattern:
                        incremental_rate = avg_pattern[weeks_since_sale] - avg_pattern[weeks_since_sale - 1]
                    else:
                        incremental_rate = avg_pattern[weeks_since_sale]
                    
                    expected_amount = sales_data['uncollected'] * (incremental_rate / 100)
                    expected_collections += expected_amount
            
            predictions[week_key] = {
                'week': week_key,
                'expected_collections': expected_collections,
                'confidence': 'high' if week_offset <= 4 else 'medium'
            }
        
        return predictions
    
    def _get_recent_uncollected_sales(self) -> Dict[str, Dict]:
        """
        Get recent sales with uncollected amounts
        """
        with SQLServerConnection() as db:
            query = """
            WITH RecentSales AS (
                SELECT 
                    DATEPART(year, Time) as SalesYear,
                    DATEPART(week, Time) as SalesWeek,
                    MIN(CAST(Time as DATE)) as WeekStart,
                    SUM(Total) as TotalSales,
                    DATEDIFF(week, MIN(CAST(Time as DATE)), GETDATE()) as WeeksAgo
                FROM [Transaction]
                WHERE Time >= DATEADD(week, -12, GETDATE())
                    AND Time < GETDATE()
                GROUP BY DATEPART(year, Time), DATEPART(week, Time)
            ),
            RecentCollections AS (
                SELECT 
                    DATEPART(year, t.Time) as SalesYear,
                    DATEPART(week, t.Time) as SalesWeek,
                    SUM(p.Amount) as TotalCollected
                FROM [Transaction] t
                INNER JOIN Payment p ON p.CustomerID = t.CustomerID
                WHERE t.Time >= DATEADD(week, -12, GETDATE())
                    AND t.Time < GETDATE()
                    AND p.Time >= t.Time
                GROUP BY DATEPART(year, t.Time), DATEPART(week, t.Time)
            )
            SELECT 
                rs.*,
                ISNULL(rc.TotalCollected, 0) as TotalCollected,
                rs.TotalSales - ISNULL(rc.TotalCollected, 0) as Uncollected
            FROM RecentSales rs
            LEFT JOIN RecentCollections rc 
                ON rs.SalesYear = rc.SalesYear 
                AND rs.SalesWeek = rc.SalesWeek
            WHERE rs.TotalSales - ISNULL(rc.TotalCollected, 0) > 0
            """
            
            df = db.execute_query(query)
            
            result = {}
            for _, row in df.iterrows():
                week_key = f"{int(row['SalesYear'])}-W{int(row['SalesWeek']):02d}"
                result[week_key] = {
                    'sales': float(row['TotalSales']) if hasattr(row['TotalSales'], 'real') else row['TotalSales'],
                    'collected': float(row['TotalCollected']) if hasattr(row['TotalCollected'], 'real') else row['TotalCollected'],
                    'uncollected': float(row['Uncollected']) if hasattr(row['Uncollected'], 'real') else row['Uncollected'],
                    'weeks_ago': int(row['WeeksAgo'])
                }
            
            return result
    
    def _generate_summary(self, cohort_metrics: Dict[str, CohortMetrics]) -> Dict[str, Any]:
        """
        Generate summary statistics
        """
        if not cohort_metrics:
            return {}
        
        all_velocities = [m.collection_velocity for m in cohort_metrics.values()]
        all_dsos = [m.dso for m in cohort_metrics.values() if m.dso > 0]
        
        # Collection pattern by week
        week_patterns = defaultdict(list)
        for cohort in cohort_metrics.values():
            for week, amount in cohort.collections_by_week.items():
                if cohort.sales_amount > 0:
                    week_patterns[week].append(amount / cohort.sales_amount * 100)
        
        avg_week_pattern = {week: np.mean(rates) for week, rates in week_patterns.items()}
        
        return {
            'avg_collection_velocity': np.mean(all_velocities) if all_velocities else 0,
            'avg_dso': np.mean(all_dsos) if all_dsos else 0,
            'best_velocity': max(all_velocities) if all_velocities else 0,
            'worst_velocity': min(all_velocities) if all_velocities else 0,
            'typical_collection_pattern': avg_week_pattern,
            'total_cohorts_analyzed': len(cohort_metrics)
        }
    
    def get_waterfall_data(self, num_cohorts: int = 12) -> List[Dict]:
        """
        Get data for waterfall chart visualization
        """
        cohorts_df = self.get_sales_cohorts()
        
        if cohorts_df.empty:
            return []
        
        # Convert WeekStartDate to datetime if it's not already
        if 'WeekStartDate' in cohorts_df.columns:
            cohorts_df['WeekStartDate'] = pd.to_datetime(cohorts_df['WeekStartDate'])
        
        # Get the most recent N cohorts
        recent_cohorts = cohorts_df[['SalesYear', 'SalesWeek', 'WeekStartDate', 'TotalSales']].drop_duplicates()
        recent_cohorts = recent_cohorts.sort_values('WeekStartDate', ascending=False).head(num_cohorts)
        
        waterfall_data = []
        
        for _, cohort in recent_cohorts.iterrows():
            year = int(cohort['SalesYear'])
            week = int(cohort['SalesWeek'])
            
            # Get collections for this cohort
            cohort_collections = cohorts_df[
                (cohorts_df['SalesYear'] == year) & 
                (cohorts_df['SalesWeek'] == week)
            ]
            
            cohort_data = {
                'cohort': f"{year}-W{week:02d}",
                'sales': float(cohort['TotalSales']),
                'collections': {}
            }
            
            for _, row in cohort_collections.iterrows():
                if pd.notna(row['WeeksAfterSale']) and pd.notna(row['CollectionAmount']):
                    week_offset = int(row['WeeksAfterSale'])
                    amount = float(row['CollectionAmount'])
                    cohort_data['collections'][f'Week_{week_offset}'] = amount
            
            waterfall_data.append(cohort_data)
        
        return waterfall_data
    
    def get_velocity_curves(self) -> Dict[str, List[Tuple[int, float]]]:
        """
        Get collection velocity curves for visualization
        """
        cohorts_df = self.get_sales_cohorts()
        
        if cohorts_df.empty:
            return {}
        
        velocity_curves = {}
        
        for (year, week), group in cohorts_df.groupby(['SalesYear', 'SalesWeek']):
            cohort_key = f"{int(year)}-W{int(week):02d}"
            sales_amount = group['TotalSales'].iloc[0] if not group.empty else 0
            
            if sales_amount == 0:
                continue
            
            curve = []
            cumulative = 0
            
            # Sort by weeks after sale
            sorted_group = group.sort_values('WeeksAfterSale')
            
            for _, row in sorted_group.iterrows():
                if pd.notna(row['WeeksAfterSale']) and pd.notna(row['CollectionAmount']):
                    week_offset = int(row['WeeksAfterSale'])
                    cumulative += float(row['CollectionAmount'])
                    collection_rate = (cumulative / sales_amount * 100)
                    curve.append((week_offset, collection_rate))
            
            if curve:
                velocity_curves[cohort_key] = curve
        
        return velocity_curves
    
    def get_aging_analysis(self) -> pd.DataFrame:
        """
        Get aging analysis showing outstanding AR by age
        """
        with SQLServerConnection() as db:
            query = """
            -- Current AR aging based on invoice age
            WITH CurrentAR AS (
                SELECT 
                    t.TransactionNumber,
                    t.CustomerID,
                    t.Time as InvoiceDate,
                    t.Total as InvoiceAmount,
                    ISNULL(paid.PaidAmount, 0) as PaidAmount,
                    t.Total - ISNULL(paid.PaidAmount, 0) as Outstanding,
                    DATEDIFF(day, CAST(t.Time as DATE), GETDATE()) as DaysOld
                FROM [Transaction] t
                LEFT JOIN (
                    -- Get total payments per customer (simplified allocation)
                    SELECT 
                        CustomerID,
                        SUM(Amount) as PaidAmount
                    FROM Payment
                    GROUP BY CustomerID
                ) paid ON paid.CustomerID = t.CustomerID
                WHERE t.Total > 0  -- Only positive invoices
                    -- Show all outstanding AR, not just recent
            )
            SELECT 
                CASE 
                    WHEN DaysOld <= 30 THEN '0-30 days'
                    WHEN DaysOld <= 60 THEN '31-60 days'
                    WHEN DaysOld <= 90 THEN '61-90 days'
                    WHEN DaysOld <= 180 THEN '91-180 days'
                    ELSE '180+ days'
                END as AgeBucket,
                COUNT(DISTINCT CustomerID) as CustomerCount,
                COUNT(*) as InvoiceCount,
                SUM(InvoiceAmount) as TotalInvoiced,
                SUM(PaidAmount) as TotalPaid,
                SUM(CASE WHEN Outstanding > 0 THEN Outstanding ELSE 0 END) as TotalOutstanding,
                AVG(CASE WHEN Outstanding > 0 THEN DaysOld ELSE NULL END) as AvgDaysOutstanding
            FROM CurrentAR
            WHERE Outstanding > 0  -- Only show unpaid amounts
            GROUP BY 
                CASE 
                    WHEN DaysOld <= 30 THEN '0-30 days'
                    WHEN DaysOld <= 60 THEN '31-60 days'
                    WHEN DaysOld <= 90 THEN '61-90 days'
                    WHEN DaysOld <= 180 THEN '91-180 days'
                    ELSE '180+ days'
                END
            ORDER BY 
                MIN(CASE 
                    WHEN DaysOld <= 30 THEN 1
                    WHEN DaysOld <= 60 THEN 2
                    WHEN DaysOld <= 90 THEN 3
                    WHEN DaysOld <= 180 THEN 4
                    ELSE 5
                END)
            """
            
            df = db.execute_query(query)
            
            # Convert Decimal types
            for col in df.columns:
                if df[col].dtype == object:
                    try:
                        df[col] = df[col].apply(lambda x: float(x) if hasattr(x, 'real') else x)
                    except:
                        pass
            
            return df
    
    def calculate_cohort_dso(self) -> pd.DataFrame:
        """
        Calculate DSO for each sales cohort
        """
        cohorts_df = self.get_sales_cohorts()
        
        if cohorts_df.empty:
            return pd.DataFrame()
        
        # Convert WeekStartDate to datetime if needed
        if 'WeekStartDate' in cohorts_df.columns:
            cohorts_df['WeekStartDate'] = pd.to_datetime(cohorts_df['WeekStartDate'])
        
        dso_data = []
        
        for (year, week), group in cohorts_df.groupby(['SalesYear', 'SalesWeek']):
            sales_amount = group['TotalSales'].iloc[0] if not group.empty else 0
            week_start = group['WeekStartDate'].iloc[0]
            
            # Calculate weighted average collection time
            total_collected = 0
            weighted_days = 0
            
            for _, row in group.iterrows():
                if pd.notna(row['WeeksAfterSale']) and pd.notna(row['CollectionAmount']):
                    week_offset = int(row['WeeksAfterSale'])
                    amount = float(row['CollectionAmount'])
                    days = week_offset * 7 + 3.5  # Mid-week assumption
                    
                    weighted_days += days * amount
                    total_collected += amount
            
            dso = weighted_days / total_collected if total_collected > 0 else None
            collection_rate = total_collected / sales_amount * 100 if sales_amount > 0 else 0
            
            dso_data.append({
                'Cohort': f"{int(year)}-W{int(week):02d}",
                'WeekStart': week_start,
                'Sales': sales_amount,
                'Collected': total_collected,
                'CollectionRate': collection_rate,
                'DSO': dso,
                'Outstanding': sales_amount - total_collected
            })
        
        return pd.DataFrame(dso_data)