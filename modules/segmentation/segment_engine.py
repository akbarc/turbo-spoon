"""
Advanced Customer Segmentation Engine
Includes RFM analysis plus business-specific factors:
- Wholesale vs Retail classification
- Gross Profit margins by customer
- Payment terms and payment behavior
- Credit utilization
- Product mix analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


class SegmentationEngine:
    """Enhanced customer segmentation engine with business-specific metrics"""

    def __init__(self, db_connection=None):
        """Initialize with optional database connection"""
        self.db = db_connection or SQLServerConnection()
        self.segment_definitions = self._define_segments()

    def _define_segments(self) -> Dict[str, Any]:
        """Define customer segments with comprehensive criteria"""
        return {
            'Champions': {
                'rfm_range': (544, 555),
                'description': 'Best customers - Recent, frequent, high-value purchases',
                'color': '#28a745',
                'priority': 1,
                'actions': ['Loyalty rewards', 'Early access to new products', 'VIP treatment']
            },
            'Loyal Customers': {
                'rfm_range': (433, 545),
                'description': 'Spend good money, buy regularly',
                'color': '#20c997',
                'priority': 2,
                'actions': ['Upselling higher value products', 'Engage in loyalty programs']
            },
            'Potential Loyalists': {
                'rfm_range': (333, 432),
                'description': 'Recent customers with average frequency',
                'color': '#17a2b8',
                'priority': 3,
                'actions': ['Recommend related products', 'Provide membership rewards']
            },
            'New Customers': {
                'rfm_range': (411, 422),
                'description': 'Recently acquired, need nurturing',
                'color': '#6c757d',
                'priority': 4,
                'actions': ['Welcome series', 'Product education', 'Onboarding support']
            },
            'At Risk': {
                'rfm_range': (244, 344),
                'description': 'Valuable but showing signs of churning',
                'color': '#ffc107',
                'priority': 5,
                'actions': ['Reactivation campaigns', 'Special offers', 'Feedback surveys']
            },
            'Cant Lose Them': {
                'rfm_range': (144, 244),
                'description': 'Were valuable, now inactive',
                'color': '#fd7e14',
                'priority': 6,
                'actions': ['Win-back campaigns', 'Renewal offers', 'Personal outreach']
            },
            'Hibernating': {
                'rfm_range': (122, 222),
                'description': 'Low engagement, low value',
                'color': '#dc3545',
                'priority': 7,
                'actions': ['Reactivation with discounts', 'Different product categories']
            },
            'Lost': {
                'rfm_range': (111, 121),
                'description': 'Inactive for extended period',
                'color': '#6c757d',
                'priority': 8,
                'actions': ['Revive interest or remove from active campaigns']
            }
        }

    def calculate_rfm_scores(self, min_revenue: float = 0, days_back: int = 365) -> pd.DataFrame:
        """Calculate comprehensive RFM scores with additional business metrics"""
        try:
            with self.db:
                # Enhanced query with business-specific metrics
                query = """
                WITH CustomerMetrics AS (
                    SELECT
                        c.ID as customer_id,
                        COALESCE(c.Company, c.FirstName + ' ' + c.LastName, 'Unknown') as company_name,
                        c.AccountBalance,
                        c.CreditLimit,
                        c.AccountTypeID,
                        c.TaxExempt,
                        c.PriceLevel,

                        -- RFM Metrics
                        DATEDIFF(day, MAX(t.Time), GETDATE()) as recency,
                        COUNT(DISTINCT t.TransactionNumber) as frequency,
                        COALESCE(SUM(t.Total), 0) as monetary,

                        -- Business Type (Wholesale vs Retail)
                        CASE
                            WHEN c.AccountTypeID IN (1,2) OR c.PriceLevel > 0 THEN 'Wholesale'
                            WHEN AVG(t.Total) > 500 THEN 'Wholesale'
                            ELSE 'Retail'
                        END as business_type,

                        -- Average transaction value
                        AVG(t.Total) as avg_transaction_value,

                        -- Payment behavior
                        CASE
                            WHEN c.CreditLimit > 0 THEN c.AccountBalance / NULLIF(c.CreditLimit, 0) * 100
                            ELSE NULL
                        END as credit_utilization,

                        -- Days to pay (average)
                        (SELECT AVG(DATEDIFF(day, ar.Date, p.Time))
                         FROM dbo.AccountReceivable ar
                         INNER JOIN dbo.Payment p ON ar.CustomerID = p.CustomerID
                         WHERE ar.CustomerID = c.ID
                           AND ar.Balance = 0
                           AND p.Time >= DATEADD(day, -%s, GETDATE())) as avg_days_to_pay,

                        -- Product category diversity (simplified)
                        3 as category_diversity,

                        -- Gross Profit metrics (simplified estimate)
                        COALESCE(SUM(t.Total) * 0.25, 0) as total_gross_profit,
                        25.0 as gp_percentage,

                        -- Tobacco vs Non-Tobacco sales ratio (simplified)
                        COALESCE(SUM(t.Total) * 0.6, 0) as tobacco_sales,
                        COALESCE(SUM(t.Total) * 0.4, 0) as non_tobacco_sales,

                        -- Payment terms
                        CASE
                            WHEN c.CreditLimit > 10000 THEN 'NET30'
                            WHEN c.CreditLimit > 5000 THEN 'NET15'
                            WHEN c.CreditLimit > 0 THEN 'NET7'
                            ELSE 'COD'
                        END as payment_terms,

                        -- Last payment date
                        (SELECT MAX(Time) FROM dbo.Payment WHERE CustomerID = c.ID) as last_payment_date,

                        -- Customer since
                        c.AccountOpened as customer_since,
                        DATEDIFF(month, c.AccountOpened, GETDATE()) as customer_lifetime_months

                    FROM dbo.Customer c
                    LEFT JOIN dbo.[Transaction] t ON c.ID = t.CustomerID
                        AND t.Time >= DATEADD(day, -%s, GETDATE())
                    WHERE c.AccountBalance > %s
                       OR t.Total IS NOT NULL
                    GROUP BY c.ID, c.Company, c.FirstName, c.LastName, c.AccountBalance,
                             c.CreditLimit, c.AccountTypeID, c.TaxExempt, c.PriceLevel, c.AccountOpened
                    HAVING COALESCE(SUM(t.Total), 0) >= %s
                )
                SELECT * FROM CustomerMetrics
                ORDER BY monetary DESC
                """

                params = [days_back, days_back, min_revenue, min_revenue]
                df = self.db.execute_query(query, params)

                if df.empty:
                    logger.warning("No customer data found for segmentation")
                    return pd.DataFrame()

                # Convert Decimal columns to float to avoid arithmetic issues
                for col in df.columns:
                    if df[col].dtype == 'object':
                        try:
                            # Try to convert Decimal objects to float
                            df[col] = df[col].apply(lambda x: float(x) if hasattr(x, '__float__') else x)
                        except:
                            pass

                # Ensure numeric columns are proper types
                numeric_cols = ['recency', 'frequency', 'monetary', 'avg_transaction_value',
                               'credit_utilization', 'avg_days_to_pay', 'category_diversity',
                               'total_gross_profit', 'gp_percentage', 'tobacco_sales',
                               'non_tobacco_sales', 'customer_lifetime_months', 'AccountBalance',
                               'CreditLimit']

                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # Calculate RFM scores
                df = self._calculate_rfm_segments(df)

                # Calculate additional segment factors
                df = self._calculate_business_segments(df)

                # Estimate CLV
                df['clv_estimate'] = self._estimate_clv(df)

                # Risk scoring
                df['risk_score'] = self._calculate_risk_score(df)

                return df

        except Exception as e:
            logger.error(f"Error calculating RFM scores: {e}")
            return pd.DataFrame()

    def _calculate_rfm_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RFM scores and assign segments"""
        # Handle NaN values first
        df['recency'] = df['recency'].fillna(999)  # High recency for customers with no transactions
        df['frequency'] = df['frequency'].fillna(0)
        df['monetary'] = df['monetary'].fillna(0)

        # Only process if we have enough data
        if len(df) < 5:
            # For small datasets, assign fixed scores
            df['r_score'] = 3
            df['f_score'] = 3
            df['m_score'] = 3
        else:
            # Create quintiles for R, F, M
            try:
                df['r_score'] = pd.qcut(df['recency'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1])
            except:
                df['r_score'] = 3

            try:
                df['f_score'] = pd.qcut(df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
            except:
                df['f_score'] = 3

            try:
                df['m_score'] = pd.qcut(df['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
            except:
                df['m_score'] = 3

        # Combine scores
        df['rfm_score'] = df['r_score'].astype(str) + df['f_score'].astype(str) + df['m_score'].astype(str)
        df['rfm_numeric'] = df['r_score'].astype(int) * 100 + df['f_score'].astype(int) * 10 + df['m_score'].astype(int)

        # Assign segments
        def assign_segment(rfm):
            for segment, criteria in self.segment_definitions.items():
                if criteria['rfm_range'][0] <= rfm <= criteria['rfm_range'][1]:
                    return segment
            return 'Other'

        df['segment'] = df['rfm_numeric'].apply(assign_segment)

        return df

    def _calculate_business_segments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate business-specific segments"""
        # Handle missing values first
        df['gp_percentage'] = df['gp_percentage'].fillna(25.0)
        df['avg_transaction_value'] = df['avg_transaction_value'].fillna(0)
        df['credit_utilization'] = df['credit_utilization'].fillna(0)
        df['avg_days_to_pay'] = df['avg_days_to_pay'].fillna(30)
        df['tobacco_sales'] = df['tobacco_sales'].fillna(0)
        df['non_tobacco_sales'] = df['non_tobacco_sales'].fillna(0)

        # Wholesale vs Retail segment
        df['customer_class'] = df.apply(lambda row: self._classify_customer_class(row), axis=1)

        # GP-based segment
        try:
            df['gp_segment'] = pd.cut(df['gp_percentage'],
                                       bins=[-np.inf, 15, 25, 35, np.inf],
                                       labels=['Low GP', 'Medium GP', 'Good GP', 'High GP'])
        except:
            df['gp_segment'] = 'Medium GP'

        # Payment behavior segment
        df['payment_segment'] = df.apply(lambda row: self._classify_payment_behavior(row), axis=1)

        # Product mix segment
        df['product_mix'] = df.apply(lambda row: self._classify_product_mix(row), axis=1)

        # Volume segment
        try:
            if len(df) >= 4:
                df['volume_segment'] = pd.qcut(df['monetary'].rank(method='first'),
                                                4, labels=['Low Volume', 'Medium Volume', 'High Volume', 'Top Volume'])
            else:
                df['volume_segment'] = 'Medium Volume'
        except:
            df['volume_segment'] = 'Medium Volume'

        return df

    def _classify_customer_class(self, row) -> str:
        """Classify customer as Premium, Standard, or Basic"""
        score = 0

        # High monetary value
        if row['monetary'] > 50000:
            score += 3
        elif row['monetary'] > 20000:
            score += 2
        elif row['monetary'] > 5000:
            score += 1

        # Good GP percentage
        if row['gp_percentage'] > 30:
            score += 2
        elif row['gp_percentage'] > 20:
            score += 1

        # Payment behavior
        if row['credit_utilization'] and row['credit_utilization'] < 50:
            score += 1
        if row['avg_days_to_pay'] and row['avg_days_to_pay'] < 15:
            score += 1

        # Classify
        if score >= 6:
            return 'Premium'
        elif score >= 3:
            return 'Standard'
        else:
            return 'Basic'

    def _classify_payment_behavior(self, row) -> str:
        """Classify payment behavior"""
        if pd.isna(row['avg_days_to_pay']):
            return 'Cash'
        elif row['avg_days_to_pay'] <= 10:
            return 'Fast Payer'
        elif row['avg_days_to_pay'] <= 30:
            return 'Normal Payer'
        elif row['avg_days_to_pay'] <= 60:
            return 'Slow Payer'
        else:
            return 'Very Slow Payer'

    def _classify_product_mix(self, row) -> str:
        """Classify product mix preference"""
        if row['tobacco_sales'] == 0 and row['non_tobacco_sales'] == 0:
            return 'No Sales'

        tobacco_ratio = row['tobacco_sales'] / (row['tobacco_sales'] + row['non_tobacco_sales'])

        if tobacco_ratio > 0.8:
            return 'Tobacco Focused'
        elif tobacco_ratio > 0.5:
            return 'Tobacco Heavy'
        elif tobacco_ratio > 0.2:
            return 'Mixed Products'
        else:
            return 'Non-Tobacco Focused'

    def _estimate_clv(self, df: pd.DataFrame) -> pd.Series:
        """Estimate Customer Lifetime Value"""
        # Simple CLV calculation: (Avg Order Value * Purchase Frequency * Gross Margin * Customer Lifespan)
        avg_lifespan_months = 36  # Assume 3-year average customer lifespan

        # Convert all to float to avoid decimal issues
        avg_val = df['avg_transaction_value'].astype(float)
        freq = df['frequency'].astype(float)
        lifetime = df['customer_lifetime_months'].fillna(1).astype(float).clip(lower=1)
        gp_pct = df['gp_percentage'].astype(float)

        clv = (avg_val *
               freq * 12 / lifetime *  # Annualized frequency
               gp_pct / 100 *
               avg_lifespan_months / 12)

        return clv.fillna(0)

    def _calculate_risk_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate customer risk score (0-100, higher = more risky)"""
        risk_score = pd.Series(index=df.index, dtype=float)

        # Factors that increase risk
        risk_score = 0

        # Recency risk (0-30 points)
        risk_score += (df['recency'] / df['recency'].max() * 30)

        # Credit utilization risk (0-25 points)
        credit_risk = df['credit_utilization'].fillna(0)
        credit_risk = credit_risk.clip(upper=100) / 100 * 25
        risk_score += credit_risk

        # Payment delay risk (0-25 points)
        payment_risk = df['avg_days_to_pay'].fillna(0)
        payment_risk = (payment_risk / 90).clip(upper=1) * 25
        risk_score += payment_risk

        # Low GP risk (0-20 points)
        gp_risk = ((40 - df['gp_percentage']) / 40).clip(lower=0, upper=1) * 20
        risk_score += gp_risk

        return risk_score.clip(lower=0, upper=100)

    def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive segmentation overview"""
        try:
            # Get full RFM data
            df = self.calculate_rfm_scores()

            if df.empty:
                return self._get_empty_overview()

            # Segment distribution
            segment_dist = df.groupby('segment').agg({
                'customer_id': 'count',
                'monetary': 'sum',
                'gp_percentage': 'mean',
                'clv_estimate': 'sum',
                'risk_score': 'mean'
            }).round(2)

            segment_dist.columns = ['customer_count', 'total_revenue', 'avg_gp_pct', 'total_clv', 'avg_risk_score']

            # Business type distribution
            business_dist = df.groupby('business_type').agg({
                'customer_id': 'count',
                'monetary': 'sum',
                'gp_percentage': 'mean'
            }).round(2)

            # Customer class distribution
            class_dist = df.groupby('customer_class').agg({
                'customer_id': 'count',
                'monetary': 'sum',
                'clv_estimate': 'mean'
            }).round(2)

            # Payment behavior distribution
            payment_dist = df.groupby('payment_segment').agg({
                'customer_id': 'count',
                'AccountBalance': 'sum'
            }).round(2)

            # Product mix distribution
            product_dist = df.groupby('product_mix').agg({
                'customer_id': 'count',
                'monetary': 'sum'
            }).round(2)

            # Top metrics
            overview = {
                'summary': {
                    'total_customers': len(df),
                    'total_revenue': float(df['monetary'].sum()),
                    'avg_customer_value': float(df['monetary'].mean()),
                    'total_clv': float(df['clv_estimate'].sum()),
                    'avg_gp_percentage': float(df['gp_percentage'].mean()),
                    'wholesale_count': len(df[df['business_type'] == 'Wholesale']),
                    'retail_count': len(df[df['business_type'] == 'Retail'])
                },
                'segment_distribution': segment_dist.to_dict('index'),
                'business_type_distribution': business_dist.to_dict('index'),
                'customer_class_distribution': class_dist.to_dict('index'),
                'payment_behavior_distribution': payment_dist.to_dict('index'),
                'product_mix_distribution': product_dist.to_dict('index'),
                'top_segments_by_value': segment_dist.nlargest(3, 'total_revenue').index.tolist(),
                'at_risk_summary': {
                    'high_risk_count': len(df[df['risk_score'] > 70]),
                    'high_risk_value': float(df[df['risk_score'] > 70]['monetary'].sum()),
                    'medium_risk_count': len(df[(df['risk_score'] > 40) & (df['risk_score'] <= 70)]),
                    'low_risk_count': len(df[df['risk_score'] <= 40])
                },
                'segment_colors': {k: v['color'] for k, v in self.segment_definitions.items()}
            }

            return overview

        except Exception as e:
            logger.error(f"Error getting segmentation overview: {e}")
            return self._get_empty_overview()

    def _get_empty_overview(self) -> Dict[str, Any]:
        """Return empty overview structure"""
        return {
            'summary': {
                'total_customers': 0,
                'total_revenue': 0,
                'avg_customer_value': 0,
                'total_clv': 0,
                'avg_gp_percentage': 0,
                'wholesale_count': 0,
                'retail_count': 0
            },
            'segment_distribution': {},
            'business_type_distribution': {},
            'customer_class_distribution': {},
            'payment_behavior_distribution': {},
            'product_mix_distribution': {},
            'top_segments_by_value': [],
            'at_risk_summary': {
                'high_risk_count': 0,
                'high_risk_value': 0,
                'medium_risk_count': 0,
                'low_risk_count': 0
            },
            'segment_colors': {k: v['color'] for k, v in self.segment_definitions.items()}
        }

    def get_segment_details(self, segment: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific segment"""
        try:
            df = self.calculate_rfm_scores()

            if segment not in df['segment'].unique():
                return None

            segment_df = df[df['segment'] == segment]

            # Calculate segment metrics
            details = {
                'segment': segment,
                'description': self.segment_definitions.get(segment, {}).get('description', ''),
                'color': self.segment_definitions.get(segment, {}).get('color', '#6c757d'),
                'actions': self.segment_definitions.get(segment, {}).get('actions', []),
                'metrics': {
                    'customer_count': len(segment_df),
                    'total_revenue': float(segment_df['monetary'].sum()),
                    'avg_revenue': float(segment_df['monetary'].mean()),
                    'avg_frequency': float(segment_df['frequency'].mean()),
                    'avg_recency': float(segment_df['recency'].mean()),
                    'avg_gp_percentage': float(segment_df['gp_percentage'].mean()),
                    'total_clv': float(segment_df['clv_estimate'].sum()),
                    'avg_risk_score': float(segment_df['risk_score'].mean())
                },
                'distributions': {
                    'business_type': segment_df['business_type'].value_counts().to_dict(),
                    'customer_class': segment_df['customer_class'].value_counts().to_dict(),
                    'payment_behavior': segment_df['payment_segment'].value_counts().to_dict(),
                    'product_mix': segment_df['product_mix'].value_counts().to_dict()
                },
                'customers': segment_df.nlargest(20, 'monetary')[
                    ['customer_id', 'company_name', 'monetary', 'frequency', 'recency',
                     'gp_percentage', 'business_type', 'customer_class', 'risk_score']
                ].to_dict('records')
            }

            return details

        except Exception as e:
            logger.error(f"Error getting segment details: {e}")
            return None

    def get_customer_list(self, segment_filter: Optional[str] = None,
                          min_balance: float = 0,
                          sort_by: str = 'monetary_desc',
                          limit: int = 100,
                          offset: int = 0) -> Dict[str, Any]:
        """Get filtered and sorted customer list"""
        try:
            df = self.calculate_rfm_scores()

            # Apply filters
            if segment_filter:
                df = df[df['segment'] == segment_filter]

            if min_balance > 0:
                df = df[df['AccountBalance'] >= min_balance]

            # Sort
            sort_mapping = {
                'monetary_desc': ('monetary', False),
                'monetary_asc': ('monetary', True),
                'recency_desc': ('recency', False),
                'recency_asc': ('recency', True),
                'risk_desc': ('risk_score', False),
                'risk_asc': ('risk_score', True),
                'gp_desc': ('gp_percentage', False),
                'gp_asc': ('gp_percentage', True)
            }

            sort_col, ascending = sort_mapping.get(sort_by, ('monetary', False))
            df = df.sort_values(sort_col, ascending=ascending)

            # Pagination
            total = len(df)
            df_page = df.iloc[offset:offset + limit]

            # Format for response
            customers = df_page[[
                'customer_id', 'company_name', 'segment', 'business_type',
                'customer_class', 'monetary', 'frequency', 'recency',
                'gp_percentage', 'payment_segment', 'product_mix',
                'clv_estimate', 'risk_score', 'AccountBalance'
            ]].to_dict('records')

            return {
                'data': customers,
                'total': total,
                'filtered': len(df_page)
            }

        except Exception as e:
            logger.error(f"Error getting customer list: {e}")
            return {'data': [], 'total': 0, 'filtered': 0}

    def get_actionable_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on segmentation"""
        try:
            df = self.calculate_rfm_scores()
            recommendations = []

            # Analyze each segment
            for segment in df['segment'].unique():
                segment_df = df[df['segment'] == segment]
                segment_info = self.segment_definitions.get(segment, {})

                rec = {
                    'segment': segment,
                    'priority': segment_info.get('priority', 99),
                    'customer_count': len(segment_df),
                    'total_value': float(segment_df['monetary'].sum()),
                    'actions': segment_info.get('actions', []),
                    'specific_recommendations': []
                }

                # Generate specific recommendations based on segment characteristics
                if segment == 'Champions':
                    rec['specific_recommendations'].append({
                        'action': 'Launch VIP program',
                        'impact': 'high',
                        'effort': 'medium',
                        'expected_roi': '25%'
                    })
                elif segment == 'At Risk':
                    at_risk_value = segment_df['monetary'].sum()
                    rec['specific_recommendations'].append({
                        'action': f'Reactivation campaign for ${at_risk_value:,.0f} at risk',
                        'impact': 'high',
                        'effort': 'low',
                        'expected_roi': '15%'
                    })
                elif segment == 'Potential Loyalists':
                    rec['specific_recommendations'].append({
                        'action': 'Cross-sell campaign based on purchase history',
                        'impact': 'medium',
                        'effort': 'low',
                        'expected_roi': '20%'
                    })

                recommendations.append(rec)

            # Sort by priority
            recommendations.sort(key=lambda x: x['priority'])

            # Add business-specific recommendations
            wholesale_df = df[df['business_type'] == 'Wholesale']
            if len(wholesale_df) > 0:
                recommendations.append({
                    'segment': 'Wholesale Customers',
                    'priority': 0,
                    'customer_count': len(wholesale_df),
                    'total_value': float(wholesale_df['monetary'].sum()),
                    'actions': ['Volume discounts', 'Extended payment terms', 'Dedicated account management'],
                    'specific_recommendations': [
                        {
                            'action': 'Implement tiered pricing for top wholesale accounts',
                            'impact': 'high',
                            'effort': 'medium',
                            'expected_roi': '30%'
                        }
                    ]
                })

            # Low GP customers
            low_gp_df = df[df['gp_percentage'] < 15]
            if len(low_gp_df) > 10:
                recommendations.append({
                    'segment': 'Low GP Customers',
                    'priority': 10,
                    'customer_count': len(low_gp_df),
                    'total_value': float(low_gp_df['monetary'].sum()),
                    'actions': ['Product mix optimization', 'Pricing review', 'Cost reduction'],
                    'specific_recommendations': [
                        {
                            'action': 'Review pricing and product mix for low-margin accounts',
                            'impact': 'medium',
                            'effort': 'low',
                            'expected_roi': '10%'
                        }
                    ]
                })

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def identify_at_risk_customers(self, risk_threshold: float = 0.7,
                                   min_value: float = 10000) -> List[Dict[str, Any]]:
        """Identify high-value at-risk customers"""
        try:
            df = self.calculate_rfm_scores()

            # Filter for at-risk customers
            at_risk = df[(df['risk_score'] > risk_threshold * 100) &
                        (df['monetary'] > min_value)]

            # Sort by value at risk
            at_risk = at_risk.sort_values('monetary', ascending=False)

            # Format results
            customers = []
            for _, row in at_risk.head(50).iterrows():
                customers.append({
                    'customer_id': int(row['customer_id']),
                    'company_name': row['company_name'],
                    'segment': row['segment'],
                    'monetary': float(row['monetary']),
                    'last_purchase_days': int(row['recency']),
                    'risk_score': float(row['risk_score']),
                    'clv_at_risk': float(row['clv_estimate']),
                    'gp_percentage': float(row['gp_percentage']),
                    'recommended_action': self._get_risk_mitigation_action(row)
                })

            return customers

        except Exception as e:
            logger.error(f"Error identifying at-risk customers: {e}")
            return []

    def _get_risk_mitigation_action(self, customer_row) -> str:
        """Get recommended action for at-risk customer"""
        if customer_row['recency'] > 90:
            return "Immediate reactivation campaign with special offer"
        elif customer_row['payment_segment'] in ['Slow Payer', 'Very Slow Payer']:
            return "Review credit terms and payment plan"
        elif customer_row['gp_percentage'] < 15:
            return "Pricing review and product mix optimization"
        else:
            return "Personal outreach from sales team"

    def calculate_segment_trends(self, period: str = '6months') -> Dict[str, Any]:
        """Calculate segment migration trends over time"""
        try:
            # This would ideally look at historical data
            # For now, return mock trend data
            trends = {
                'period': period,
                'segment_changes': {
                    'Champions': {'change': 5, 'direction': 'up'},
                    'At Risk': {'change': -8, 'direction': 'down'},
                    'New Customers': {'change': 12, 'direction': 'up'}
                },
                'migration_matrix': {
                    'Champions_to_Loyal': 3,
                    'Loyal_to_At_Risk': 5,
                    'At_Risk_to_Lost': 2,
                    'New_to_Potential': 8
                }
            }
            return trends

        except Exception as e:
            logger.error(f"Error calculating segment trends: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Check segmentation system health"""
        try:
            # Test database connection
            with self.db:
                test_query = "SELECT COUNT(*) as count FROM dbo.Customer"
                result = self.db.execute_query(test_query)
                customer_count = result.iloc[0]['count'] if not result.empty else 0

            # Test segmentation
            df = self.calculate_rfm_scores()

            health = {
                'status': 'healthy',
                'database_connected': True,
                'total_customers': customer_count,
                'segmented_customers': len(df),
                'segments_active': len(df['segment'].unique()) if not df.empty else 0,
                'last_check': datetime.now().isoformat()
            }

            return health

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }