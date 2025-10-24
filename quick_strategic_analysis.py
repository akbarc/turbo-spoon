#!/usr/bin/env python3
"""Quick Strategic Business Analysis"""

from database_pymssql import SQLServerConnection
import pandas as pd
import numpy as np
from datetime import datetime
import json

def run_analysis():
    results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {},
        'recommendations': []
    }
    
    with SQLServerConnection() as db:
        conn = db.connection
        
        # CUSTOMER CONCENTRATION
        print("\n📊 CUSTOMER ANALYSIS")
        print("-" * 40)
        
        try:
            query = """
            SELECT TOP 200
                c.ID,
                c.CustomerName,
                c.AccountBalance
            FROM Customer c
            WHERE c.AccountBalance != 0
            ORDER BY c.AccountBalance DESC
            """
            
            df = pd.read_sql(query, conn)
            
            if len(df) > 0:
                total = abs(df['AccountBalance'].sum())
                df['pct'] = abs(df['AccountBalance']) / total * 100
                
                top_10_count = min(10, len(df))
                top_10_pct = df.head(top_10_count)['pct'].sum()
                
                top_20_count = min(20, len(df))
                top_20_pct = df.head(top_20_count)['pct'].sum()
                
                # HHI calculation
                hhi = (df['pct'] ** 2).sum()
                
                results['metrics']['customers'] = {
                    'total': len(df),
                    'top_10_concentration': round(top_10_pct, 1),
                    'top_20_concentration': round(top_20_pct, 1),
                    'hhi_index': round(hhi, 0)
                }
                
                print(f"Total Customers: {len(df)}")
                print(f"Top 10% Control: {top_10_pct:.1f}% of balances")
                print(f"Top 20% Control: {top_20_pct:.1f}% of balances")
                print(f"HHI Index: {hhi:.0f}")
                
                # Risk assessment
                if hhi > 1500:
                    results['recommendations'].append({
                        'priority': 'HIGH',
                        'area': 'Customer Concentration',
                        'issue': f'HHI of {hhi:.0f} indicates high concentration risk',
                        'action': 'Diversify customer base to reduce dependency'
                    })
                    
        except Exception as e:
            print(f"Customer analysis error: {e}")
            
        # INVENTORY ANALYSIS
        print("\n📦 INVENTORY ANALYSIS")
        print("-" * 40)
        
        try:
            query = """
            SELECT 
                COUNT(*) as total_items,
                SUM(Quantity * Price) as inventory_value,
                SUM(CASE WHEN Quantity <= ReorderPoint THEN 1 ELSE 0 END) as below_reorder,
                SUM(CASE WHEN Quantity = 0 THEN 1 ELSE 0 END) as out_of_stock
            FROM Item
            WHERE Price > 0
            """
            
            inv = pd.read_sql(query, conn).iloc[0]
            
            results['metrics']['inventory'] = {
                'total_skus': int(inv['total_items']),
                'total_value': float(inv['inventory_value']) if inv['inventory_value'] else 0,
                'below_reorder': int(inv['below_reorder']),
                'out_of_stock': int(inv['out_of_stock'])
            }
            
            print(f"Total SKUs: {inv['total_items']:,}")
            print(f"Inventory Value: ${inv['inventory_value']:,.0f}" if inv['inventory_value'] else "Inventory Value: $0")
            print(f"Below Reorder Point: {inv['below_reorder']:,}")
            print(f"Out of Stock: {inv['out_of_stock']:,}")
            
            # Inventory recommendations
            if inv['out_of_stock'] > inv['total_items'] * 0.1:
                results['recommendations'].append({
                    'priority': 'HIGH',
                    'area': 'Inventory',
                    'issue': f"{inv['out_of_stock']} items out of stock",
                    'action': 'Review reorder points and supplier lead times'
                })
                
        except Exception as e:
            print(f"Inventory analysis error: {e}")
            
        # RECEIVABLES ANALYSIS
        print("\n💰 RECEIVABLES ANALYSIS")
        print("-" * 40)
        
        try:
            query = """
            SELECT 
                COUNT(*) as ar_count,
                SUM(Balance) as total_ar,
                SUM(CASE WHEN DATEDIFF(day, DueDate, GETDATE()) > 90 THEN Balance ELSE 0 END) as over_90,
                AVG(DATEDIFF(day, DueDate, GETDATE())) as avg_days_overdue
            FROM AccountReceivable
            WHERE Balance > 0
            """
            
            ar = pd.read_sql(query, conn).iloc[0]
            
            if ar['ar_count'] > 0:
                over_90_pct = (ar['over_90'] / ar['total_ar'] * 100) if ar['total_ar'] else 0
                
                results['metrics']['receivables'] = {
                    'total_ar': float(ar['total_ar']) if ar['total_ar'] else 0,
                    'count': int(ar['ar_count']),
                    'over_90_days': float(ar['over_90']) if ar['over_90'] else 0,
                    'over_90_pct': round(over_90_pct, 1),
                    'avg_days_overdue': float(ar['avg_days_overdue']) if ar['avg_days_overdue'] else 0
                }
                
                print(f"Total Receivables: ${ar['total_ar']:,.0f}" if ar['total_ar'] else "Total Receivables: $0")
                print(f"Outstanding Invoices: {ar['ar_count']:,}")
                print(f"Over 90 Days: ${ar['over_90']:,.0f} ({over_90_pct:.1f}%)" if ar['over_90'] else "Over 90 Days: $0")
                print(f"Avg Days Overdue: {ar['avg_days_overdue']:.0f}" if ar['avg_days_overdue'] else "Avg Days Overdue: 0")
                
                # AR recommendations
                if over_90_pct > 20:
                    results['recommendations'].append({
                        'priority': 'CRITICAL',
                        'area': 'Receivables',
                        'issue': f'{over_90_pct:.1f}% of AR over 90 days',
                        'action': 'Immediate collection efforts required'
                    })
                elif ar['avg_days_overdue'] > 45:
                    results['recommendations'].append({
                        'priority': 'MEDIUM',
                        'area': 'Cash Flow',
                        'issue': f'Average {ar["avg_days_overdue"]:.0f} days overdue',
                        'action': 'Tighten credit terms and accelerate collections'
                    })
            else:
                print("No receivables data available")
                
        except Exception as e:
            print(f"Receivables analysis error: {e}")
            
        # SUPPLIER ANALYSIS
        print("\n🚚 SUPPLIER ANALYSIS")
        print("-" * 40)
        
        try:
            query = """
            SELECT 
                COUNT(DISTINCT SupplierID) as supplier_count,
                COUNT(DISTINCT ItemID) as items_ordered
            FROM PurchaseOrder
            WHERE DateCreated >= DATEADD(month, -12, GETDATE())
            """
            
            supp = pd.read_sql(query, conn).iloc[0]
            
            results['metrics']['suppliers'] = {
                'count': int(supp['supplier_count']),
                'items_ordered': int(supp['items_ordered'])
            }
            
            print(f"Active Suppliers: {supp['supplier_count']:,}")
            print(f"Items Ordered (12mo): {supp['items_ordered']:,}")
            
        except Exception as e:
            print(f"Supplier analysis error: {e}")
    
    # CALCULATE OVERALL RISK SCORE
    risk_score = 0
    
    if 'customers' in results['metrics']:
        if results['metrics']['customers']['hhi_index'] > 2000:
            risk_score += 30
        elif results['metrics']['customers']['hhi_index'] > 1500:
            risk_score += 20
        elif results['metrics']['customers']['hhi_index'] > 1000:
            risk_score += 10
            
    if 'receivables' in results['metrics']:
        if results['metrics']['receivables']['over_90_pct'] > 30:
            risk_score += 25
        elif results['metrics']['receivables']['over_90_pct'] > 20:
            risk_score += 15
        elif results['metrics']['receivables']['over_90_pct'] > 10:
            risk_score += 10
            
    results['risk_score'] = risk_score
    
    # PRINT SUMMARY
    print("\n" + "="*60)
    print("EXECUTIVE SUMMARY")
    print("="*60)
    
    risk_level = ('🔴 CRITICAL' if risk_score > 60 else
                  '🟠 HIGH' if risk_score > 40 else
                  '🟡 MEDIUM' if risk_score > 20 else
                  '🟢 LOW')
    
    print(f"\n📊 OVERALL RISK ASSESSMENT: {risk_level} ({risk_score}/100)")
    
    print("\n🎯 TOP RECOMMENDATIONS:")
    
    # Sort recommendations by priority
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    sorted_recs = sorted(results['recommendations'], 
                        key=lambda x: priority_order.get(x['priority'], 4))
    
    for i, rec in enumerate(sorted_recs[:5], 1):
        print(f"\n{i}. [{rec['priority']}] {rec['area']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Action: {rec['action']}")
    
    # Save results
    filename = f"strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Full report saved to: {filename}")
    
    return results

if __name__ == "__main__":
    print("\n" + "="*60)
    print("STRATEGIC BUSINESS ANALYSIS")
    print(datetime.now().strftime("%B %d, %Y %I:%M %p"))
    print("="*60)
    
    try:
        run_analysis()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()