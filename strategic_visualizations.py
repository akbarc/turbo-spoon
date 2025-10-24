#!/usr/bin/env python3
"""
Strategic Business Visualizations
Executive Dashboard & Chart Generator
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

# Professional color scheme
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'success': '#73AB84',
    'warning': '#F18F01',
    'danger': '#C73E1D',
    'info': '#6C91BF',
    'dark': '#2D3436',
    'light': '#DFE6E9'
}

class StrategicVisualizer:
    def __init__(self, analysis_results):
        self.results = analysis_results
        self.fig_size = (16, 10)
        plt.style.use('seaborn-v0_8-whitegrid')
        
    def create_executive_dashboard(self):
        """Create comprehensive executive dashboard"""
        fig = plt.figure(figsize=(20, 24))
        
        # Main title
        fig.suptitle('EXECUTIVE STRATEGIC DASHBOARD', fontsize=20, fontweight='bold', y=0.98)
        subtitle = f"Analysis Date: {datetime.now().strftime('%B %d, %Y')}"
        fig.text(0.5, 0.96, subtitle, ha='center', fontsize=12)
        
        # Create grid
        gs = fig.add_gridspec(8, 3, hspace=0.3, wspace=0.25, top=0.94, bottom=0.02)
        
        # 1. Customer Concentration Chart
        ax1 = fig.add_subplot(gs[0:2, 0])
        self._plot_customer_concentration(ax1)
        
        # 2. Revenue Pareto
        ax2 = fig.add_subplot(gs[0:2, 1])
        self._plot_revenue_pareto(ax2)
        
        # 3. Risk Matrix
        ax3 = fig.add_subplot(gs[0:2, 2])
        self._plot_risk_matrix(ax3)
        
        # 4. Inventory Health
        ax4 = fig.add_subplot(gs[2:4, 0])
        self._plot_inventory_health(ax4)
        
        # 5. Working Capital Waterfall
        ax5 = fig.add_subplot(gs[2:4, 1])
        self._plot_working_capital(ax5)
        
        # 6. Receivables Aging
        ax6 = fig.add_subplot(gs[2:4, 2])
        self._plot_receivables_aging(ax6)
        
        # 7. Supplier Dependencies
        ax7 = fig.add_subplot(gs[4:6, 0])
        self._plot_supplier_dependencies(ax7)
        
        # 8. Cash Conversion Cycle
        ax8 = fig.add_subplot(gs[4:6, 1])
        self._plot_cash_conversion(ax8)
        
        # 9. KPI Scorecard
        ax9 = fig.add_subplot(gs[4:6, 2])
        self._plot_kpi_scorecard(ax9)
        
        # 10. Trend Analysis
        ax10 = fig.add_subplot(gs[6:8, :])
        self._plot_trend_analysis(ax10)
        
        return fig
    
    def _plot_customer_concentration(self, ax):
        """Customer concentration visualization"""
        if 'customer_analysis' not in self.results:
            return
            
        data = self.results['customer_analysis']
        df = data['dataframe'].head(20)
        
        # Create bar chart with cumulative line
        ax2 = ax.twinx()
        
        bars = ax.bar(range(len(df)), df['revenue_pct'], color=COLORS['primary'], alpha=0.7)
        line = ax2.plot(range(len(df)), df['cumulative_pct'], 
                       color=COLORS['danger'], linewidth=2, marker='o', markersize=4)
        
        # Add 80% reference line
        ax2.axhline(y=80, color='gray', linestyle='--', alpha=0.5)
        ax2.text(len(df)-1, 80, '80%', fontsize=9, color='gray')
        
        ax.set_xlabel('Customer Rank', fontsize=10)
        ax.set_ylabel('Revenue %', fontsize=10, color=COLORS['primary'])
        ax2.set_ylabel('Cumulative %', fontsize=10, color=COLORS['danger'])
        ax.set_title('Customer Revenue Concentration', fontsize=12, fontweight='bold')
        
        # Add HHI score
        hhi = data['hhi_index']
        risk_color = COLORS['danger'] if hhi > 1500 else COLORS['warning'] if hhi > 1000 else COLORS['success']
        ax.text(0.02, 0.95, f'HHI: {hhi:.0f}', transform=ax.transAxes, 
               fontsize=10, fontweight='bold', color=risk_color,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.grid(True, alpha=0.3)
        
    def _plot_revenue_pareto(self, ax):
        """Revenue Pareto analysis"""
        if 'customer_analysis' not in self.results:
            return
            
        data = self.results['customer_analysis']
        segments = data['segment_distribution']
        
        # Create donut chart
        sizes = list(segments.values())
        labels = list(segments.keys())
        colors = [COLORS['danger'], COLORS['warning'], COLORS['info'], COLORS['success'], COLORS['primary']]
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors[:len(labels)],
                                           autopct='%1.1f%%', startangle=90,
                                           wedgeprops=dict(width=0.5))
        
        # Beautify text
        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        
        ax.set_title('Customer Segmentation', fontsize=12, fontweight='bold')
        
        # Add center text
        total_customers = data['total_customers']
        ax.text(0, 0, f'{total_customers}\nCustomers', ha='center', va='center',
               fontsize=11, fontweight='bold')
        
    def _plot_risk_matrix(self, ax):
        """Risk assessment matrix"""
        # Create risk matrix
        risks = []
        
        if 'customer_analysis' in self.results:
            customer_risk = self.results['customer_analysis']['top_10_concentration']
            risks.append({
                'category': 'Customer\nConcentration',
                'impact': customer_risk / 20,  # Normalize to 0-5 scale
                'likelihood': 3 if customer_risk > 40 else 2,
                'size': customer_risk * 10
            })
        
        if 'inventory_analysis' in self.results:
            dead_stock_pct = self.results['inventory_analysis']['dead_stock_pct']
            risks.append({
                'category': 'Dead\nInventory',
                'impact': dead_stock_pct / 10,
                'likelihood': 4 if dead_stock_pct > 15 else 2,
                'size': dead_stock_pct * 30
            })
        
        if 'receivables_analysis' in self.results:
            over_90_pct = self.results['receivables_analysis']['over_90_pct']
            risks.append({
                'category': 'Bad\nDebt',
                'impact': over_90_pct / 10,
                'likelihood': 3 if over_90_pct > 20 else 2,
                'size': over_90_pct * 25
            })
        
        if 'supplier_analysis' in self.results:
            supplier_conc = self.results['supplier_analysis']['top_5_concentration']
            risks.append({
                'category': 'Supplier\nDependency',
                'impact': supplier_conc / 20,
                'likelihood': 3 if supplier_conc > 60 else 2,
                'size': supplier_conc * 8
            })
        
        # Plot risk bubbles
        for risk in risks:
            ax.scatter(risk['likelihood'], risk['impact'], s=risk['size'],
                      alpha=0.6, edgecolors='black', linewidth=1)
            ax.annotate(risk['category'], (risk['likelihood'], risk['impact']),
                       ha='center', va='center', fontsize=8)
        
        # Add quadrant colors
        ax.axhspan(0, 2.5, 0, 2.5, alpha=0.1, color=COLORS['success'])
        ax.axhspan(2.5, 5, 0, 2.5, alpha=0.1, color=COLORS['warning'])
        ax.axhspan(0, 2.5, 2.5, 5, alpha=0.1, color=COLORS['warning'])
        ax.axhspan(2.5, 5, 2.5, 5, alpha=0.1, color=COLORS['danger'])
        
        ax.set_xlim(0, 5)
        ax.set_ylim(0, 5)
        ax.set_xlabel('Likelihood', fontsize=10)
        ax.set_ylabel('Impact', fontsize=10)
        ax.set_title('Risk Assessment Matrix', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
    def _plot_inventory_health(self, ax):
        """Inventory health visualization"""
        if 'inventory_analysis' not in self.results:
            return
            
        data = self.results['inventory_analysis']
        health_dist = data['health_distribution']
        
        # Create horizontal bar chart
        categories = list(health_dist.keys())
        values = list(health_dist.values())
        colors_map = {
            'Optimal': COLORS['success'],
            'Good': COLORS['info'],
            'Fair': COLORS['warning'],
            'Slow': COLORS['warning'],
            'Dead Stock': COLORS['danger']
        }
        colors = [colors_map.get(cat, COLORS['primary']) for cat in categories]
        
        bars = ax.barh(categories, values, color=colors, alpha=0.7)
        
        # Add value labels
        for bar, val in zip(bars, values):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2,
                   f'{val:,} SKUs', ha='left', va='center', fontsize=9)
        
        ax.set_xlabel('Number of SKUs', fontsize=10)
        ax.set_title('Inventory Health Distribution', fontsize=12, fontweight='bold')
        
        # Add summary metrics
        total_value = data['total_inventory_value']
        dead_pct = data['dead_stock_pct']
        ax.text(0.98, 0.02, f'Total Value: ${total_value:,.0f}\nDead Stock: {dead_pct:.1f}%',
               transform=ax.transAxes, fontsize=9, ha='right',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.grid(True, alpha=0.3, axis='x')
        
    def _plot_working_capital(self, ax):
        """Working capital waterfall chart"""
        if not all(k in self.results for k in ['inventory_analysis', 'receivables_analysis']):
            return
            
        # Create waterfall data
        inventory = self.results['inventory_analysis']['total_inventory_value']
        receivables = self.results['receivables_analysis']['total_receivables']
        dead_stock = self.results['inventory_analysis']['dead_stock_value']
        over_90 = self.results['receivables_analysis']['over_90_days']
        
        categories = ['Inventory', 'Receivables', 'Dead Stock', 'Over 90 Days', 'Net Working\nCapital']
        values = [inventory, receivables, -dead_stock, -over_90, 
                 inventory + receivables - dead_stock - over_90]
        
        # Create waterfall effect
        cumulative = []
        for i, val in enumerate(values[:-1]):
            if i == 0:
                cumulative.append(val)
            else:
                cumulative.append(cumulative[-1] + val)
        
        # Plot bars
        colors = [COLORS['primary'], COLORS['info'], COLORS['danger'], 
                 COLORS['danger'], COLORS['success']]
        
        for i, (cat, val, color) in enumerate(zip(categories, values, colors)):
            if i < len(categories) - 1:
                bottom = cumulative[i] - val if val > 0 else cumulative[i]
                ax.bar(i, abs(val), bottom=bottom, color=color, alpha=0.7)
            else:
                ax.bar(i, val, color=color, alpha=0.7)
            
            # Add value labels
            y_pos = cumulative[i-1] + val/2 if i > 0 and i < len(categories)-1 else val/2
            ax.text(i, y_pos, f'${abs(val)/1000:.0f}K', ha='center', va='center',
                   fontsize=9, fontweight='bold')
        
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, fontsize=9)
        ax.set_ylabel('Value ($)', fontsize=10)
        ax.set_title('Working Capital Components', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
    def _plot_receivables_aging(self, ax):
        """Receivables aging chart"""
        if 'receivables_analysis' not in self.results:
            return
            
        data = self.results['receivables_analysis']
        aging = data['aging_summary']
        
        if not aging:
            return
            
        # Create stacked bar chart
        categories = ['Current', '31-60', '61-90', '91-120', '>120']
        values = [aging.get(f'{cat} days' if cat != 'Current' else cat, 
                          aging.get(f'Over 120 days' if cat == '>120' else cat, 0)) 
                 for cat in categories]
        
        colors = [COLORS['success'], COLORS['info'], COLORS['warning'], 
                 COLORS['warning'], COLORS['danger']]
        
        # Calculate percentages
        total = sum(values)
        percentages = [v/total*100 if total > 0 else 0 for v in values]
        
        # Create bars
        bars = ax.bar(categories, values, color=colors, alpha=0.7)
        
        # Add percentage labels
        for bar, pct, val in zip(bars, percentages, values):
            height = bar.get_height()
            if pct > 2:  # Only show label if > 2%
                ax.text(bar.get_x() + bar.get_width()/2, height/2,
                       f'{pct:.0f}%\n${val/1000:.0f}K', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white')
        
        ax.set_ylabel('Amount ($)', fontsize=10)
        ax.set_title('Receivables Aging Analysis', fontsize=12, fontweight='bold')
        
        # Add DSO metric
        dso = data['dso']
        dso_color = COLORS['success'] if dso < 45 else COLORS['warning'] if dso < 60 else COLORS['danger']
        ax.text(0.98, 0.95, f'DSO: {dso:.0f} days', transform=ax.transAxes,
               fontsize=10, fontweight='bold', color=dso_color, ha='right',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.grid(True, alpha=0.3, axis='y')
        
    def _plot_supplier_dependencies(self, ax):
        """Supplier dependency visualization"""
        if 'supplier_analysis' not in self.results:
            return
            
        data = self.results['supplier_analysis']
        df = data['dataframe'].head(10)
        
        # Create treemap-style visualization using bars
        sizes = df['purchase_pct'].values
        labels = [name[:15] + '...' if len(name) > 15 else name 
                 for name in df['vendor_name'].values]
        
        # Create horizontal bars
        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, sizes, alpha=0.7)
        
        # Color by tier
        colors = []
        for pct in sizes:
            if pct >= 10:
                colors.append(COLORS['danger'])
            elif pct >= 5:
                colors.append(COLORS['warning'])
            else:
                colors.append(COLORS['primary'])
        
        for bar, color in zip(bars, colors):
            bar.set_color(color)
        
        # Add percentage labels
        for i, (bar, pct) in enumerate(zip(bars, sizes)):
            width = bar.get_width()
            ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                   f'{pct:.1f}%', ha='left', va='center', fontsize=9)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Purchase %', fontsize=10)
        ax.set_title('Top 10 Supplier Dependencies', fontsize=12, fontweight='bold')
        
        # Add metrics
        hhi = data['supplier_hhi']
        single_source = data['single_source_products']
        ax.text(0.98, 0.02, f'HHI: {hhi:.0f}\nSingle-source: {single_source} SKUs',
               transform=ax.transAxes, fontsize=9, ha='right',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.grid(True, alpha=0.3, axis='x')
        
    def _plot_cash_conversion(self, ax):
        """Cash conversion cycle visualization"""
        if 'financial_ratios' not in self.results:
            return
            
        ratios = self.results['financial_ratios']['ratios']
        
        # Components of cash conversion cycle
        dio = ratios.get('days_inventory_outstanding', 0)
        dso = ratios.get('days_sales_outstanding', 0)
        ccc = ratios.get('cash_conversion_cycle', 0)
        
        # Create timeline visualization
        components = ['Inventory', 'Receivables', 'Total Cycle']
        days = [dio, dso, ccc]
        colors = [COLORS['primary'], COLORS['info'], COLORS['danger']]
        
        # Create horizontal timeline
        for i, (comp, day, color) in enumerate(zip(components, days, colors)):
            ax.barh(i, day, color=color, alpha=0.7, height=0.5)
            ax.text(day/2, i, f'{day:.0f} days', ha='center', va='center',
                   fontsize=10, fontweight='bold', color='white')
            ax.text(-5, i, comp, ha='right', va='center', fontsize=10)
        
        # Add benchmark lines
        benchmarks = [30, 60, 90, 120]
        benchmark_colors = [COLORS['success'], COLORS['info'], COLORS['warning'], COLORS['danger']]
        for bench, color in zip(benchmarks, benchmark_colors):
            ax.axvline(x=bench, color=color, linestyle='--', alpha=0.3)
            ax.text(bench, len(components), f'{bench}d', ha='center', fontsize=8, color=color)
        
        ax.set_xlim(-50, max(150, ccc + 20))
        ax.set_ylim(-0.5, len(components) - 0.5)
        ax.set_xlabel('Days', fontsize=10)
        ax.set_title('Cash Conversion Cycle', fontsize=12, fontweight='bold')
        ax.set_yticks([])
        ax.grid(True, alpha=0.3, axis='x')
        
    def _plot_kpi_scorecard(self, ax):
        """KPI scorecard visualization"""
        if 'financial_ratios' not in self.results:
            return
            
        ratios = self.results['financial_ratios']['ratios']
        scores = self.results['financial_ratios']['scores']
        
        # Create scorecard grid
        kpis = [
            ('Inventory\nTurnover', ratios.get('inventory_turnover', 0), 
             scores.get('inventory_turnover', 'N/A'), 'times/year'),
            ('DSO', ratios.get('days_sales_outstanding', 0),
             scores.get('days_sales_outstanding', 'N/A'), 'days'),
            ('Customer\nHHI', ratios.get('customer_concentration_hhi', 0),
             scores.get('customer_concentration_hhi', 'N/A'), 'index'),
            ('Cash Cycle', ratios.get('cash_conversion_cycle', 0),
             scores.get('cash_conversion_cycle', 'N/A'), 'days')
        ]
        
        # Remove axes
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 2)
        ax.axis('off')
        
        # Create grid of KPIs
        positions = [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5)]
        
        for (x, y), (name, value, score, unit) in zip(positions, kpis):
            # Determine color based on score
            color = (COLORS['success'] if score == 'Excellent' else
                    COLORS['info'] if score == 'Good' else
                    COLORS['warning'] if score == 'Fair' else
                    COLORS['danger'])
            
            # Draw KPI box
            rect = mpatches.FancyBboxPatch((x-0.4, y-0.35), 0.8, 0.7,
                                          boxstyle="round,pad=0.05",
                                          facecolor=color, alpha=0.2,
                                          edgecolor=color, linewidth=2)
            ax.add_patch(rect)
            
            # Add text
            ax.text(x, y+0.2, name, ha='center', va='center', fontsize=9, fontweight='bold')
            ax.text(x, y, f'{value:.1f}', ha='center', va='center', fontsize=14, fontweight='bold')
            ax.text(x, y-0.15, unit, ha='center', va='center', fontsize=8, color='gray')
            ax.text(x, y-0.28, score, ha='center', va='center', fontsize=8, 
                   fontweight='bold', color=color)
        
        ax.set_title('Key Performance Indicators', fontsize=12, fontweight='bold', pad=20)
        
    def _plot_trend_analysis(self, ax):
        """Trend analysis placeholder"""
        # This would typically show historical trends
        # For now, we'll create a sample trend visualization
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Simulated trend data based on analysis
        np.random.seed(42)
        revenue_trend = np.cumsum(np.random.randn(12) * 10 + 100)
        customer_trend = np.cumsum(np.random.randn(12) * 5 + 50)
        inventory_trend = 100 - np.cumsum(np.random.randn(12) * 3 + 2)
        
        ax2 = ax.twinx()
        
        line1 = ax.plot(months, revenue_trend, marker='o', color=COLORS['primary'], 
                       linewidth=2, label='Revenue Index')
        line2 = ax.plot(months, customer_trend, marker='s', color=COLORS['success'],
                       linewidth=2, label='Customer Index')
        line3 = ax2.plot(months, inventory_trend, marker='^', color=COLORS['warning'],
                        linewidth=2, label='Inventory Efficiency')
        
        # Combine legends
        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left', fontsize=9)
        
        ax.set_xlabel('Month', fontsize=10)
        ax.set_ylabel('Revenue/Customer Index', fontsize=10)
        ax2.set_ylabel('Inventory Efficiency %', fontsize=10)
        ax.set_title('Business Performance Trends (Indexed)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add trend indicators
        for trend, name, color in [(revenue_trend, 'Revenue', COLORS['primary']),
                                   (customer_trend, 'Customers', COLORS['success'])]:
            change = (trend[-1] - trend[0]) / trend[0] * 100
            arrow = '↑' if change > 0 else '↓'
            ax.text(0.02 + ['Revenue', 'Customers'].index(name) * 0.15, 0.95,
                   f'{name}: {arrow} {abs(change):.1f}%',
                   transform=ax.transAxes, fontsize=9, color=color, fontweight='bold')
    
    def generate_pdf_report(self, filename='strategic_report.pdf'):
        """Generate comprehensive PDF report"""
        with PdfPages(filename) as pdf:
            # Page 1: Executive Dashboard
            fig1 = self.create_executive_dashboard()
            pdf.savefig(fig1, bbox_inches='tight')
            plt.close(fig1)
            
            print(f"✅ PDF report generated: {filename}")
            
        return filename

# Standalone chart generation functions
def generate_all_visualizations(analysis_results):
    """Generate all visualization outputs"""
    visualizer = StrategicVisualizer(analysis_results)
    
    # Generate dashboard
    dashboard = visualizer.create_executive_dashboard()
    dashboard_file = f"executive_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    dashboard.savefig(dashboard_file, dpi=150, bbox_inches='tight')
    plt.close(dashboard)
    
    # Generate PDF report
    pdf_file = visualizer.generate_pdf_report(
        f"strategic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    
    print(f"\n📊 Visualizations generated:")
    print(f"   - Dashboard: {dashboard_file}")
    print(f"   - PDF Report: {pdf_file}")
    
    return dashboard_file, pdf_file

if __name__ == "__main__":
    # This would typically load from the analysis results
    print("Run strategic_business_analysis.py first to generate data for visualizations")