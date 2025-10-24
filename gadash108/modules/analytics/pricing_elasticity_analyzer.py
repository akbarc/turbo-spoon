#!/usr/bin/env python3
"""
B2B Wholesale Pricing & Promotion Effectiveness Analyzer
========================================================

Comprehensive pricing analytics for wholesale business including:
- Price elasticity analysis by category
- Optimal pricing for margin maximization  
- Promotion effectiveness evaluation
- Competitive pricing opportunities
- SKU-level pricing power analysis

Author: AI Assistant
Date: 2025-09-08
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
from database_pymssql import SQLServerConnection
from scipy import stats
from scipy.optimize import minimize_scalar
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingElasticityAnalyzer:
    """
    Advanced B2B wholesale pricing elasticity and promotion effectiveness analyzer
    """
    
    def __init__(self, strategic_data_file: str, private_label_file: str):
        """Initialize analyzer with data sources"""
        self.strategic_data_file = strategic_data_file
        self.private_label_file = private_label_file
        self.strategic_data = None
        self.private_label_data = None
        self.db_connection = None
        
        # Analysis results storage
        self.category_elasticity = {}
        self.sku_analysis = {}
        self.promotion_effectiveness = {}
        self.competitive_opportunities = {}
        
        logger.info("🎯 Initializing B2B Wholesale Pricing Elasticity Analyzer")
        
    def load_data(self):
        """Load and prepare data from files"""
        try:
            # Load strategic data
            with open(self.strategic_data_file, 'r') as f:
                self.strategic_data = json.load(f)
            logger.info(f"✅ Loaded strategic data: {len(self.strategic_data)} sections")
            
            # Load private label opportunities
            with open(self.private_label_file, 'r') as f:
                self.private_label_data = json.load(f)
            logger.info(f"✅ Loaded private label data: {len(self.private_label_data['category_scores'])} categories")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading data files: {e}")
            return False
            
    def calculate_price_elasticity_by_category(self) -> Dict:
        """
        Calculate price elasticity of demand by product category
        
        Price Elasticity = % Change in Quantity Demanded / % Change in Price
        """
        logger.info("📊 Calculating price elasticity by category...")
        
        elasticity_results = {}
        
        try:
            # Get gross margin data from strategic file
            gross_margin_data = self.strategic_data.get('gross_margin_by_category', [])
            
            # Get category performance from private label data
            category_scores = self.private_label_data.get('category_scores', [])
            
            for category_data in category_scores:
                category = category_data['category']
                current_metrics = category_data['current_metrics']
                
                # Find matching gross margin data
                matching_margin = None
                for margin_item in gross_margin_data:
                    if margin_item['category'] == category:
                        matching_margin = margin_item
                        break
                
                if matching_margin and current_metrics.get('transactions', 0) > 100:
                    # Calculate elasticity factors
                    avg_price = current_metrics.get('avg_price', 0)
                    units_sold = current_metrics.get('units_sold', 0)
                    margin_pct = current_metrics.get('margin_pct', 0)
                    transactions = current_metrics.get('transactions', 0)
                    
                    # Price sensitivity indicators
                    price_coefficient_of_variation = self._calculate_price_variation(category_data)
                    demand_stability = self._calculate_demand_stability(category_data)
                    
                    # Estimated elasticity based on B2B wholesale patterns
                    # Higher margin categories tend to be less elastic
                    # Higher transaction frequency suggests less elasticity
                    base_elasticity = -0.8  # Typical B2B elasticity
                    
                    # Adjust based on margin (luxury goods more elastic)
                    margin_factor = max(0.5, min(2.0, (30 - margin_pct) / 20))
                    
                    # Adjust based on transaction frequency (necessities less elastic)
                    frequency_factor = max(0.7, min(1.5, 1000 / max(transactions, 100)))
                    
                    # Calculate final elasticity
                    estimated_elasticity = base_elasticity * margin_factor * frequency_factor
                    
                    # Price power calculation (inverse of elasticity magnitude)
                    price_power = 1 / abs(estimated_elasticity) if estimated_elasticity != 0 else 1
                    
                    elasticity_results[category] = {
                        'price_elasticity': round(estimated_elasticity, 3),
                        'price_power_score': round(price_power, 3),
                        'elasticity_category': self._classify_elasticity(estimated_elasticity),
                        'current_avg_price': avg_price,
                        'annual_units': units_sold,
                        'current_margin_pct': margin_pct,
                        'transactions': transactions,
                        'price_variation_coefficient': price_coefficient_of_variation,
                        'demand_stability': demand_stability,
                        'pricing_recommendation': self._get_pricing_recommendation(
                            estimated_elasticity, margin_pct, avg_price
                        )
                    }
                    
            logger.info(f"✅ Calculated elasticity for {len(elasticity_results)} categories")
            return elasticity_results
            
        except Exception as e:
            logger.error(f"❌ Error calculating price elasticity: {e}")
            return {}
    
    def analyze_optimal_pricing_top_skus(self, top_n: int = 20) -> Dict:
        """
        Analyze optimal pricing for top SKUs based on profit maximization
        """
        logger.info(f"🎯 Analyzing optimal pricing for top {top_n} SKUs...")
        
        try:
            # Get product-level data from database
            sku_analysis = {}
            
            with SQLServerConnection() as db:
                # Get top SKUs by revenue using correct table structure
                top_skus_query = f"""
                WITH TopSKUs AS (
                    SELECT TOP {top_n}
                        te.ItemID,
                        i.Description as ItemName,
                        SUM(CAST(te.Quantity AS DECIMAL(18,4))) as total_quantity,
                        SUM(CAST(te.Price * te.Quantity AS DECIMAL(18,4))) as total_revenue,
                        AVG(CAST(te.Price AS DECIMAL(18,4))) as avg_selling_price,
                        AVG(CAST(te.Cost AS DECIMAL(18,4))) as avg_cost,
                        COUNT(DISTINCT t.Time) as active_days,
                        COUNT(*) as transaction_count
                    FROM TransactionEntry te
                    INNER JOIN Transaction t ON te.TransactionNumber = t.TransactionNumber
                    INNER JOIN Item i ON te.ItemID = i.ID
                    WHERE t.Time >= DATEADD(month, -12, GETDATE())
                        AND CAST(te.Quantity AS DECIMAL(18,4)) > 0
                        AND CAST(te.Price AS DECIMAL(18,4)) > 0
                        AND t.TransactionType = 1
                    GROUP BY te.ItemID, i.Description
                    HAVING SUM(CAST(te.Price * te.Quantity AS DECIMAL(18,4))) > 1000
                    ORDER BY total_revenue DESC
                )
                SELECT * FROM TopSKUs
                """
                
                top_skus_df = db.execute_query(
                    top_skus_query, 
                    description=f"Top {top_n} SKUs Analysis"
                )
                
                if not top_skus_df.empty:
                    for _, sku in top_skus_df.iterrows():
                        # Get price history for elasticity calculation
                        price_history = self._get_sku_price_history(db, sku['ItemID'])
                        
                        if len(price_history) > 5:  # Need enough data points
                            # Calculate elasticity and optimal price
                            elasticity = self._calculate_sku_elasticity(price_history)
                            current_margin = ((sku['avg_selling_price'] - sku['avg_cost']) / 
                                            sku['avg_selling_price']) * 100
                            
                            # Optimal pricing calculation
                            optimal_price = self._calculate_optimal_price(
                                sku['avg_cost'], elasticity, sku['avg_selling_price']
                            )
                            
                            # Revenue impact projection
                            revenue_impact = self._project_revenue_impact(
                                sku['total_revenue'], sku['avg_selling_price'], 
                                optimal_price, elasticity
                            )
                            
                            sku_analysis[sku['ItemID']] = {
                                'item_name': sku['ItemName'],
                                'current_price': float(sku['avg_selling_price']),
                                'current_cost': float(sku['avg_cost']),
                                'current_margin_pct': round(current_margin, 2),
                                'optimal_price': round(optimal_price, 2),
                                'optimal_margin_pct': round(((optimal_price - sku['avg_cost']) / 
                                                          optimal_price) * 100, 2),
                                'price_elasticity': round(elasticity, 3),
                                'annual_revenue': float(sku['total_revenue']),
                                'annual_quantity': float(sku['total_quantity']),
                                'revenue_impact': revenue_impact,
                                'pricing_power': 'High' if abs(elasticity) < 0.5 else 
                                               'Medium' if abs(elasticity) < 1.0 else 'Low',
                                'recommendation': self._get_sku_recommendation(
                                    sku['avg_selling_price'], optimal_price, elasticity, current_margin
                                )
                            }
                            
            logger.info(f"✅ Analyzed {len(sku_analysis)} top SKUs")
            return sku_analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing optimal pricing: {e}")
            return {}
    
    def analyze_promotion_effectiveness(self) -> Dict:
        """
        Analyze promotion effectiveness and ROI by type
        """
        logger.info("🎯 Analyzing promotion effectiveness...")
        
        try:
            promotion_analysis = {}
            
            with SQLServerConnection() as db:
                # Analyze different promotion patterns using correct table structure
                promotion_query = """
                WITH PromotionAnalysis AS (
                    SELECT 
                        te.ItemID,
                        i.Description as ItemName,
                        t.Time as SaleDate,
                        CAST(te.Price AS DECIMAL(18,4)) as selling_price,
                        CAST(te.Cost AS DECIMAL(18,4)) as cost,
                        CAST(te.Quantity AS DECIMAL(18,4)) as quantity,
                        CAST(te.Price * te.Quantity AS DECIMAL(18,4)) as line_total,
                        -- Identify potential promotions (below average price)
                        CASE 
                            WHEN CAST(te.Price AS DECIMAL(18,4)) < 
                                 AVG(CAST(te.Price AS DECIMAL(18,4))) OVER (PARTITION BY te.ItemID) * 0.9
                            THEN 'Discount'
                            WHEN CAST(te.Quantity AS DECIMAL(18,4)) > 
                                 AVG(CAST(te.Quantity AS DECIMAL(18,4))) OVER (PARTITION BY te.ItemID) * 2
                            THEN 'Volume'
                            ELSE 'Regular'
                        END as promotion_type
                    FROM TransactionEntry te
                    INNER JOIN Transaction t ON te.TransactionNumber = t.TransactionNumber
                    INNER JOIN Item i ON te.ItemID = i.ID
                    WHERE t.Time >= DATEADD(month, -12, GETDATE())
                        AND CAST(te.Quantity AS DECIMAL(18,4)) > 0
                        AND CAST(te.Price AS DECIMAL(18,4)) > 0
                        AND t.TransactionType = 1
                )
                SELECT 
                    promotion_type,
                    COUNT(*) as transaction_count,
                    AVG(selling_price) as avg_price,
                    AVG(quantity) as avg_quantity,
                    SUM(line_total) as total_revenue,
                    AVG((selling_price - cost) / selling_price * 100) as avg_margin_pct,
                    COUNT(DISTINCT ItemID) as unique_products
                FROM PromotionAnalysis
                GROUP BY promotion_type
                """
                
                promotion_df = db.execute_query(
                    promotion_query, 
                    description="Promotion Effectiveness Analysis"
                )
                
                if not promotion_df.empty:
                    for _, promo in promotion_df.iterrows():
                        promo_type = promo['promotion_type']
                        
                        # Calculate effectiveness metrics
                        revenue_per_transaction = promo['total_revenue'] / promo['transaction_count']
                        margin_impact = promo['avg_margin_pct']
                        
                        # ROI calculation (simplified)
                        # Assume promotion cost is 2% of revenue for discounts, 1% for volume
                        promotion_cost_pct = 2.0 if promo_type == 'Discount' else 1.0
                        promotion_cost = promo['total_revenue'] * (promotion_cost_pct / 100)
                        net_profit = (promo['total_revenue'] * margin_impact / 100) - promotion_cost
                        roi = (net_profit / promotion_cost) * 100 if promotion_cost > 0 else 0
                        
                        promotion_analysis[promo_type] = {
                            'transaction_count': int(promo['transaction_count']),
                            'avg_price': round(float(promo['avg_price']), 2),
                            'avg_quantity': round(float(promo['avg_quantity']), 2),
                            'total_revenue': round(float(promo['total_revenue']), 2),
                            'avg_margin_pct': round(float(promo['avg_margin_pct']), 2),
                            'unique_products': int(promo['unique_products']),
                            'revenue_per_transaction': round(revenue_per_transaction, 2),
                            'estimated_promotion_cost': round(promotion_cost, 2),
                            'estimated_roi_pct': round(roi, 2),
                            'effectiveness_score': self._calculate_promotion_score(
                                roi, revenue_per_transaction, promo['avg_margin_pct']
                            ),
                            'recommendation': self._get_promotion_recommendation(roi, margin_impact)
                        }
                        
            logger.info(f"✅ Analyzed {len(promotion_analysis)} promotion types")
            return promotion_analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing promotions: {e}")
            return {}
    
    def identify_competitive_pricing_opportunities(self) -> Dict:
        """
        Identify competitive pricing opportunities based on market positioning
        """
        logger.info("🎯 Identifying competitive pricing opportunities...")
        
        opportunities = {}
        
        try:
            # Use private label data as proxy for competitive opportunities
            category_scores = self.private_label_data.get('category_scores', [])
            
            for category_data in category_scores:
                category = category_data['category']
                current_metrics = category_data['current_metrics']
                opportunity_metrics = category_data.get('opportunity_metrics', {})
                
                if current_metrics.get('revenue', 0) > 10000:  # Focus on significant categories
                    current_price = current_metrics.get('avg_price', 0)
                    target_price = opportunity_metrics.get('target_price_point', current_price)
                    margin_headroom = category_data.get('score_components', {}).get('margin_headroom', 0)
                    
                    # Competitive opportunity score
                    price_gap_pct = ((current_price - target_price) / current_price * 100) if current_price > 0 else 0
                    
                    # Market share potential
                    market_potential = self._estimate_market_potential(category_data)
                    
                    opportunities[category] = {
                        'current_avg_price': round(current_price, 2),
                        'competitive_price_point': round(target_price, 2),
                        'price_reduction_opportunity_pct': round(price_gap_pct, 2),
                        'margin_headroom_score': round(margin_headroom, 2),
                        'current_margin_pct': current_metrics.get('margin_pct', 0),
                        'target_margin_pct': opportunity_metrics.get('target_margin_pct', 0),
                        'annual_revenue': round(current_metrics.get('revenue', 0), 2),
                        'market_potential_score': market_potential,
                        'competitive_advantage': self._assess_competitive_advantage(
                            price_gap_pct, margin_headroom, current_metrics
                        ),
                        'implementation_priority': self._calculate_implementation_priority(
                            current_metrics.get('revenue', 0), 
                            price_gap_pct, 
                            margin_headroom,
                            opportunity_metrics.get('estimated_break_even_months', 12)
                        ),
                        'revenue_impact_projection': self._project_competitive_revenue_impact(
                            current_metrics, price_gap_pct, market_potential
                        )
                    }
                    
            logger.info(f"✅ Identified opportunities for {len(opportunities)} categories")
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error identifying competitive opportunities: {e}")
            return {}
    
    def generate_comprehensive_report(self) -> Dict:
        """
        Generate comprehensive pricing analysis report
        """
        logger.info("📋 Generating comprehensive pricing analysis report...")
        
        # Run all analyses
        elasticity_data = self.calculate_price_elasticity_by_category()
        sku_data = self.analyze_optimal_pricing_top_skus(20)
        promotion_data = self.analyze_promotion_effectiveness() 
        competitive_data = self.identify_competitive_pricing_opportunities()
        
        # Create summary metrics
        summary_metrics = self._generate_summary_metrics(
            elasticity_data, sku_data, promotion_data, competitive_data
        )
        
        # Compile final report
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_type': 'B2B Wholesale Pricing Elasticity & Promotion Effectiveness',
            'data_sources': {
                'strategic_data': self.strategic_data_file,
                'private_label_data': self.private_label_file,
                'database_queries': 'Real-time SQL Server queries'
            },
            'summary_metrics': summary_metrics,
            'price_elasticity_by_category': elasticity_data,
            'optimal_pricing_top_skus': sku_data,
            'promotion_effectiveness': promotion_data,
            'competitive_pricing_opportunities': competitive_data,
            'strategic_recommendations': self._generate_strategic_recommendations(
                elasticity_data, sku_data, promotion_data, competitive_data
            )
        }
        
        logger.info("✅ Comprehensive report generated successfully")
        return report
    
    # Helper methods
    
    def _calculate_price_variation(self, category_data: Dict) -> float:
        """Calculate price variation coefficient for category"""
        return category_data.get('score_components', {}).get('price_dispersion', 0) / 100
    
    def _calculate_demand_stability(self, category_data: Dict) -> float:
        """Calculate demand stability score"""
        return category_data.get('score_components', {}).get('velocity_consistency', 0) / 100
    
    def _classify_elasticity(self, elasticity: float) -> str:
        """Classify elasticity into categories"""
        abs_elasticity = abs(elasticity)
        if abs_elasticity < 0.5:
            return 'Inelastic (Price Power)'
        elif abs_elasticity < 1.0:
            return 'Unit Elastic'
        else:
            return 'Elastic (Price Sensitive)'
    
    def _get_pricing_recommendation(self, elasticity: float, margin_pct: float, current_price: float) -> str:
        """Generate pricing recommendation based on elasticity"""
        if abs(elasticity) < 0.5 and margin_pct < 25:
            return f"INCREASE PRICE: Low elasticity suggests {5-10}% price increase possible"
        elif abs(elasticity) > 1.5 and margin_pct > 30:
            return f"DECREASE PRICE: High elasticity suggests {5-15}% price reduction for volume gain"
        else:
            return "MAINTAIN PRICE: Current pricing appears optimal"
    
    def _get_sku_price_history(self, db, item_id: int) -> pd.DataFrame:
        """Get price history for specific SKU"""
        query = f"""
        SELECT 
            t.Time as SaleDate,
            CAST(te.Price AS DECIMAL(18,4)) as price,
            SUM(CAST(te.Quantity AS DECIMAL(18,4))) as quantity
        FROM TransactionEntry te
        INNER JOIN Transaction t ON te.TransactionNumber = t.TransactionNumber
        WHERE te.ItemID = {item_id}
            AND t.Time >= DATEADD(month, -12, GETDATE())
            AND CAST(te.Quantity AS DECIMAL(18,4)) > 0
            AND t.TransactionType = 1
        GROUP BY t.Time, CAST(te.Price AS DECIMAL(18,4))
        ORDER BY t.Time
        """
        return db.execute_query(query, description=f"Price history for ItemID {item_id}")
    
    def _calculate_sku_elasticity(self, price_history: pd.DataFrame) -> float:
        """Calculate price elasticity for specific SKU"""
        if len(price_history) < 3:
            return -1.0  # Default moderate elasticity
            
        try:
            # Calculate price and quantity changes
            price_changes = price_history['price'].pct_change().dropna()
            qty_changes = price_history['quantity'].pct_change().dropna()
            
            if len(price_changes) > 1 and price_changes.std() > 0:
                # Simple correlation-based elasticity
                correlation = np.corrcoef(price_changes, qty_changes)[0, 1]
                if not np.isnan(correlation):
                    return correlation * -2  # Convert to elasticity estimate
                    
        except Exception:
            pass
            
        return -1.0  # Default if calculation fails
    
    def _calculate_optimal_price(self, cost: float, elasticity: float, current_price: float) -> float:
        """Calculate profit-maximizing price"""
        if elasticity >= 0 or elasticity == -1:
            return current_price  # No change if elasticity is problematic
            
        try:
            # Theoretical optimal markup: 1 / (1 + elasticity)
            optimal_markup = 1 / (1 + elasticity)
            optimal_price = cost / (1 - optimal_markup)
            
            # Constrain to reasonable bounds
            max_increase = current_price * 1.3  # Max 30% increase
            min_decrease = current_price * 0.7   # Max 30% decrease
            
            return max(min_decrease, min(max_increase, optimal_price))
            
        except (ZeroDivisionError, OverflowError):
            return current_price
    
    def _project_revenue_impact(self, current_revenue: float, current_price: float, 
                               new_price: float, elasticity: float) -> Dict:
        """Project revenue impact of price change"""
        price_change_pct = ((new_price - current_price) / current_price) if current_price > 0 else 0
        quantity_change_pct = elasticity * price_change_pct
        
        new_revenue = current_revenue * (1 + price_change_pct) * (1 + quantity_change_pct)
        revenue_change = new_revenue - current_revenue
        
        return {
            'price_change_pct': round(price_change_pct * 100, 2),
            'quantity_change_pct': round(quantity_change_pct * 100, 2),
            'revenue_change': round(revenue_change, 2),
            'revenue_change_pct': round((revenue_change / current_revenue * 100), 2) if current_revenue > 0 else 0,
            'projected_annual_revenue': round(new_revenue, 2)
        }
    
    def _get_sku_recommendation(self, current_price: float, optimal_price: float, 
                               elasticity: float, margin: float) -> str:
        """Generate SKU-specific recommendation"""
        price_diff_pct = ((optimal_price - current_price) / current_price * 100) if current_price > 0 else 0
        
        if abs(price_diff_pct) < 2:
            return "Current pricing is optimal"
        elif price_diff_pct > 2:
            return f"Consider {price_diff_pct:.1f}% price increase to maximize profit"
        else:
            return f"Consider {abs(price_diff_pct):.1f}% price reduction to increase volume"
    
    def _calculate_promotion_score(self, roi: float, revenue_per_transaction: float, margin: float) -> float:
        """Calculate promotion effectiveness score"""
        roi_score = min(100, max(0, roi)) / 100 * 40  # Max 40 points for ROI
        revenue_score = min(40, revenue_per_transaction / 100)  # Max 40 points for revenue
        margin_score = min(20, margin)  # Max 20 points for margin
        
        return round(roi_score + revenue_score + margin_score, 1)
    
    def _get_promotion_recommendation(self, roi: float, margin: float) -> str:
        """Generate promotion recommendation"""
        if roi > 50 and margin > 20:
            return "Highly Effective: Expand this promotion type"
        elif roi > 20:
            return "Moderately Effective: Continue with optimization"
        elif roi > 0:
            return "Marginally Effective: Consider refinements"
        else:
            return "Ineffective: Discontinue or completely redesign"
    
    def _estimate_market_potential(self, category_data: Dict) -> float:
        """Estimate market potential score"""
        velocity = category_data.get('score_components', {}).get('velocity_consistency', 0)
        repeat_purchase = category_data.get('score_components', {}).get('repeat_purchase', 0)
        transactions = category_data.get('current_metrics', {}).get('transactions', 0)
        
        # Composite score
        return round((velocity + repeat_purchase) / 2 * min(1.0, transactions / 1000), 2)
    
    def _assess_competitive_advantage(self, price_gap: float, margin_headroom: float, metrics: Dict) -> str:
        """Assess competitive advantage level"""
        if price_gap > 15 and margin_headroom > 50:
            return "Strong: Significant pricing power and margin flexibility"
        elif price_gap > 10 or margin_headroom > 30:
            return "Moderate: Good positioning with some flexibility"
        else:
            return "Limited: Constrained pricing flexibility"
    
    def _calculate_implementation_priority(self, revenue: float, price_gap: float, 
                                         margin_headroom: float, break_even_months: int) -> str:
        """Calculate implementation priority"""
        revenue_score = min(100, revenue / 10000)  # Higher revenue = higher priority
        price_score = min(100, price_gap * 2)      # Larger gaps = higher priority
        margin_score = min(100, margin_headroom)   # More headroom = higher priority
        time_score = max(0, 100 - break_even_months * 10)  # Faster payback = higher priority
        
        total_score = (revenue_score + price_score + margin_score + time_score) / 4
        
        if total_score > 70:
            return "High"
        elif total_score > 40:
            return "Medium" 
        else:
            return "Low"
    
    def _project_competitive_revenue_impact(self, metrics: Dict, price_gap: float, 
                                          market_potential: float) -> Dict:
        """Project revenue impact of competitive pricing"""
        current_revenue = metrics.get('revenue', 0)
        
        # Assume price reduction leads to volume increase
        volume_multiplier = 1 + (price_gap / 100 * market_potential / 100)
        price_multiplier = 1 - (price_gap / 100)
        
        projected_revenue = current_revenue * volume_multiplier * price_multiplier
        
        return {
            'current_annual_revenue': round(current_revenue, 2),
            'projected_annual_revenue': round(projected_revenue, 2),
            'revenue_change': round(projected_revenue - current_revenue, 2),
            'revenue_change_pct': round(((projected_revenue - current_revenue) / current_revenue * 100), 2) if current_revenue > 0 else 0
        }
    
    def _generate_summary_metrics(self, elasticity_data: Dict, sku_data: Dict, 
                                 promotion_data: Dict, competitive_data: Dict) -> Dict:
        """Generate summary metrics across all analyses"""
        
        # Elasticity summary
        elastic_categories = len([cat for cat, data in elasticity_data.items() 
                                if data.get('price_power_score', 0) < 1])
        inelastic_categories = len(elasticity_data) - elastic_categories
        
        # SKU summary
        sku_price_increases = len([sku for sku, data in sku_data.items() 
                                 if data.get('optimal_price', 0) > data.get('current_price', 0)])
        total_sku_revenue_impact = sum([data.get('revenue_impact', {}).get('revenue_change', 0) 
                                      for data in sku_data.values()])
        
        # Promotion summary
        best_promotion = max(promotion_data.items(), 
                           key=lambda x: x[1].get('estimated_roi_pct', 0))[0] if promotion_data else 'None'
        
        # Competitive summary  
        high_priority_opportunities = len([cat for cat, data in competitive_data.items() 
                                         if data.get('implementation_priority') == 'High'])
        
        return {
            'categories_analyzed': len(elasticity_data),
            'elastic_categories': elastic_categories,
            'inelastic_categories': inelastic_categories,
            'top_skus_analyzed': len(sku_data),
            'skus_with_price_increase_opportunity': sku_price_increases,
            'total_sku_revenue_impact': round(total_sku_revenue_impact, 2),
            'promotion_types_analyzed': len(promotion_data),
            'best_performing_promotion_type': best_promotion,
            'competitive_opportunities': len(competitive_data),
            'high_priority_competitive_opportunities': high_priority_opportunities,
            'analysis_confidence': 'High' if len(elasticity_data) > 10 else 'Medium'
        }
    
    def _generate_strategic_recommendations(self, elasticity_data: Dict, sku_data: Dict, 
                                          promotion_data: Dict, competitive_data: Dict) -> List[str]:
        """Generate strategic recommendations"""
        recommendations = []
        
        # Price elasticity recommendations
        high_power_categories = [cat for cat, data in elasticity_data.items() 
                               if data.get('price_power_score', 0) > 1.5]
        if high_power_categories:
            recommendations.append(
                f"PRICING POWER: Categories with pricing power ({', '.join(high_power_categories[:3])}) "
                f"can support 5-15% price increases with minimal volume loss."
            )
        
        # SKU-specific recommendations
        if sku_data:
            high_impact_skus = [sku for sku, data in sku_data.items() 
                              if data.get('revenue_impact', {}).get('revenue_change', 0) > 5000]
            if high_impact_skus:
                recommendations.append(
                    f"HIGH-IMPACT SKUS: {len(high_impact_skus)} SKUs show significant profit optimization "
                    f"potential with projected revenue impact > $5,000 annually."
                )
        
        # Promotion recommendations
        if promotion_data:
            best_promo = max(promotion_data.items(), key=lambda x: x[1].get('estimated_roi_pct', 0))
            if best_promo[1].get('estimated_roi_pct', 0) > 25:
                recommendations.append(
                    f"PROMOTION FOCUS: '{best_promo[0]}' promotions show {best_promo[1]['estimated_roi_pct']:.1f}% ROI. "
                    f"Consider expanding this promotion type."
                )
        
        # Competitive recommendations
        high_priority = [cat for cat, data in competitive_data.items() 
                        if data.get('implementation_priority') == 'High']
        if high_priority:
            recommendations.append(
                f"COMPETITIVE OPPORTUNITIES: {len(high_priority)} high-priority categories "
                f"({', '.join(high_priority[:2])}) offer immediate competitive pricing advantages."
            )
        
        # General B2B recommendations
        recommendations.extend([
            "DYNAMIC PRICING: Implement category-specific pricing strategies based on elasticity analysis.",
            "MARGIN OPTIMIZATION: Focus on categories with pricing power for margin expansion.",
            "VOLUME STRATEGIES: Use competitive pricing in price-sensitive categories to gain market share.",
            "PROMOTION EFFICIENCY: Optimize promotion spend based on ROI analysis by type."
        ])
        
        return recommendations
    
    def save_results(self, filename: str = None):
        """Save analysis results to JSON file"""
        if not filename:
            filename = f"pricing_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            report = self.generate_comprehensive_report()
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"✅ Results saved to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
            return None


def main():
    """Main execution function"""
    logger.info("🚀 Starting B2B Wholesale Pricing Elasticity Analysis")
    
    # Initialize analyzer
    analyzer = PricingElasticityAnalyzer(
        strategic_data_file="strategic_data_extraction_20250908_164747.json",
        private_label_file="private_label_opportunities.json"
    )
    
    # Load data
    if not analyzer.load_data():
        logger.error("❌ Failed to load required data files")
        return
    
    # Run analysis and save results
    results_file = analyzer.save_results("pricing_analysis_results.json")
    
    if results_file:
        logger.info(f"🎯 Analysis complete! Results saved to: {results_file}")
        
        # Print key findings
        report = analyzer.generate_comprehensive_report()
        summary = report['summary_metrics']
        
        print("\n" + "="*60)
        print("📊 B2B WHOLESALE PRICING ANALYSIS SUMMARY")
        print("="*60)
        print(f"Categories Analyzed: {summary['categories_analyzed']}")
        print(f"Price-Inelastic Categories: {summary['inelastic_categories']}")
        print(f"Top SKUs Analyzed: {summary['top_skus_analyzed']}")
        print(f"SKUs with Price Increase Opportunity: {summary['skus_with_price_increase_opportunity']}")
        print(f"Total Revenue Impact Potential: ${summary['total_sku_revenue_impact']:,.2f}")
        print(f"Best Promotion Type: {summary['best_performing_promotion_type']}")
        print(f"High-Priority Competitive Opportunities: {summary['high_priority_competitive_opportunities']}")
        
        print(f"\n📋 Key Strategic Recommendations:")
        for i, rec in enumerate(report['strategic_recommendations'][:5], 1):
            print(f"{i}. {rec}")
        
        print("="*60)
    else:
        logger.error("❌ Analysis failed")


if __name__ == "__main__":
    main()