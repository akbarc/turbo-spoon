"""
Advanced Cash Flow Prediction System
Multi-model approach with customer-specific, sales-based, and cyclical predictions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

class PredictionModel(Enum):
    """Types of prediction models"""
    CUSTOMER_SPECIFIC = "customer_specific"
    SALES_BASED = "sales_based"
    SEASONAL = "seasonal"
    AR_AGING = "ar_aging"
    HISTORICAL_PATTERN = "historical_pattern"
    ENSEMBLE = "ensemble"

@dataclass
class PredictionResult:
    """Structured prediction result"""
    date: str
    amount: float
    confidence: float
    model: str
    components: Dict[str, float]
    explanation: str

class AdvancedCashFlowPredictor:
    """Advanced multi-model cash flow prediction system"""
    
    def __init__(self):
        self.lookback_months = 12  # Use 12 months of history for patterns
        self.min_confidence = 0.1
        self.max_confidence = 0.9
        
    def predict_comprehensive(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive cash flow predictions using all models
        """
        try:
            logger.info(f"Starting comprehensive prediction for {days_ahead} days")
            
            # Gather all data needed for predictions
            data = self._gather_prediction_data()
            
            # Run individual prediction models
            predictions = {
                'customer_specific': self._predict_customer_specific(data, days_ahead),
                'sales_based': self._predict_sales_based(data, days_ahead),
                'seasonal': self._predict_seasonal(data, days_ahead),
                'ar_aging': self._predict_ar_aging(data, days_ahead),
                'historical_pattern': self._predict_historical_pattern(data, days_ahead)
            }
            
            # Combine predictions using ensemble method
            ensemble = self._ensemble_predictions(predictions, data, days_ahead)
            
            # Calculate accuracy metrics
            accuracy = self._calculate_model_accuracy(predictions, data)
            
            # Generate detailed explanation
            explanation = self._generate_prediction_explanation(ensemble, predictions, data)
            
            return {
                'success': True,
                'predictions': ensemble,
                'individual_models': predictions,
                'accuracy_metrics': accuracy,
                'explanation': explanation,
                'data_summary': self._summarize_data(data),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error in comprehensive prediction: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'predictions': []
            }
    
    def _gather_prediction_data(self) -> Dict[str, pd.DataFrame]:
        """
        Gather all data needed for predictions
        """
        with SQLServerConnection() as db:
            data = {}
            
            # 1. Customer payment history with detailed patterns
            customer_history_query = """
            WITH CustomerPayments AS (
                SELECT 
                    c.ID as CustomerID,
                    c.Company as CustomerName,
                    c.AccountBalance as CurrentAR,
                    c.CreditLimit,
                    -- Payment timing patterns
                    (SELECT AVG(DATEDIFF(day, t.Time, p.Time))
                     FROM [Transaction] t
                     INNER JOIN Payment p ON p.CustomerID = c.ID
                     WHERE t.CustomerID = c.ID 
                       AND t.Time >= DATEADD(month, -6, GETDATE())
                       AND p.Time >= t.Time
                       AND p.Time <= DATEADD(day, 90, t.Time)) as AvgDaysToPay,
                    -- Payment frequency
                    (SELECT COUNT(DISTINCT CAST(Time as DATE))
                     FROM Payment
                     WHERE CustomerID = c.ID
                       AND Time >= DATEADD(month, -3, GETDATE())) as PaymentDaysLast3Months,
                    -- Recent payment amounts
                    (SELECT AVG(Amount)
                     FROM Payment
                     WHERE CustomerID = c.ID
                       AND Time >= DATEADD(month, -3, GETDATE())) as AvgPaymentAmount,
                    -- Last payment info
                    (SELECT MAX(Time)
                     FROM Payment
                     WHERE CustomerID = c.ID) as LastPaymentDate,
                    -- Preferred payment day of week
                    (SELECT TOP 1 DATEPART(dw, Time)
                     FROM Payment
                     WHERE CustomerID = c.ID
                       AND Time >= DATEADD(month, -6, GETDATE())
                     GROUP BY DATEPART(dw, Time)
                     ORDER BY COUNT(*) DESC) as PreferredDayOfWeek,
                    -- Preferred payment day of month
                    (SELECT TOP 1 DATEPART(day, Time)
                     FROM Payment
                     WHERE CustomerID = c.ID
                       AND Time >= DATEADD(month, -6, GETDATE())
                     GROUP BY DATEPART(day, Time)
                     ORDER BY COUNT(*) DESC) as PreferredDayOfMonth
                FROM Customer c
                WHERE c.AccountBalance > 0
            )
            SELECT * FROM CustomerPayments
            ORDER BY CurrentAR DESC
            """
            data['customer_history'] = db.execute_query(customer_history_query)
            
            # 2. AR aging details with invoice-level data
            ar_aging_query = """
            SELECT 
                ar.CustomerID,
                ar.ID as InvoiceID,
                ar.Date as InvoiceDate,
                ar.Balance,
                ar.OriginalAmount,
                DATEDIFF(day, ar.Date, GETDATE()) as Age,
                CASE 
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 30 THEN '0-30'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 60 THEN '31-60'
                    WHEN DATEDIFF(day, ar.Date, GETDATE()) <= 90 THEN '61-90'
                    ELSE '90+'
                END as AgeBucket,
                c.Company as CustomerName
            FROM AccountReceivable ar
            INNER JOIN Customer c ON ar.CustomerID = c.ID
            WHERE ar.Balance > 0
            ORDER BY ar.CustomerID, ar.Date
            """
            data['ar_aging'] = db.execute_query(ar_aging_query)
            
            # 3. Sales and transaction patterns
            sales_pattern_query = """
            WITH MonthlySales AS (
                SELECT 
                    YEAR(Time) as Year,
                    MONTH(Time) as Month,
                    COUNT(*) as TransactionCount,
                    SUM(Total) as TotalSales,
                    COUNT(DISTINCT CustomerID) as UniqueCustomers,
                    AVG(Total) as AvgTransactionSize
                FROM [Transaction]
                WHERE Time >= DATEADD(month, -12, GETDATE())
                GROUP BY YEAR(Time), MONTH(Time)
            ),
            MonthlyPayments AS (
                SELECT 
                    YEAR(Time) as Year,
                    MONTH(Time) as Month,
                    SUM(Amount) as TotalPayments,
                    COUNT(*) as PaymentCount
                FROM Payment
                WHERE Time >= DATEADD(month, -12, GETDATE())
                GROUP BY YEAR(Time), MONTH(Time)
            )
            SELECT 
                ms.*,
                mp.TotalPayments,
                mp.PaymentCount,
                mp.TotalPayments / NULLIF(ms.TotalSales, 0) as CollectionRate
            FROM MonthlySales ms
            LEFT JOIN MonthlyPayments mp ON ms.Year = mp.Year AND ms.Month = mp.Month
            ORDER BY ms.Year, ms.Month
            """
            data['sales_patterns'] = db.execute_query(sales_pattern_query)
            
            # 4. Daily payment patterns (SQL Server 2008 compatible)
            daily_pattern_query = """
            WITH DailyStats AS (
                SELECT 
                    CAST(Time as DATE) as PaymentDate,
                    DATEPART(dw, Time) as DayOfWeek,
                    DATEPART(day, Time) as DayOfMonth,
                    DATEPART(wk, Time) as WeekOfYear,
                    SUM(Amount) as DailyTotal,
                    COUNT(*) as PaymentCount,
                    COUNT(DISTINCT CustomerID) as UniqueCustomers
                FROM Payment
                WHERE Time >= DATEADD(month, -6, GETDATE())
                GROUP BY CAST(Time as DATE), DATEPART(dw, Time), 
                         DATEPART(day, Time), DATEPART(wk, Time)
            ),
            DayOfWeekAvg AS (
                SELECT 
                    DayOfWeek,
                    AVG(DailyTotal) as AvgByDayOfWeek
                FROM DailyStats
                GROUP BY DayOfWeek
            ),
            DayOfMonthAvg AS (
                SELECT 
                    DayOfMonth,
                    AVG(DailyTotal) as AvgByDayOfMonth
                FROM DailyStats
                GROUP BY DayOfMonth
            )
            SELECT 
                ds.*,
                dwa.AvgByDayOfWeek,
                dma.AvgByDayOfMonth,
                -- Simple 7-day moving average approximation
                (SELECT AVG(DailyTotal) 
                 FROM DailyStats ds2 
                 WHERE ds2.PaymentDate >= DATEADD(day, -7, ds.PaymentDate)
                   AND ds2.PaymentDate <= ds.PaymentDate) as MovingAvg7Day
            FROM DailyStats ds
            LEFT JOIN DayOfWeekAvg dwa ON ds.DayOfWeek = dwa.DayOfWeek
            LEFT JOIN DayOfMonthAvg dma ON ds.DayOfMonth = dma.DayOfMonth
            ORDER BY ds.PaymentDate DESC
            """
            data['daily_patterns'] = db.execute_query(daily_pattern_query)
            
            # 5. Customer segments and behaviors
            customer_segment_query = """
            WITH CustomerMetrics AS (
                SELECT 
                    c.ID as CustomerID,
                    c.Company,
                    c.AccountBalance,
                    c.CreditLimit,
                    -- Payment consistency score
                    CAST(COUNT(DISTINCT DATEPART(month, p.Time)) as FLOAT) / 12 as PaymentConsistency,
                    -- Average monthly payment
                    SUM(p.Amount) / NULLIF(COUNT(DISTINCT DATEPART(month, p.Time)), 0) as AvgMonthlyPayment,
                    -- Payment velocity (payments per month)
                    COUNT(p.ID) / 12.0 as PaymentVelocity,
                    -- Risk indicators
                    MAX(DATEDIFF(day, p.Time, GETDATE())) as DaysSinceLastPayment,
                    CASE 
                        WHEN c.AccountBalance > c.CreditLimit THEN 1 
                        ELSE 0 
                    END as OverCreditLimit
                FROM Customer c
                LEFT JOIN Payment p ON p.CustomerID = c.ID 
                    AND p.Time >= DATEADD(year, -1, GETDATE())
                WHERE c.AccountBalance > 0
                GROUP BY c.ID, c.Company, c.AccountBalance, c.CreditLimit
            )
            SELECT 
                *,
                CASE 
                    WHEN PaymentConsistency >= 0.8 AND OverCreditLimit = 0 THEN 'Premium'
                    WHEN PaymentConsistency >= 0.5 THEN 'Regular'
                    WHEN PaymentConsistency >= 0.3 THEN 'Occasional'
                    ELSE 'Risk'
                END as CustomerSegment
            FROM CustomerMetrics
            """
            data['customer_segments'] = db.execute_query(customer_segment_query)
            
            # 6. Recent collection performance
            recent_collections_query = """
            SELECT 
                CAST(Time as DATE) as Date,
                SUM(Amount) as Collections
            FROM Payment
            WHERE Time >= DATEADD(day, -90, GETDATE())
            GROUP BY CAST(Time as DATE)
            ORDER BY Date
            """
            data['recent_collections'] = db.execute_query(recent_collections_query)
            
            # Convert all Decimal columns to float to avoid type errors
            for key in data:
                df = data[key]
                if not df.empty:
                    for col in df.columns:
                        if df[col].dtype == object:
                            try:
                                # Try to convert Decimal columns to float
                                df[col] = df[col].apply(lambda x: float(x) if hasattr(x, 'real') else x)
                            except:
                                pass
            
            return data
    
    def _predict_customer_specific(self, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Predict based on individual customer payment patterns
        """
        predictions = []
        base_date = datetime.now().date()
        
        customer_history = data.get('customer_history', pd.DataFrame())
        ar_aging = data.get('ar_aging', pd.DataFrame())
        customer_segments = data.get('customer_segments', pd.DataFrame())
        
        if customer_history.empty or ar_aging.empty:
            return predictions
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            day_of_week = predict_date.weekday() + 1  # SQL Server format (1=Sunday)
            day_of_month = predict_date.day
            
            daily_prediction = 0
            customer_details = []
            
            for _, customer in customer_history.iterrows():
                customer_id = customer['CustomerID']
                current_ar = float(customer['CurrentAR'] or 0)
                
                if current_ar <= 0:
                    continue
                
                # Get customer segment
                segment_info = customer_segments[customer_segments['CustomerID'] == customer_id]
                segment = segment_info['CustomerSegment'].iloc[0] if not segment_info.empty else 'Unknown'
                
                # Calculate probability of payment on this day
                prob = 0
                
                # Factor 1: Preferred day of week (30% weight)
                if customer['PreferredDayOfWeek'] == day_of_week:
                    prob += 0.3
                elif customer['PreferredDayOfWeek'] and abs(customer['PreferredDayOfWeek'] - day_of_week) == 1:
                    prob += 0.15
                
                # Factor 2: Preferred day of month (20% weight)
                if customer['PreferredDayOfMonth'] == day_of_month:
                    prob += 0.2
                elif customer['PreferredDayOfMonth'] and abs(customer['PreferredDayOfMonth'] - day_of_month) <= 2:
                    prob += 0.1
                
                # Factor 3: Days since last payment (25% weight)
                if pd.notna(customer['LastPaymentDate']):
                    days_since = (predict_date - pd.to_datetime(customer['LastPaymentDate']).date()).days
                    avg_days = float(customer['AvgDaysToPay']) if customer['AvgDaysToPay'] else 30
                    
                    if abs(days_since - avg_days) <= 3:
                        prob += 0.25
                    elif abs(days_since - avg_days) <= 7:
                        prob += 0.15
                    elif abs(days_since - avg_days) <= 14:
                        prob += 0.05
                
                # Factor 4: Customer segment (25% weight)
                segment_probs = {
                    'Premium': 0.25,
                    'Regular': 0.15,
                    'Occasional': 0.08,
                    'Risk': 0.03
                }
                prob += segment_probs.get(segment, 0.05)
                
                # Calculate expected payment
                if prob > 0:
                    avg_payment = float(customer['AvgPaymentAmount'] or 0) if customer['AvgPaymentAmount'] else 0
                    if avg_payment > 0:
                        expected_payment = min(float(avg_payment * prob), float(current_ar))
                        daily_prediction += expected_payment
                        
                        if expected_payment > 100:  # Only track significant payments
                            customer_details.append({
                                'customer': customer['CustomerName'],
                                'probability': round(prob, 3),
                                'expected': round(expected_payment, 2)
                            })
            
            predictions.append({
                'date': predict_date.isoformat(),
                'amount': round(daily_prediction, 2),
                'confidence': 0.7,  # Customer-specific models are generally reliable
                'customer_count': len(customer_details),
                'top_customers': sorted(customer_details, key=lambda x: x['expected'], reverse=True)[:5]
            })
        
        return predictions
    
    def _predict_sales_based(self, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Predict based on sales patterns and collection rates
        """
        predictions = []
        base_date = datetime.now().date()
        
        sales_patterns = data.get('sales_patterns', pd.DataFrame())
        
        if sales_patterns.empty:
            return predictions
        
        # Calculate average collection rate and lag
        avg_collection_rate = float(sales_patterns['CollectionRate'].mean()) if not sales_patterns['CollectionRate'].empty else 0.7
        avg_monthly_sales = float(sales_patterns['TotalSales'].mean()) if not sales_patterns['TotalSales'].empty else 0
        avg_daily_sales = avg_monthly_sales / 30
        
        # Analyze collection lag pattern
        collection_lags = []
        for i in range(1, len(sales_patterns)):
            if sales_patterns.iloc[i]['TotalPayments'] and sales_patterns.iloc[i-1]['TotalSales']:
                lag_rate = float(sales_patterns.iloc[i]['TotalPayments']) / float(sales_patterns.iloc[i-1]['TotalSales'])
                collection_lags.append(lag_rate)
        
        avg_lag_rate = np.mean(collection_lags) if collection_lags else 0.7
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            
            # Estimate collections based on past sales
            # Assume 30-day average collection period
            expected = 0
            
            # Immediate collections (same day) - 10% of daily sales
            expected += avg_daily_sales * 0.1
            
            # 7-day collections - 20% of week-old sales
            if day_offset >= 7:
                expected += avg_daily_sales * 0.2
            
            # 30-day collections - 50% of month-old sales
            if day_offset >= 30:
                expected += avg_daily_sales * 0.5
            
            # 60-day collections - 20% of 2-month-old sales
            if day_offset >= 60:
                expected += avg_daily_sales * 0.2
            
            predictions.append({
                'date': predict_date.isoformat(),
                'amount': round(expected * avg_lag_rate, 2),
                'confidence': 0.6,
                'sales_based': True,
                'collection_rate': round(avg_collection_rate, 3)
            })
        
        return predictions
    
    def _predict_seasonal(self, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Predict based on seasonal and cyclical patterns
        """
        predictions = []
        base_date = datetime.now().date()
        
        daily_patterns = data.get('daily_patterns', pd.DataFrame())
        
        if daily_patterns.empty:
            return predictions
        
        # Calculate seasonal factors
        day_of_week_avg = daily_patterns.groupby('DayOfWeek')['DailyTotal'].mean().to_dict()
        day_of_month_avg = daily_patterns.groupby('DayOfMonth')['DailyTotal'].mean().to_dict()
        
        # Calculate week of month patterns
        daily_patterns['WeekOfMonth'] = (daily_patterns['DayOfMonth'] - 1) // 7 + 1
        week_of_month_avg = daily_patterns.groupby('WeekOfMonth')['DailyTotal'].mean().to_dict()
        
        # Overall average for normalization
        overall_avg = float(daily_patterns['DailyTotal'].mean()) if not daily_patterns.empty else 0
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            day_of_week = predict_date.weekday() + 1
            day_of_month = predict_date.day
            week_of_month = (day_of_month - 1) // 7 + 1
            
            # Combine seasonal factors
            dow_value = float(day_of_week_avg.get(day_of_week, overall_avg)) if day_of_week in day_of_week_avg else overall_avg
            dom_value = float(day_of_month_avg.get(day_of_month, overall_avg)) if day_of_month in day_of_month_avg else overall_avg
            wom_value = float(week_of_month_avg.get(week_of_month, overall_avg)) if week_of_month in week_of_month_avg else overall_avg
            
            dow_factor = dow_value / overall_avg if overall_avg > 0 else 1
            dom_factor = dom_value / overall_avg if overall_avg > 0 else 1
            wom_factor = wom_value / overall_avg if overall_avg > 0 else 1
            
            # Weighted combination of factors
            seasonal_multiplier = (dow_factor * 0.5 + dom_factor * 0.3 + wom_factor * 0.2)
            
            # Apply to base average
            expected = overall_avg * seasonal_multiplier
            
            predictions.append({
                'date': predict_date.isoformat(),
                'amount': round(expected, 2),
                'confidence': 0.5,
                'seasonal_factors': {
                    'day_of_week': round(dow_factor, 2),
                    'day_of_month': round(dom_factor, 2),
                    'week_of_month': round(wom_factor, 2)
                }
            })
        
        return predictions
    
    def _predict_ar_aging(self, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Predict based on AR aging buckets and historical collection rates
        """
        predictions = []
        base_date = datetime.now().date()
        
        ar_aging = data.get('ar_aging', pd.DataFrame())
        
        if ar_aging.empty:
            return predictions
        
        # Calculate total AR by age bucket
        bucket_totals = ar_aging.groupby('AgeBucket')['Balance'].sum().to_dict()
        
        # Historical collection rates by age bucket (from analysis)
        collection_rates = {
            '0-30': 0.015,   # 1.5% daily collection rate for current
            '31-60': 0.012,  # 1.2% daily for 31-60 days
            '61-90': 0.008,  # 0.8% daily for 61-90 days
            '90+': 0.003     # 0.3% daily for 90+ days
        }
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            
            daily_collection = 0
            bucket_details = {}
            
            for bucket, total in bucket_totals.items():
                rate = collection_rates.get(bucket, 0.005)
                
                # Adjust rate based on day of week
                day_of_week = predict_date.weekday()
                if day_of_week == 4:  # Friday
                    rate *= 1.5
                elif day_of_week in [5, 6]:  # Weekend
                    rate *= 0.3
                
                expected = float(total) * rate
                daily_collection += expected
                bucket_details[bucket] = round(expected, 2)
            
            predictions.append({
                'date': predict_date.isoformat(),
                'amount': round(daily_collection, 2),
                'confidence': 0.6,
                'bucket_collections': bucket_details
            })
        
        return predictions
    
    def _predict_historical_pattern(self, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Predict based on historical payment patterns using moving averages
        """
        predictions = []
        base_date = datetime.now().date()
        
        recent_collections = data.get('recent_collections', pd.DataFrame())
        
        if recent_collections.empty:
            return predictions
        
        # Calculate various moving averages
        recent_collections['MA7'] = recent_collections['Collections'].rolling(window=7, min_periods=1).mean()
        recent_collections['MA14'] = recent_collections['Collections'].rolling(window=14, min_periods=1).mean()
        recent_collections['MA30'] = recent_collections['Collections'].rolling(window=30, min_periods=1).mean()
        
        # Get recent trends
        last_7_avg = float(recent_collections['Collections'].tail(7).mean()) if len(recent_collections) >= 7 else 0
        last_14_avg = float(recent_collections['Collections'].tail(14).mean()) if len(recent_collections) >= 14 else 0
        last_30_avg = float(recent_collections['Collections'].tail(30).mean()) if len(recent_collections) >= 30 else 0
        
        # Calculate trend direction
        if len(recent_collections) >= 14:
            first_half = float(recent_collections['Collections'].iloc[-14:-7].mean())
            second_half = float(recent_collections['Collections'].iloc[-7:].mean())
            trend_factor = second_half / first_half if first_half > 0 else 1
        else:
            trend_factor = 1
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            
            # Weight recent averages
            base_prediction = (last_7_avg * 0.5 + last_14_avg * 0.3 + last_30_avg * 0.2)
            
            # Apply trend
            if day_offset <= 7:
                trend_adjustment = 1 + (trend_factor - 1) * (1 - day_offset / 14)
            else:
                trend_adjustment = 1
            
            expected = base_prediction * trend_adjustment
            
            # Add day of week adjustment based on historical data
            day_of_week = predict_date.weekday()
            dow_adjustments = {
                0: 0.7,   # Monday
                1: 1.2,   # Tuesday
                2: 1.0,   # Wednesday
                3: 1.1,   # Thursday
                4: 1.5,   # Friday
                5: 0.4,   # Saturday
                6: 0.4    # Sunday
            }
            expected *= dow_adjustments.get(day_of_week, 1)
            
            predictions.append({
                'date': predict_date.isoformat(),
                'amount': round(expected, 2),
                'confidence': 0.7,
                'trend_factor': round(trend_factor, 3),
                'base_avg': round(base_prediction, 2)
            })
        
        return predictions
    
    def _ensemble_predictions(self, predictions: Dict, data: Dict, days_ahead: int) -> List[Dict]:
        """
        Combine all model predictions using weighted ensemble
        """
        ensemble = []
        base_date = datetime.now().date()
        
        # Model weights based on expected accuracy
        weights = {
            'customer_specific': 0.35,
            'historical_pattern': 0.25,
            'ar_aging': 0.20,
            'seasonal': 0.12,
            'sales_based': 0.08
        }
        
        for day_offset in range(days_ahead):
            predict_date = base_date + timedelta(days=day_offset)
            date_str = predict_date.isoformat()
            
            weighted_sum = 0
            weight_sum = 0
            components = {}
            confidences = []
            
            for model_name, model_predictions in predictions.items():
                if model_predictions and day_offset < len(model_predictions):
                    pred = model_predictions[day_offset]
                    weight = weights.get(model_name, 0.1)
                    
                    amount = pred.get('amount', 0)
                    confidence = pred.get('confidence', 0.5)
                    
                    weighted_sum += amount * weight * confidence
                    weight_sum += weight * confidence
                    
                    components[model_name] = amount
                    confidences.append(confidence)
            
            # Calculate final prediction
            if weight_sum > 0:
                final_amount = weighted_sum / weight_sum
            else:
                final_amount = 0
            
            # Calculate ensemble confidence
            if confidences:
                ensemble_confidence = np.mean(confidences) * min(1, weight_sum)
            else:
                ensemble_confidence = 0.1
            
            # Calculate confidence bands
            std_dev = np.std([v for v in components.values() if v > 0]) if components else final_amount * 0.3
            
            ensemble.append({
                'date': date_str,
                'expected': round(final_amount, 2),
                'low_confidence': round(max(0, final_amount - 2 * std_dev), 2),
                'medium_confidence': round(final_amount, 2),
                'high_confidence': round(final_amount + 2 * std_dev, 2),
                'confidence_score': round(ensemble_confidence, 3),
                'components': components,
                'day_of_week': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][predict_date.weekday()]
            })
        
        return ensemble
    
    def _calculate_model_accuracy(self, predictions: Dict, data: Dict) -> Dict:
        """
        Calculate accuracy metrics for each model
        """
        recent_collections = data.get('recent_collections', pd.DataFrame())
        
        if recent_collections.empty:
            return {}
        
        if not recent_collections.empty:
            actual_avg = float(recent_collections['Collections'].mean())
            actual_std = float(recent_collections['Collections'].std()) if len(recent_collections) > 1 else float(actual_avg * 0.3)
        else:
            actual_avg = 0
            actual_std = 1
        
        accuracy = {}
        for model_name, model_predictions in predictions.items():
            if model_predictions:
                pred_amounts = [p.get('amount', 0) for p in model_predictions[:30]]
                pred_avg = np.mean(pred_amounts)
                
                # Calculate accuracy as inverse of relative error
                if actual_avg > 0:
                    relative_error = abs(pred_avg - actual_avg) / actual_avg
                    model_accuracy = max(0, 1 - relative_error)
                else:
                    model_accuracy = 0
                
                accuracy[model_name] = {
                    'accuracy_score': round(model_accuracy, 3),
                    'predicted_avg': round(pred_avg, 2),
                    'actual_avg': round(actual_avg, 2),
                    'volatility_ratio': round(np.std(pred_amounts) / actual_std if actual_std > 0 else 1, 3)
                }
        
        return accuracy
    
    def _generate_prediction_explanation(self, ensemble: List, predictions: Dict, data: Dict) -> Dict:
        """
        Generate detailed explanation of predictions
        """
        explanation = {
            'summary': '',
            'key_factors': [],
            'risks': [],
            'opportunities': []
        }
        
        # Calculate summary statistics
        if ensemble:
            total_expected = sum(p['expected'] for p in ensemble[:30])
            daily_avg = total_expected / min(30, len(ensemble))
            
            # Get current AR total
            ar_aging = data.get('ar_aging', pd.DataFrame())
            total_ar = float(ar_aging['Balance'].sum()) if not ar_aging.empty else 0
            
            explanation['summary'] = (
                f"Expected to collect ${total_expected:,.2f} over the next 30 days "
                f"(average ${daily_avg:,.2f}/day). "
                f"This represents {(total_expected/total_ar*100):.1f}% of current AR balance."
            )
            
            # Identify key factors
            customer_segments = data.get('customer_segments', pd.DataFrame())
            if not customer_segments.empty:
                premium_count = len(customer_segments[customer_segments['CustomerSegment'] == 'Premium'])
                risk_count = len(customer_segments[customer_segments['CustomerSegment'] == 'Risk'])
                
                explanation['key_factors'].append(
                    f"{premium_count} premium customers likely to pay on schedule"
                )
                if risk_count > 0:
                    explanation['risks'].append(
                        f"{risk_count} customers classified as payment risks"
                    )
            
            # Identify patterns
            daily_patterns = data.get('daily_patterns', pd.DataFrame())
            if not daily_patterns.empty:
                best_day = daily_patterns.groupby('DayOfWeek')['DailyTotal'].mean().idxmax()
                day_names = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 
                            5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
                explanation['key_factors'].append(
                    f"{day_names.get(best_day, 'Unknown')} typically has highest collections"
                )
            
            # Check AR aging
            ar_aging = data.get('ar_aging', pd.DataFrame())
            if not ar_aging.empty:
                over_90 = float(ar_aging[ar_aging['Age'] > 90]['Balance'].sum())
                if over_90 > total_ar * 0.2:
                    explanation['risks'].append(
                        f"${over_90:,.2f} ({(over_90/total_ar*100):.1f}%) of AR is over 90 days old"
                    )
            
            # Identify opportunities
            if daily_avg > 100000:
                high_days = [p for p in ensemble[:7] if p['expected'] > daily_avg * 1.3]
                if high_days:
                    explanation['opportunities'].append(
                        f"{len(high_days)} days in the next week expected to have above-average collections"
                    )
        
        return explanation
    
    def _summarize_data(self, data: Dict) -> Dict:
        """
        Summarize the data used for predictions
        """
        summary = {}
        
        ar_aging = data.get('ar_aging', pd.DataFrame())
        if not ar_aging.empty:
            summary['total_ar'] = round(ar_aging['Balance'].sum(), 2)
            summary['invoice_count'] = len(ar_aging)
            summary['customer_count'] = ar_aging['CustomerID'].nunique()
            summary['avg_age'] = round(ar_aging['Age'].mean(), 1)
        
        customer_segments = data.get('customer_segments', pd.DataFrame())
        if not customer_segments.empty:
            summary['segment_distribution'] = customer_segments['CustomerSegment'].value_counts().to_dict()
        
        recent_collections = data.get('recent_collections', pd.DataFrame())
        if not recent_collections.empty:
            summary['recent_daily_avg'] = round(recent_collections['Collections'].tail(30).mean(), 2)
            summary['recent_daily_std'] = round(recent_collections['Collections'].tail(30).std(), 2)
        
        return summary
    
    def _assess_data_quality(self, data_summary: Dict) -> Dict:
        """
        Assess quality of data used for predictions
        """
        quality = {
            'score': 0,
            'issues': [],
            'strengths': []
        }
        
        # Check data completeness
        if data_summary.get('customer_count', 0) > 10:
            quality['strengths'].append('Sufficient customer data')
            quality['score'] += 25
        else:
            quality['issues'].append('Limited customer data')
        
        if data_summary.get('invoice_count', 0) > 50:
            quality['strengths'].append('Good invoice history')
            quality['score'] += 25
        else:
            quality['issues'].append('Limited invoice history')
        
        # Check data freshness
        avg_age = data_summary.get('avg_age', 999)
        if avg_age < 45:
            quality['strengths'].append('Recent AR data')
            quality['score'] += 25
        else:
            quality['issues'].append('Aging AR data')
        
        # Check volatility
        if data_summary.get('recent_daily_std', 0) < data_summary.get('recent_daily_avg', 1) * 0.5:
            quality['strengths'].append('Stable payment patterns')
            quality['score'] += 25
        else:
            quality['issues'].append('High payment volatility')
        
        return quality
    
    def get_model_performance_metrics(self) -> Dict:
        """
        Get detailed performance metrics for all models
        """
        try:
            # Run predictions
            result = self.predict_comprehensive(days_ahead=7)
            
            if not result['success']:
                return {'error': result.get('error')}
            
            metrics = {
                'model_accuracies': result.get('accuracy_metrics', {}),
                'data_quality': self._assess_data_quality(result.get('data_summary', {})),
                'confidence_score': np.mean([p['confidence_score'] for p in result['predictions']]),
                'generated_at': datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}