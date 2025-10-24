#!/usr/bin/env python3
"""
Enhanced Customer Risk Predictor Module
Calculates comprehensive risk scores (0-100%) with detailed analysis
"""

import logging
from datetime import datetime
from modules.customer_balance_engine import CustomerBalanceEngine

logger = logging.getLogger(__name__)

class EnhancedCustomerRiskPredictor:
    """Enhanced customer risk assessment with percentage-based scoring and detailed metrics"""
    
    def __init__(self):
        self.balance_engine = CustomerBalanceEngine()
    
    def calculate_risk_score(self, customer_id: int) -> dict:
        """
        Calculates a comprehensive risk score (0-100%) for a given customer based on financial and behavioral metrics.
        """
        try:
            logger.info(f"Calculating comprehensive risk score for customer {customer_id}")
            overview = self.balance_engine.get_comprehensive_customer_overview(customer_id)

            customer_details = overview['customer_details']
            overview_metrics = overview['overview_metrics']
            balance_data = overview['balance_data']

            # Extract core metrics
            current_balance = balance_data['current_balance']['authoritative_balance']
            total_sales = customer_details['total_sales_lifetime']
            total_payments = overview_metrics['payments']['total_payment_amount']
            nsf_returned_amount = overview_metrics['fees_and_nsf']['nsf_returned_amount']
            nsf_returned_count = overview_metrics['fees_and_nsf']['nsf_returned_count']
            nsf_fee_amount = overview_metrics['fees_and_nsf']['nsf_fee_amount']
            credit_limit = customer_details['credit_limit']
            total_visits = customer_details['total_visits']
            
            # Calculate days since last payment
            last_payment_date = overview_metrics['payments']['last_payment_date']
            if last_payment_date:
                try:
                    days_since_last_payment = (datetime.now() - datetime.fromisoformat(last_payment_date)).days
                except:
                    days_since_last_payment = 9999  # Very high if date parsing fails
            else:
                days_since_last_payment = 9999  # Never paid
            
            # Calculate last visit days
            last_visit = customer_details.get('last_visit')
            if last_visit:
                try:
                    days_since_last_visit = (datetime.now() - datetime.fromisoformat(last_visit)).days
                except:
                    days_since_last_visit = 9999
            else:
                days_since_last_visit = 9999

            # Calculate comprehensive ratios and metrics
            balance_to_sales_ratio = abs(current_balance) / total_sales if total_sales > 0 else (1.0 if current_balance > 0 else 0.0)
            nsf_to_sales_ratio = abs(nsf_returned_amount) / total_sales if total_sales > 0 else (1.0 if nsf_returned_amount > 0 else 0.0)
            payment_to_sales_ratio = abs(total_payments) / total_sales if total_sales > 0 else 0.0
            credit_utilization = abs(current_balance) / credit_limit if credit_limit > 0 else 0.0
            
            # Additional metrics
            avg_transaction_size = total_sales / total_visits if total_visits > 0 else 0.0
            payment_frequency_score = min(365, days_since_last_payment) / 365.0  # 0-1 scale
            visit_frequency_score = min(365, days_since_last_visit) / 365.0  # 0-1 scale
            
            # PERCENTAGE-BASED SCORING (0-100)
            risk_components = {}
            
            # 1. Balance Outstanding Risk (25 points max)
            if balance_to_sales_ratio >= 1.0:
                risk_components['balance_risk'] = 25.0  # Owes everything or more
            elif balance_to_sales_ratio >= 0.75:
                risk_components['balance_risk'] = 20.0
            elif balance_to_sales_ratio >= 0.50:
                risk_components['balance_risk'] = 15.0
            elif balance_to_sales_ratio >= 0.25:
                risk_components['balance_risk'] = 10.0
            elif balance_to_sales_ratio >= 0.10:
                risk_components['balance_risk'] = 5.0
            else:
                risk_components['balance_risk'] = 0.0
            
            # 2. Payment History Risk (20 points max)
            if days_since_last_payment >= 365:
                risk_components['payment_history_risk'] = 20.0
            elif days_since_last_payment >= 180:
                risk_components['payment_history_risk'] = 15.0
            elif days_since_last_payment >= 90:
                risk_components['payment_history_risk'] = 10.0
            elif days_since_last_payment >= 60:
                risk_components['payment_history_risk'] = 7.0
            elif days_since_last_payment >= 30:
                risk_components['payment_history_risk'] = 3.0
            else:
                risk_components['payment_history_risk'] = 0.0
            
            # 3. NSF/Bounced Check Risk (20 points max)
            nsf_risk = 0.0
            if nsf_returned_count >= 10:
                nsf_risk += 15.0
            elif nsf_returned_count >= 5:
                nsf_risk += 10.0
            elif nsf_returned_count >= 1:
                nsf_risk += 5.0
                
            if nsf_to_sales_ratio >= 0.5:
                nsf_risk += 5.0
            elif nsf_to_sales_ratio >= 0.1:
                nsf_risk += 3.0
                
            risk_components['nsf_risk'] = min(20.0, nsf_risk)
            
            # 4. Credit Utilization Risk (15 points max)
            if credit_utilization >= 1.0:
                risk_components['credit_risk'] = 15.0
            elif credit_utilization >= 0.90:
                risk_components['credit_risk'] = 12.0
            elif credit_utilization >= 0.75:
                risk_components['credit_risk'] = 9.0
            elif credit_utilization >= 0.50:
                risk_components['credit_risk'] = 6.0
            elif credit_utilization >= 0.25:
                risk_components['credit_risk'] = 3.0
            else:
                risk_components['credit_risk'] = 0.0
            
            # 5. Payment Behavior Risk (10 points max)
            payment_behavior_risk = 0.0
            if payment_to_sales_ratio < 0.25:
                payment_behavior_risk += 5.0
            elif payment_to_sales_ratio < 0.50:
                payment_behavior_risk += 3.0
                
            if current_balance > 50000:
                payment_behavior_risk += 3.0
            elif current_balance > 25000:
                payment_behavior_risk += 2.0
                
            risk_components['payment_behavior_risk'] = min(10.0, payment_behavior_risk)
            
            # 6. Activity/Engagement Risk (10 points max)
            activity_risk = 0.0
            if days_since_last_visit >= 180:
                activity_risk += 5.0
            elif days_since_last_visit >= 90:
                activity_risk += 3.0
            elif days_since_last_visit >= 30:
                activity_risk += 1.0
                
            if total_visits < 5:  # Very low engagement
                activity_risk += 3.0
            elif total_visits < 20:
                activity_risk += 1.0
                
            risk_components['activity_risk'] = min(10.0, activity_risk)
            
            # Calculate total risk percentage (0-100)
            total_risk_percentage = sum(risk_components.values())
            
            # Determine risk level based on percentage
            if total_risk_percentage >= 75:
                risk_level = "CRITICAL"
                risk_color = "#dc2626"
            elif total_risk_percentage >= 50:
                risk_level = "HIGH"
                risk_color = "#ea580c"
            elif total_risk_percentage >= 25:
                risk_level = "MEDIUM"
                risk_color = "#d97706"
            else:
                risk_level = "LOW"
                risk_color = "#16a34a"
            
            # Generate detailed red flags
            red_flags = []
            flag_details = []
            
            if days_since_last_payment >= 365:
                red_flags.append(f"No payment in {days_since_last_payment} days")
                flag_details.append({"category": "Payment History", "severity": "Critical", "message": f"No payment in {days_since_last_payment} days"})
            elif days_since_last_payment >= 90:
                red_flags.append(f"No payment in {days_since_last_payment} days")
                flag_details.append({"category": "Payment History", "severity": "High", "message": f"No payment in {days_since_last_payment} days"})
            
            if balance_to_sales_ratio >= 1.0:
                red_flags.append(f"Owes {balance_to_sales_ratio:.1%} of lifetime sales")
                flag_details.append({"category": "Outstanding Balance", "severity": "Critical", "message": f"Balance-to-sales ratio: {balance_to_sales_ratio:.1%}"})
            elif balance_to_sales_ratio >= 0.5:
                red_flags.append(f"High balance-to-sales ratio: {balance_to_sales_ratio:.1%}")
                flag_details.append({"category": "Outstanding Balance", "severity": "High", "message": f"Balance-to-sales ratio: {balance_to_sales_ratio:.1%}"})
            
            if nsf_returned_count >= 5:
                red_flags.append(f"High NSF count: {nsf_returned_count} returns (${nsf_returned_amount:,.2f})")
                flag_details.append({"category": "NSF History", "severity": "Critical", "message": f"{nsf_returned_count} NSF incidents totaling ${nsf_returned_amount:,.2f}"})
            elif nsf_returned_count > 0:
                red_flags.append(f"NSF history: {nsf_returned_count} returns (${nsf_returned_amount:,.2f})")
                flag_details.append({"category": "NSF History", "severity": "Medium", "message": f"{nsf_returned_count} NSF incidents totaling ${nsf_returned_amount:,.2f}"})
            
            if credit_utilization >= 0.9:
                red_flags.append(f"Credit maxed out: {credit_utilization:.1%} utilization")
                flag_details.append({"category": "Credit Utilization", "severity": "Critical", "message": f"Credit utilization: {credit_utilization:.1%}"})
            elif credit_utilization >= 0.75:
                red_flags.append(f"High credit utilization: {credit_utilization:.1%}")
                flag_details.append({"category": "Credit Utilization", "severity": "High", "message": f"Credit utilization: {credit_utilization:.1%}"})
            
            if payment_to_sales_ratio < 0.25 and total_sales > 1000:
                red_flags.append(f"Low payment ratio: {payment_to_sales_ratio:.1%} of sales paid")
                flag_details.append({"category": "Payment Behavior", "severity": "High", "message": f"Only {payment_to_sales_ratio:.1%} of sales have been paid"})
            
            if current_balance > 100000:
                red_flags.append(f"Extremely high balance: ${current_balance:,.2f}")
                flag_details.append({"category": "Outstanding Balance", "severity": "Critical", "message": f"Outstanding balance: ${current_balance:,.2f}"})
            elif current_balance > 50000:
                red_flags.append(f"High outstanding balance: ${current_balance:,.2f}")
                flag_details.append({"category": "Outstanding Balance", "severity": "High", "message": f"Outstanding balance: ${current_balance:,.2f}"})

            return {
                "customer_id": customer_id,
                "customer_name": customer_details.get('name', 'Unknown'),
                "risk_score": round(total_risk_percentage, 1),  # 0-100 percentage
                "risk_level": risk_level,
                "risk_color": risk_color,
                "red_flags": red_flags,
                "flag_details": flag_details,
                "risk_components": risk_components,
                "detailed_metrics": {
                    "financial_metrics": {
                        "current_balance": current_balance,
                        "total_sales": total_sales,
                        "total_payments": total_payments,
                        "credit_limit": credit_limit,
                        "balance_to_sales_ratio": round(balance_to_sales_ratio, 3),
                        "payment_to_sales_ratio": round(payment_to_sales_ratio, 3),
                        "credit_utilization": round(credit_utilization, 3)
                    },
                    "payment_metrics": {
                        "days_since_last_payment": days_since_last_payment,
                        "last_payment_date": last_payment_date,
                        "payment_frequency_score": round(payment_frequency_score, 3)
                    },
                    "nsf_metrics": {
                        "nsf_returned_count": nsf_returned_count,
                        "nsf_returned_amount": nsf_returned_amount,
                        "nsf_fee_amount": nsf_fee_amount,
                        "nsf_to_sales_ratio": round(nsf_to_sales_ratio, 3)
                    },
                    "activity_metrics": {
                        "total_visits": total_visits,
                        "days_since_last_visit": days_since_last_visit,
                        "last_visit": last_visit,
                        "avg_transaction_size": round(avg_transaction_size, 2),
                        "visit_frequency_score": round(visit_frequency_score, 3)
                    }
                },
                "calculated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score for customer {customer_id}: {e}")
            return {
                "customer_id": customer_id,
                "customer_name": "Unknown",
                "risk_score": -1,
                "risk_level": "ERROR",
                "risk_color": "#6b7280",
                "red_flags": [f"Error calculating risk: {str(e)}"],
                "flag_details": [],
                "risk_components": {},
                "detailed_metrics": {},
                "calculated_at": datetime.now().isoformat()
            }

    def get_risk_distribution(self, customer_ids: list) -> dict:
        """Get risk distribution across multiple customers"""
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        total_at_risk_balance = 0
        assessments = []
        
        for customer_id in customer_ids:
            try:
                assessment = self.calculate_risk_score(customer_id)
                if assessment['risk_score'] >= 0:
                    assessments.append(assessment)
                    risk_level = assessment['risk_level']
                    if risk_level in risk_counts:
                        risk_counts[risk_level] += 1
                    
                    if risk_level in ['HIGH', 'CRITICAL']:
                        total_at_risk_balance += assessment['detailed_metrics']['financial_metrics']['current_balance']
                        
            except Exception as e:
                logger.error(f"Error in risk assessment for customer {customer_id}: {e}")
                continue
        
        return {
            "assessments": assessments,
            "risk_distribution": risk_counts,
            "total_assessed": len(assessments),
            "total_at_risk_balance": total_at_risk_balance,
            "high_risk_percentage": round((risk_counts['HIGH'] + risk_counts['CRITICAL']) / max(len(assessments), 1) * 100, 1)
        }
