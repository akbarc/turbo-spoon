#!/usr/bin/env python3
"""
Test customer 360 view fix for NoneType comparison error
"""

import requests
import json

def test_customer_360():
    """Test the customer 360 view API for customer 4625"""
    
    # Test customer ID that was causing the error
    customer_id = 4625
    
    print("=" * 80)
    print(f"Testing Customer 360 View for Customer ID: {customer_id}")
    print("=" * 80)
    print()
    
    # Make API request
    url = f"http://127.0.0.1:5000/api/customer/{customer_id}/360-view"
    
    try:
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data:
                print("✅ Customer 360 view loaded successfully!")
                print()
                
                # Display key information
                if 'customer' in data:
                    customer = data['customer']
                    print("Customer Info:")
                    print(f"  Name: {customer.get('customer_name', 'N/A')}")
                    print(f"  Company: {customer.get('company', 'N/A')}")
                    print(f"  Balance: ${customer.get('account_balance', 0):,.2f}")
                    print()
                
                if 'risk' in data:
                    risk = data['risk']
                    if 'risk_assessment' in risk:
                        assessment = risk['risk_assessment']
                        print("Risk Assessment:")
                        print(f"  Risk Level: {assessment.get('risk_level', 'N/A')}")
                        print(f"  Risk Score: {assessment.get('risk_score', 'N/A')}")
                        print(f"  NSF Count: {assessment.get('nsf_count', 0)}")
                        print(f"  AR Over 90: ${assessment.get('ar_over_90', 0) or 0:,.2f}")
                        print()
                
                if 'payments' in data:
                    payments = data['payments']
                    print("Payment Metrics:")
                    print(f"  Behavior: {payments.get('behavior_classification', 'N/A')}")
                    print(f"  Avg Days to Pay: {payments.get('payment_summary', {}).get('avg_days_to_pay', 'N/A')}")
                    print()
                
                print("All sections present:")
                for key in ['customer', 'sales', 'payments', 'receivables', 'patterns', 'risk', 'predictions', 'recommendations']:
                    print(f"  {key}: {'✅' if key in data else '❌'}")
                
            else:
                print("❌ Empty response received")
        else:
            print(f"❌ Error: Status code {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask server")
        print("Make sure the AR dashboard is running (python3 ar_dashboard.py)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_customer_360()