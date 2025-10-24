#!/usr/bin/env python3
"""
Executive Strategic Business Report
High-End Consulting Analysis with Visualizations
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Professional styling
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72', 
    'success': '#73AB84',
    'warning': '#F18F01',
    'danger': '#C73E1D',
    'info': '#6C91BF'
}

class ExecutiveAnalyzer:
    def __init__(self):
        self.results = {}
        self.recommendations = []
        
    def analyze_customers(self):
        """Customer concentration and dependency analysis"""
        print("\n📊 CUSTOMER CONCENTRATION ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as db_conn:
            # Get customer revenue data
            query = """
            SELECT 
                c.ID as customer_id,
                c.CustomerName as customer_name,
                c.City,
                c.State,
                COALESCE(SUM(te.Price * te.Quantity), 0) as total_revenue,
                COUNT(DISTINCT t.Time) as transaction_count,
                MAX(t.Time) as last_transaction
            FROM Customer c
            LEFT JOIN [Transaction] t ON c.ID = t.CustomerID 
                AND t.Time >= DATEADD(month, -12, GETDATE())
            LEFT JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
            WHERE c.IsActive = 1
            GROUP BY c.ID, c.CustomerName, c.City, c.State
            HAVING SUM(te.Price * te.Quantity) > 0
            ORDER BY total_revenue DESC
            """
            
            df = pd.read_sql(query, db_conn.connection)
            
        if len(df) == 0:
            print("⚠️ No customer data found")
            return {}
            
        # Calculate concentration metrics
        total_revenue = df['total_revenue'].sum()
        df['revenue_pct'] = (df['total_revenue'] / total_revenue * 100)
        df['cumulative_pct'] = df['revenue_pct'].cumsum()
        
        # Key metrics
        top_10_count = max(1, int(len(df) * 0.1))
        top_10_pct = df.head(top_10_count)['revenue_pct'].sum()
        top_20_count = max(1, int(len(df) * 0.2)) 
        top_20_pct = df.head(top_20_count)['revenue_pct'].sum()
        
        # HHI Index (market concentration)
        hhi = (df['revenue_pct'] ** 2).sum()
        
        # Customer segmentation
        df['segment'] = pd.cut(
            df['revenue_pct'],
            bins=[-np.inf, 0.1, 0.5, 2, 5, np.inf],
            labels=['Dormant', 'Low', 'Mid', 'High', 'Key']
        )
        
        self.results['customers'] = {
            'dataframe': df,
            'total_customers': len(df),
            'active_customers': len(df[df['total_revenue'] > 0]),
            'top_10_concentration': round(top_10_pct, 1),
            'top_20_concentration': round(top_20_pct, 1),
            'hhi_index': round(hhi, 0),
            'segment_distribution': df['segment'].value_counts().to_dict(),
            'top_customers': df.head(10)[['customer_name', 'revenue_pct']].to_dict('records')
        }
        
        # Risk assessment
        if hhi > 1500:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Customer Risk',
                'issue': f'High concentration (HHI: {hhi:.0f})',
                'action': f'Diversify base - Top 10% control {top_10_pct:.1f}% of revenue'
            })
            
        print(f"✅ Analyzed {len(df)} customers")
        print(f"   Top 10% concentration: {top_10_pct:.1f}%")
        print(f"   HHI Index: {hhi:.0f}")
        
        return self.results['customers']
        
    def analyze_inventory(self):
        """Inventory efficiency and working capital analysis"""
        print("\n📦 INVENTORY & WORKING CAPITAL ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as db_conn:
            query = """
            SELECT 
                i.ID as item_id,
                i.Description,
                i.Quantity as on_hand,
                i.Price as unit_cost,
                i.Quantity * i.Price as inventory_value,
                COALESCE(sold.qty_sold_30d, 0) as units_sold_30d,
                COALESCE(sold.qty_sold_90d, 0) as units_sold_90d
            FROM Item i
            LEFT JOIN (
                SELECT 
                    te.ItemID,
                    SUM(CASE WHEN t.Time >= DATEADD(day, -30, GETDATE()) 
                        THEN te.Quantity ELSE 0 END) as qty_sold_30d,
                    SUM(CASE WHEN t.Time >= DATEADD(day, -90, GETDATE())
                        THEN te.Quantity ELSE 0 END) as qty_sold_90d
                FROM TransactionEntry te
                JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.Time >= DATEADD(day, -90, GETDATE())
                GROUP BY te.ItemID
            ) sold ON i.ID = sold.ItemID
            WHERE i.Quantity > 0
            """
            
            df = pd.read_sql(query, db_conn.connection)
            
        if len(df) == 0:
            print("⚠️ No inventory data found")
            return {}
            
        # Calculate inventory metrics
        df['daily_velocity'] = df['units_sold_30d'] / 30
        df['days_of_inventory'] = np.where(
            df['daily_velocity'] > 0,
            df['on_hand'] / df['daily_velocity'],
            999
        )
        
        # Inventory health categories
        conditions = [
            (df['days_of_inventory'] <= 30),
            (df['days_of_inventory'] <= 60),
            (df['days_of_inventory'] <= 90),
            (df['days_of_inventory'] > 90)
        ]
        choices = ['Optimal', 'Good', 'Slow', 'Dead']
        df['health'] = np.select(conditions, choices, default='Dead')
        
        total_value = df['inventory_value'].sum()
        dead_value = df[df['health'] == 'Dead']['inventory_value'].sum()
        
        # Turnover calculation
        df['annual_turnover'] = (df['units_sold_90d'] * 4) / df['on_hand'].replace(0, 1)
        
        self.results['inventory'] = {
            'dataframe': df,
            'total_skus': len(df),
            'total_value': round(total_value, 0),
            'dead_stock_value': round(dead_value, 0),
            'dead_stock_pct': round((dead_value/total_value*100) if total_value > 0 else 0, 1),
            'avg_days_inventory': round(df[df['days_of_inventory'] < 999]['days_of_inventory'].mean(), 0),
            'avg_turnover': round(df['annual_turnover'].mean(), 1),
            'health_distribution': df['health'].value_counts().to_dict()
        }
        
        # Inventory recommendations
        if self.results['inventory']['dead_stock_pct'] > 15:
            self.recommendations.append({
                'priority': 'HIGH',
                'category': 'Inventory',
                'issue': f"{self.results['inventory']['dead_stock_pct']}% dead stock",
                'action': 'Liquidate slow-moving inventory, improve forecasting'
            })
            
        print(f"✅ Analyzed {len(df)} SKUs")
        print(f"   Total value: ${total_value:,.0f}")
        print(f"   Dead stock: {self.results['inventory']['dead_stock_pct']}%")
        
        return self.results['inventory']
        
    def analyze_receivables(self):
        """Receivables and cash flow analysis"""
        print("\n💰 RECEIVABLES & CASH FLOW ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as db_conn:
            # Get AR aging
            query_ar = """
            SELECT 
                c.CustomerName,
                ar.AccountReceivableID,
                ar.Amount,
                ar.Balance,
                ar.DueDate,
                DATEDIFF(day, ar.DueDate, GETDATE()) as days_overdue
            FROM AccountReceivable ar
            JOIN Customer c ON ar.CustomerID = c.ID
            WHERE ar.Balance > 0
            """
            
            df_ar = pd.read_sql(query_ar, db_conn.connection)
            
            # Get recent sales for DSO calculation
            query_sales = """
            SELECT SUM(te.Price * te.Quantity) as total_sales
            FROM TransactionEntry te
            JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            WHERE t.Time >= DATEADD(day, -90, GETDATE())
            """
            
            sales_result = pd.read_sql(query_sales, db_conn.connection)
            recent_sales = sales_result.iloc[0]['total_sales'] if len(sales_result) > 0 else 0
            
        if len(df_ar) == 0:
            print("⚠️ No receivables data found")
            return {}
            
        # Aging buckets
        conditions = [
            (df_ar['days_overdue'] <= 0),
            (df_ar['days_overdue'] <= 30),
            (df_ar['days_overdue'] <= 60),
            (df_ar['days_overdue'] <= 90),
            (df_ar['days_overdue'] > 90)
        ]
        choices = ['Current', '1-30 days', '31-60 days', '61-90 days', 'Over 90']
        df_ar['aging_bucket'] = np.select(conditions, choices, default='Over 90')
        
        total_ar = df_ar['Balance'].sum()
        over_90 = df_ar[df_ar['days_overdue'] > 90]['Balance'].sum()
        
        # DSO calculation
        daily_sales = recent_sales / 90 if recent_sales else 0
        dso = total_ar / daily_sales if daily_sales > 0 else 0
        
        self.results['receivables'] = {
            'dataframe': df_ar,
            'total_receivables': round(total_ar, 0),
            'dso': round(dso, 0),
            'over_90_days': round(over_90, 0),
            'over_90_pct': round((over_90/total_ar*100) if total_ar > 0 else 0, 1),
            'aging_summary': df_ar.groupby('aging_bucket')['Balance'].sum().to_dict()
        }
        
        # Cash flow recommendations
        if dso > 45:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Cash Flow',
                'issue': f'DSO of {dso:.0f} days',
                'action': 'Tighten credit terms, accelerate collections'
            })
            
        if self.results['receivables']['over_90_pct'] > 20:
            self.recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Bad Debt',
                'issue': f"{self.results['receivables']['over_90_pct']}% over 90 days",
                'action': 'Immediate collection efforts, consider write-offs'
            })
            
        print(f"✅ Total receivables: ${total_ar:,.0f}")
        print(f"   DSO: {dso:.0f} days")
        print(f"   Over 90 days: {self.results['receivables']['over_90_pct']}%")
        
        return self.results['receivables']
        
    def analyze_suppliers(self):
        """Supplier dependency analysis"""
        print("\n🚚 SUPPLIER DEPENDENCY ANALYSIS")
        print("=" * 60)
        
        with SQLServerConnection() as db_conn:
            query = """
            SELECT 
                s.SupplierName,
                COUNT(DISTINCT po.ItemID) as sku_count,
                SUM(po.QuantityOrdered * po.Cost) as total_purchases
            FROM PurchaseOrder po
            JOIN Supplier s ON po.SupplierID = s.ID
            WHERE po.DateCreated >= DATEADD(month, -12, GETDATE())
            GROUP BY s.SupplierName
            ORDER BY total_purchases DESC
            """
            
            df = pd.read_sql(query, db_conn.connection)
            
        if len(df) == 0:
            print("⚠️ No supplier data found")
            return {}
            
        total_purchases = df['total_purchases'].sum()
        df['purchase_pct'] = (df['total_purchases'] / total_purchases * 100)
        
        top_5_pct = df.head(5)['purchase_pct'].sum()
        supplier_hhi = (df['purchase_pct'] ** 2).sum()
        
        self.results['suppliers'] = {
            'dataframe': df,
            'total_suppliers': len(df),
            'total_purchases': round(total_purchases, 0),
            'top_5_concentration': round(top_5_pct, 1),
            'supplier_hhi': round(supplier_hhi, 0),
            'top_suppliers': df.head(5)[['SupplierName', 'purchase_pct']].to_dict('records')
        }
        
        # Supply chain recommendations
        if supplier_hhi > 2000:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Supply Chain',
                'issue': f'High supplier concentration (HHI: {supplier_hhi:.0f})',
                'action': 'Diversify supplier base for critical items'
            })
            
        print(f"✅ Analyzed {len(df)} suppliers")
        print(f"   Top 5 concentration: {top_5_pct:.1f}%")
        
        return self.results['suppliers']
        
    def calculate_ratios(self):
        """Calculate key financial ratios"""
        print("\n📈 CALCULATING FINANCIAL RATIOS")
        print("=" * 60)
        
        ratios = {}
        
        # Inventory metrics
        if 'inventory' in self.results:
            ratios['inventory_turnover'] = self.results['inventory']['avg_turnover']
            ratios['days_inventory'] = self.results['inventory']['avg_days_inventory']
            ratios['dead_stock_pct'] = self.results['inventory']['dead_stock_pct']
            
        # Receivables metrics
        if 'receivables' in self.results:
            ratios['dso'] = self.results['receivables']['dso']
            ratios['bad_debt_risk'] = self.results['receivables']['over_90_pct']
            
        # Customer metrics
        if 'customers' in self.results:
            ratios['customer_hhi'] = self.results['customers']['hhi_index']
            ratios['customer_concentration'] = self.results['customers']['top_10_concentration']
            
        # Supplier metrics
        if 'suppliers' in self.results:
            ratios['supplier_hhi'] = self.results['suppliers']['supplier_hhi']
            ratios['supplier_concentration'] = self.results['suppliers']['top_5_concentration']
            
        # Cash conversion cycle
        ratios['cash_conversion_cycle'] = (
            ratios.get('days_inventory', 0) + 
            ratios.get('dso', 0)
        )
        
        # Risk scores
        ratios['overall_risk'] = self._calculate_risk_score(ratios)
        
        self.results['ratios'] = ratios
        
        print(f"✅ Calculated {len(ratios)} key ratios")
        
        return ratios
        
    def _calculate_risk_score(self, ratios):
        """Calculate overall business risk score (0-100)"""
        score = 0
        
        # Customer concentration risk (0-30 points)
        if ratios.get('customer_hhi', 0) > 2500:
            score += 30
        elif ratios.get('customer_hhi', 0) > 1500:
            score += 20
        elif ratios.get('customer_hhi', 0) > 1000:
            score += 10
            
        # Inventory risk (0-25 points)
        if ratios.get('dead_stock_pct', 0) > 25:
            score += 25
        elif ratios.get('dead_stock_pct', 0) > 15:
            score += 15
        elif ratios.get('dead_stock_pct', 0) > 10:
            score += 10
            
        # Receivables risk (0-25 points)
        if ratios.get('bad_debt_risk', 0) > 30:
            score += 25
        elif ratios.get('bad_debt_risk', 0) > 20:
            score += 15
        elif ratios.get('bad_debt_risk', 0) > 10:
            score += 10
            
        # Cash flow risk (0-20 points)
        if ratios.get('cash_conversion_cycle', 0) > 120:
            score += 20
        elif ratios.get('cash_conversion_cycle', 0) > 90:
            score += 15
        elif ratios.get('cash_conversion_cycle', 0) > 60:
            score += 10
            
        return score
        
    def generate_visualizations(self):
        """Generate executive dashboard visualizations"""
        print("\n📊 GENERATING VISUALIZATIONS")
        print("=" * 60)
        
        fig = plt.figure(figsize=(20, 12))
        
        # Title
        fig.suptitle('EXECUTIVE STRATEGIC DASHBOARD', fontsize=18, fontweight='bold')
        fig.text(0.5, 0.94, datetime.now().strftime('%B %d, %Y'), ha='center', fontsize=12)
        
        # Create subplots
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.25, top=0.92, bottom=0.05)
        
        # 1. Customer Concentration
        ax1 = fig.add_subplot(gs[0, 0])
        if 'customers' in self.results:
            df = self.results['customers']['dataframe'].head(20)
            ax1.bar(range(len(df)), df['revenue_pct'], color=COLORS['primary'], alpha=0.7)
            ax1.plot(range(len(df)), df['cumulative_pct'], 
                    color=COLORS['danger'], linewidth=2, marker='o')
            ax1.set_xlabel('Customer Rank')
            ax1.set_ylabel('Revenue %')
            ax1.set_title('Customer Concentration')
            ax1.grid(True, alpha=0.3)
            
        # 2. Inventory Health
        ax2 = fig.add_subplot(gs[0, 1])
        if 'inventory' in self.results:
            health = self.results['inventory']['health_distribution']
            colors = [COLORS['success'], COLORS['info'], COLORS['warning'], COLORS['danger']]
            ax2.pie(health.values(), labels=health.keys(), colors=colors[:len(health)],
                   autopct='%1.1f%%', startangle=90)
            ax2.set_title('Inventory Health')
            
        # 3. Receivables Aging
        ax3 = fig.add_subplot(gs[0, 2])
        if 'receivables' in self.results:
            aging = self.results['receivables']['aging_summary']
            ax3.bar(aging.keys(), aging.values(), 
                   color=[COLORS['success'], COLORS['info'], COLORS['warning'], 
                         COLORS['warning'], COLORS['danger']][:len(aging)])
            ax3.set_xlabel('Age')
            ax3.set_ylabel('Amount ($)')
            ax3.set_title('Receivables Aging')
            ax3.tick_params(axis='x', rotation=45)
            
        # 4. Risk Matrix
        ax4 = fig.add_subplot(gs[1, :])
        risk_categories = ['Customer\nConcentration', 'Inventory\nEfficiency', 
                          'Receivables\nHealth', 'Cash Flow']
        risk_scores = []
        
        if 'ratios' in self.results:
            ratios = self.results['ratios']
            risk_scores = [
                min(100, ratios.get('customer_hhi', 0) / 25),
                ratios.get('dead_stock_pct', 0),
                ratios.get('bad_debt_risk', 0),
                min(100, ratios.get('cash_conversion_cycle', 0) / 1.2)
            ]
            
            colors_risk = []
            for score in risk_scores:
                if score > 50:
                    colors_risk.append(COLORS['danger'])
                elif score > 30:
                    colors_risk.append(COLORS['warning'])
                else:
                    colors_risk.append(COLORS['success'])
                    
            bars = ax4.bar(risk_categories, risk_scores, color=colors_risk, alpha=0.7)
            ax4.set_ylabel('Risk Level (%)')
            ax4.set_title('Risk Assessment Dashboard')
            ax4.axhline(y=30, color='gray', linestyle='--', alpha=0.5, label='Low Risk')
            ax4.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='Medium Risk')
            ax4.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, score in zip(bars, risk_scores):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{score:.0f}%', ha='center', va='bottom')
                        
        # 5. Key Metrics Table
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('tight')
        ax5.axis('off')
        
        if 'ratios' in self.results:
            metrics_data = [
                ['Metric', 'Value', 'Status'],
                ['Customer HHI', f"{ratios.get('customer_hhi', 0):.0f}", 
                 '⚠️ High' if ratios.get('customer_hhi', 0) > 1500 else '✅ OK'],
                ['Inventory Turnover', f"{ratios.get('inventory_turnover', 0):.1f}x", 
                 '⚠️ Low' if ratios.get('inventory_turnover', 0) < 4 else '✅ Good'],
                ['DSO', f"{ratios.get('dso', 0):.0f} days",
                 '⚠️ High' if ratios.get('dso', 0) > 45 else '✅ Good'],
                ['Dead Stock', f"{ratios.get('dead_stock_pct', 0):.1f}%",
                 '⚠️ High' if ratios.get('dead_stock_pct', 0) > 15 else '✅ OK'],
                ['Cash Cycle', f"{ratios.get('cash_conversion_cycle', 0):.0f} days",
                 '⚠️ Long' if ratios.get('cash_conversion_cycle', 0) > 90 else '✅ OK'],
                ['Overall Risk', f"{ratios.get('overall_risk', 0):.0f}/100",
                 '🔴 Critical' if ratios.get('overall_risk', 0) > 70 else 
                 '⚠️ High' if ratios.get('overall_risk', 0) > 50 else
                 '🟡 Medium' if ratios.get('overall_risk', 0) > 30 else '✅ Low']
            ]
            
            table = ax5.table(cellText=metrics_data, loc='center', cellLoc='center')
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.5)
            
            # Style header row
            for i in range(3):
                table[(0, i)].set_facecolor('#E0E0E0')
                table[(0, i)].set_text_props(weight='bold')
                
        # Save figure
        filename = f"executive_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✅ Dashboard saved to {filename}")
        
        return filename
        
    def generate_report(self):
        """Generate comprehensive JSON report"""
        output = {
            'analysis_date': datetime.now().isoformat(),
            'executive_summary': {
                'overall_risk_score': self.results.get('ratios', {}).get('overall_risk', 0),
                'total_recommendations': len(self.recommendations),
                'critical_issues': len([r for r in self.recommendations if r['priority'] == 'CRITICAL'])
            },
            'key_metrics': {},
            'recommendations': sorted(self.recommendations, 
                                    key=lambda x: {'CRITICAL': 0, 'HIGH': 1, 
                                                  'MEDIUM': 2, 'LOW': 3}.get(x['priority'], 4)),
            'detailed_results': {}
        }
        
        # Add key metrics
        if 'customers' in self.results:
            output['key_metrics']['customers'] = {
                'total': self.results['customers']['total_customers'],
                'concentration': f"{self.results['customers']['top_10_concentration']}%",
                'hhi': self.results['customers']['hhi_index']
            }
            
        if 'inventory' in self.results:
            output['key_metrics']['inventory'] = {
                'value': f"${self.results['inventory']['total_value']:,.0f}",
                'dead_stock': f"{self.results['inventory']['dead_stock_pct']}%",
                'turnover': f"{self.results['inventory']['avg_turnover']:.1f}x"
            }
            
        if 'receivables' in self.results:
            output['key_metrics']['receivables'] = {
                'total': f"${self.results['receivables']['total_receivables']:,.0f}",
                'dso': f"{self.results['receivables']['dso']:.0f} days",
                'overdue': f"{self.results['receivables']['over_90_pct']}%"
            }
            
        if 'suppliers' in self.results:
            output['key_metrics']['suppliers'] = {
                'count': self.results['suppliers']['total_suppliers'],
                'concentration': f"{self.results['suppliers']['top_5_concentration']}%"
            }
            
        # Save non-dataframe results
        for key in ['customers', 'inventory', 'receivables', 'suppliers']:
            if key in self.results:
                output['detailed_results'][key] = {
                    k: v for k, v in self.results[key].items() 
                    if k != 'dataframe'
                }
                
        if 'ratios' in self.results:
            output['financial_ratios'] = self.results['ratios']
            
        # Save to file
        filename = f"strategic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2, default=str)
            
        print(f"✅ Report saved to {filename}")
        
        return filename
        
def main():
    print("\n" + "="*80)
    print(" EXECUTIVE STRATEGIC BUSINESS ANALYSIS")
    print(" High-End Consulting Report")
    print("="*80)
    
    analyzer = ExecutiveAnalyzer()
    
    try:
        # Run all analyses
        analyzer.analyze_customers()
        analyzer.analyze_inventory()
        analyzer.analyze_receivables()
        analyzer.analyze_suppliers()
        analyzer.calculate_ratios()
        
        # Generate outputs
        dashboard_file = analyzer.generate_visualizations()
        report_file = analyzer.generate_report()
        
        # Print executive summary
        print("\n" + "="*80)
        print(" EXECUTIVE SUMMARY")
        print("="*80)
        
        if 'ratios' in analyzer.results:
            risk_score = analyzer.results['ratios']['overall_risk']
            risk_level = ('🔴 CRITICAL' if risk_score > 70 else
                         '🟠 HIGH' if risk_score > 50 else
                         '🟡 MEDIUM' if risk_score > 30 else
                         '🟢 LOW')
            
            print(f"\n📊 OVERALL RISK ASSESSMENT: {risk_level} ({risk_score:.0f}/100)")
            
        print("\n🎯 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(analyzer.recommendations[:5], 1):
            print(f"\n{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Action: {rec['action']}")
            
        print(f"\n📁 OUTPUTS GENERATED:")
        print(f"   Dashboard: {dashboard_file}")
        print(f"   Report: {report_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    main()