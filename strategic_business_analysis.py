#!/usr/bin/env python3
"""
Strategic Business Analysis Engine
High-End Consulting Report Generator
Generated: 2025-01-09
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

from database_pymssql import SQLServerConnection
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches

# Set professional styling
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class StrategicBusinessAnalyzer:
    def __init__(self):
        self.analysis_date = datetime.now()
        self.results = {}
        self.recommendations = []
        
    def run_chunk_1_customer_analysis(self):
        """Chunk 1: Customer Concentration & Dependency Analysis"""
        print("\n🔍 CHUNK 1: CUSTOMER CONCENTRATION ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as conn:
        
        # 1. Customer Revenue Concentration
        query_revenue = """
        SELECT 
            c.ID as customer_id,
            c.NAME as customer_name,
            c.ADDR1 as address,
            c.CITY,
            c.STATE,
            c.ACTIVE,
            COALESCE(SUM(s.QTY * s.RETAIL), 0) as total_revenue,
            COUNT(DISTINCT s.DTE) as transaction_days,
            COUNT(s.ID) as transaction_count,
            MAX(s.DTE) as last_transaction,
            MIN(s.DTE) as first_transaction
        FROM CUS c
        LEFT JOIN SAL s ON c.ID = s.CID AND s.DTE >= DATEADD(month, -12, GETDATE())
        WHERE c.ACTIVE = 1
        GROUP BY c.ID, c.NAME, c.ADDR1, c.CITY, c.STATE, c.ACTIVE
        ORDER BY total_revenue DESC
        """
        
        df_customers = pd.read_sql(query_revenue, conn)
        total_revenue = df_customers['total_revenue'].sum()
        
        # Calculate concentration metrics
        df_customers['revenue_pct'] = (df_customers['total_revenue'] / total_revenue * 100)
        df_customers['cumulative_pct'] = df_customers['revenue_pct'].cumsum()
        
        # Identify key concentration points
        top_10_pct = df_customers.head(int(len(df_customers) * 0.1))['revenue_pct'].sum()
        top_20_pct = df_customers.head(int(len(df_customers) * 0.2))['revenue_pct'].sum()
        
        # Customer segmentation
        df_customers['segment'] = pd.cut(
            df_customers['revenue_pct'],
            bins=[-np.inf, 0.1, 0.5, 2, 5, np.inf],
            labels=['Dormant', 'Low Value', 'Mid Value', 'High Value', 'Key Account']
        )
        
        # Calculate Herfindahl-Hirschman Index (HHI) for concentration
        hhi = (df_customers['revenue_pct'] ** 2).sum()
        
        # Days since last transaction
        df_customers['days_since_last'] = (datetime.now() - pd.to_datetime(df_customers['last_transaction'])).dt.days
        
        # Customer lifetime
        df_customers['customer_lifetime_days'] = (pd.to_datetime(df_customers['last_transaction']) - 
                                                   pd.to_datetime(df_customers['first_transaction'])).dt.days
        
        # Churn risk scoring
        df_customers['churn_risk_score'] = (
            (df_customers['days_since_last'] / 30) * 0.4 +  # Recency weight
            (1 / (df_customers['transaction_count'] + 1)) * 100 * 0.3 +  # Frequency weight
            (1 / (df_customers['revenue_pct'] + 0.01)) * 0.3  # Monetary weight
        )
        
        self.results['customer_analysis'] = {
            'dataframe': df_customers,
            'total_customers': len(df_customers),
            'active_customers': len(df_customers[df_customers['total_revenue'] > 0]),
            'top_10_concentration': top_10_pct,
            'top_20_concentration': top_20_pct,
            'hhi_index': hhi,
            'segment_distribution': df_customers['segment'].value_counts().to_dict(),
            'avg_customer_lifetime': df_customers['customer_lifetime_days'].mean(),
            'high_risk_customers': len(df_customers[df_customers['churn_risk_score'] > 50])
        }
        
        # Risk assessment
        if hhi > 1500:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Customer Concentration',
                'issue': f'High customer concentration risk (HHI: {hhi:.0f})',
                'recommendation': 'Implement customer diversification strategy. Top 10% of customers control {:.1f}% of revenue.'.format(top_10_pct)
            })
        
        conn.close()
        print(f"✅ Analyzed {len(df_customers)} customers")
        print(f"📊 Top 10% concentration: {top_10_pct:.1f}%")
        print(f"📊 HHI Index: {hhi:.0f}")
        
        return self.results['customer_analysis']
    
    def run_chunk_2_inventory_analysis(self):
        """Chunk 2: Inventory Efficiency & Working Capital"""
        print("\n📦 CHUNK 2: INVENTORY & WORKING CAPITAL ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as conn:
        
        # Inventory metrics query
        query_inventory = """
        SELECT 
            i.INVID,
            i.DES as description,
            i.BRAND,
            i.QOH as quantity_on_hand,
            i.COST as unit_cost,
            i.RETAIL as unit_retail,
            i.QOH * i.COST as inventory_value,
            i.QOH * i.RETAIL as retail_value,
            i.RORD as reorder_point,
            i.DEPT as department,
            COALESCE(s.units_sold_30d, 0) as units_sold_30d,
            COALESCE(s.units_sold_90d, 0) as units_sold_90d,
            COALESCE(s.revenue_30d, 0) as revenue_30d
        FROM INV i
        LEFT JOIN (
            SELECT 
                INVID,
                SUM(CASE WHEN DTE >= DATEADD(day, -30, GETDATE()) THEN QTY ELSE 0 END) as units_sold_30d,
                SUM(CASE WHEN DTE >= DATEADD(day, -90, GETDATE()) THEN QTY ELSE 0 END) as units_sold_90d,
                SUM(CASE WHEN DTE >= DATEADD(day, -30, GETDATE()) THEN QTY * RETAIL ELSE 0 END) as revenue_30d
            FROM SAL
            GROUP BY INVID
        ) s ON i.INVID = s.INVID
        WHERE i.ACTIVE = 1
        """
        
        df_inventory = pd.read_sql(query_inventory, conn)
        
        # Calculate inventory metrics
        df_inventory['gross_margin'] = ((df_inventory['unit_retail'] - df_inventory['unit_cost']) / 
                                        df_inventory['unit_retail'] * 100).fillna(0)
        
        # Days of inventory (DOI)
        df_inventory['daily_velocity'] = df_inventory['units_sold_30d'] / 30
        df_inventory['days_of_inventory'] = np.where(
            df_inventory['daily_velocity'] > 0,
            df_inventory['quantity_on_hand'] / df_inventory['daily_velocity'],
            999  # Flag for non-moving inventory
        )
        
        # Inventory turnover
        df_inventory['turnover_annual'] = np.where(
            df_inventory['quantity_on_hand'] > 0,
            (df_inventory['units_sold_90d'] * 4) / df_inventory['quantity_on_hand'],
            0
        )
        
        # Categorize inventory health
        conditions = [
            (df_inventory['days_of_inventory'] <= 30),
            (df_inventory['days_of_inventory'] <= 60),
            (df_inventory['days_of_inventory'] <= 90),
            (df_inventory['days_of_inventory'] <= 180),
            (df_inventory['days_of_inventory'] > 180)
        ]
        choices = ['Optimal', 'Good', 'Fair', 'Slow', 'Dead Stock']
        df_inventory['inventory_health'] = np.select(conditions, choices, default='Dead Stock')
        
        # Calculate working capital metrics
        total_inventory_value = df_inventory['inventory_value'].sum()
        dead_stock_value = df_inventory[df_inventory['inventory_health'] == 'Dead Stock']['inventory_value'].sum()
        slow_moving_value = df_inventory[df_inventory['inventory_health'].isin(['Slow', 'Dead Stock'])]['inventory_value'].sum()
        
        # ABC Analysis
        df_inventory_sorted = df_inventory.sort_values('revenue_30d', ascending=False)
        df_inventory_sorted['revenue_cumsum'] = df_inventory_sorted['revenue_30d'].cumsum()
        total_revenue = df_inventory_sorted['revenue_30d'].sum()
        
        if total_revenue > 0:
            df_inventory_sorted['revenue_cumsum_pct'] = df_inventory_sorted['revenue_cumsum'] / total_revenue * 100
            df_inventory_sorted['abc_category'] = pd.cut(
                df_inventory_sorted['revenue_cumsum_pct'],
                bins=[0, 80, 95, 100],
                labels=['A', 'B', 'C']
            )
        else:
            df_inventory_sorted['abc_category'] = 'C'
        
        self.results['inventory_analysis'] = {
            'dataframe': df_inventory,
            'total_skus': len(df_inventory),
            'total_inventory_value': total_inventory_value,
            'dead_stock_value': dead_stock_value,
            'dead_stock_pct': (dead_stock_value / total_inventory_value * 100) if total_inventory_value > 0 else 0,
            'slow_moving_value': slow_moving_value,
            'avg_days_inventory': df_inventory[df_inventory['days_of_inventory'] < 999]['days_of_inventory'].mean(),
            'avg_turnover': df_inventory['turnover_annual'].mean(),
            'health_distribution': df_inventory['inventory_health'].value_counts().to_dict(),
            'abc_distribution': df_inventory_sorted['abc_category'].value_counts().to_dict() if total_revenue > 0 else {}
        }
        
        # Working capital recommendations
        if dead_stock_value / total_inventory_value > 0.15:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Inventory Management',
                'issue': f'Excessive dead stock: ${dead_stock_value:,.0f} ({dead_stock_value/total_inventory_value*100:.1f}% of inventory)',
                'recommendation': 'Implement liquidation strategy for dead stock. Consider promotions, bundling, or write-offs.'
            })
        
        conn.close()
        print(f"✅ Analyzed {len(df_inventory)} SKUs")
        print(f"💰 Total inventory value: ${total_inventory_value:,.0f}")
        print(f"⚠️ Dead stock: ${dead_stock_value:,.0f} ({dead_stock_value/total_inventory_value*100:.1f}%)")
        
        return self.results['inventory_analysis']
    
    def run_chunk_3_receivables_analysis(self):
        """Chunk 3: Receivables Health & Cash Flow Impact"""
        print("\n💳 CHUNK 3: RECEIVABLES & CASH FLOW ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as conn:
        
        # Receivables aging query
        query_receivables = """
        SELECT 
            c.ID as customer_id,
            c.NAME as customer_name,
            c.CRLIMIT as credit_limit,
            ar.DOCNUM as document_number,
            ar.DTE as transaction_date,
            ar.AMOUNT as amount,
            ar.PAYAMT as paid_amount,
            ar.AMOUNT - ar.PAYAMT as balance,
            ar.PDTE as payment_date,
            ar.COMMENT,
            DATEDIFF(day, ar.DTE, GETDATE()) as days_outstanding
        FROM AR ar
        JOIN CUS c ON ar.CID = c.ID
        WHERE ar.AMOUNT - ar.PAYAMT != 0
        ORDER BY days_outstanding DESC
        """
        
        df_receivables = pd.read_sql(query_receivables, conn)
        
        # Calculate aging buckets
        conditions = [
            (df_receivables['days_outstanding'] <= 30),
            (df_receivables['days_outstanding'] <= 60),
            (df_receivables['days_outstanding'] <= 90),
            (df_receivables['days_outstanding'] <= 120),
            (df_receivables['days_outstanding'] > 120)
        ]
        choices = ['Current', '31-60 days', '61-90 days', '91-120 days', 'Over 120 days']
        df_receivables['aging_bucket'] = np.select(conditions, choices, default='Over 120 days')
        
        # Calculate DSO (Days Sales Outstanding)
        query_sales_recent = """
        SELECT SUM(QTY * RETAIL) as total_sales
        FROM SAL
        WHERE DTE >= DATEADD(day, -90, GETDATE())
        """
        
        recent_sales = pd.read_sql(query_sales_recent, conn).iloc[0]['total_sales']
        daily_sales = recent_sales / 90 if recent_sales else 0
        total_receivables = df_receivables['balance'].sum()
        dso = total_receivables / daily_sales if daily_sales > 0 else 0
        
        # Customer credit utilization
        customer_receivables = df_receivables.groupby(['customer_id', 'customer_name', 'credit_limit']).agg({
            'balance': 'sum',
            'days_outstanding': 'mean'
        }).reset_index()
        
        customer_receivables['credit_utilization'] = np.where(
            customer_receivables['credit_limit'] > 0,
            customer_receivables['balance'] / customer_receivables['credit_limit'] * 100,
            0
        )
        
        # Risk scoring for receivables
        df_receivables['collection_risk'] = np.select(
            [
                df_receivables['days_outstanding'] <= 30,
                df_receivables['days_outstanding'] <= 60,
                df_receivables['days_outstanding'] <= 90,
                df_receivables['days_outstanding'] > 90
            ],
            ['Low', 'Medium', 'High', 'Critical'],
            default='Critical'
        )
        
        # Expected loss calculation (simplified)
        risk_weights = {'Low': 0.01, 'Medium': 0.05, 'High': 0.15, 'Critical': 0.30}
        df_receivables['expected_loss'] = df_receivables.apply(
            lambda x: x['balance'] * risk_weights.get(x['collection_risk'], 0.30), axis=1
        )
        
        total_expected_loss = df_receivables['expected_loss'].sum()
        
        # Cash flow impact analysis
        aging_summary = df_receivables.groupby('aging_bucket')['balance'].sum().to_dict()
        
        self.results['receivables_analysis'] = {
            'dataframe': df_receivables,
            'total_receivables': total_receivables,
            'dso': dso,
            'aging_summary': aging_summary,
            'over_90_days': df_receivables[df_receivables['days_outstanding'] > 90]['balance'].sum(),
            'over_90_pct': (df_receivables[df_receivables['days_outstanding'] > 90]['balance'].sum() / 
                           total_receivables * 100) if total_receivables > 0 else 0,
            'expected_loss': total_expected_loss,
            'high_risk_accounts': len(customer_receivables[customer_receivables['credit_utilization'] > 100]),
            'avg_days_outstanding': df_receivables['days_outstanding'].mean()
        }
        
        # Cash flow recommendations
        if dso > 45:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Receivables Management',
                'issue': f'High DSO of {dso:.0f} days impacting cash flow',
                'recommendation': 'Implement aggressive collection strategy. Consider early payment discounts and stricter credit terms.'
            })
        
        if self.results['receivables_analysis']['over_90_pct'] > 20:
            self.recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Bad Debt Risk',
                'issue': f"{self.results['receivables_analysis']['over_90_pct']:.1f}% of receivables over 90 days",
                'recommendation': 'Immediate action required on aged receivables. Consider write-offs and legal action where appropriate.'
            })
        
        conn.close()
        print(f"✅ Analyzed {len(df_receivables)} outstanding invoices")
        print(f"💰 Total receivables: ${total_receivables:,.0f}")
        print(f"📊 DSO: {dso:.0f} days")
        print(f"⚠️ Over 90 days: ${self.results['receivables_analysis']['over_90_days']:,.0f}")
        
        return self.results['receivables_analysis']
    
    def run_chunk_4_supplier_analysis(self):
        """Chunk 4: Supplier Dependencies & Supply Chain Risks"""
        print("\n🚚 CHUNK 4: SUPPLIER & SUPPLY CHAIN ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as conn:
        
        # Supplier concentration query
        query_suppliers = """
        SELECT 
            v.ID as vendor_id,
            v.NAME as vendor_name,
            v.ADDR1 as address,
            v.CITY,
            v.STATE,
            COUNT(DISTINCT p.INVID) as sku_count,
            SUM(p.QTY * p.COST) as total_purchases,
            COUNT(DISTINCT p.DOCNUM) as po_count,
            AVG(DATEDIFF(day, p.ODTE, p.DTE)) as avg_lead_time,
            MAX(p.DTE) as last_purchase,
            MIN(p.DTE) as first_purchase
        FROM VEN v
        LEFT JOIN PUR p ON v.ID = p.VID AND p.DTE >= DATEADD(month, -12, GETDATE())
        WHERE v.ACTIVE = 1
        GROUP BY v.ID, v.NAME, v.ADDR1, v.CITY, v.STATE
        HAVING SUM(p.QTY * p.COST) > 0
        ORDER BY total_purchases DESC
        """
        
        df_suppliers = pd.read_sql(query_suppliers, conn)
        total_purchases = df_suppliers['total_purchases'].sum()
        
        # Calculate supplier concentration
        df_suppliers['purchase_pct'] = (df_suppliers['total_purchases'] / total_purchases * 100)
        df_suppliers['cumulative_pct'] = df_suppliers['purchase_pct'].cumsum()
        
        # Supplier risk scoring
        df_suppliers['days_since_last'] = (datetime.now() - pd.to_datetime(df_suppliers['last_purchase'])).dt.days
        
        # Categorize suppliers
        conditions = [
            (df_suppliers['purchase_pct'] >= 10),
            (df_suppliers['purchase_pct'] >= 5),
            (df_suppliers['purchase_pct'] >= 1),
            (df_suppliers['purchase_pct'] < 1)
        ]
        choices = ['Critical', 'Major', 'Standard', 'Minor']
        df_suppliers['supplier_tier'] = np.select(conditions, choices, default='Minor')
        
        # Supply chain risk factors
        df_suppliers['supply_risk_score'] = (
            (df_suppliers['days_since_last'] / 30) * 0.3 +  # Recency
            (1 / (df_suppliers['po_count'] + 1)) * 100 * 0.2 +  # Frequency
            (df_suppliers['purchase_pct'] * 0.5)  # Dependency
        )
        
        # Product category analysis by supplier
        query_category_supplier = """
        SELECT 
            v.NAME as vendor_name,
            i.DEPT as department,
            COUNT(DISTINCT i.INVID) as sku_count,
            SUM(p.QTY * p.COST) as category_purchases
        FROM PUR p
        JOIN VEN v ON p.VID = v.ID
        JOIN INV i ON p.INVID = i.INVID
        WHERE p.DTE >= DATEADD(month, -12, GETDATE())
        GROUP BY v.NAME, i.DEPT
        """
        
        df_category_supplier = pd.read_sql(query_category_supplier, conn)
        
        # Identify single-source products
        query_single_source = """
        SELECT 
            i.INVID,
            i.DES as product,
            i.DEPT,
            COUNT(DISTINCT p.VID) as supplier_count,
            MAX(v.NAME) as primary_supplier
        FROM INV i
        LEFT JOIN PUR p ON i.INVID = p.INVID AND p.DTE >= DATEADD(month, -6, GETDATE())
        LEFT JOIN VEN v ON p.VID = v.ID
        WHERE i.ACTIVE = 1
        GROUP BY i.INVID, i.DES, i.DEPT
        HAVING COUNT(DISTINCT p.VID) = 1
        """
        
        df_single_source = pd.read_sql(query_single_source, conn)
        
        # Calculate supply chain metrics
        top_5_concentration = df_suppliers.head(5)['purchase_pct'].sum()
        supplier_hhi = (df_suppliers['purchase_pct'] ** 2).sum()
        
        self.results['supplier_analysis'] = {
            'dataframe': df_suppliers,
            'total_suppliers': len(df_suppliers),
            'total_purchases': total_purchases,
            'top_5_concentration': top_5_concentration,
            'supplier_hhi': supplier_hhi,
            'critical_suppliers': len(df_suppliers[df_suppliers['supplier_tier'] == 'Critical']),
            'single_source_products': len(df_single_source),
            'avg_lead_time': df_suppliers['avg_lead_time'].mean(),
            'tier_distribution': df_suppliers['supplier_tier'].value_counts().to_dict(),
            'high_risk_suppliers': len(df_suppliers[df_suppliers['supply_risk_score'] > 50])
        }
        
        # Supply chain recommendations
        if supplier_hhi > 2000:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Supplier Concentration',
                'issue': f'High supplier concentration (HHI: {supplier_hhi:.0f})',
                'recommendation': f'Diversify supplier base. Top 5 suppliers control {top_5_concentration:.1f}% of purchases.'
            })
        
        if len(df_single_source) > 100:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Supply Chain Risk',
                'issue': f'{len(df_single_source)} products have single-source suppliers',
                'recommendation': 'Identify alternative suppliers for critical single-source products to reduce supply disruption risk.'
            })
        
        conn.close()
        print(f"✅ Analyzed {len(df_suppliers)} suppliers")
        print(f"💰 Total purchases: ${total_purchases:,.0f}")
        print(f"📊 Top 5 concentration: {top_5_concentration:.1f}%")
        print(f"⚠️ Single-source products: {len(df_single_source)}")
        
        return self.results['supplier_analysis']
    
    def run_chunk_5_financial_ratios(self):
        """Chunk 5: Financial Ratios & KPI Calculations"""
        print("\n📈 CHUNK 5: FINANCIAL RATIOS & KEY METRICS")
        print("=" * 60)
        
        # Calculate comprehensive financial ratios
        ratios = {}
        
        # Liquidity Ratios
        if 'inventory_analysis' in self.results:
            inventory_value = self.results['inventory_analysis']['total_inventory_value']
            
        if 'receivables_analysis' in self.results:
            receivables = self.results['receivables_analysis']['total_receivables']
            dso = self.results['receivables_analysis']['dso']
            
        # Efficiency Ratios
        if 'inventory_analysis' in self.results:
            ratios['inventory_turnover'] = self.results['inventory_analysis']['avg_turnover']
            ratios['days_inventory_outstanding'] = self.results['inventory_analysis']['avg_days_inventory']
            
        if 'receivables_analysis' in self.results:
            ratios['days_sales_outstanding'] = dso
            ratios['receivables_to_sales'] = self.results['receivables_analysis']['avg_days_outstanding']
            
        # Risk Ratios
        if 'customer_analysis' in self.results:
            ratios['customer_concentration_hhi'] = self.results['customer_analysis']['hhi_index']
            ratios['top_10_customer_concentration'] = self.results['customer_analysis']['top_10_concentration']
            
        if 'supplier_analysis' in self.results:
            ratios['supplier_concentration_hhi'] = self.results['supplier_analysis']['supplier_hhi']
            ratios['top_5_supplier_concentration'] = self.results['supplier_analysis']['top_5_concentration']
            
        # Working Capital Metrics
        ratios['cash_conversion_cycle'] = (
            ratios.get('days_inventory_outstanding', 0) + 
            ratios.get('days_sales_outstanding', 0)
        )
        
        # Industry Benchmarks (retail/wholesale)
        benchmarks = {
            'inventory_turnover': {'poor': 2, 'fair': 4, 'good': 6, 'excellent': 10},
            'days_sales_outstanding': {'excellent': 30, 'good': 45, 'fair': 60, 'poor': 90},
            'customer_concentration_hhi': {'excellent': 500, 'good': 1000, 'fair': 1500, 'poor': 2500},
            'cash_conversion_cycle': {'excellent': 30, 'good': 60, 'fair': 90, 'poor': 120}
        }
        
        # Score each ratio against benchmarks
        ratio_scores = {}
        for ratio_name, value in ratios.items():
            if ratio_name in benchmarks:
                bench = benchmarks[ratio_name]
                if 'poor' in bench and value > bench['poor']:
                    ratio_scores[ratio_name] = 'Poor'
                elif 'fair' in bench and value > bench['fair']:
                    ratio_scores[ratio_name] = 'Fair'
                elif 'good' in bench and value > bench['good']:
                    ratio_scores[ratio_name] = 'Good'
                else:
                    ratio_scores[ratio_name] = 'Excellent'
        
        self.results['financial_ratios'] = {
            'ratios': ratios,
            'benchmarks': benchmarks,
            'scores': ratio_scores
        }
        
        print(f"✅ Calculated {len(ratios)} financial ratios")
        for ratio, value in ratios.items():
            if isinstance(value, (int, float)):
                print(f"📊 {ratio}: {value:.2f}")
        
        return self.results['financial_ratios']

    def save_results(self):
        """Save all analysis results to JSON"""
        output = {
            'analysis_date': self.analysis_date.isoformat(),
            'executive_summary': {},
            'recommendations': self.recommendations
        }
        
        # Build executive summary
        if 'customer_analysis' in self.results:
            output['executive_summary']['customer_metrics'] = {
                'total_customers': self.results['customer_analysis']['total_customers'],
                'active_customers': self.results['customer_analysis']['active_customers'],
                'top_10_concentration': self.results['customer_analysis']['top_10_concentration'],
                'hhi_index': self.results['customer_analysis']['hhi_index']
            }
            
        if 'inventory_analysis' in self.results:
            output['executive_summary']['inventory_metrics'] = {
                'total_skus': self.results['inventory_analysis']['total_skus'],
                'inventory_value': self.results['inventory_analysis']['total_inventory_value'],
                'dead_stock_pct': self.results['inventory_analysis']['dead_stock_pct'],
                'avg_turnover': self.results['inventory_analysis']['avg_turnover']
            }
            
        if 'receivables_analysis' in self.results:
            output['executive_summary']['receivables_metrics'] = {
                'total_receivables': self.results['receivables_analysis']['total_receivables'],
                'dso': self.results['receivables_analysis']['dso'],
                'over_90_days_pct': self.results['receivables_analysis']['over_90_pct']
            }
            
        if 'supplier_analysis' in self.results:
            output['executive_summary']['supplier_metrics'] = {
                'total_suppliers': self.results['supplier_analysis']['total_suppliers'],
                'top_5_concentration': self.results['supplier_analysis']['top_5_concentration'],
                'single_source_products': self.results['supplier_analysis']['single_source_products']
            }
            
        if 'financial_ratios' in self.results:
            output['executive_summary']['key_ratios'] = self.results['financial_ratios']['ratios']
            
        # Save to JSON
        filename = f"strategic_analysis_{self.analysis_date.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to {filename}")
        return filename

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" STRATEGIC BUSINESS ANALYSIS - HIGH-END CONSULTING REPORT")
    print("="*80)
    
    analyzer = StrategicBusinessAnalyzer()
    
    try:
        # Run analysis chunks
        analyzer.run_chunk_1_customer_analysis()
        analyzer.run_chunk_2_inventory_analysis()
        analyzer.run_chunk_3_receivables_analysis()
        analyzer.run_chunk_4_supplier_analysis()
        analyzer.run_chunk_5_financial_ratios()
        
        # Save results
        output_file = analyzer.save_results()
        
        print("\n" + "="*80)
        print(" ANALYSIS COMPLETE")
        print("="*80)
        
        # Print top recommendations
        print("\n🎯 TOP STRATEGIC RECOMMENDATIONS:")
        print("-" * 40)
        for i, rec in enumerate(analyzer.recommendations[:5], 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Action: {rec['recommendation']}")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()