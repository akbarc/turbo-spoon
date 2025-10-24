#!/usr/bin/env python3
"""
Customer Risk Prediction Module
Based on analysis of bad debt vs good customers to predict collection risk
"""

from modules.customer_balance_engine import CustomerBalanceEngine
from database_pymssql import SQLServerConnection
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CustomerRiskPredictor:
    """
    Predicts customer collection risk based on payment and purchasing patterns
    """
    
    def __init__(self):
        self.balance_engine = CustomerBalanceEngine()
        
        # Risk scoring weights based on analysis of bad debt vs good customers
        self.risk_weights = {
            'balance_to_sales_ratio': 0.30,      # Strongest indicator (285,735x difference!)
            'days_since_last_payment': 0.25,     # 38x difference - critical timing indicator
            'nsf_to_sales_ratio': 0.20,          # 3.48x difference - NSF history matters
            'payment_to_sales_ratio': -0.15,     # Negative weight (higher payment ratio = lower risk)
            'avg_transaction_size': 0.10         # 3.86x difference - transaction patterns
        }
        
        # Risk thresholds based on analysis
        self.risk_thresholds = {
            'LOW': 0.0,
            'MEDIUM': 0.3,
            'HIGH': 0.7,
            'CRITICAL': 1.5
        }
        
        # Key risk indicators from analysis
        self.critical_indicators = {
            'balance_to_sales_ratio_threshold': 0.3,    # Bad debt avg: 15,332x, Good: 0.054
            'days_since_payment_threshold': 90,         # Bad debt avg: 304 days, Good: 8 days
            'nsf_to_sales_ratio_threshold': 0.15,       # Bad debt avg: 0.388, Good: 0.112
            'payment_frequency_threshold': 30           # Days between payments
        }
    
    def calculate_risk_score(self, customer_id: int) -> dict:
        """
        Calculate comprehensive risk score for a customer
        
        Returns:
            dict: Risk assessment with score, level, and detailed breakdown
        """
        try:
            logger.info(f"Calculating risk score for customer {customer_id}")
            
            # Get comprehensive customer data
            overview = self.balance_engine.get_comprehensive_customer_overview(customer_id)
            customer_details = overview['customer_details']
            overview_metrics = overview['overview_metrics']
            balance_data = overview['balance_data']
            
            # Extract risk factors
            risk_factors = self._extract_risk_factors(customer_details, overview_metrics, balance_data)
            
            # Calculate weighted risk score
            risk_score = self._calculate_weighted_score(risk_factors)
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Generate risk explanation
            risk_explanation = self._generate_risk_explanation(risk_factors, risk_score, risk_level)
            
            # Identify red flags
            red_flags = self._identify_red_flags(risk_factors)
            
            return {
                'customer_id': customer_id,
                'customer_name': customer_details.get('name', 'Unknown'),
                'risk_score': round(risk_score, 3),
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'red_flags': red_flags,
                'explanation': risk_explanation,
                'recommendations': self._generate_recommendations(risk_level, red_flags),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score for customer {customer_id}: {e}")
            return {
                'customer_id': customer_id,
                'error': str(e),
                'risk_score': None,
                'risk_level': 'UNKNOWN'
            }
    
    def _extract_risk_factors(self, customer_details: dict, overview_metrics: dict, balance_data: dict) -> dict:
        """Extract key risk factors from customer data"""
        
        current_balance = balance_data['current_balance']['authoritative_balance']
        total_sales = customer_details['total_sales_lifetime']
        
        # Calculate key ratios (handle division by zero)
        balance_to_sales_ratio = current_balance / max(total_sales, 1) if total_sales > 0 else float('inf')
        
        payment_metrics = overview_metrics.get('payments', {})
        total_payments = payment_metrics.get('total_payment_amount', 0)
        payment_to_sales_ratio = total_payments / max(total_sales, 1) if total_sales > 0 else 0
        
        nsf_metrics = overview_metrics.get('fees_and_nsf', {})
        nsf_amount = nsf_metrics.get('nsf_returned_amount', 0)
        nsf_to_sales_ratio = nsf_amount / max(total_sales, 1) if total_sales > 0 else 0
        
        # Calculate days since last payment
        last_payment = payment_metrics.get('last_payment_date')
        if last_payment:
            try:
                last_payment_date = datetime.fromisoformat(last_payment)
                days_since_payment = (datetime.now() - last_payment_date).days
            except:
                days_since_payment = 9999
        else:
            days_since_payment = 9999
        
        # Normalize avg transaction size (divide by 1000 for scoring)
        avg_transaction = overview_metrics.get('sales', {}).get('avg_transaction', 0)
        normalized_avg_transaction = avg_transaction / 1000
        
        return {
            'balance_to_sales_ratio': balance_to_sales_ratio,
            'payment_to_sales_ratio': payment_to_sales_ratio,
            'nsf_to_sales_ratio': nsf_to_sales_ratio,
            'days_since_last_payment': days_since_payment,
            'avg_transaction_size': normalized_avg_transaction,
            'current_balance': current_balance,
            'total_sales': total_sales,
            'nsf_count': nsf_metrics.get('nsf_returned_count', 0),
            'payment_count': payment_metrics.get('total_payments', 0),
            'credit_utilization': customer_details.get('credit_limit', 0)
        }
    
    def _calculate_weighted_score(self, factors: dict) -> float:
        """Calculate weighted risk score based on identified patterns"""
        
        score = 0.0
        
        # Apply weights to normalized factors
        for factor, weight in self.risk_weights.items():
            if factor in factors:
                value = factors[factor]
                
                # Apply normalization/scaling based on analysis
                if factor == 'balance_to_sales_ratio':
                    # Cap extreme values for scoring
                    normalized_value = min(value, 2.0)  # Cap at 2.0 for scoring
                elif factor == 'days_since_last_payment':
                    # Scale days to 0-1 range (365 days = 1.0)
                    normalized_value = min(value / 365, 2.0)
                elif factor == 'nsf_to_sales_ratio':
                    # Scale NSF ratio
                    normalized_value = min(value * 2, 2.0)  # Multiply by 2 to emphasize
                elif factor == 'payment_to_sales_ratio':
                    # For payment ratio, higher is better (negative weight)
                    normalized_value = min(value, 2.0)
                elif factor == 'avg_transaction_size':
                    # Already normalized by dividing by 1000
                    normalized_value = min(value / 10, 1.0)  # Scale to reasonable range
                else:
                    normalized_value = value
                
                score += normalized_value * weight
        
        return max(score, 0)  # Ensure non-negative score
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        
        if score >= self.risk_thresholds['CRITICAL']:
            return 'CRITICAL'
        elif score >= self.risk_thresholds['HIGH']:
            return 'HIGH'
        elif score >= self.risk_thresholds['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_red_flags(self, factors: dict) -> list:
        """Identify specific red flags based on thresholds"""
        
        red_flags = []
        
        # Balance to sales ratio
        if factors['balance_to_sales_ratio'] > self.critical_indicators['balance_to_sales_ratio_threshold']:
            red_flags.append(f"High balance-to-sales ratio: {factors['balance_to_sales_ratio']:.3f}")
        
        # Days since payment
        if factors['days_since_last_payment'] > self.critical_indicators['days_since_payment_threshold']:
            red_flags.append(f"No payment in {factors['days_since_last_payment']} days")
        
        # NSF history
        if factors['nsf_to_sales_ratio'] > self.critical_indicators['nsf_to_sales_ratio_threshold']:
            red_flags.append(f"High NSF ratio: {factors['nsf_to_sales_ratio']:.3f}")
        
        # NSF count
        if factors['nsf_count'] > 20:
            red_flags.append(f"High NSF count: {factors['nsf_count']} returns")
        
        # Low payment ratio
        if factors['payment_to_sales_ratio'] < 0.5:
            red_flags.append(f"Low payment ratio: {factors['payment_to_sales_ratio']:.3f}")
        
        # High current balance
        if factors['current_balance'] > 100000:
            red_flags.append(f"High outstanding balance: ${factors['current_balance']:,.2f}")
        
        return red_flags
    
    def _generate_risk_explanation(self, factors: dict, score: float, level: str) -> str:
        """Generate human-readable risk explanation"""
        
        explanations = []
        
        if level == 'CRITICAL':
            explanations.append("⚠️ CRITICAL RISK - Immediate attention required")
        elif level == 'HIGH':
            explanations.append("🔴 HIGH RISK - Monitor closely")
        elif level == 'MEDIUM':
            explanations.append("🟡 MEDIUM RISK - Watch for changes")
        else:
            explanations.append("🟢 LOW RISK - Normal collection patterns")
        
        # Add specific factor explanations
        if factors['days_since_last_payment'] > 180:
            explanations.append(f"No payment received in {factors['days_since_last_payment']} days")
        
        if factors['balance_to_sales_ratio'] > 0.5:
            explanations.append("Outstanding balance is high relative to sales volume")
        
        if factors['nsf_count'] > 10:
            explanations.append(f"Significant NSF history ({factors['nsf_count']} returns)")
        
        return " • ".join(explanations)
    
    def _generate_recommendations(self, risk_level: str, red_flags: list) -> list:
        """Generate actionable recommendations based on risk assessment"""
        
        recommendations = []
        
        if risk_level == 'CRITICAL':
            recommendations.extend([
                "🚨 Immediate action required - consider legal collection",
                "📞 Contact customer immediately for payment plan",
                "🔒 Place account on credit hold",
                "📋 Review all outstanding invoices"
            ])
        elif risk_level == 'HIGH':
            recommendations.extend([
                "📞 Call customer to discuss payment",
                "📅 Establish payment schedule",
                "⚠️ Reduce credit limit",
                "📧 Send formal collection notice"
            ])
        elif risk_level == 'MEDIUM':
            recommendations.extend([
                "📧 Send payment reminder",
                "👀 Monitor payment patterns closely",
                "📋 Review credit terms"
            ])
        else:
            recommendations.extend([
                "✅ Customer shows good payment patterns",
                "📈 Consider credit limit increase if requested"
            ])
        
        # Add specific recommendations based on red flags
        if any('NSF' in flag for flag in red_flags):
            recommendations.append("💳 Require certified payment methods")
        
        if any('days' in flag for flag in red_flags):
            recommendations.append("⏰ Implement shorter payment terms")
        
        return recommendations
    
    def batch_risk_assessment(self, customer_ids: list = None, limit: int = None) -> pd.DataFrame:
        """
        Perform risk assessment on multiple customers
        
        Args:
            customer_ids: List of specific customer IDs, or None for all customers
            limit: Maximum number of customers to assess
            
        Returns:
            DataFrame with risk assessments
        """
        try:
            if customer_ids is None:
                # Get all customers with significant balances
                with SQLServerConnection() as db:
                    query = """
                    SELECT TOP {} ID, COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                           AccountBalance, TotalSales
                    FROM dbo.Customer 
                    WHERE AccountBalance > 1000 OR TotalSales > 10000
                    ORDER BY AccountBalance DESC
                    """.format(limit or 100)
                    
                    result = db.execute_query(query)
                    customer_ids = result['ID'].tolist()
            
            logger.info(f"Performing batch risk assessment on {len(customer_ids)} customers")
            
            assessments = []
            for customer_id in customer_ids:
                try:
                    assessment = self.calculate_risk_score(customer_id)
                    assessments.append(assessment)
                except Exception as e:
                    logger.error(f"Error assessing customer {customer_id}: {e}")
                    continue
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(assessments)
            
            # Sort by risk score (highest first)
            if 'risk_score' in df.columns:
                df = df.sort_values('risk_score', ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"Error in batch risk assessment: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # Test the risk predictor
    predictor = CustomerRiskPredictor()
    
    # Test with known bad debt customers
    bad_debt_customers = [4915, 5087, 3853, 5196]  # 5 Star, Nerr, N Ali, Rishi
    good_customers = [3310, 4725, 4957, 4026]      # Karim, Amit, Malik, Murad
    
    print("=== TESTING RISK PREDICTOR ===")
    
    print("\nBAD DEBT CUSTOMERS:")
    for customer_id in bad_debt_customers:
        assessment = predictor.calculate_risk_score(customer_id)
        print(f"Customer {customer_id}: {assessment['risk_level']} (Score: {assessment.get('risk_score', 'N/A')})")
        if 'red_flags' in assessment:
            for flag in assessment['red_flags']:
                print(f"  🚩 {flag}")
    
    print("\nGOOD CUSTOMERS:")
    for customer_id in good_customers:
        assessment = predictor.calculate_risk_score(customer_id)
        print(f"Customer {customer_id}: {assessment['risk_level']} (Score: {assessment.get('risk_score', 'N/A')})")
        if 'red_flags' in assessment:
            for flag in assessment['red_flags']:
                print(f"  🚩 {flag}")
