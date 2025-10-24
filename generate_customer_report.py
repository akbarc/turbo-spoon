#!/usr/bin/env python3
"""
Comprehensive Customer Analysis Report Generator
Includes segmentation, concentration, sales patterns, and deep insights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json

def generate_customer_report():
    """Generate comprehensive customer analysis report"""
    
    print("🔍 Starting Comprehensive Customer Analysis...")
    db = SQLServerConnection()
    db.connect()
    
    current_date = datetime.now()
    current_year = current_date.year
    
    # Initialize report
    report = {
        'generated_at': current_date.strftime('%Y-%m-%d %H:%M:%S'),
        'report_title': 'Comprehensive Customer Analysis Report',
        'sections': {}
    }
    
    # 1. CUSTOMER OVERVIEW AND SEGMENTATION
    print("\n📊 Analyzing Customer Segmentation...")
    segmentation_query = """
    WITH CustomerMetrics AS (
        SELECT 
            c.ID,
            c.FirstName + ' ' + c.LastName as CustomerName,
            c.Company,
            c.AccountBalance,
            c.CreditLimit,
            c.City,
            c.State,
            c.Zip,
            -- Sales metrics
            COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
            COUNT(DISTINCT CAST(t.Time as DATE)) as DaysActive,
            SUM(t.Total) as LifetimeSales,
            SUM(CASE WHEN t.Time >= DATEADD(month, -12, GETDATE()) THEN t.Total ELSE 0 END) as Sales12M,
            SUM(CASE WHEN t.Time >= DATEADD(month, -6, GETDATE()) THEN t.Total ELSE 0 END) as Sales6M,
            SUM(CASE WHEN t.Time >= DATEADD(month, -3, GETDATE()) THEN t.Total ELSE 0 END) as Sales3M,
            SUM(CASE WHEN t.Time >= DATEADD(month, -1, GETDATE()) THEN t.Total ELSE 0 END) as Sales1M,
            MIN(t.Time) as FirstPurchase,
            MAX(t.Time) as LastPurchase,
            DATEDIFF(day, MAX(t.Time), GETDATE()) as DaysSinceLastPurchase,
            AVG(t.Total) as AvgTicket,
            MAX(t.Total) as MaxTicket,
            -- GP metrics (approximate using 15% margin)
            SUM(t.Total * 0.15) as LifetimeGP,
            SUM(CASE WHEN t.Time >= DATEADD(month, -12, GETDATE()) THEN t.Total * 0.15 ELSE 0 END) as GP12M
        FROM Customer c
        LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        GROUP BY c.ID, c.FirstName, c.LastName, c.Company, c.AccountBalance, 
                 c.CreditLimit, c.City, c.State, c.Zip
    )
    SELECT 
        *,
        CASE 
            WHEN Sales12M >= 100000 THEN 'Platinum'
            WHEN Sales12M >= 50000 THEN 'Gold'
            WHEN Sales12M >= 20000 THEN 'Silver'
            WHEN Sales12M >= 5000 THEN 'Bronze'
            WHEN Sales12M > 0 THEN 'Active'
            ELSE 'Inactive'
        END as CustomerTier,
        CASE 
            WHEN DaysSinceLastPurchase <= 30 THEN 'Active'
            WHEN DaysSinceLastPurchase <= 90 THEN 'At Risk'
            WHEN DaysSinceLastPurchase <= 180 THEN 'Dormant'
            ELSE 'Lost'
        END as ActivityStatus,
        CASE
            WHEN Sales1M > Sales3M/3 * 1.2 THEN 'Growing'
            WHEN Sales1M < Sales3M/3 * 0.8 THEN 'Declining'
            ELSE 'Stable'
        END as Trend,
        CAST(GP12M * 100.0 / NULLIF(Sales12M, 0) as DECIMAL(5,2)) as GPMargin12M
    FROM CustomerMetrics
    ORDER BY Sales12M DESC
    """
    
    customers_df = db.execute_query(segmentation_query, description="Customer Segmentation")
    
    # Customer tier summary
    tier_summary = customers_df.groupby('CustomerTier').agg({
        'ID': 'count',
        'Sales12M': 'sum',
        'GP12M': 'sum',
        'AvgTicket': 'mean'
    }).round(2)
    
    report['sections']['customer_tiers'] = {
        'summary': tier_summary.to_dict('index'),
        'total_customers': int(len(customers_df)),
        'active_customers': int(len(customers_df[customers_df['Sales12M'] > 0]))
    }
    
    # 2. CONCENTRATION ANALYSIS
    print("📈 Analyzing Sales Concentration...")
    
    # Calculate cumulative percentages
    customers_sorted = customers_df[customers_df['Sales12M'] > 0].sort_values('Sales12M', ascending=False).copy()
    customers_sorted['Sales12M'] = customers_sorted['Sales12M'].astype(float)
    customers_sorted['CumulativeSales'] = customers_sorted['Sales12M'].cumsum()
    total_sales = float(customers_sorted['Sales12M'].sum())
    customers_sorted['CumulativePercent'] = (customers_sorted['CumulativeSales'] / total_sales * 100).round(2)
    customers_sorted['CustomerRank'] = range(1, len(customers_sorted) + 1)
    customers_sorted['CustomerPercentile'] = (customers_sorted['CustomerRank'] / len(customers_sorted) * 100).round(2)
    
    # Pareto analysis
    top_20_percent_count = int(len(customers_sorted) * 0.2)
    top_20_percent_sales = customers_sorted.iloc[:top_20_percent_count]['Sales12M'].sum()
    pareto_ratio = (top_20_percent_sales / total_sales * 100).round(2)
    
    # Concentration metrics
    report['sections']['concentration'] = {
        'pareto_80_20': {
            'top_20_percent_customers': top_20_percent_count,
            'sales_from_top_20_percent': f"{pareto_ratio}%",
            'concentration_level': 'High' if pareto_ratio > 80 else 'Moderate' if pareto_ratio > 60 else 'Low'
        },
        'top_customers': customers_sorted.head(10)[['CustomerName', 'Company', 'Sales12M', 'CumulativePercent']].to_dict('records'),
        'revenue_brackets': {
            'over_100k': len(customers_sorted[customers_sorted['Sales12M'] >= 100000]),
            '50k_to_100k': len(customers_sorted[(customers_sorted['Sales12M'] >= 50000) & (customers_sorted['Sales12M'] < 100000)]),
            '20k_to_50k': len(customers_sorted[(customers_sorted['Sales12M'] >= 20000) & (customers_sorted['Sales12M'] < 50000)]),
            '10k_to_20k': len(customers_sorted[(customers_sorted['Sales12M'] >= 10000) & (customers_sorted['Sales12M'] < 20000)]),
            'under_10k': len(customers_sorted[customers_sorted['Sales12M'] < 10000])
        }
    }
    
    # 3. CUSTOMER GROUPS AND PATTERNS
    print("👥 Analyzing Customer Groups...")
    
    groups_query = """
    WITH CustomerGroups AS (
        SELECT 
            CASE 
                WHEN c.Company LIKE '%SHELL%' OR c.Company LIKE '%CHEVRON%' OR c.Company LIKE '%BP%' 
                     OR c.Company LIKE '%EXXON%' OR c.Company LIKE '%CITGO%' OR c.Company LIKE '%MARATHON%'
                     OR c.Company LIKE '%VALERO%' OR c.Company LIKE '%TEXACO%' THEN 'Major Gas Chains'
                WHEN c.Company LIKE '%FOOD MART%' OR c.Company LIKE '%CONVENIENCE%' OR c.Company LIKE '%MARKET%' 
                     OR c.Company LIKE '%STORE%' OR c.Company LIKE '%SHOP%' THEN 'Convenience Stores'
                WHEN c.Company LIKE '%LIQUOR%' OR c.Company LIKE '%WINE%' OR c.Company LIKE '%SPIRITS%' THEN 'Liquor Stores'
                WHEN c.Company LIKE '%SMOKE%' OR c.Company LIKE '%TOBACCO%' OR c.Company LIKE '%VAPE%' THEN 'Smoke Shops'
                WHEN c.Company LIKE '%RESTAURANT%' OR c.Company LIKE '%CAFE%' OR c.Company LIKE '%GRILL%' THEN 'Restaurants'
                WHEN c.Company LIKE '%HOTEL%' OR c.Company LIKE '%MOTEL%' OR c.Company LIKE '%INN%' THEN 'Hospitality'
                WHEN c.Company IS NULL OR c.Company = '' THEN 'Individual Customers'
                ELSE 'Other Retail'
            END as CustomerGroup,
            c.ID,
            SUM(t.Total) as GroupSales,
            COUNT(DISTINCT t.TransactionNumber) as GroupTransactions,
            AVG(t.Total) as GroupAvgTicket
        FROM Customer c
        LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        WHERE t.Time >= DATEADD(month, -12, GETDATE())
        GROUP BY 
            CASE 
                WHEN c.Company LIKE '%SHELL%' OR c.Company LIKE '%CHEVRON%' OR c.Company LIKE '%BP%' 
                     OR c.Company LIKE '%EXXON%' OR c.Company LIKE '%CITGO%' OR c.Company LIKE '%MARATHON%'
                     OR c.Company LIKE '%VALERO%' OR c.Company LIKE '%TEXACO%' THEN 'Major Gas Chains'
                WHEN c.Company LIKE '%FOOD MART%' OR c.Company LIKE '%CONVENIENCE%' OR c.Company LIKE '%MARKET%' 
                     OR c.Company LIKE '%STORE%' OR c.Company LIKE '%SHOP%' THEN 'Convenience Stores'
                WHEN c.Company LIKE '%LIQUOR%' OR c.Company LIKE '%WINE%' OR c.Company LIKE '%SPIRITS%' THEN 'Liquor Stores'
                WHEN c.Company LIKE '%SMOKE%' OR c.Company LIKE '%TOBACCO%' OR c.Company LIKE '%VAPE%' THEN 'Smoke Shops'
                WHEN c.Company LIKE '%RESTAURANT%' OR c.Company LIKE '%CAFE%' OR c.Company LIKE '%GRILL%' THEN 'Restaurants'
                WHEN c.Company LIKE '%HOTEL%' OR c.Company LIKE '%MOTEL%' OR c.Company LIKE '%INN%' THEN 'Hospitality'
                WHEN c.Company IS NULL OR c.Company = '' THEN 'Individual Customers'
                ELSE 'Other Retail'
            END, c.ID
    )
    SELECT 
        CustomerGroup,
        COUNT(DISTINCT ID) as CustomerCount,
        SUM(GroupSales) as TotalSales,
        SUM(GroupTransactions) as TotalTransactions,
        AVG(GroupAvgTicket) as AvgTicket,
        SUM(GroupSales) / COUNT(DISTINCT ID) as AvgSalesPerCustomer
    FROM CustomerGroups
    GROUP BY CustomerGroup
    ORDER BY TotalSales DESC
    """
    
    groups_df = db.execute_query(groups_query, description="Customer Groups")
    report['sections']['customer_groups'] = groups_df.to_dict('records')
    
    # 4. GEOGRAPHIC ANALYSIS
    print("🗺️ Analyzing Geographic Distribution...")
    
    geo_query = """
    SELECT 
        ISNULL(c.State, 'Unknown') as State,
        ISNULL(c.City, 'Unknown') as City,
        COUNT(DISTINCT c.ID) as CustomerCount,
        SUM(t.Total) as TotalSales,
        AVG(t.Total) as AvgTicket,
        COUNT(DISTINCT t.TransactionNumber) as Transactions
    FROM Customer c
    LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
    WHERE t.Time >= DATEADD(month, -12, GETDATE())
    GROUP BY c.State, c.City
    HAVING SUM(t.Total) > 1000
    ORDER BY TotalSales DESC
    """
    
    geo_df = db.execute_query(geo_query, description="Geographic Analysis")
    
    # State summary
    state_summary = geo_df.groupby('State').agg({
        'CustomerCount': 'sum',
        'TotalSales': 'sum',
        'Transactions': 'sum'
    }).sort_values('TotalSales', ascending=False)
    
    report['sections']['geographic'] = {
        'top_states': state_summary.head(10).to_dict(),
        'top_cities': geo_df.head(20)[['City', 'State', 'CustomerCount', 'TotalSales']].to_dict('records')
    }
    
    # 5. PURCHASE PATTERNS AND BEHAVIOR
    print("🛒 Analyzing Purchase Patterns...")
    
    patterns_query = """
    WITH PurchasePatterns AS (
        SELECT 
            c.ID,
            -- Frequency metrics
            COUNT(DISTINCT CAST(t.Time as DATE)) as PurchaseDays,
            COUNT(DISTINCT DATEPART(week, t.Time)) as ActiveWeeks,
            COUNT(DISTINCT DATEPART(month, t.Time)) as ActiveMonths,
            -- Time patterns
            AVG(DATEPART(hour, t.Time)) as AvgPurchaseHour,
            -- Category preferences
            COUNT(DISTINCT cat.Name) as CategoriesPurchased,
            -- Payment patterns
            SUM(CASE WHEN t.Total > 1000 THEN 1 ELSE 0 END) as LargeTransactions,
            SUM(CASE WHEN t.Total < 50 THEN 1 ELSE 0 END) as SmallTransactions
        FROM Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        LEFT JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Category cat ON i.CategoryID = cat.ID
        WHERE t.Time >= DATEADD(month, -12, GETDATE())
        GROUP BY c.ID
    )
    SELECT 
        CASE 
            WHEN ActiveWeeks >= 40 THEN 'Weekly Regular'
            WHEN ActiveMonths >= 10 THEN 'Monthly Regular'
            WHEN ActiveMonths >= 6 THEN 'Occasional'
            WHEN ActiveMonths >= 3 THEN 'Rare'
            ELSE 'Very Rare'
        END as FrequencySegment,
        COUNT(*) as CustomerCount,
        AVG(PurchaseDays) as AvgPurchaseDays,
        AVG(CategoriesPurchased) as AvgCategories
    FROM PurchasePatterns
    GROUP BY 
        CASE 
            WHEN ActiveWeeks >= 40 THEN 'Weekly Regular'
            WHEN ActiveMonths >= 10 THEN 'Monthly Regular'
            WHEN ActiveMonths >= 6 THEN 'Occasional'
            WHEN ActiveMonths >= 3 THEN 'Rare'
            ELSE 'Very Rare'
        END
    """
    
    patterns_df = db.execute_query(patterns_query, description="Purchase Patterns")
    report['sections']['purchase_patterns'] = patterns_df.to_dict('records')
    
    # 6. RETENTION AND CHURN ANALYSIS
    print("🔄 Analyzing Retention and Churn...")
    
    retention_query = """
    WITH MonthlyActivity AS (
        SELECT 
            c.ID,
            YEAR(t.Time) as Year,
            MONTH(t.Time) as Month,
            SUM(t.Total) as MonthlySales
        FROM Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        WHERE t.Time >= DATEADD(month, -24, GETDATE())
        GROUP BY c.ID, YEAR(t.Time), MONTH(t.Time)
    ),
    CustomerRetention AS (
        SELECT 
            Year,
            Month,
            COUNT(DISTINCT ID) as ActiveCustomers,
            SUM(MonthlySales) as TotalSales
        FROM MonthlyActivity
        GROUP BY Year, Month
    )
    SELECT * FROM CustomerRetention
    ORDER BY Year DESC, Month DESC
    """
    
    retention_df = db.execute_query(retention_query, description="Retention Analysis")
    
    # Calculate churn metrics
    if len(retention_df) > 1:
        latest_month_customers = retention_df.iloc[0]['ActiveCustomers']
        previous_month_customers = retention_df.iloc[1]['ActiveCustomers']
        churn_rate = ((previous_month_customers - latest_month_customers) / previous_month_customers * 100) if previous_month_customers > 0 else 0
    else:
        churn_rate = 0
    
    report['sections']['retention'] = {
        'monthly_trend': retention_df.head(12).to_dict('records'),
        'estimated_monthly_churn_rate': f"{churn_rate:.2f}%"
    }
    
    # 7. CUSTOMER LIFETIME VALUE ANALYSIS
    print("💰 Calculating Customer Lifetime Value...")
    
    clv_query = """
    WITH CLVMetrics AS (
        SELECT 
            c.ID,
            c.FirstName + ' ' + c.LastName as CustomerName,
            c.Company,
            MIN(t.Time) as FirstPurchase,
            MAX(t.Time) as LastPurchase,
            DATEDIFF(month, MIN(t.Time), MAX(t.Time)) + 1 as LifetimeMonths,
            COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
            SUM(t.Total) as LifetimeRevenue,
            SUM(t.Total * 0.15) as LifetimeGP,
            SUM(t.Total) / NULLIF(DATEDIFF(month, MIN(t.Time), MAX(t.Time)) + 1, 0) as MonthlyValue,
            COUNT(DISTINCT t.TransactionNumber) / NULLIF(DATEDIFF(month, MIN(t.Time), MAX(t.Time)) + 1, 0) as MonthlyFrequency
        FROM Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        GROUP BY c.ID, c.FirstName, c.LastName, c.Company
        HAVING COUNT(DISTINCT t.TransactionNumber) > 5
    )
    SELECT 
        TOP 100
        CustomerName,
        Company,
        LifetimeMonths,
        TotalTransactions,
        LifetimeRevenue,
        LifetimeGP,
        MonthlyValue,
        MonthlyFrequency,
        MonthlyValue * 12 as ProjectedAnnualValue,
        CAST(LifetimeGP * 100.0 / NULLIF(LifetimeRevenue, 0) as DECIMAL(5,2)) as GPMargin
    FROM CLVMetrics
    WHERE LifetimeMonths > 3
    ORDER BY LifetimeRevenue DESC
    """
    
    clv_df = db.execute_query(clv_query, description="CLV Analysis")
    
    report['sections']['lifetime_value'] = {
        'top_clv_customers': clv_df.head(20).to_dict('records'),
        'avg_monthly_value': float(clv_df['MonthlyValue'].mean()),
        'avg_lifetime_months': float(clv_df['LifetimeMonths'].mean()),
        'avg_gp_margin': float(clv_df['GPMargin'].mean())
    }
    
    # 8. RISK ANALYSIS
    print("⚠️ Analyzing At-Risk Customers...")
    
    # Identify at-risk high-value customers
    at_risk = customers_df[
        (customers_df['Sales12M'] > 20000) & 
        (customers_df['DaysSinceLastPurchase'] > 60)
    ].sort_values('Sales12M', ascending=False)
    
    report['sections']['at_risk_customers'] = {
        'count': len(at_risk),
        'total_revenue_at_risk': float(at_risk['Sales12M'].sum()),
        'top_at_risk': at_risk.head(10)[['CustomerName', 'Company', 'Sales12M', 'DaysSinceLastPurchase', 'ActivityStatus']].to_dict('records')
    }
    
    # 9. GROWTH OPPORTUNITIES
    print("🚀 Identifying Growth Opportunities...")
    
    # Growing customers
    growing = customers_df[
        (customers_df['Trend'] == 'Growing') & 
        (customers_df['Sales12M'] > 5000)
    ].sort_values('Sales12M', ascending=False)
    
    # Underutilized credit
    customers_df['CreditLimit'] = customers_df['CreditLimit'].astype(float)
    customers_df['AccountBalance'] = customers_df['AccountBalance'].astype(float)
    credit_opportunity = customers_df[
        (customers_df['CreditLimit'] > 0) &
        (customers_df['AccountBalance'] < customers_df['CreditLimit'] * 0.3) &
        (customers_df['Sales12M'] > 10000)
    ]
    
    report['sections']['growth_opportunities'] = {
        'growing_customers': {
            'count': len(growing),
            'total_current_revenue': float(growing['Sales12M'].sum()),
            'top_growing': growing.head(10)[['CustomerName', 'Company', 'Sales12M', 'Sales1M']].to_dict('records')
        },
        'credit_opportunities': {
            'count': len(credit_opportunity),
            'unused_credit': float((credit_opportunity['CreditLimit'] - credit_opportunity['AccountBalance']).sum()),
            'potential_revenue': float(credit_opportunity['Sales12M'].sum()) * 0.2  # 20% growth potential
        }
    }
    
    # 10. EXECUTIVE SUMMARY
    print("\n📋 Creating Executive Summary...")
    
    total_customers = len(customers_df)
    active_customers = len(customers_df[customers_df['Sales12M'] > 0])
    total_revenue = customers_df['Sales12M'].sum()
    total_gp = customers_df['GP12M'].sum()
    avg_gp_margin = (total_gp / total_revenue * 100) if total_revenue > 0 else 0
    
    report['executive_summary'] = {
        'total_customers': int(total_customers),
        'active_customers_12m': int(active_customers),
        'total_revenue_12m': float(total_revenue),
        'total_gp_12m': float(total_gp),
        'avg_gp_margin': float(avg_gp_margin),
        'top_20_percent_concentration': f"{pareto_ratio}%",
        'at_risk_revenue': float(at_risk['Sales12M'].sum()),
        'growth_opportunity_revenue': float(growing['Sales12M'].sum()),
        'monthly_churn_rate': f"{churn_rate:.2f}%",
        'key_insights': [
            f"Top 20% of customers generate {pareto_ratio}% of revenue",
            f"{len(at_risk)} high-value customers are at risk (${at_risk['Sales12M'].sum():,.0f} revenue)",
            f"{len(growing)} customers showing growth trend",
            f"Average customer lifetime: {clv_df['LifetimeMonths'].mean():.1f} months",
            f"Unused credit opportunity: ${(credit_opportunity['CreditLimit'] - credit_opportunity['AccountBalance']).sum():,.0f}"
        ]
    }
    
    # Save detailed customer list
    print("\n💾 Saving detailed customer data...")
    
    customer_export = customers_df[[
        'CustomerName', 'Company', 'City', 'State', 
        'Sales12M', 'Sales6M', 'Sales3M', 'Sales1M',
        'GP12M', 'GPMargin12M', 'CustomerTier', 'ActivityStatus', 'Trend',
        'AvgTicket', 'TotalTransactions', 'DaysSinceLastPurchase',
        'AccountBalance', 'CreditLimit'
    ]].copy()
    
    customer_export.columns = [
        'Customer Name', 'Company', 'City', 'State',
        'Sales 12M', 'Sales 6M', 'Sales 3M', 'Sales 1M',
        'GP 12M', 'GP Margin %', 'Tier', 'Status', 'Trend',
        'Avg Ticket', 'Total Transactions', 'Days Since Last Purchase',
        'Account Balance', 'Credit Limit'
    ]
    
    # Save to Excel with multiple sheets
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = f'customer_analysis_report_{timestamp}.xlsx'
    
    with pd.ExcelWriter(excel_filename, engine='xlsxwriter') as writer:
        # Customer details sheet
        customer_export.to_excel(writer, sheet_name='Customer Details', index=False)
        
        # Summary metrics sheet
        summary_df = pd.DataFrame([report['executive_summary']])
        summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
        
        # Customer groups sheet
        pd.DataFrame(report['sections']['customer_groups']).to_excel(
            writer, sheet_name='Customer Groups', index=False
        )
        
        # Geographic analysis sheet
        geo_df.to_excel(writer, sheet_name='Geographic Analysis', index=False)
        
        # Format the Excel file
        workbook = writer.book
        currency_format = workbook.add_format({'num_format': '$#,##0'})
        percent_format = workbook.add_format({'num_format': '0.0%'})
        
        # Format Customer Details sheet
        worksheet = writer.sheets['Customer Details']
        worksheet.set_column('E:I', 15, currency_format)  # Sales columns
        worksheet.set_column('J:J', 12, percent_format)   # GP Margin
        worksheet.set_column('O:P', 15, currency_format)  # Balance and Credit
    
    # Save JSON report
    json_filename = f'customer_analysis_report_{timestamp}.json'
    with open(json_filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Save markdown summary
    md_filename = f'customer_analysis_report_{timestamp}.md'
    with open(md_filename, 'w') as f:
        f.write(f"# Customer Analysis Report\n")
        f.write(f"*Generated: {report['generated_at']}*\n\n")
        
        f.write("## Executive Summary\n\n")
        for key, value in report['executive_summary'].items():
            if key != 'key_insights':
                formatted_value = f"{value:,}" if isinstance(value, (int, float)) else str(value)
                f.write(f"- **{key.replace('_', ' ').title()}**: {formatted_value}\n")
        
        f.write("\n### Key Insights\n\n")
        for insight in report['executive_summary']['key_insights']:
            f.write(f"- {insight}\n")
        
        f.write("\n## Customer Segmentation\n\n")
        f.write(f"- **Total Customers**: {report['sections']['customer_tiers']['total_customers']}\n")
        f.write(f"- **Active Customers**: {report['sections']['customer_tiers']['active_customers']}\n")
        
        f.write("\n## Sales Concentration\n\n")
        f.write(f"- **Pareto Analysis**: Top 20% of customers = {report['sections']['concentration']['pareto_80_20']['sales_from_top_20_percent']} of sales\n")
        f.write(f"- **Concentration Level**: {report['sections']['concentration']['pareto_80_20']['concentration_level']}\n")
        
        f.write("\n## Top 10 Customers\n\n")
        f.write("| Customer | Company | Sales 12M | Cumulative % |\n")
        f.write("|----------|---------|-----------|-------------|\n")
        for customer in report['sections']['concentration']['top_customers']:
            f.write(f"| {customer['CustomerName']} | {customer['Company'] or 'N/A'} | ${customer['Sales12M']:,.0f} | {customer['CumulativePercent']}% |\n")
    
    db.close()
    
    print("\n✅ Customer Analysis Report Generated Successfully!")
    print(f"📊 Excel Report: {excel_filename}")
    print(f"📄 JSON Report: {json_filename}")
    print(f"📝 Summary Report: {md_filename}")
    
    return report

if __name__ == "__main__":
    generate_customer_report()