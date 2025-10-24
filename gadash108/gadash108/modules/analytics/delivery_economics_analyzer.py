#!/usr/bin/env python3
"""
Delivery Economics Analyzer for B2B Wholesale Distribution
Analyzes contribution margins, delivery costs, and optimal delivery zones
"""

import json
import math
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re

class DeliveryEconomicsAnalyzer:
    def __init__(self):
        # B2B Wholesale Distribution Constants
        self.FUEL_COST_PER_MILE = 0.65  # Current commercial fuel rates
        self.DRIVER_COST_PER_HOUR = 28.50  # Including benefits
        self.VEHICLE_MAINT_PER_MILE = 0.18  # Maintenance and depreciation
        self.INSURANCE_PER_MILE = 0.12  # Commercial vehicle insurance
        self.OVERHEAD_ALLOCATION = 0.08  # Administrative overhead per mile
        
        # Delivery efficiency constants
        self.AVG_SPEED_HIGHWAY = 65  # mph
        self.AVG_SPEED_URBAN = 35   # mph
        self.AVG_SPEED_RURAL = 45   # mph
        self.STOP_TIME_MINUTES = 25  # Average unload time per stop
        self.LOADING_TIME_MINUTES = 45  # Warehouse loading time
        
        # Profitability thresholds
        self.MIN_CONTRIBUTION_MARGIN = 0.15  # 15% minimum margin
        self.TARGET_CONTRIBUTION_MARGIN = 0.25  # 25% target margin
        self.DELIVERY_COST_MAX_PCT = 0.08  # Max 8% of order value for delivery
        
    def calculate_delivery_cost_per_mile(self) -> float:
        """Calculate total delivery cost per mile"""
        return (self.FUEL_COST_PER_MILE + 
                self.VEHICLE_MAINT_PER_MILE + 
                self.INSURANCE_PER_MILE + 
                self.OVERHEAD_ALLOCATION)
    
    def estimate_delivery_time(self, distance_miles: float, area_type: str = 'urban') -> float:
        """Estimate total delivery time including stops"""
        speed_map = {
            'highway': self.AVG_SPEED_HIGHWAY,
            'urban': self.AVG_SPEED_URBAN,
            'rural': self.AVG_SPEED_RURAL
        }
        
        speed = speed_map.get(area_type, self.AVG_SPEED_URBAN)
        drive_time = (distance_miles * 2) / speed  # Round trip
        stop_time = self.STOP_TIME_MINUTES / 60  # Convert to hours
        loading_time = self.LOADING_TIME_MINUTES / 60  # Convert to hours
        
        return drive_time + stop_time + loading_time
    
    def calculate_delivery_cost(self, distance_miles: float, area_type: str = 'urban') -> Dict:
        """Calculate comprehensive delivery cost"""
        cost_per_mile = self.calculate_delivery_cost_per_mile()
        total_miles = distance_miles * 2  # Round trip
        delivery_time = self.estimate_delivery_time(distance_miles, area_type)
        
        # Cost components
        mileage_cost = total_miles * cost_per_mile
        driver_cost = delivery_time * self.DRIVER_COST_PER_HOUR
        
        total_cost = mileage_cost + driver_cost
        
        return {
            'distance_miles': distance_miles,
            'total_miles_roundtrip': total_miles,
            'delivery_time_hours': round(delivery_time, 2),
            'mileage_cost': round(mileage_cost, 2),
            'driver_cost': round(driver_cost, 2),
            'total_delivery_cost': round(total_cost, 2),
            'cost_per_mile': round(cost_per_mile, 2)
        }
    
    def analyze_customer_profitability(self, strategic_data: Dict) -> Dict:
        """Analyze customer profitability from strategic data"""
        summary = strategic_data.get('summary_metrics', {})
        
        # Extract key metrics
        total_revenue = float(summary.get('total_revenue', 0))
        total_transactions = int(summary.get('total_transactions', 0))
        unique_customers = int(summary.get('unique_customers', 0))
        avg_transaction_value = float(summary.get('avg_transaction_value', 0))
        
        # Calculate contribution margins (assuming 22% gross margin for wholesale)
        gross_margin_rate = 0.22
        estimated_cogs = total_revenue * (1 - gross_margin_rate)
        gross_profit = total_revenue * gross_margin_rate
        
        # Estimate operating expenses (12% of revenue typical for wholesale)
        operating_expense_rate = 0.12
        operating_expenses = total_revenue * operating_expense_rate
        
        # Contribution margin before delivery costs
        contribution_margin = gross_profit - operating_expenses
        contribution_margin_rate = contribution_margin / total_revenue if total_revenue > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'gross_profit': round(gross_profit, 2),
            'contribution_margin': round(contribution_margin, 2),
            'contribution_margin_rate': round(contribution_margin_rate, 4),
            'avg_transaction_value': avg_transaction_value,
            'avg_revenue_per_customer': round(total_revenue / unique_customers, 2) if unique_customers > 0 else 0,
            'transactions_per_customer': round(total_transactions / unique_customers, 2) if unique_customers > 0 else 0
        }
    
    def calculate_optimal_delivery_radius(self, avg_order_value: float, 
                                        contribution_margin_rate: float) -> Dict:
        """Calculate optimal delivery radius based on order economics"""
        results = {}
        
        for radius in range(10, 201, 10):  # Test radii from 10 to 200 miles
            delivery_cost = self.calculate_delivery_cost(radius, 'urban')
            total_delivery_cost = delivery_cost['total_delivery_cost']
            
            # Calculate delivery cost as percentage of order value
            delivery_cost_pct = total_delivery_cost / avg_order_value if avg_order_value > 0 else 1
            
            # Calculate net contribution after delivery
            contribution_before_delivery = avg_order_value * contribution_margin_rate
            net_contribution = contribution_before_delivery - total_delivery_cost
            net_margin_rate = net_contribution / avg_order_value if avg_order_value > 0 else 0
            
            results[radius] = {
                'delivery_cost': total_delivery_cost,
                'delivery_cost_pct': round(delivery_cost_pct, 4),
                'net_contribution': round(net_contribution, 2),
                'net_margin_rate': round(net_margin_rate, 4),
                'profitable': net_margin_rate >= self.MIN_CONTRIBUTION_MARGIN,
                'target_achieved': net_margin_rate >= self.TARGET_CONTRIBUTION_MARGIN
            }
        
        # Find optimal radius
        optimal_radius = None
        max_profitable_radius = None
        
        for radius, data in results.items():
            if data['target_achieved'] and optimal_radius is None:
                optimal_radius = radius
            if data['profitable']:
                max_profitable_radius = radius
        
        return {
            'radius_analysis': results,
            'optimal_radius_miles': optimal_radius or max_profitable_radius,
            'max_profitable_radius_miles': max_profitable_radius,
            'recommended_radius': optimal_radius or max_profitable_radius or 50
        }
    
    def analyze_customer_segments(self, segmentation_data: Dict) -> Dict:
        """Analyze delivery economics by customer segment"""
        segment_analysis = {}
        
        if 'segment_insights' in segmentation_data:
            for segment_name, segment_data in segmentation_data['segment_insights'].items():
                avg_revenue = segment_data.get('avg_revenue_per_customer', 0)
                customer_count = segment_data.get('customer_count', 0)
                avg_transactions = segment_data.get('avg_transactions', 1)
                
                # Estimate average order value
                avg_order_value = avg_revenue / avg_transactions if avg_transactions > 0 else 0
                
                # Calculate delivery economics for different radii
                delivery_scenarios = {}
                for radius in [25, 50, 75, 100, 150]:
                    delivery_cost = self.calculate_delivery_cost(radius, 'urban')
                    total_cost = delivery_cost['total_delivery_cost']
                    
                    # Assume 10% net margin on average
                    contribution_margin = avg_order_value * 0.10
                    net_profit = contribution_margin - total_cost
                    
                    delivery_scenarios[f'{radius}_miles'] = {
                        'delivery_cost': total_cost,
                        'net_profit_per_delivery': round(net_profit, 2),
                        'profitable': net_profit > 0,
                        'roi_pct': round((net_profit / total_cost * 100), 2) if total_cost > 0 else 0
                    }
                
                segment_analysis[segment_name] = {
                    'customer_count': customer_count,
                    'avg_order_value': round(avg_order_value, 2),
                    'delivery_scenarios': delivery_scenarios,
                    'priority_level': self._classify_segment_priority(segment_data)
                }
        
        return segment_analysis
    
    def _classify_segment_priority(self, segment_data: Dict) -> str:
        """Classify segment priority for delivery optimization"""
        avg_revenue = segment_data.get('avg_revenue_per_customer', 0)
        customer_count = segment_data.get('customer_count', 0)
        
        if avg_revenue > 200000 and customer_count > 100:
            return 'High Priority'
        elif avg_revenue > 100000 and customer_count > 50:
            return 'Medium Priority'
        else:
            return 'Low Priority'
    
    def identify_expansion_opportunities(self, georgia_market_data: str) -> List[Dict]:
        """Identify expansion opportunities from market research"""
        opportunities = []
        
        # Extract key insights from market research
        if 'Atlanta Metropolitan Area' in georgia_market_data:
            opportunities.append({
                'market': 'Atlanta Metro Suburbs',
                'population': '6.3M (57% of state)',
                'opportunity_type': 'Suburban Expansion',
                'growth_rate': '2.4% YoY',
                'priority': 'High',
                'recommended_radius': 75,
                'rationale': 'Largest market with sustained growth'
            })
        
        if 'Sandy Springs' in georgia_market_data:
            opportunities.append({
                'market': 'North Atlanta Suburbs',
                'population': 'High-income demographic',
                'opportunity_type': 'Premium Market',
                'growth_rate': '5.2% home price increase',
                'priority': 'High',
                'recommended_radius': 50,
                'rationale': 'High disposable income, premium convenience focus'
            })
        
        if 'Federal Opportunity Zones' in georgia_market_data:
            opportunities.append({
                'market': 'Federal Opportunity Zones',
                'population': 'Underserved communities',
                'opportunity_type': 'Tax Incentive Market',
                'growth_rate': 'Government supported',
                'priority': 'Medium',
                'recommended_radius': 100,
                'rationale': 'Tax advantages for investment, less competition'
            })
        
        if 'Rural Areas' in georgia_market_data:
            opportunities.append({
                'market': 'Rural Georgia',
                'population': '67 counties losing population',
                'opportunity_type': 'Service Gap Fill',
                'growth_rate': 'Declining',
                'priority': 'Low',
                'recommended_radius': 150,
                'rationale': 'Less competition but longer delivery routes required'
            })
        
        return opportunities
    
    def calculate_route_optimization_savings(self, customer_density: int, 
                                           avg_distance_between_stops: float) -> Dict:
        """Calculate potential savings from route optimization"""
        
        # Single delivery scenario
        single_delivery_cost_per_mile = self.calculate_delivery_cost_per_mile()
        
        # Optimized route scenario (multiple stops)
        stops_per_route = min(customer_density, 8)  # Max 8 stops per route
        total_route_distance = avg_distance_between_stops * stops_per_route
        
        # Cost savings calculation
        individual_delivery_cost = single_delivery_cost_per_mile * 50 * stops_per_route  # Assume 50 mile avg
        optimized_route_cost = single_delivery_cost_per_mile * (50 + total_route_distance)
        
        savings = individual_delivery_cost - optimized_route_cost
        savings_pct = (savings / individual_delivery_cost * 100) if individual_delivery_cost > 0 else 0
        
        return {
            'stops_per_optimized_route': stops_per_route,
            'individual_delivery_cost': round(individual_delivery_cost, 2),
            'optimized_route_cost': round(optimized_route_cost, 2),
            'cost_savings': round(savings, 2),
            'savings_percentage': round(savings_pct, 2),
            'annual_savings_potential': round(savings * 250, 2)  # 250 delivery days/year
        }

def load_data_files():
    """Load the required data files"""
    data = {}
    
    try:
        with open('/Users/akbarchranya/georgiadashboard/strategic_data_extraction_20250908_164747.json', 'r') as f:
            data['strategic_data'] = json.load(f)
    except FileNotFoundError:
        print("Strategic data file not found")
        data['strategic_data'] = {}
    
    try:
        with open('/Users/akbarchranya/georgiadashboard/customer_segmentation_results.json', 'r') as f:
            data['segmentation_data'] = json.load(f)
    except FileNotFoundError:
        print("Customer segmentation file not found")
        data['segmentation_data'] = {}
    
    try:
        with open('/Users/akbarchranya/georgiadashboard/georgia_market_research.md', 'r') as f:
            data['georgia_market'] = f.read()
    except FileNotFoundError:
        print("Georgia market research file not found")
        data['georgia_market'] = ""
    
    return data

def main():
    """Main analysis function"""
    print("Starting Delivery Economics Analysis...")
    
    # Initialize analyzer
    analyzer = DeliveryEconomicsAnalyzer()
    
    # Load data
    data = load_data_files()
    
    # Perform analyses
    print("Analyzing customer profitability...")
    profitability = analyzer.analyze_customer_profitability(data['strategic_data'])
    
    print("Calculating optimal delivery radius...")
    radius_analysis = analyzer.calculate_optimal_delivery_radius(
        profitability['avg_transaction_value'],
        profitability['contribution_margin_rate']
    )
    
    print("Analyzing customer segments...")
    segment_analysis = analyzer.analyze_customer_segments(data['segmentation_data'])
    
    print("Identifying expansion opportunities...")
    expansion_opportunities = analyzer.identify_expansion_opportunities(data['georgia_market'])
    
    print("Calculating route optimization savings...")
    route_savings = analyzer.calculate_route_optimization_savings(5, 12)  # 5 customers per cluster, 12 miles between
    
    # Compile comprehensive analysis
    analysis_results = {
        'analysis_metadata': {
            'timestamp': datetime.now().isoformat(),
            'analyzer_version': '1.0',
            'data_sources': ['strategic_data_extraction', 'customer_segmentation', 'georgia_market_research']
        },
        'executive_summary': {
            'current_avg_order_value': profitability['avg_transaction_value'],
            'contribution_margin_rate': profitability['contribution_margin_rate'],
            'optimal_delivery_radius_miles': radius_analysis['recommended_radius'],
            'route_optimization_savings_annual': route_savings['annual_savings_potential'],
            'total_expansion_opportunities': len(expansion_opportunities)
        },
        'contribution_margin_analysis': profitability,
        'delivery_radius_optimization': radius_analysis,
        'customer_segment_economics': segment_analysis,
        'geographic_expansion_opportunities': expansion_opportunities,
        'route_optimization_potential': route_savings,
        'top_recommendations': {
            'recommended_delivery_radius_miles': radius_analysis['recommended_radius'],
            'priority_customer_segments': [
                segment for segment, data in segment_analysis.items() 
                if data.get('priority_level') == 'High Priority'
            ],
            'top_expansion_markets': [
                opp['market'] for opp in expansion_opportunities 
                if opp['priority'] == 'High'
            ][:5],
            'estimated_annual_route_savings': route_savings['annual_savings_potential']
        }
    }
    
    # Save results
    output_file = '/Users/akbarchranya/georgiadashboard/delivery_economics_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"Analysis complete! Results saved to: {output_file}")
    
    # Print key findings
    print("\n=== KEY FINDINGS ===")
    print(f"Optimal Delivery Radius: {radius_analysis['recommended_radius']} miles")
    print(f"Current Contribution Margin: {profitability['contribution_margin_rate']:.1%}")
    print(f"Average Order Value: ${profitability['avg_transaction_value']:,.2f}")
    print(f"Route Optimization Savings: ${route_savings['annual_savings_potential']:,.2f} annually")
    print(f"High Priority Expansion Markets: {len([o for o in expansion_opportunities if o['priority'] == 'High'])}")
    
    return analysis_results

if __name__ == "__main__":
    results = main()