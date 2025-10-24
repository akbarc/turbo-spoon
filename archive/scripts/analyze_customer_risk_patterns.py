#!/usr/bin/env python3
"""
Customer Risk Pattern Analysis
Analyzes payment and purchasing patterns to predict customer risk
"""

from database_pymssql import SQLServerConnection
from modules.customer_balance_engine import CustomerBalanceEngine
import pandas as pd
import json
from datetime import datetime, timedelta
import numpy as np

def find_customers():
    """Find customer IDs for the specified customers"""
    
    # Customers to analyze
    bad_debt_customers = ['5 star food mart', 'nerr petroleum', 'n ali enterprises', 'rishi shukla']
    good_customers = ['karim jiwani', 'amit budhwani', 'malik kherani', 'murad ali']
    
    all_customers = bad_debt_customers + good_customers
    customer_ids = {}
    
    try:
        with SQLServerConnection() as db:
            print("=== FINDING CUSTOMER IDs ===")
            
            for customer_name in all_customers:
                # Search by company name and individual name
                search_query = """
                SELECT TOP 5 
                    ID, AccountNumber, Company, FirstName, LastName,
                    COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                    AccountBalance, TotalSales, LastVisit
                FROM dbo.Customer 
                WHERE (Company LIKE %s OR FirstName + ' ' + LastName LIKE %s)
                ORDER BY TotalSales DESC
                """
                
                search_term = f'%{customer_name}%'
                result = db.execute_query(search_query, (search_term, search_term))
                
                if not result.empty:
                    print(f"\n--- {customer_name.upper()} ---")
                    for i, row in result.iterrows():
                        name = row['CustomerName'] or 'Unknown'
                        balance = float(row['AccountBalance']) if pd.notna(row['AccountBalance']) else 0
                        sales = float(row['TotalSales']) if pd.notna(row['TotalSales']) else 0
                        print(f"ID: {row['ID']}, Account: {row['AccountNumber']}, Name: {name}")
                        print(f"  Balance: ${balance:,.2f}, Sales: ${sales:,.2f}")
                        if customer_name not in customer_ids:
                            customer_ids[customer_name] = row['ID']  # Use the first/highest sales match
                else:
                    print(f"\n--- {customer_name.upper()} --- NOT FOUND")
            
            print("\n=== SELECTED CUSTOMER IDs ===")
            for name, cid in customer_ids.items():
                print(f"{name}: {cid}")
                
        return customer_ids, bad_debt_customers, good_customers
        
    except Exception as e:
        print(f"Error finding customers: {e}")
        return {}, [], []

def analyze_customer_patterns(customer_ids, bad_debt_customers, good_customers):
    """Analyze payment and purchasing patterns for risk prediction"""
    
    engine = CustomerBalanceEngine()
    
    print("\n" + "="*80)
    print("CUSTOMER RISK PATTERN ANALYSIS")
    print("="*80)
    
    bad_debt_analysis = []
    good_customer_analysis = []
    
    # Analyze each customer
    for customer_name, customer_id in customer_ids.items():
        try:
            print(f"\n--- ANALYZING: {customer_name.upper()} (ID: {customer_id}) ---")
            
            # Get comprehensive overview
            overview = engine.get_comprehensive_customer_overview(customer_id)
            customer_details = overview['customer_details']
            overview_metrics = overview['overview_metrics']
            balance_data = overview['balance_data']
            
            # Extract key risk indicators
            analysis = {
                'name': customer_name,
                'customer_id': customer_id,
                'current_balance': balance_data['current_balance']['authoritative_balance'],
                'total_sales': customer_details['total_sales_lifetime'],
                'credit_limit': customer_details['credit_limit'],
                'total_visits': customer_details['total_visits'],
                'tenure_years': overview_metrics['tenure']['tenure_years'],
                
                # Sales patterns
                'avg_transaction': overview_metrics['sales']['avg_transaction'],
                'total_transactions': overview_metrics['sales']['total_transactions'],
                'total_items_sold': overview_metrics['sales']['total_items_sold'],
                'last_purchase': overview_metrics['sales']['last_purchase'],
                
                # Payment patterns
                'total_payments': overview_metrics['payments']['total_payment_amount'],
                'payment_count': overview_metrics['payments']['total_payments'],
                'avg_payment': overview_metrics['payments']['avg_payment'],
                'last_payment': overview_metrics['payments']['last_payment_date'],
                
                # Risk indicators
                'nsf_returned_count': overview_metrics['fees_and_nsf']['nsf_returned_count'],
                'nsf_returned_amount': overview_metrics['fees_and_nsf']['nsf_returned_amount'],
                'nsf_fee_amount': overview_metrics['fees_and_nsf']['nsf_fee_amount'],
                'active_invoices': overview_metrics['receivables']['active_invoices'],
                'avg_invoice_balance': overview_metrics['receivables']['avg_invoice_balance'],
            }
            
            # Calculate derived metrics
            analysis['balance_to_sales_ratio'] = analysis['current_balance'] / max(analysis['total_sales'], 1)
            analysis['payment_to_sales_ratio'] = analysis['total_payments'] / max(analysis['total_sales'], 1)
            analysis['nsf_to_sales_ratio'] = analysis['nsf_returned_amount'] / max(analysis['total_sales'], 1)
            analysis['credit_utilization'] = analysis['current_balance'] / max(analysis['credit_limit'], 1) if analysis['credit_limit'] > 0 else 0
            
            # Days since last payment/purchase
            try:
                if analysis['last_payment']:
                    last_payment_date = datetime.fromisoformat(analysis['last_payment'])
                    analysis['days_since_last_payment'] = (datetime.now() - last_payment_date).days
                else:
                    analysis['days_since_last_payment'] = 9999
                    
                if analysis['last_purchase']:
                    last_purchase_date = datetime.fromisoformat(analysis['last_purchase'])
                    analysis['days_since_last_purchase'] = (datetime.now() - last_purchase_date).days
                else:
                    analysis['days_since_last_purchase'] = 9999
            except:
                analysis['days_since_last_payment'] = 9999
                analysis['days_since_last_purchase'] = 9999
            
            # Print key metrics
            print(f"  Current Balance: ${analysis['current_balance']:,.2f}")
            print(f"  Total Sales: ${analysis['total_sales']:,.2f}")
            print(f"  Balance/Sales Ratio: {analysis['balance_to_sales_ratio']:.3f}")
            print(f"  Payment/Sales Ratio: {analysis['payment_to_sales_ratio']:.3f}")
            print(f"  NSF Returns: {analysis['nsf_returned_count']} (${analysis['nsf_returned_amount']:,.2f})")
            print(f"  NSF/Sales Ratio: {analysis['nsf_to_sales_ratio']:.3f}")
            print(f"  Days Since Last Payment: {analysis['days_since_last_payment']}")
            print(f"  Credit Utilization: {analysis['credit_utilization']:.1%}")
            
            # Categorize customer
            if customer_name in bad_debt_customers:
                analysis['category'] = 'BAD_DEBT'
                bad_debt_analysis.append(analysis)
            else:
                analysis['category'] = 'GOOD_CUSTOMER'
                good_customer_analysis.append(analysis)
                
        except Exception as e:
            print(f"Error analyzing {customer_name}: {e}")
            continue
    
    return bad_debt_analysis, good_customer_analysis

def identify_risk_patterns(bad_debt_analysis, good_customer_analysis):
    """Identify patterns that distinguish bad debt from good customers"""
    
    print("\n" + "="*80)
    print("RISK PATTERN IDENTIFICATION")
    print("="*80)
    
    if not bad_debt_analysis or not good_customer_analysis:
        print("Insufficient data for pattern analysis")
        return
    
    # Convert to DataFrames for easier analysis
    bad_df = pd.DataFrame(bad_debt_analysis)
    good_df = pd.DataFrame(good_customer_analysis)
    
    print(f"\nBAD DEBT CUSTOMERS ({len(bad_df)}):")
    print(bad_df[['name', 'current_balance', 'balance_to_sales_ratio', 'nsf_returned_count', 'days_since_last_payment']].to_string())
    
    print(f"\nGOOD CUSTOMERS ({len(good_df)}):")
    print(good_df[['name', 'current_balance', 'balance_to_sales_ratio', 'nsf_returned_count', 'days_since_last_payment']].to_string())
    
    # Calculate averages for comparison
    risk_metrics = [
        'balance_to_sales_ratio', 'payment_to_sales_ratio', 'nsf_to_sales_ratio',
        'nsf_returned_count', 'days_since_last_payment', 'credit_utilization',
        'avg_transaction', 'current_balance'
    ]
    
    print(f"\n{'RISK INDICATOR':<25} {'BAD DEBT AVG':<15} {'GOOD CUSTOMER AVG':<18} {'RISK FACTOR':<12}")
    print("-" * 75)
    
    risk_factors = {}
    
    for metric in risk_metrics:
        if metric in bad_df.columns and metric in good_df.columns:
            bad_avg = bad_df[metric].mean()
            good_avg = good_df[metric].mean()
            
            if good_avg != 0:
                risk_factor = bad_avg / good_avg
            else:
                risk_factor = float('inf') if bad_avg > 0 else 1.0
            
            risk_factors[metric] = risk_factor
            
            print(f"{metric:<25} {bad_avg:<15.3f} {good_avg:<18.3f} {risk_factor:<12.2f}")
    
    # Identify top risk indicators
    print(f"\nTOP RISK INDICATORS (sorted by difference):")
    sorted_factors = sorted(risk_factors.items(), key=lambda x: abs(x[1] - 1), reverse=True)
    
    for i, (metric, factor) in enumerate(sorted_factors[:5], 1):
        interpretation = "Higher risk" if factor > 1 else "Lower risk"
        print(f"{i}. {metric}: {factor:.2f}x ({interpretation})")
    
    return risk_factors

def create_risk_scoring_model(risk_factors):
    """Create a simple risk scoring model based on identified patterns"""
    
    print(f"\n{'='*80}")
    print("RISK SCORING MODEL")
    print("="*80)
    
    # Define risk weights based on analysis
    weights = {
        'balance_to_sales_ratio': 0.25,
        'nsf_to_sales_ratio': 0.20,
        'days_since_last_payment': 0.15,
        'credit_utilization': 0.15,
        'nsf_returned_count': 0.10,
        'payment_to_sales_ratio': -0.15  # Negative because higher is better
    }
    
    print("RISK SCORING FORMULA:")
    print("Risk Score = (Balance/Sales * 0.25) + (NSF/Sales * 0.20) + (Days Since Payment * 0.15)")
    print("           + (Credit Utilization * 0.15) + (NSF Count * 0.10) - (Payment/Sales * 0.15)")
    print()
    print("Risk Levels:")
    print("  • 0.0 - 0.2: LOW RISK")
    print("  • 0.2 - 0.5: MEDIUM RISK") 
    print("  • 0.5 - 1.0: HIGH RISK")
    print("  • 1.0+:      CRITICAL RISK")
    
    return weights

if __name__ == "__main__":
    # Run the analysis
    customer_ids, bad_debt_customers, good_customers = find_customers()
    
    if customer_ids:
        bad_debt_analysis, good_customer_analysis = analyze_customer_patterns(
            customer_ids, bad_debt_customers, good_customers
        )
        
        if bad_debt_analysis and good_customer_analysis:
            risk_factors = identify_risk_patterns(bad_debt_analysis, good_customer_analysis)
            scoring_model = create_risk_scoring_model(risk_factors)
            
            print(f"\n{'='*80}")
            print("ANALYSIS COMPLETE - Risk prediction model created!")
            print("="*80)
        else:
            print("Insufficient data for pattern analysis")
    else:
        print("No customers found for analysis")
