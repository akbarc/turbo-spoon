#!/usr/bin/env python3
"""
Private Label Opportunity Scorer
Analyzes product categories and individual products for private label opportunities
Focuses on non-tobacco categories for regulatory compliance
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any
import os


class PrivateLabelOpportunityScorer:
    """
    Analyzes private label opportunities based on multiple scoring factors:
    - Price dispersion within category
    - Margin headroom (current vs potential) 
    - Sales velocity and consistency
    - Supplier concentration risk
    - Repeat purchase patterns
    """
    
    def __init__(self, data_file_path: str):
        """Initialize with strategic data extraction file"""
        self.data_file_path = data_file_path
        self.data = self._load_data()
        
        # Private label target parameters
        self.target_discount_pct = 0.15  # 10-20% below branded average
        self.target_margin_min = 35.0    # Target 35-45% GP
        self.target_margin_max = 45.0
        self.min_annual_volume = 1000    # Minimum units for break-even
        
        # Category exclusions for regulatory compliance
        self.tobacco_categories = {
            'CIGARETTE', 'CIGARS', 'CIGAR GA', 'ELECTRONIC CIG', 'ECIG - PODS',
            'T7 SMOKELESS GA', 'NICOTINE POUCHES', 'CIG ROLLING PAPER', 'BLUNT WRAP',
            'KRATOM', 'CBD/HEMP'
        }
        
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'category_scores': [],
            'top_opportunities': [],
            'first_five_skus': [],
            'exclusions': {
                'tobacco_categories': list(self.tobacco_categories),
                'reason': 'Regulatory compliance - focusing on non-tobacco first'
            }
        }
    
    def _load_data(self) -> dict:
        """Load and parse strategic data extraction JSON"""
        try:
            with open(self.data_file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Could not load data file {self.data_file_path}: {e}")
    
    def calculate_price_dispersion_score(self, category_data: dict, products: list) -> float:
        """
        Calculate price dispersion score (0-100)
        Higher dispersion = more opportunity for private label positioning
        """
        if not products:
            return 0.0
        
        prices = []
        for product in products:
            if product.get('category') == category_data.get('category'):
                avg_price = float(product.get('avg_selling_price', 0))
                max_price = float(product.get('max_price', avg_price))
                min_price = float(product.get('min_price', avg_price))
                prices.extend([avg_price, max_price, min_price])
        
        if len(prices) < 2:
            return 0.0
        
        # Calculate coefficient of variation (CV)
        prices = [p for p in prices if p > 0]
        if not prices:
            return 0.0
        
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        
        if mean_price == 0:
            return 0.0
        
        cv = std_price / mean_price
        # Normalize CV to 0-100 scale (CV > 0.3 is considered high dispersion)
        return min(100.0, (cv / 0.3) * 100.0)
    
    def calculate_margin_headroom_score(self, category_data: dict) -> float:
        """
        Calculate margin headroom score (0-100)
        Lower current margins = more opportunity for private label margins
        """
        current_margin = float(category_data.get('gross_margin_pct', 0))
        
        if current_margin >= self.target_margin_min:
            # Already at target, less opportunity
            return max(0.0, 50.0 - current_margin)
        
        # Calculate potential improvement
        max_improvement = self.target_margin_max - current_margin
        # Normalize to 0-100 scale
        return min(100.0, (max_improvement / self.target_margin_max) * 100.0)
    
    def calculate_velocity_consistency_score(self, category_data: dict, monthly_data: list) -> float:
        """
        Calculate sales velocity and consistency score (0-100)
        Higher, more consistent sales = better private label opportunity
        """
        # Get monthly sales data for this category
        category_monthly = [
            item for item in monthly_data 
            if item.get('category') == category_data.get('category')
        ]
        
        if not category_monthly:
            return 0.0
        
        # Calculate velocity (average monthly revenue)
        revenues = [float(item.get('total_revenue', 0)) for item in category_monthly]
        avg_monthly_revenue = np.mean(revenues) if revenues else 0
        
        # Calculate consistency (inverse of coefficient of variation)
        if len(revenues) > 1:
            consistency = 1 - (np.std(revenues) / avg_monthly_revenue if avg_monthly_revenue > 0 else 1)
            consistency = max(0, min(1, consistency))
        else:
            consistency = 0.5
        
        # Velocity score based on monthly revenue (normalize to typical range)
        velocity_score = min(100.0, (avg_monthly_revenue / 50000.0) * 100.0)
        
        # Consistency score
        consistency_score = consistency * 100.0
        
        # Weighted combination (70% velocity, 30% consistency)
        return (velocity_score * 0.7) + (consistency_score * 0.3)
    
    def calculate_supplier_concentration_score(self, category_data: dict, products: list) -> float:
        """
        Calculate supplier concentration score (0-100)
        More suppliers = less risk, better opportunity for private label
        """
        category_products = [
            p for p in products 
            if p.get('category') == category_data.get('category')
        ]
        
        if not category_products:
            return 0.0
        
        # Use unique product count as proxy for supplier diversity
        unique_products = len(category_products)
        
        # Normalize based on typical product ranges
        if unique_products >= 50:
            return 100.0  # High diversity
        elif unique_products >= 20:
            return 75.0   # Good diversity
        elif unique_products >= 10:
            return 50.0   # Moderate diversity
        elif unique_products >= 5:
            return 25.0   # Limited diversity
        else:
            return 10.0   # Very limited diversity
    
    def calculate_repeat_purchase_score(self, category_data: dict) -> float:
        """
        Calculate repeat purchase pattern score (0-100)
        Higher repeat purchases = better private label opportunity
        """
        transactions = int(category_data.get('transactions', 0))
        total_units = float(category_data.get('total_units_sold', 0))
        unique_products = int(category_data.get('unique_products', 1))
        
        if transactions == 0 or unique_products == 0:
            return 0.0
        
        # Calculate average units per transaction
        avg_units_per_transaction = total_units / transactions
        
        # Calculate products per transaction (diversity indicator)
        avg_products_per_transaction = unique_products / transactions
        
        # Higher units per transaction suggests repeat purchases
        repeat_score = min(100.0, (avg_units_per_transaction / 10.0) * 100.0)
        
        return repeat_score
    
    def calculate_category_opportunity_score(self, category_data: dict, monthly_data: list, products: list) -> dict:
        """Calculate overall opportunity score for a category"""
        
        category_name = category_data.get('category', 'Unknown')
        
        # Skip tobacco categories
        if category_name in self.tobacco_categories:
            return None
        
        # Calculate individual scores
        price_dispersion = self.calculate_price_dispersion_score(category_data, products)
        margin_headroom = self.calculate_margin_headroom_score(category_data)
        velocity_consistency = self.calculate_velocity_consistency_score(category_data, monthly_data)
        supplier_concentration = self.calculate_supplier_concentration_score(category_data, products)
        repeat_purchase = self.calculate_repeat_purchase_score(category_data)
        
        # Weighted scoring (adjust weights based on business priorities)
        weights = {
            'margin_headroom': 0.30,      # Most important
            'velocity_consistency': 0.25,  # High importance
            'price_dispersion': 0.20,     # Good opportunity indicator
            'supplier_concentration': 0.15, # Risk factor
            'repeat_purchase': 0.10       # Market validation
        }
        
        overall_score = (
            margin_headroom * weights['margin_headroom'] +
            velocity_consistency * weights['velocity_consistency'] +
            price_dispersion * weights['price_dispersion'] +
            supplier_concentration * weights['supplier_concentration'] +
            repeat_purchase * weights['repeat_purchase']
        )
        
        # Calculate target pricing and margins
        current_avg_price = self._calculate_category_average_price(category_data, products)
        target_price = current_avg_price * (1 - self.target_discount_pct)
        current_margin = float(category_data.get('gross_margin_pct', 0))
        potential_margin = min(self.target_margin_max, current_margin + 20)  # Conservative estimate
        
        return {
            'category': category_name,
            'overall_score': round(overall_score, 2),
            'score_components': {
                'price_dispersion': round(price_dispersion, 2),
                'margin_headroom': round(margin_headroom, 2),
                'velocity_consistency': round(velocity_consistency, 2),
                'supplier_concentration': round(supplier_concentration, 2),
                'repeat_purchase': round(repeat_purchase, 2)
            },
            'current_metrics': {
                'revenue': float(category_data.get('total_revenue', 0)),
                'margin_pct': float(category_data.get('gross_margin_pct', 0)),
                'transactions': int(category_data.get('transactions', 0)),
                'units_sold': float(category_data.get('total_units_sold', 0)),
                'unique_products': int(category_data.get('unique_products', 0)),
                'avg_price': round(current_avg_price, 2)
            },
            'opportunity_metrics': {
                'target_price_point': round(target_price, 2),
                'target_margin_pct': round(potential_margin, 2),
                'volume_requirement_annual': self.min_annual_volume,
                'estimated_break_even_months': self._estimate_break_even_months(category_data)
            }
        }
    
    def _calculate_category_average_price(self, category_data: dict, products: list) -> float:
        """Calculate average selling price for category"""
        if 'avg_item_price' in category_data:
            return float(category_data.get('avg_item_price', 0))
        
        # Fallback calculation from products
        category_products = [
            p for p in products 
            if p.get('category') == category_data.get('category')
        ]
        
        if not category_products:
            return 0.0
        
        prices = [float(p.get('avg_selling_price', 0)) for p in category_products]
        return np.mean(prices) if prices else 0.0
    
    def _estimate_break_even_months(self, category_data: dict) -> int:
        """Estimate months to break-even based on current sales velocity"""
        monthly_units = float(category_data.get('total_units_sold', 0)) / 12  # Assuming annual data
        
        if monthly_units == 0:
            return 12  # Conservative estimate
        
        months_needed = self.min_annual_volume / monthly_units
        return max(1, min(24, int(months_needed)))  # Cap between 1-24 months
    
    def identify_top_opportunities(self, category_scores: list, n_top: int = 10) -> list:
        """Identify top N categories for private label opportunities"""
        
        # Filter valid scores and sort by overall score
        valid_scores = [score for score in category_scores if score is not None]
        sorted_scores = sorted(valid_scores, key=lambda x: x['overall_score'], reverse=True)
        
        return sorted_scores[:n_top]
    
    def select_first_five_skus(self, top_opportunities: list, products: list) -> list:
        """Select the first 5 SKUs to launch based on top opportunities"""
        
        selected_skus = []
        
        for opportunity in top_opportunities:
            if len(selected_skus) >= 5:
                break
                
            category = opportunity['category']
            
            # Find products in this category
            category_products = [
                p for p in products 
                if p.get('category') == category
            ]
            
            # Sort by revenue and select top product
            if category_products:
                top_product = max(category_products, key=lambda x: float(x.get('total_revenue', 0)))
                
                current_price = float(top_product.get('avg_selling_price', 0))
                target_price = current_price * (1 - self.target_discount_pct)
                
                selected_skus.append({
                    'rank': len(selected_skus) + 1,
                    'category': category,
                    'reference_product_name': top_product.get('product_name', 'Unknown'),
                    'reference_product_id': top_product.get('product_id'),
                    'reference_upc': top_product.get('lookup_code'),
                    'current_market_price': round(current_price, 2),
                    'proposed_private_label_price': round(target_price, 2),
                    'price_advantage_pct': round(self.target_discount_pct * 100, 1),
                    'category_opportunity_score': opportunity['overall_score'],
                    'annual_revenue_potential': round(float(top_product.get('total_revenue', 0)), 2),
                    'units_sold_reference': int(top_product.get('total_units_sold', 0))
                })
        
        return selected_skus
    
    def run_analysis(self) -> dict:
        """Run complete private label opportunity analysis"""
        
        print("🔍 Starting Private Label Opportunity Analysis...")
        
        # Extract data sections
        margin_data = self.data.get('gross_margin_by_category', [])
        monthly_data = self.data.get('monthly_revenue_by_category', [])
        products_data = self.data.get('top_products_by_revenue', [])
        
        print(f"📊 Analyzing {len(margin_data)} categories, {len(products_data)} products")
        
        # Calculate scores for each category
        category_scores = []
        for category in margin_data:
            score = self.calculate_category_opportunity_score(category, monthly_data, products_data)
            if score:  # Only include non-tobacco categories
                category_scores.append(score)
        
        print(f"✅ Scored {len(category_scores)} eligible categories (excluded tobacco)")
        
        # Identify top opportunities
        top_opportunities = self.identify_top_opportunities(category_scores, n_top=10)
        
        print(f"🎯 Identified top {len(top_opportunities)} opportunities")
        
        # Select first 5 SKUs
        first_five_skus = self.select_first_five_skus(top_opportunities, products_data)
        
        print(f"🚀 Selected {len(first_five_skus)} SKUs for initial launch")
        
        # Compile results
        self.results.update({
            'category_scores': category_scores,
            'top_opportunities': top_opportunities,
            'first_five_skus': first_five_skus,
            'summary_stats': {
                'total_categories_analyzed': len(category_scores),
                'categories_excluded': len(margin_data) - len(category_scores),
                'avg_opportunity_score': round(np.mean([c['overall_score'] for c in category_scores]), 2) if category_scores else 0,
                'top_score': max([c['overall_score'] for c in category_scores]) if category_scores else 0,
                'total_revenue_potential': sum([float(sku.get('annual_revenue_potential', 0)) for sku in first_five_skus])
            }
        })
        
        return self.results
    
    def export_results(self, output_file: str = 'private_label_opportunities.json'):
        """Export analysis results to JSON file"""
        
        output_path = os.path.join(os.path.dirname(self.data_file_path), output_file)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📁 Results exported to: {output_path}")
        return output_path


def main():
    """Main execution function"""
    
    # Input file path
    data_file = '/Users/akbarchranya/georgiadashboard/strategic_data_extraction_20250908_164747.json'
    
    try:
        # Initialize scorer
        scorer = PrivateLabelOpportunityScorer(data_file)
        
        # Run analysis
        results = scorer.run_analysis()
        
        # Export results
        output_file = scorer.export_results()
        
        # Print summary
        print("\n" + "="*60)
        print("🏆 PRIVATE LABEL OPPORTUNITY ANALYSIS SUMMARY")
        print("="*60)
        
        summary = results.get('summary_stats', {})
        print(f"Categories Analyzed: {summary.get('total_categories_analyzed', 0)}")
        print(f"Categories Excluded (Tobacco): {summary.get('categories_excluded', 0)}")
        print(f"Average Opportunity Score: {summary.get('avg_opportunity_score', 0)}")
        print(f"Highest Score: {summary.get('top_score', 0)}")
        print(f"Total Revenue Potential (Top 5 SKUs): ${summary.get('total_revenue_potential', 0):,.2f}")
        
        print(f"\n🎯 TOP 5 OPPORTUNITIES:")
        for i, opp in enumerate(results.get('top_opportunities', [])[:5], 1):
            print(f"{i}. {opp['category']} (Score: {opp['overall_score']})")
        
        print(f"\n🚀 FIRST 5 SKUS TO LAUNCH:")
        for sku in results.get('first_five_skus', []):
            print(f"{sku['rank']}. {sku['category']} - ${sku['proposed_private_label_price']} " +
                  f"({sku['price_advantage_pct']}% below market)")
        
        print(f"\n📁 Full analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main()