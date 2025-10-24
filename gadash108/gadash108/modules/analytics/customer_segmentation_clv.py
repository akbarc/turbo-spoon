"""
Customer Segmentation and Customer Lifetime Value (CLV) Analysis
RFM Segmentation, CLV Calculation, Risk Analysis, and Cross-sell Opportunities

This module provides comprehensive customer analytics including:
- RFM (Recency, Frequency, Monetary) segmentation  
- Customer Lifetime Value (CLV) calculation
- High-value at-risk customer identification
- Basket affinity analysis for cross-sell opportunities
- Win-back campaign targeting
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging
import sys
import os
from dataclasses import dataclass
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database_pymssql import SQLServerConnection
from modules.customer_analytics import CustomerAnalytics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RFMMetrics:
    """RFM Analysis metrics"""
    customer_id: int
    company_name: str
    recency: int  # Days since last purchase
    frequency: int  # Number of transactions
    monetary: float  # Total revenue
    rfm_score: str  # Combined RFM score (e.g., "544")
    segment: str  # Customer segment name
    clv_12_month: float  # Predicted CLV for next 12 months
    clv_total: float  # Total predicted lifetime value
    at_risk: bool  # Whether customer is at risk of churning
    win_back_candidate: bool  # Whether customer needs win-back campaign

@dataclass
class CrossSellOpportunity:
    """Cross-sell opportunity data"""
    customer_id: int
    company_name: str
    primary_category: str
    recommended_categories: List[str]
    affinity_score: float
    potential_revenue: float
    confidence: str

class CustomerSegmentationCLV:
    """Advanced Customer Segmentation and CLV Analysis"""
    
    def __init__(self, strategic_data_path: str = None):
        """Initialize with optional strategic data file"""
        self.db = SQLServerConnection()
        self.strategic_data = None
        
        if strategic_data_path and os.path.exists(strategic_data_path):
            try:
                with open(strategic_data_path, 'r') as f:
                    self.strategic_data = json.load(f)
                logger.info(f"✅ Loaded strategic data from {strategic_data_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load strategic data: {e}")
    
    def perform_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Perform complete customer segmentation and CLV analysis
        Returns comprehensive results for B2B wholesale business insights
        """
        logger.info("🚀 Starting comprehensive customer segmentation and CLV analysis...")
        
        # Step 1: Extract customer transaction data
        customer_data = self._extract_customer_transaction_data()
        if customer_data.empty:
            logger.error("❌ No customer data found")
            return {}
        
        logger.info(f"✅ Extracted data for {len(customer_data)} customers")
        
        # Step 2: Calculate RFM scores
        rfm_data = self._calculate_rfm_scores(customer_data)
        logger.info(f"✅ Calculated RFM scores for {len(rfm_data)} customers")
        
        # Step 3: Perform customer segmentation
        segmented_customers = self._perform_customer_segmentation(rfm_data)
        logger.info(f"✅ Segmented customers into {len(segmented_customers['segment'].unique())} segments")
        
        # Step 4: Calculate CLV by cohort
        clv_analysis = self._calculate_clv_by_cohort(segmented_customers)
        logger.info("✅ Calculated CLV by cohort")
        
        # Step 5: Identify high-value at-risk customers
        at_risk_customers = self._identify_at_risk_customers(segmented_customers)
        logger.info(f"✅ Identified {len(at_risk_customers)} high-value at-risk customers")
        
        # Step 6: Analyze basket affinity for cross-sell
        cross_sell_opportunities = self._analyze_cross_sell_opportunities()
        logger.info(f"✅ Found {len(cross_sell_opportunities)} cross-sell opportunities")
        
        # Step 7: Identify win-back targets
        win_back_targets = self._identify_win_back_targets(segmented_customers)
        logger.info(f"✅ Identified {len(win_back_targets)} win-back campaign targets")
        
        # Step 8: Generate segment insights
        segment_insights = self._generate_segment_insights(segmented_customers)
        logger.info("✅ Generated segment insights")
        
        # Compile comprehensive results
        results = {
            'analysis_date': datetime.now().isoformat(),
            'summary': {
                'total_customers_analyzed': len(customer_data),
                'segments_created': len(segmented_customers['segment'].unique()),
                'high_value_at_risk_count': len(at_risk_customers),
                'cross_sell_opportunities_count': len(cross_sell_opportunities),
                'win_back_targets_count': len(win_back_targets)
            },
            'segment_insights': segment_insights,
            'clv_analysis': clv_analysis,
            'high_value_at_risk': at_risk_customers[:20],  # Top 20
            'cross_sell_opportunities': cross_sell_opportunities,
            'win_back_targets': win_back_targets,
            'rfm_distribution': self._get_rfm_distribution(segmented_customers),
            'actionable_recommendations': self._generate_actionable_recommendations(
                segmented_customers, at_risk_customers, cross_sell_opportunities, win_back_targets
            )
        }
        
        logger.info("🎉 Comprehensive analysis completed successfully!")
        return results
    
    def _extract_customer_transaction_data(self) -> pd.DataFrame:
        """Extract customer transaction data for analysis"""
        with self.db:
            query = """
            WITH CustomerMetrics AS (
                SELECT 
                    c.ID as customer_id,
                    c.Company,
                    c.FirstName,
                    c.LastName,
                    c.AccountBalance,
                    c.CreditLimit,
                    c.TotalSales,
                    c.LastVisit,
                    c.AccountOpened,
                    -- Transaction metrics
                    COUNT(DISTINCT t.TransactionNumber) as total_transactions,
                    COUNT(DISTINCT CAST(t.Time as DATE)) as active_days,
                    SUM(t.Total) as total_revenue,
                    AVG(t.Total) as avg_transaction_value,
                    MAX(t.Time) as last_purchase_date,
                    MIN(t.Time) as first_purchase_date,
                    -- Recency (days since last purchase)
                    DATEDIFF(day, MAX(t.Time), GETDATE()) as recency_days,
                    -- Customer lifetime in days
                    DATEDIFF(day, MIN(t.Time), MAX(t.Time)) as customer_lifetime_days,
                    DATEDIFF(day, c.AccountOpened, GETDATE()) as account_age_days,
                    -- Purchase frequency per month
                    CASE 
                        WHEN DATEDIFF(day, MIN(t.Time), MAX(t.Time)) > 0
                        THEN COUNT(DISTINCT t.TransactionNumber) * 30.0 / DATEDIFF(day, MIN(t.Time), MAX(t.Time))
                        ELSE COUNT(DISTINCT t.TransactionNumber)
                    END as frequency_per_month,
                    -- Seasonality indicators
                    COUNT(DISTINCT MONTH(t.Time)) as active_months,
                    -- Recent activity (last 90 days)
                    SUM(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE()) THEN t.Total ELSE 0 END) as revenue_last_90_days,
                    COUNT(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE()) THEN 1 END) as transactions_last_90_days,
                    -- Payment behavior
                    (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                     FROM dbo.Payment p
                     JOIN dbo.AccountReceivable ar ON p.CustomerID = ar.CustomerID
                     WHERE p.CustomerID = c.ID) as avg_payment_days,
                    (SELECT COUNT(*) FROM dbo.Payment 
                     WHERE CustomerID = c.ID AND (Comment LIKE '%NSF%' OR Comment LIKE '%RETURN%')) as nsf_count,
                    -- AR metrics
                    (SELECT SUM(Balance) FROM dbo.AccountReceivable 
                     WHERE CustomerID = c.ID AND Balance > 0) as current_ar_balance
                FROM dbo.Customer c
                LEFT JOIN dbo.[Transaction] t ON c.ID = t.CustomerID AND t.Status = 0
                WHERE c.ID IS NOT NULL
                GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance, 
                         c.CreditLimit, c.TotalSales, c.LastVisit, c.AccountOpened
                HAVING COUNT(t.TransactionNumber) > 0  -- Only customers with transactions
            )
            SELECT 
                *,
                -- Risk indicators
                CASE 
                    WHEN recency_days > 180 AND total_revenue > 50000 THEN 1
                    WHEN nsf_count > 1 AND current_ar_balance > 10000 THEN 1
                    ELSE 0
                END as is_high_value_at_risk,
                -- Win-back candidate
                CASE
                    WHEN recency_days > 90 AND recency_days <= 365 
                         AND total_revenue > 10000 THEN 1
                    ELSE 0
                END as is_win_back_candidate,
                -- Customer size classification
                CASE 
                    WHEN total_revenue > 500000 THEN 'Enterprise'
                    WHEN total_revenue > 100000 THEN 'Large'
                    WHEN total_revenue > 25000 THEN 'Medium'
                    WHEN total_revenue > 5000 THEN 'Small'
                    ELSE 'Micro'
                END as customer_size
            FROM CustomerMetrics
            ORDER BY total_revenue DESC
            """
            
            return self.db.execute_query(query, description="Extract Customer Transaction Data")
    
    def _calculate_rfm_scores(self, customer_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate RFM (Recency, Frequency, Monetary) scores"""
        if customer_data.empty:
            return pd.DataFrame()
        
        logger.info("📊 Calculating RFM scores...")
        
        # Prepare RFM data
        rfm_data = customer_data.copy()
        
        # Handle missing values and convert data types
        rfm_data['recency_days'] = pd.to_numeric(rfm_data['recency_days'], errors='coerce').fillna(365)
        rfm_data['total_transactions'] = pd.to_numeric(rfm_data['total_transactions'], errors='coerce').fillna(0)
        rfm_data['total_revenue'] = pd.to_numeric(rfm_data['total_revenue'], errors='coerce').fillna(0)
        
        # Convert other decimal/numeric columns to float
        numeric_columns = ['avg_transaction_value', 'customer_lifetime_days', 'frequency_per_month',
                          'revenue_last_90_days', 'transactions_last_90_days', 'avg_payment_days',
                          'nsf_count', 'current_ar_balance', 'account_age_days', 'active_days', 'active_months']
        for col in numeric_columns:
            if col in rfm_data.columns:
                rfm_data[col] = pd.to_numeric(rfm_data[col], errors='coerce').fillna(0)
        
        # Calculate RFM scores (1-5 scale, 5 is best)
        # Recency: Lower days = higher score
        rfm_data['R_score'] = pd.qcut(
            rfm_data['recency_days'].rank(method='first', ascending=False), 
            5, labels=[5,4,3,2,1]
        ).astype(int)
        
        # Frequency: Higher transactions = higher score  
        rfm_data['F_score'] = pd.qcut(
            rfm_data['total_transactions'].rank(method='first'), 
            5, labels=[1,2,3,4,5]
        ).astype(int)
        
        # Monetary: Higher revenue = higher score
        rfm_data['M_score'] = pd.qcut(
            rfm_data['total_revenue'].rank(method='first'), 
            5, labels=[1,2,3,4,5]
        ).astype(int)
        
        # Combined RFM score
        rfm_data['RFM_score'] = (
            rfm_data['R_score'].astype(str) + 
            rfm_data['F_score'].astype(str) + 
            rfm_data['M_score'].astype(str)
        )
        
        # RFM combined numeric score for ranking
        rfm_data['RFM_numeric'] = (
            rfm_data['R_score'] * 100 + 
            rfm_data['F_score'] * 10 + 
            rfm_data['M_score']
        )
        
        logger.info(f"✅ RFM scores calculated - Range: {rfm_data['RFM_numeric'].min()}-{rfm_data['RFM_numeric'].max()}")
        return rfm_data
    
    def _perform_customer_segmentation(self, rfm_data: pd.DataFrame) -> pd.DataFrame:
        """Segment customers based on RFM scores"""
        if rfm_data.empty:
            return pd.DataFrame()
        
        logger.info("🎯 Performing customer segmentation...")
        
        def assign_segment(row):
            """Assign segment based on RFM scores"""
            r, f, m = row['R_score'], row['F_score'], row['M_score']
            
            # VIP Customers: High value, frequent, recent
            if r >= 4 and f >= 4 and m >= 4:
                return 'VIP Champions'
            
            # Loyal Customers: High frequency and monetary, varying recency
            elif f >= 4 and m >= 4:
                return 'Loyal Customers' if r >= 3 else 'At-Risk Loyal'
            
            # Big Spenders: High monetary, varying frequency and recency
            elif m >= 4:
                if r >= 4:
                    return 'New Big Spenders'
                elif r >= 2:
                    return 'Big Spenders'
                else:
                    return 'Lost Big Spenders'
            
            # Recent customers with potential
            elif r >= 4:
                if f >= 3:
                    return 'Potential Loyalists'
                else:
                    return 'New Customers'
            
            # Hibernating customers (were active, now inactive)
            elif r <= 2:
                if f >= 3 or m >= 3:
                    return 'Hibernating'
                else:
                    return 'Lost Customers'
            
            # At-risk customers (declining engagement)
            elif r == 3:
                if f >= 3 or m >= 3:
                    return 'At-Risk'
                else:
                    return 'Casual Customers'
            
            # Default for remaining customers
            else:
                return 'Casual Customers'
        
        rfm_data['segment'] = rfm_data.apply(assign_segment, axis=1)
        
        # Calculate segment statistics
        segment_stats = rfm_data.groupby('segment').agg({
            'customer_id': 'count',
            'total_revenue': ['sum', 'mean'],
            'total_transactions': 'mean',
            'recency_days': 'mean',
            'RFM_numeric': 'mean'
        }).round(2)
        
        logger.info(f"✅ Customer segmentation completed:")
        for segment in rfm_data['segment'].unique():
            count = (rfm_data['segment'] == segment).sum()
            logger.info(f"   {segment}: {count} customers")
        
        return rfm_data
    
    def _calculate_clv_by_cohort(self, segmented_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate Customer Lifetime Value by cohort/segment"""
        if segmented_data.empty:
            return {}
        
        logger.info("💰 Calculating CLV by cohort...")
        
        clv_analysis = {}
        
        for segment in segmented_data['segment'].unique():
            segment_data = segmented_data[segmented_data['segment'] == segment].copy()
            
            if len(segment_data) == 0:
                continue
            
            # Calculate segment metrics
            avg_transaction_value = segment_data['avg_transaction_value'].mean()
            avg_transactions_per_month = segment_data['frequency_per_month'].mean() 
            avg_customer_lifetime_months = segment_data['customer_lifetime_days'].mean() / 30.42
            
            # Simple CLV calculation: AOV * Purchase Frequency * Customer Lifetime
            avg_monthly_revenue = avg_transaction_value * avg_transactions_per_month
            total_clv = avg_monthly_revenue * avg_customer_lifetime_months
            
            # 12-month CLV projection
            clv_12_month = avg_monthly_revenue * 12
            
            # Risk-adjusted CLV (reduce CLV for at-risk segments)
            risk_multiplier = 1.0
            if 'At-Risk' in segment or 'Lost' in segment or 'Hibernating' in segment:
                risk_multiplier = 0.5
            elif segment == 'VIP Champions':
                risk_multiplier = 1.2
            elif 'Loyal' in segment:
                risk_multiplier = 1.1
            
            adjusted_clv = total_clv * risk_multiplier
            adjusted_clv_12_month = clv_12_month * risk_multiplier
            
            # Add CLV back to segment data
            segment_data['clv_total'] = adjusted_clv
            segment_data['clv_12_month'] = adjusted_clv_12_month
            
            clv_analysis[segment] = {
                'customer_count': len(segment_data),
                'avg_transaction_value': round(avg_transaction_value, 2),
                'avg_frequency_per_month': round(avg_transactions_per_month, 2),
                'avg_lifetime_months': round(avg_customer_lifetime_months, 1),
                'avg_clv_total': round(adjusted_clv, 2),
                'avg_clv_12_month': round(adjusted_clv_12_month, 2),
                'total_segment_clv': round(adjusted_clv * len(segment_data), 2),
                'risk_multiplier': risk_multiplier,
                'revenue_contribution': round(segment_data['total_revenue'].sum(), 2)
            }
        
        # Update the main dataframe with CLV values
        for segment in segmented_data['segment'].unique():
            mask = segmented_data['segment'] == segment
            if segment in clv_analysis:
                segmented_data.loc[mask, 'clv_total'] = clv_analysis[segment]['avg_clv_total']
                segmented_data.loc[mask, 'clv_12_month'] = clv_analysis[segment]['avg_clv_12_month']
        
        logger.info(f"✅ CLV calculated for {len(clv_analysis)} segments")
        return clv_analysis
    
    def _identify_at_risk_customers(self, segmented_data: pd.DataFrame) -> List[Dict]:
        """Identify high-value customers at risk of churning"""
        if segmented_data.empty:
            return []
        
        logger.info("⚠️ Identifying high-value at-risk customers...")
        
        # Define at-risk criteria
        at_risk_conditions = (
            (segmented_data['total_revenue'] > segmented_data['total_revenue'].quantile(0.7)) &  # High value
            (
                (segmented_data['recency_days'] > 90) |  # Haven't purchased recently
                (segmented_data['revenue_last_90_days'] < segmented_data['total_revenue'] * 0.1) |  # Low recent activity
                (segmented_data['nsf_count'] > 0) |  # Payment issues
                (segmented_data['segment'].str.contains('At-Risk|Lost|Hibernating', na=False))  # Risk segment
            )
        )
        
        at_risk_customers = segmented_data[at_risk_conditions].copy()
        
        if at_risk_customers.empty:
            return []
        
        # Calculate risk score (0-100, higher is riskier)
        at_risk_customers['risk_score'] = (
            np.minimum(at_risk_customers['recency_days'] / 365 * 40, 40) +  # Recency risk (max 40)
            np.minimum(at_risk_customers['nsf_count'] * 15, 30) +  # Payment risk (max 30)
            (100 - at_risk_customers['RFM_numeric']) / 5.55 * 30  # RFM risk (max 30)
        ).round(1)
        
        # Sort by risk score and revenue
        at_risk_customers = at_risk_customers.sort_values(['risk_score', 'total_revenue'], ascending=[False, False])
        
        # Convert to list of dictionaries
        at_risk_list = []
        for _, customer in at_risk_customers.iterrows():
            at_risk_list.append({
                'customer_id': int(customer['customer_id']),
                'company_name': str(customer['Company'] or ''),
                'total_revenue': float(customer['total_revenue']),
                'recency_days': int(customer['recency_days']),
                'last_purchase_date': customer['last_purchase_date'].strftime('%Y-%m-%d') if pd.notna(customer['last_purchase_date']) else None,
                'segment': str(customer['segment']),
                'clv_12_month': float(customer.get('clv_12_month', 0)),
                'current_ar_balance': float(customer.get('current_ar_balance') or 0),
                'nsf_count': int(customer.get('nsf_count') or 0),
                'risk_score': float(customer['risk_score']),
                'recommended_action': self._get_retention_recommendation(customer)
            })
        
        logger.info(f"✅ Identified {len(at_risk_list)} high-value at-risk customers")
        return at_risk_list
    
    def _analyze_cross_sell_opportunities(self) -> List[Dict]:
        """Analyze basket affinity for cross-sell opportunities"""
        logger.info("🛒 Analyzing cross-sell opportunities...")
        
        with self.db:
            # Get customer category purchase patterns
            query = """
            WITH CustomerCategoryPurchases AS (
                SELECT 
                    t.CustomerID,
                    c.Company,
                    cat.Name as Category,
                    COUNT(*) as purchase_count,
                    SUM(td.Price * td.Quantity) as category_revenue,
                    MAX(t.Time) as last_purchase_date,
                    COUNT(DISTINCT CAST(t.Time as DATE)) as purchase_days
                FROM dbo.[Transaction] t
                JOIN dbo.TransactionEntry td ON t.TransactionNumber = td.TransactionNumber
                LEFT JOIN dbo.Item i ON td.ItemID = i.ID
                LEFT JOIN dbo.Category cat ON i.CategoryID = cat.ID
                LEFT JOIN dbo.Customer c ON t.CustomerID = c.ID
                WHERE t.Status = 0
                    AND cat.Name IS NOT NULL
                    AND cat.Name != ''
                    AND t.Time >= DATEADD(month, -12, GETDATE())  -- Last 12 months
                GROUP BY t.CustomerID, c.Company, cat.Name
            ),
            CustomerPrimaryCat AS (
                SELECT 
                    CustomerID,
                    Company,
                    Category as primary_category,
                    category_revenue as primary_revenue,
                    ROW_NUMBER() OVER (PARTITION BY CustomerID ORDER BY category_revenue DESC) as cat_rank
                FROM CustomerCategoryPurchases
            ),
            CategoryAffinity AS (
                SELECT 
                    cp1.Category as category_a,
                    cp2.Category as category_b,
                    COUNT(DISTINCT cp1.CustomerID) as shared_customers,
                    AVG(cp1.category_revenue + cp2.category_revenue) as avg_combined_revenue
                FROM CustomerCategoryPurchases cp1
                JOIN CustomerCategoryPurchases cp2 ON cp1.CustomerID = cp2.CustomerID
                WHERE cp1.Category != cp2.Category
                GROUP BY cp1.Category, cp2.Category
                HAVING COUNT(DISTINCT cp1.CustomerID) >= 5  -- At least 5 customers bought both
            )
            SELECT TOP 50
                pc.CustomerID,
                pc.Company,
                pc.primary_category,
                pc.primary_revenue,
                ca.category_b as recommended_category,
                ca.avg_combined_revenue as potential_revenue,
                1 as recommendation_count
            FROM CustomerPrimaryCat pc
            LEFT JOIN CategoryAffinity ca ON pc.primary_category = ca.category_a
            WHERE pc.cat_rank = 1  -- Only primary category per customer
                AND pc.primary_revenue > 1000  -- Minimum revenue threshold
                AND ca.category_b IS NOT NULL
                AND ca.category_b != pc.primary_category
            ORDER BY pc.primary_revenue DESC, ca.avg_combined_revenue DESC
            """
            
            cross_sell_data = self.db.execute_query(query, description="Analyze Cross-sell Opportunities")
        
        if cross_sell_data.empty:
            return []
        
        # Group by customer to create recommended categories list
        cross_sell_dict = {}
        for _, row in cross_sell_data.iterrows():
            customer_id = int(row['CustomerID'])
            if customer_id not in cross_sell_dict:
                cross_sell_dict[customer_id] = {
                    'customer_id': customer_id,
                    'company_name': str(row['Company'] or ''),
                    'primary_category': str(row['primary_category']),
                    'primary_revenue': float(row['primary_revenue']),
                    'recommended_categories': [],
                    'potential_revenue': 0,
                    'recommendation_count': 0
                }
            
            cross_sell_dict[customer_id]['recommended_categories'].append(str(row['recommended_category']))
            cross_sell_dict[customer_id]['potential_revenue'] += float(row.get('potential_revenue') or 0)
            cross_sell_dict[customer_id]['recommendation_count'] += 1
        
        cross_sell_opportunities = []
        for customer_id, data in cross_sell_dict.items():
            # Calculate confidence based on revenue and recommendation count
            confidence = 'High' if data['primary_revenue'] > 10000 and data['recommendation_count'] >= 3 else \
                        'Medium' if data['primary_revenue'] > 5000 or data['recommendation_count'] >= 2 else 'Low'
            
            # Calculate affinity score (0-1)
            affinity_score = min((data['recommendation_count'] / 5) * (data['primary_revenue'] / 50000), 1.0)
            
            data['affinity_score'] = round(affinity_score, 3)
            data['confidence'] = confidence
            cross_sell_opportunities.append(data)
        
        # Sort by affinity score and primary revenue
        cross_sell_opportunities.sort(key=lambda x: (x['affinity_score'], x['primary_revenue']), reverse=True)
        
        logger.info(f"✅ Found {len(cross_sell_opportunities)} cross-sell opportunities")
        return cross_sell_opportunities[:50]  # Return top 50
    
    def _identify_win_back_targets(self, segmented_data: pd.DataFrame) -> List[Dict]:
        """Identify customers for win-back campaigns"""
        if segmented_data.empty:
            return []
        
        logger.info("🎯 Identifying win-back campaign targets...")
        
        # Win-back criteria: Previously valuable customers who haven't purchased recently
        win_back_conditions = (
            (segmented_data['total_revenue'] > segmented_data['total_revenue'].quantile(0.5)) &  # Above median revenue
            (segmented_data['recency_days'] > 60) &  # Haven't purchased in 60+ days
            (segmented_data['recency_days'] <= 365) &  # But within last year
            (segmented_data['total_transactions'] >= 3) &  # Had meaningful engagement
            (~segmented_data['segment'].str.contains('Lost', na=False))  # Not completely lost
        )
        
        win_back_candidates = segmented_data[win_back_conditions].copy()
        
        if win_back_candidates.empty:
            return []
        
        # Calculate win-back score (likelihood of re-engagement)
        win_back_candidates['win_back_score'] = (
            (win_back_candidates['total_revenue'] / win_back_candidates['total_revenue'].max() * 40) +  # Revenue potential
            (win_back_candidates['total_transactions'] / win_back_candidates['total_transactions'].max() * 30) +  # Engagement history
            (np.maximum(365 - win_back_candidates['recency_days'], 0) / 305 * 30)  # Recency bonus
        ).round(1)
        
        win_back_candidates = win_back_candidates.sort_values('win_back_score', ascending=False)
        
        win_back_list = []
        for _, customer in win_back_candidates.iterrows():
            win_back_list.append({
                'customer_id': int(customer['customer_id']),
                'company_name': str(customer['Company'] or ''),
                'total_revenue': float(customer['total_revenue']),
                'total_transactions': int(customer['total_transactions']),
                'recency_days': int(customer['recency_days']),
                'last_purchase_date': customer['last_purchase_date'].strftime('%Y-%m-%d') if pd.notna(customer['last_purchase_date']) else None,
                'segment': str(customer['segment']),
                'clv_12_month': float(customer.get('clv_12_month', 0)),
                'win_back_score': float(customer['win_back_score']),
                'recommended_campaign': self._get_win_back_campaign_type(customer)
            })
        
        logger.info(f"✅ Identified {len(win_back_list)} win-back campaign targets")
        return win_back_list
    
    def _generate_segment_insights(self, segmented_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights for each customer segment"""
        if segmented_data.empty:
            return {}
        
        logger.info("💡 Generating segment insights...")
        
        insights = {}
        
        for segment in segmented_data['segment'].unique():
            segment_data = segmented_data[segmented_data['segment'] == segment]
            
            if len(segment_data) == 0:
                continue
            
            # Calculate segment metrics
            total_customers = len(segment_data)
            total_revenue = segment_data['total_revenue'].sum()
            avg_revenue = segment_data['total_revenue'].mean()
            avg_recency = segment_data['recency_days'].mean()
            avg_frequency = segment_data['total_transactions'].mean()
            avg_clv = segment_data.get('clv_12_month', pd.Series([0])).mean()
            
            # Revenue contribution
            total_business_revenue = segmented_data['total_revenue'].sum()
            revenue_contribution = (total_revenue / total_business_revenue * 100) if total_business_revenue > 0 else 0
            
            # Segment characteristics
            characteristics = self._get_segment_characteristics(segment, segment_data)
            
            insights[segment] = {
                'customer_count': total_customers,
                'total_revenue': round(total_revenue, 2),
                'avg_revenue_per_customer': round(avg_revenue, 2),
                'revenue_contribution_pct': round(revenue_contribution, 1),
                'avg_recency_days': round(avg_recency, 1),
                'avg_transactions': round(avg_frequency, 1),
                'avg_clv_12_month': round(avg_clv, 2),
                'characteristics': characteristics,
                'recommended_strategies': self._get_segment_strategies(segment)
            }
        
        logger.info(f"✅ Generated insights for {len(insights)} segments")
        return insights
    
    def _get_rfm_distribution(self, segmented_data: pd.DataFrame) -> Dict[str, Any]:
        """Get RFM score distribution analysis"""
        if segmented_data.empty:
            return {}
        
        return {
            'total_customers': len(segmented_data),
            'rfm_score_ranges': {
                'high_value': len(segmented_data[segmented_data['RFM_numeric'] >= 444]),
                'medium_value': len(segmented_data[(segmented_data['RFM_numeric'] >= 333) & (segmented_data['RFM_numeric'] < 444)]),
                'low_value': len(segmented_data[segmented_data['RFM_numeric'] < 333])
            },
            'segment_distribution': segmented_data['segment'].value_counts().to_dict(),
            'avg_rfm_by_segment': segmented_data.groupby('segment')['RFM_numeric'].mean().round(1).to_dict()
        }
    
    def _generate_actionable_recommendations(self, segmented_data: pd.DataFrame, 
                                           at_risk_customers: List[Dict],
                                           cross_sell_opportunities: List[Dict],
                                           win_back_targets: List[Dict]) -> List[Dict]:
        """Generate actionable business recommendations"""
        recommendations = []
        
        # VIP Champions recommendations
        vip_count = len(segmented_data[segmented_data['segment'] == 'VIP Champions'])
        if vip_count > 0:
            recommendations.append({
                'category': 'VIP Retention',
                'priority': 'Critical',
                'recommendation': f'Implement white-glove service for {vip_count} VIP Champions',
                'expected_impact': 'Retain highest-value customers, increase loyalty',
                'action_items': [
                    'Assign dedicated account managers',
                    'Offer exclusive pricing tiers', 
                    'Provide priority support and delivery'
                ]
            })
        
        # At-risk customer recommendations
        if len(at_risk_customers) > 0:
            high_risk = len([c for c in at_risk_customers if c['risk_score'] > 70])
            recommendations.append({
                'category': 'Risk Mitigation',
                'priority': 'Urgent',
                'recommendation': f'Launch urgent retention campaign for {len(at_risk_customers)} at-risk customers ({high_risk} high-risk)',
                'expected_impact': 'Prevent customer churn, protect revenue',
                'action_items': [
                    'Personal outreach to high-risk customers',
                    'Address payment issues proactively',
                    'Offer incentives to re-engage'
                ]
            })
        
        # Cross-sell recommendations
        if len(cross_sell_opportunities) > 0:
            high_confidence = len([o for o in cross_sell_opportunities if o['confidence'] == 'High'])
            recommendations.append({
                'category': 'Revenue Growth',
                'priority': 'High',
                'recommendation': f'Execute cross-sell campaigns for {len(cross_sell_opportunities)} opportunities ({high_confidence} high-confidence)',
                'expected_impact': 'Increase average order value, diversify customer purchases',
                'action_items': [
                    'Create targeted product bundles',
                    'Implement recommendation engine in ordering system',
                    'Train sales team on category affinities'
                ]
            })
        
        # Win-back recommendations
        if len(win_back_targets) > 0:
            recommendations.append({
                'category': 'Customer Re-engagement',
                'priority': 'Medium',
                'recommendation': f'Launch win-back campaign for {len(win_back_targets)} dormant customers',
                'expected_impact': 'Re-activate dormant revenue streams',
                'action_items': [
                    'Send personalized re-engagement offers',
                    'Conduct customer feedback surveys',
                    'Offer trial periods or discounts'
                ]
            })
        
        # Segment-specific recommendations
        new_customers = len(segmented_data[segmented_data['segment'] == 'New Customers'])
        if new_customers > 0:
            recommendations.append({
                'category': 'Customer Development',
                'priority': 'Medium',
                'recommendation': f'Implement onboarding program for {new_customers} new customers',
                'expected_impact': 'Improve customer lifetime value, reduce churn',
                'action_items': [
                    'Create welcome package with product samples',
                    'Schedule regular check-ins in first 90 days',
                    'Provide educational content about products'
                ]
            })
        
        return recommendations
    
    def _get_retention_recommendation(self, customer_row) -> str:
        """Get specific retention recommendation for at-risk customer"""
        risk_score = customer_row.get('risk_score', 0)
        recency = customer_row.get('recency_days', 0)
        nsf_count = customer_row.get('nsf_count', 0)
        
        if risk_score > 80:
            return 'Urgent: Personal call from management within 24 hours'
        elif nsf_count > 1:
            return 'Address payment issues and offer payment plan'
        elif recency > 180:
            return 'Win-back campaign with special offer'
        else:
            return 'Regular check-in and needs assessment'
    
    def _get_win_back_campaign_type(self, customer_row) -> str:
        """Get specific win-back campaign recommendation"""
        revenue = customer_row.get('total_revenue', 0)
        recency = customer_row.get('recency_days', 0)
        
        if revenue > 100000:
            return 'VIP Re-engagement: Personal meeting with account manager'
        elif recency > 180:
            return 'Special Offer Campaign: 15% discount on next order'
        else:
            return 'Check-in Campaign: Phone call to assess needs'
    
    def _get_segment_characteristics(self, segment: str, segment_data: pd.DataFrame) -> List[str]:
        """Get characteristics for a customer segment"""
        characteristics = []
        
        avg_revenue = segment_data['total_revenue'].mean()
        avg_recency = segment_data['recency_days'].mean()
        avg_frequency = segment_data['total_transactions'].mean()
        
        if avg_revenue > 100000:
            characteristics.append('High-value customers')
        elif avg_revenue > 25000:
            characteristics.append('Medium-value customers')
        else:
            characteristics.append('Lower-value customers')
            
        if avg_recency < 30:
            characteristics.append('Very active')
        elif avg_recency < 90:
            characteristics.append('Recently active')
        else:
            characteristics.append('Inactive')
            
        if avg_frequency > 20:
            characteristics.append('Frequent buyers')
        elif avg_frequency > 10:
            characteristics.append('Regular buyers')
        else:
            characteristics.append('Occasional buyers')
        
        return characteristics
    
    def _get_segment_strategies(self, segment: str) -> List[str]:
        """Get recommended strategies for each segment"""
        strategies = {
            'VIP Champions': [
                'Maintain premium service levels',
                'Offer exclusive products and pricing',
                'Implement loyalty rewards program'
            ],
            'Loyal Customers': [
                'Recognize loyalty with special perks',
                'Cross-sell complementary products',
                'Request referrals and testimonials'
            ],
            'Big Spenders': [
                'Provide volume-based discounts',
                'Offer premium product lines',
                'Ensure excellent customer service'
            ],
            'At-Risk': [
                'Proactive engagement campaigns',
                'Address service issues quickly',
                'Offer win-back incentives'
            ],
            'New Customers': [
                'Onboarding and education programs',
                'Product trial opportunities',
                'Regular check-ins and support'
            ],
            'Hibernating': [
                'Re-engagement campaigns',
                'Survey for feedback',
                'Special comeback offers'
            ],
            'Lost Customers': [
                'Win-back campaigns',
                'Competitive analysis',
                'Product portfolio review'
            ]
        }
        
        return strategies.get(segment, ['Develop targeted engagement strategy'])

def main():
    """Main execution function"""
    logger.info("🚀 Starting Customer Segmentation and CLV Analysis...")
    
    # Initialize analyzer with strategic data
    strategic_data_path = "/Users/akbarchranya/georgiadashboard/strategic_data_extraction_20250908_164747.json"
    analyzer = CustomerSegmentationCLV(strategic_data_path)
    
    try:
        # Perform comprehensive analysis
        results = analyzer.perform_comprehensive_analysis()
        
        if not results:
            logger.error("❌ Analysis failed - no results generated")
            return
        
        # Export results to JSON
        output_file = "/Users/akbarchranya/georgiadashboard/customer_segmentation_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"✅ Analysis complete! Results exported to: {output_file}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("CUSTOMER SEGMENTATION & CLV ANALYSIS SUMMARY")
        print("="*80)
        
        summary = results.get('summary', {})
        print(f"📊 Total Customers Analyzed: {summary.get('total_customers_analyzed', 0):,}")
        print(f"🎯 Customer Segments Created: {summary.get('segments_created', 0)}")
        print(f"⚠️  High-Value At-Risk Customers: {summary.get('high_value_at_risk_count', 0)}")
        print(f"🛒 Cross-Sell Opportunities: {summary.get('cross_sell_opportunities_count', 0)}")
        print(f"🎯 Win-Back Campaign Targets: {summary.get('win_back_targets_count', 0)}")
        
        print(f"\n📈 SEGMENT BREAKDOWN:")
        segment_insights = results.get('segment_insights', {})
        for segment, data in segment_insights.items():
            print(f"   {segment}: {data['customer_count']:,} customers (${data['total_revenue']:,.0f} revenue)")
        
        print(f"\n🎯 TOP ACTIONABLE RECOMMENDATIONS:")
        recommendations = results.get('actionable_recommendations', [])[:3]
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['recommendation']}")
        
        print(f"\n💾 Full results exported to: {output_file}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Analysis failed with error: {e}")
        raise

if __name__ == "__main__":
    main()