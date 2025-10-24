#!/usr/bin/env python3
"""
Georgia Wholesale - Simplified Bank Loan Validation
Direct queries to validate key loan application metrics
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import quick_query
import json

def get_trailing_revenue():
    """Get trailing 12 months revenue"""
    query = """
    SELECT 
        YEAR(t.Time) as Year,
        MONTH(t.Time) as Month,
        SUM(te.Price * te.Quantity) as Revenue
    FROM [Transaction] t
    JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= DATEADD(month, -12, GETDATE())
        AND te.Quantity > 0  -- Sales transactions (positive quantity)
    GROUP BY YEAR(t.Time), MONTH(t.Time)
    ORDER BY Year DESC, Month DESC
    """
    try:
        df = quick_query(query)
        if not df.empty:
            return df['Revenue'].sum()
    except Exception as e:
        print(f"Error: {e}")
    return 0

def get_active_customers():
    """Get count of active customers in last 90 days"""
    query = """
    SELECT COUNT(DISTINCT CustomerID) as ActiveCustomers
    FROM [Transaction]
    WHERE Time >= DATEADD(day, -90, GETDATE())
        AND CustomerID IS NOT NULL
        AND Total > 0  -- Sales transactions
    """
    try:
        df = quick_query(query)
        if not df.empty:
            return df.iloc[0]['ActiveCustomers']
    except Exception as e:
        print(f"Error: {e}")
    return 0

def get_monthly_gross_profit():
    """Get average monthly gross profit for last 6 months"""
    query = """
    SELECT 
        YEAR(t.Time) as Year,
        MONTH(t.Time) as Month,
        SUM(te.Price * te.Quantity) as Revenue,
        SUM(te.Cost * te.Quantity) as Cost,
        SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
    FROM [Transaction] t
    JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    WHERE t.Time >= DATEADD(month, -6, GETDATE())
        AND te.Quantity > 0
    GROUP BY YEAR(t.Time), MONTH(t.Time)
    ORDER BY Year DESC, Month DESC
    """
    try:
        df = quick_query(query)
        if not df.empty:
            return df['GrossProfit'].mean()
    except Exception as e:
        print(f"Error: {e}")
    return 0

def get_customer_metrics():
    """Get various customer metrics"""
    
    # Customer retention query
    retention_query = """
    SELECT 
        COUNT(DISTINCT CASE 
            WHEN EXISTS (
                SELECT 1 FROM [Transaction] t2 
                WHERE t2.CustomerID = t1.CustomerID 
                AND t2.Time >= DATEADD(month, -1, GETDATE())
                AND t2.Total > 0
            ) THEN t1.CustomerID 
        END) * 100.0 / COUNT(DISTINCT t1.CustomerID) as RetentionRate
    FROM [Transaction] t1
    WHERE t1.Time >= DATEADD(month, -13, GETDATE())
        AND t1.Time < DATEADD(month, -12, GETDATE())
        AND t1.Total > 0
        AND t1.CustomerID IS NOT NULL
    """
    
    # New customers monthly
    new_customers_query = """
    SELECT 
        YEAR(FirstPurchase) as Year,
        MONTH(FirstPurchase) as Month,
        COUNT(*) as NewCustomers
    FROM (
        SELECT 
            CustomerID,
            MIN(Time) as FirstPurchase
        FROM [Transaction]
        WHERE Total > 0
            AND CustomerID IS NOT NULL
        GROUP BY CustomerID
    ) fc
    WHERE FirstPurchase >= DATEADD(month, -12, GETDATE())
    GROUP BY YEAR(FirstPurchase), MONTH(FirstPurchase)
    ORDER BY Year DESC, Month DESC
    """
    
    try:
        retention_df = quick_query(retention_query)
        new_df = quick_query(new_customers_query)
    except Exception as e:
        print(f"Error: {e}")
        return {'retention_rate': 0, 'avg_new_customers_monthly': 0}
    
    metrics = {
        'retention_rate': 0,
        'avg_new_customers_monthly': 0
    }
    
    if not retention_df.empty:
        metrics['retention_rate'] = retention_df.iloc[0].get('RetentionRate', 0)
    
    if not new_df.empty:
        metrics['avg_new_customers_monthly'] = new_df['NewCustomers'].mean()
    
    return metrics

def get_ar_metrics():
    """Get accounts receivable metrics"""
    
    # Current AR balance
    ar_query = """
    SELECT 
        COUNT(DISTINCT CustomerID) as CustomersWithAR,
        SUM(Balance) as TotalAR,
        AVG(Balance) as AvgBalance,
        MAX(Balance) as MaxBalance
    FROM AccountReceivable
    WHERE Balance > 0
    """
    
    # AR aging
    aging_query = """
    SELECT 
        CASE 
            WHEN DueDate >= DATEADD(day, -30, GETDATE()) THEN 'Current'
            WHEN DueDate >= DATEADD(day, -60, GETDATE()) THEN '31-60 days'
            WHEN DueDate >= DATEADD(day, -90, GETDATE()) THEN '61-90 days'
            ELSE 'Over 90 days'
        END as AgingBucket,
        SUM(Balance) as Amount,
        COUNT(DISTINCT CustomerID) as CustomerCount
    FROM AccountReceivable
    WHERE Balance > 0
    GROUP BY 
        CASE 
            WHEN DueDate >= DATEADD(day, -30, GETDATE()) THEN 'Current'
            WHEN DueDate >= DATEADD(day, -60, GETDATE()) THEN '31-60 days'
            WHEN DueDate >= DATEADD(day, -90, GETDATE()) THEN '61-90 days'
            ELSE 'Over 90 days'
        END
    """
    
    try:
        ar_df = quick_query(ar_query)
        aging_df = quick_query(aging_query)
    except Exception as e:
        print(f"Error: {e}")
        return {
            'total_ar': 0,
            'customers_with_ar': 0,
            'avg_balance': 0,
            'max_balance': 0,
            'aging': {}
        }
    
    metrics = {
        'total_ar': 0,
        'customers_with_ar': 0,
        'avg_balance': 0,
        'max_balance': 0,
        'aging': {}
    }
    
    if not ar_df.empty:
        data = ar_df.iloc[0]
        metrics['total_ar'] = data.get('TotalAR', 0)
        metrics['customers_with_ar'] = data.get('CustomersWithAR', 0)
        metrics['avg_balance'] = data.get('AvgBalance', 0)
        metrics['max_balance'] = data.get('MaxBalance', 0)
    
    if not aging_df.empty:
        for _, row in aging_df.iterrows():
            metrics['aging'][row['AgingBucket']] = {
                'amount': row['Amount'],
                'customers': row['CustomerCount']
            }
    
    return metrics

def get_product_diversity():
    """Analyze product category diversity"""
    
    query = """
    SELECT 
        c.Name as Category,
        COUNT(DISTINCT te.TransactionNumber) as Transactions,
        SUM(te.Price * te.Quantity) as Revenue,
        COUNT(DISTINCT t.CustomerID) as UniqueCustomers
    FROM TransactionEntry te
    JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
    JOIN Item i ON te.ItemID = i.ID
    JOIN Category c ON i.CategoryID = c.ID
    WHERE t.Time >= DATEADD(month, -3, GETDATE())
        AND te.Quantity > 0
    GROUP BY c.Name
    ORDER BY Revenue DESC
    """
    
    try:
        df = quick_query(query)
    except Exception as e:
        print(f"Error: {e}")
        return None
    
    if not df.empty:
        
        # Calculate cigarette vs non-cigarette
        cigarette_revenue = df[df['Category'].str.contains('CIGARETTE|CIGAR', case=False, na=False)]['Revenue'].sum()
        total_revenue = df['Revenue'].sum()
        non_cigarette_pct = ((total_revenue - cigarette_revenue) / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'total_categories': len(df),
            'top_categories': df.head(10).to_dict('records'),
            'non_cigarette_pct': non_cigarette_pct,
            'total_revenue': total_revenue
        }
    return None

def run_validation():
    """Run comprehensive validation suite"""
    print("=" * 80)
    print("GEORGIA WHOLESALE - LOAN APPLICATION VALIDATION")
    print("Direct Database Analysis")
    print("=" * 80)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {}
    }
    
    # 1. Revenue Validation
    print("\n📊 REVENUE VALIDATION")
    print("-" * 40)
    trailing_revenue = get_trailing_revenue()
    results['metrics']['trailing_12m_revenue'] = trailing_revenue
    print(f"Trailing 12-Month Revenue: ${trailing_revenue:,.2f}")
    print(f"Claimed: $32,300,000")
    print(f"Variance: {((trailing_revenue/32300000 - 1) * 100):.1f}%")
    
    # 2. Customer Metrics
    print("\n👥 CUSTOMER METRICS")
    print("-" * 40)
    active_customers = get_active_customers()
    customer_metrics = get_customer_metrics()
    results['metrics']['active_customers'] = active_customers
    results['metrics']['customer_metrics'] = customer_metrics
    
    print(f"Active Customers (90 days): {active_customers}")
    print(f"Claimed: 676")
    print(f"Customer Retention Rate: {customer_metrics['retention_rate']:.1f}%")
    print(f"Avg New Customers/Month: {customer_metrics['avg_new_customers_monthly']:.0f}")
    
    # 3. Profitability Analysis
    print("\n💰 PROFITABILITY ANALYSIS")
    print("-" * 40)
    avg_monthly_gp = get_monthly_gross_profit()
    results['metrics']['avg_monthly_gross_profit'] = avg_monthly_gp
    
    monthly_payment = 77000  # Estimated loan payment
    coverage_ratio = avg_monthly_gp / monthly_payment if monthly_payment > 0 else 0
    
    print(f"Avg Monthly Gross Profit (6 months): ${avg_monthly_gp:,.2f}")
    print(f"Required Debt Payment: ${monthly_payment:,.2f}")
    print(f"Debt Service Coverage Ratio: {coverage_ratio:.2f}x")
    
    # 4. Accounts Receivable Health
    print("\n📈 ACCOUNTS RECEIVABLE ANALYSIS")
    print("-" * 40)
    ar_metrics = get_ar_metrics()
    results['metrics']['ar_metrics'] = ar_metrics
    
    print(f"Total AR Balance: ${ar_metrics['total_ar']:,.2f}")
    print(f"Customers with AR: {ar_metrics['customers_with_ar']}")
    print(f"Average Balance: ${ar_metrics['avg_balance']:,.2f}")
    print(f"Largest Balance: ${ar_metrics['max_balance']:,.2f}")
    
    if ar_metrics['aging']:
        print("\nAR Aging:")
        for bucket, data in ar_metrics['aging'].items():
            print(f"  {bucket}: ${data['amount']:,.2f} ({data['customers']} customers)")
    
    # 5. Product Diversity
    print("\n📦 PRODUCT DIVERSITY ANALYSIS")
    print("-" * 40)
    product_data = get_product_diversity()
    if product_data:
        results['metrics']['product_diversity'] = product_data
        print(f"Total Categories: {product_data['total_categories']}")
        print(f"Non-Cigarette Revenue: {product_data['non_cigarette_pct']:.1f}%")
        print(f"Claimed: 64.2%")
        
        print("\nTop Revenue Categories:")
        for i, cat in enumerate(product_data['top_categories'][:5], 1):
            print(f"  {i}. {cat['Category']}: ${cat['Revenue']:,.2f} ({cat['UniqueCustomers']} customers)")
    
    # Generate Summary
    print("\n" + "=" * 80)
    print("📋 EXECUTIVE SUMMARY")
    print("=" * 80)
    
    # Calculate validation scores
    validations = []
    
    # Revenue validation
    revenue_variance = abs((trailing_revenue/32300000 - 1)) if trailing_revenue > 0 else 1
    if revenue_variance < 0.15:  # Within 15%
        validations.append("✅ Revenue claim validated")
    else:
        validations.append("⚠️ Revenue variance exceeds 15%")
    
    # Customer validation
    customer_variance = abs((active_customers/676 - 1)) if active_customers > 0 else 1
    if customer_variance < 0.15:
        validations.append("✅ Customer count validated")
    else:
        validations.append("⚠️ Customer count variance exceeds 15%")
    
    # Debt service validation
    if coverage_ratio >= 2.0:
        validations.append("✅ Strong debt service coverage")
    elif coverage_ratio >= 1.25:
        validations.append("✅ Adequate debt service coverage")
    else:
        validations.append("⚠️ Debt service coverage below minimum")
    
    # AR health validation
    current_ar = ar_metrics['aging'].get('Current', {}).get('amount', 0)
    total_ar = ar_metrics['total_ar']
    current_pct = (current_ar / total_ar * 100) if total_ar > 0 else 0
    
    if current_pct > 70:
        validations.append("✅ Healthy AR aging profile")
    else:
        validations.append("⚠️ AR aging needs attention")
    
    print("\nVALIDATION RESULTS:")
    for validation in validations:
        print(f"  {validation}")
    
    # Final recommendation
    positive_validations = len([v for v in validations if v.startswith("✅")])
    validation_rate = (positive_validations / len(validations) * 100) if validations else 0
    
    print(f"\nVALIDATION SCORE: {positive_validations}/{len(validations)} ({validation_rate:.0f}%)")
    
    if validation_rate >= 75:
        print("\n🎯 RECOMMENDATION: APPROVE")
        print("The business demonstrates strong fundamentals supporting the loan application.")
    elif validation_rate >= 50:
        print("\n🎯 RECOMMENDATION: CONDITIONAL APPROVAL")
        print("Consider additional covenants or monitoring requirements.")
    else:
        print("\n🎯 RECOMMENDATION: FURTHER REVIEW REQUIRED")
        print("Additional due diligence recommended before approval.")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"bank_validation_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Complete analysis saved to: {report_file}")
    
    return results

if __name__ == "__main__":
    try:
        print("\n🚀 Starting Georgia Wholesale Loan Validation...")
        print("Connecting to database and analyzing metrics...\n")
        results = run_validation()
        print("\n✅ Validation Complete")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)