#!/usr/bin/env python3
"""
Strategic Business Analysis Runner
Simplified version for quick execution
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import warnings
warnings.filterwarnings('ignore')

def run_customer_analysis():
    """Analyze customer concentration and risks"""
    print("\n🔍 ANALYZING CUSTOMER CONCENTRATION")
    print("=" * 60)
    
    with SQLServerConnection() as db_conn:
        query = """
        SELECT 
            c.ID as customer_id,
            c.CustomerName as customer_name,
            c.City,
            c.State,
            COALESCE(SUM(s.Quantity * s.PricePerUnit), 0) as total_revenue,
            COUNT(DISTINCT s.TransactionTime) as transaction_days,
            MAX(s.TransactionTime) as last_transaction
        FROM Customer c
        LEFT JOIN Sales s ON c.ID = s.CustomerID AND s.TransactionTime >= DATEADD(month, -12, GETDATE())
        WHERE c.IsActive = 1
        GROUP BY c.ID, c.CustomerName, c.City, c.State
        ORDER BY total_revenue DESC
        """
        
        df = pd.read_sql(query, db_conn.connection)
        
    total_revenue = df['total_revenue'].sum()
    df['revenue_pct'] = (df['total_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    df['cumulative_pct'] = df['revenue_pct'].cumsum()
    
    # Key metrics
    top_10_count = max(1, int(len(df) * 0.1))
    top_10_pct = df.head(top_10_count)['revenue_pct'].sum()
    top_20_count = max(1, int(len(df) * 0.2))
    top_20_pct = df.head(top_20_count)['revenue_pct'].sum()
    
    # HHI Index
    hhi = (df['revenue_pct'] ** 2).sum()
    
    results = {
        'total_customers': len(df),
        'active_customers': len(df[df['total_revenue'] > 0]),
        'top_10_concentration': round(top_10_pct, 1),
        'top_20_concentration': round(top_20_pct, 1),
        'hhi_index': round(hhi, 0),
        'top_customers': df.head(10)[['customer_name', 'revenue_pct', 'cumulative_pct']].to_dict('records')
    }
    
    print(f"✅ Total Customers: {results['total_customers']}")
    print(f"📊 Top 10% Control: {results['top_10_concentration']}% of revenue")
    print(f"📊 HHI Index: {results['hhi_index']} (>1500 = High concentration risk)")
    
    return results

def run_inventory_analysis():
    """Analyze inventory efficiency"""
    print("\n📦 ANALYZING INVENTORY & WORKING CAPITAL")
    print("=" * 60)
    
    with SQLServerConnection() as db_conn:
        query = """
        SELECT 
            i.INVID,
            i.DES as description,
            i.QOH as quantity_on_hand,
            i.COST as unit_cost,
            i.QOH * i.COST as inventory_value,
            COALESCE(s.units_sold_30d, 0) as units_sold_30d
        FROM INV i
        LEFT JOIN (
            SELECT 
                INVID,
                SUM(QTY) as units_sold_30d
            FROM SAL
            WHERE DTE >= DATEADD(day, -30, GETDATE())
            GROUP BY INVID
        ) s ON i.INVID = s.INVID
        WHERE i.ACTIVE = 1 AND i.QOH > 0
        """
        
        df = pd.read_sql(query, db_conn.connection)
    
    # Calculate metrics
    df['daily_velocity'] = df['units_sold_30d'] / 30
    df['days_of_inventory'] = np.where(
        df['daily_velocity'] > 0,
        df['quantity_on_hand'] / df['daily_velocity'],
        999
    )
    
    # Categorize health
    conditions = [
        (df['days_of_inventory'] <= 30),
        (df['days_of_inventory'] <= 60),
        (df['days_of_inventory'] <= 90),
        (df['days_of_inventory'] > 90)
    ]
    choices = ['Optimal', 'Good', 'Fair', 'Dead Stock']
    df['health'] = np.select(conditions, choices, default='Dead Stock')
    
    total_value = df['inventory_value'].sum()
    dead_stock_value = df[df['health'] == 'Dead Stock']['inventory_value'].sum()
    
    results = {
        'total_skus': len(df),
        'total_inventory_value': round(total_value, 0),
        'dead_stock_value': round(dead_stock_value, 0),
        'dead_stock_pct': round((dead_stock_value / total_value * 100) if total_value > 0 else 0, 1),
        'avg_days_inventory': round(df[df['days_of_inventory'] < 999]['days_of_inventory'].mean(), 0),
        'health_distribution': df['health'].value_counts().to_dict()
    }
    
    print(f"✅ Total SKUs: {results['total_skus']}")
    print(f"💰 Inventory Value: ${results['total_inventory_value']:,.0f}")
    print(f"⚠️ Dead Stock: ${results['dead_stock_value']:,.0f} ({results['dead_stock_pct']}%)")
    
    return results

def run_receivables_analysis():
    """Analyze receivables and cash flow"""
    print("\n💳 ANALYZING RECEIVABLES & CASH FLOW")
    print("=" * 60)
    
    with SQLServerConnection() as db_conn:
        # Receivables aging
        query_ar = """
        SELECT 
            c.NAME as customer_name,
            ar.AMOUNT - ar.PAYAMT as balance,
            DATEDIFF(day, ar.DTE, GETDATE()) as days_outstanding
        FROM AR ar
        JOIN CUS c ON ar.CID = c.ID
        WHERE ar.AMOUNT - ar.PAYAMT != 0
        """
        
        df_ar = pd.read_sql(query_ar, db_conn.connection)
        
        # Recent sales for DSO
        query_sales = """
        SELECT SUM(QTY * RETAIL) as total_sales
        FROM SAL
        WHERE DTE >= DATEADD(day, -90, GETDATE())
        """
        
        recent_sales = pd.read_sql(query_sales, db_conn.connection).iloc[0]['total_sales']
    
    # Calculate aging
    conditions = [
        (df_ar['days_outstanding'] <= 30),
        (df_ar['days_outstanding'] <= 60),
        (df_ar['days_outstanding'] <= 90),
        (df_ar['days_outstanding'] > 90)
    ]
    choices = ['Current', '31-60 days', '61-90 days', 'Over 90 days']
    df_ar['aging_bucket'] = np.select(conditions, choices, default='Over 90 days')
    
    total_receivables = df_ar['balance'].sum()
    daily_sales = recent_sales / 90 if recent_sales else 0
    dso = total_receivables / daily_sales if daily_sales > 0 else 0
    
    aging_summary = df_ar.groupby('aging_bucket')['balance'].sum().to_dict()
    over_90 = df_ar[df_ar['days_outstanding'] > 90]['balance'].sum()
    
    results = {
        'total_receivables': round(total_receivables, 0),
        'dso': round(dso, 0),
        'aging_summary': aging_summary,
        'over_90_days': round(over_90, 0),
        'over_90_pct': round((over_90 / total_receivables * 100) if total_receivables > 0 else 0, 1)
    }
    
    print(f"✅ Total Receivables: ${results['total_receivables']:,.0f}")
    print(f"📊 DSO: {results['dso']} days")
    print(f"⚠️ Over 90 days: {results['over_90_pct']}% of receivables")
    
    return results

def run_supplier_analysis():
    """Analyze supplier dependencies"""
    print("\n🚚 ANALYZING SUPPLIER DEPENDENCIES")
    print("=" * 60)
    
    with SQLServerConnection() as db_conn:
        query = """
        SELECT 
            v.NAME as vendor_name,
            COUNT(DISTINCT p.INVID) as sku_count,
            SUM(p.QTY * p.COST) as total_purchases
        FROM VEN v
        JOIN PUR p ON v.ID = p.VID 
        WHERE p.DTE >= DATEADD(month, -12, GETDATE())
            AND v.ACTIVE = 1
        GROUP BY v.NAME
        ORDER BY total_purchases DESC
        """
        
        df = pd.read_sql(query, db_conn.connection)
    
    if len(df) == 0:
        return {
            'total_suppliers': 0,
            'top_5_concentration': 0,
            'supplier_hhi': 0
        }
    
    total_purchases = df['total_purchases'].sum()
    df['purchase_pct'] = (df['total_purchases'] / total_purchases * 100) if total_purchases > 0 else 0
    
    top_5_concentration = df.head(5)['purchase_pct'].sum()
    supplier_hhi = (df['purchase_pct'] ** 2).sum()
    
    results = {
        'total_suppliers': len(df),
        'total_purchases': round(total_purchases, 0),
        'top_5_concentration': round(top_5_concentration, 1),
        'supplier_hhi': round(supplier_hhi, 0),
        'top_suppliers': df.head(5)[['vendor_name', 'purchase_pct']].to_dict('records')
    }
    
    print(f"✅ Total Suppliers: {results['total_suppliers']}")
    print(f"💰 Annual Purchases: ${results['total_purchases']:,.0f}")
    print(f"📊 Top 5 Control: {results['top_5_concentration']}% of purchases")
    
    return results

def generate_recommendations(analysis_results):
    """Generate strategic recommendations"""
    recommendations = []
    
    # Customer concentration risk
    if 'customer' in analysis_results:
        if analysis_results['customer']['hhi_index'] > 1500:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Customer Concentration',
                'issue': f"HHI of {analysis_results['customer']['hhi_index']:.0f} indicates high concentration risk",
                'action': f"Diversify customer base. Top 10% control {analysis_results['customer']['top_10_concentration']}% of revenue"
            })
    
    # Inventory management
    if 'inventory' in analysis_results:
        if analysis_results['inventory']['dead_stock_pct'] > 15:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Inventory Management',
                'issue': f"{analysis_results['inventory']['dead_stock_pct']}% of inventory is dead stock",
                'action': "Implement clearance strategy and improve demand forecasting"
            })
    
    # Receivables management
    if 'receivables' in analysis_results:
        if analysis_results['receivables']['dso'] > 45:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Cash Flow',
                'issue': f"DSO of {analysis_results['receivables']['dso']} days impacts working capital",
                'action': "Tighten credit terms and accelerate collections"
            })
        
        if analysis_results['receivables']['over_90_pct'] > 20:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Bad Debt Risk',
                'issue': f"{analysis_results['receivables']['over_90_pct']}% of receivables over 90 days",
                'action': "Immediate collection efforts required, consider write-offs"
            })
    
    # Supplier risk
    if 'supplier' in analysis_results:
        if analysis_results['supplier']['supplier_hhi'] > 2000:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Supply Chain',
                'issue': f"High supplier concentration (HHI: {analysis_results['supplier']['supplier_hhi']:.0f})",
                'action': "Identify alternative suppliers for critical products"
            })
    
    return recommendations

def main():
    print("\n" + "="*80)
    print(" STRATEGIC BUSINESS ANALYSIS - EXECUTIVE REPORT")
    print(" " + datetime.now().strftime("%B %d, %Y %I:%M %p"))
    print("="*80)
    
    results = {}
    
    try:
        # Run all analysis chunks
        results['customer'] = run_customer_analysis()
        results['inventory'] = run_inventory_analysis()
        results['receivables'] = run_receivables_analysis()
        results['supplier'] = run_supplier_analysis()
        
        # Generate recommendations
        recommendations = generate_recommendations(results)
        
        # Calculate key ratios
        ratios = {
            'inventory_turnover': 12 / (results['inventory']['avg_days_inventory'] / 30) if results['inventory']['avg_days_inventory'] > 0 else 0,
            'cash_conversion_cycle': results['inventory']['avg_days_inventory'] + results['receivables']['dso'],
            'customer_concentration_risk': 'HIGH' if results['customer']['hhi_index'] > 1500 else 'MODERATE' if results['customer']['hhi_index'] > 1000 else 'LOW',
            'working_capital_efficiency': 'POOR' if results['inventory']['dead_stock_pct'] > 20 else 'FAIR' if results['inventory']['dead_stock_pct'] > 10 else 'GOOD'
        }
        
        # Save results
        output = {
            'analysis_date': datetime.now().isoformat(),
            'executive_summary': {
                'customer_metrics': {
                    'total': results['customer']['total_customers'],
                    'concentration': f"{results['customer']['top_10_concentration']}%",
                    'risk_level': ratios['customer_concentration_risk']
                },
                'inventory_metrics': {
                    'value': f"${results['inventory']['total_inventory_value']:,.0f}",
                    'dead_stock': f"{results['inventory']['dead_stock_pct']}%",
                    'efficiency': ratios['working_capital_efficiency']
                },
                'receivables_metrics': {
                    'total': f"${results['receivables']['total_receivables']:,.0f}",
                    'dso': f"{results['receivables']['dso']} days",
                    'overdue': f"{results['receivables']['over_90_pct']}%"
                },
                'supplier_metrics': {
                    'count': results['supplier']['total_suppliers'],
                    'concentration': f"{results['supplier']['top_5_concentration']}%"
                }
            },
            'key_ratios': ratios,
            'recommendations': recommendations,
            'detailed_results': results
        }
        
        filename = f"strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        # Print executive summary
        print("\n" + "="*80)
        print(" EXECUTIVE SUMMARY")
        print("="*80)
        
        print("\n📊 KEY METRICS:")
        print(f"  • Customer Concentration Risk: {ratios['customer_concentration_risk']}")
        print(f"  • Working Capital Efficiency: {ratios['working_capital_efficiency']}")
        print(f"  • Cash Conversion Cycle: {ratios['cash_conversion_cycle']:.0f} days")
        print(f"  • Inventory Turnover: {ratios['inventory_turnover']:.1f}x per year")
        
        print("\n🎯 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(sorted(recommendations, 
                                      key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}.get(x['priority'], 3))[:5], 1):
            print(f"\n  {i}. [{rec['priority']}] {rec['category']}")
            print(f"     Issue: {rec['issue']}")
            print(f"     Action: {rec['action']}")
        
        print(f"\n💾 Full report saved to: {filename}")
        
        return output
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()