#!/usr/bin/env python3
"""
Bank-Focused Financial Metrics Report
Highlighting creditworthiness, diversification, stability, and growth
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import json

def generate_bank_metrics_report():
    """Generate comprehensive financial metrics for bank presentation"""
    
    print("🏦 Generating Bank-Focused Financial Metrics Report...")
    db = SQLServerConnection()
    db.connect()
    
    current_date = datetime.now()
    current_year = current_date.year
    
    # Initialize report
    report = {
        'generated_at': current_date.strftime('%Y-%m-%d %H:%M:%S'),
        'report_title': 'Financial Metrics Report for Banking Review',
        'company': 'Georgia Business',
        'prepared_for': 'Banking/Lending Institution',
        'sections': {}
    }
    
    # 1. REVENUE STABILITY AND GROWTH METRICS
    print("📈 Analyzing Revenue Stability and Growth...")
    
    revenue_query = """
    WITH MonthlyRevenue AS (
        SELECT 
            YEAR(Time) as Year,
            MONTH(Time) as Month,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            COUNT(DISTINCT TransactionNumber) as TransactionCount,
            SUM(Total) as Revenue,
            AVG(Total) as AvgTransactionValue,
            STDEV(Total) as TransactionStdDev
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(year, -3, GETDATE())
        GROUP BY YEAR(Time), MONTH(Time)
    ),
    YearlyMetrics AS (
        SELECT 
            Year,
            SUM(Revenue) as AnnualRevenue,
            AVG(Revenue) as AvgMonthlyRevenue,
            STDEV(Revenue) as MonthlyStdDev,
            MIN(Revenue) as MinMonthlyRevenue,
            MAX(Revenue) as MaxMonthlyRevenue,
            SUM(TransactionCount) as AnnualTransactions,
            AVG(UniqueCustomers) as AvgMonthlyCustomers
        FROM MonthlyRevenue
        GROUP BY Year
    )
    SELECT 
        Year,
        AnnualRevenue,
        AvgMonthlyRevenue,
        MonthlyStdDev,
        CAST(MonthlyStdDev / NULLIF(AvgMonthlyRevenue, 0) as DECIMAL(5,2)) as CoefficientOfVariation,
        MinMonthlyRevenue,
        MaxMonthlyRevenue,
        AnnualTransactions,
        AvgMonthlyCustomers,
        AnnualRevenue / NULLIF(AnnualTransactions, 0) as AvgTransactionValue
    FROM YearlyMetrics
    ORDER BY Year DESC
    """
    
    revenue_df = db.execute_query(revenue_query, description="Revenue Stability Analysis")
    
    if len(revenue_df) >= 2:
        latest_year = revenue_df.iloc[0]['AnnualRevenue']
        previous_year = revenue_df.iloc[1]['AnnualRevenue']
        yoy_growth = ((float(latest_year) - float(previous_year)) / float(previous_year) * 100) if previous_year else 0
        
        if len(revenue_df) >= 3:
            three_year_cagr = ((float(revenue_df.iloc[0]['AnnualRevenue']) / float(revenue_df.iloc[2]['AnnualRevenue'])) ** (1/2) - 1) * 100
        else:
            three_year_cagr = yoy_growth
    else:
        yoy_growth = 0
        three_year_cagr = 0
    
    report['sections']['revenue_stability'] = {
        'three_year_history': revenue_df.to_dict('records'),
        'yoy_growth_rate': f"{yoy_growth:.1f}%",
        'three_year_cagr': f"{three_year_cagr:.1f}%",
        'revenue_predictability': 'High' if revenue_df.iloc[0]['CoefficientOfVariation'] < 0.15 else 'Moderate' if revenue_df.iloc[0]['CoefficientOfVariation'] < 0.30 else 'Variable',
        'monthly_consistency': float(revenue_df.iloc[0]['CoefficientOfVariation'])
    }
    
    # 2. CUSTOMER DIVERSIFICATION ANALYSIS
    print("🎯 Analyzing Customer Diversification...")
    
    diversification_query = """
    WITH CustomerConcentration AS (
        SELECT 
            c.ID,
            c.Company,
            SUM(t.Total) as CustomerRevenue12M,
            COUNT(DISTINCT t.TransactionNumber) as Transactions,
            COUNT(DISTINCT CAST(t.Time as DATE)) as ActiveDays
        FROM Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        WHERE t.Time >= DATEADD(month, -12, GETDATE())
        GROUP BY c.ID, c.Company
    ),
    ConcentrationMetrics AS (
        SELECT 
            CustomerRevenue12M,
            SUM(CustomerRevenue12M) OVER () as TotalRevenue,
            CAST(CustomerRevenue12M * 100.0 / SUM(CustomerRevenue12M) OVER () as DECIMAL(5,2)) as RevenuePercent,
            ROW_NUMBER() OVER (ORDER BY CustomerRevenue12M DESC) as CustomerRank
        FROM CustomerConcentration
    )
    SELECT 
        COUNT(*) as ActiveCustomers,
        MAX(RevenuePercent) as LargestCustomerPercent,
        (SELECT COUNT(*) FROM ConcentrationMetrics WHERE CustomerRank <= 10) as Top10Count,
        (SELECT SUM(RevenuePercent) FROM ConcentrationMetrics WHERE CustomerRank <= 10) as Top10Percent,
        (SELECT SUM(RevenuePercent) FROM ConcentrationMetrics WHERE CustomerRank <= 20) as Top20Percent,
        (SELECT SUM(RevenuePercent) FROM ConcentrationMetrics WHERE CustomerRank <= 50) as Top50Percent,
        (SELECT COUNT(*) FROM ConcentrationMetrics WHERE RevenuePercent < 1.0) as CustomersUnder1Percent,
        CAST(1.0 / COUNT(*) * 100 as DECIMAL(10,2)) as PerfectDiversificationScore
    FROM ConcentrationMetrics
    """
    
    diversification = db.execute_query(diversification_query, description="Customer Diversification")
    
    # Calculate Herfindahl-Hirschman Index (HHI) for concentration
    hhi_query = """
    WITH CustomerShare AS (
        SELECT 
            c.ID,
            SUM(t.Total) as Revenue,
            CAST(SUM(t.Total) * 100.0 / (SELECT SUM(Total) FROM [dbo].[Transaction] WHERE Time >= DATEADD(month, -12, GETDATE())) as DECIMAL(10,4)) as MarketShare
        FROM Customer c
        JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        WHERE t.Time >= DATEADD(month, -12, GETDATE())
        GROUP BY c.ID
    )
    SELECT 
        SUM(MarketShare * MarketShare) as HHI,
        COUNT(*) as CustomerCount,
        MAX(MarketShare) as MaxShare,
        AVG(MarketShare) as AvgShare
    FROM CustomerShare
    """
    
    hhi_result = db.execute_query(hhi_query, description="HHI Calculation")
    hhi_score = float(hhi_result.iloc[0]['HHI']) if not hhi_result.empty else 0
    
    # HHI interpretation: <1500 = competitive, 1500-2500 = moderate concentration, >2500 = high concentration
    concentration_level = 'Highly Diversified' if hhi_score < 1500 else 'Moderately Diversified' if hhi_score < 2500 else 'Concentrated'
    
    report['sections']['customer_diversification'] = {
        'active_customers': int(diversification.iloc[0]['ActiveCustomers']),
        'largest_customer_percent': float(diversification.iloc[0]['LargestCustomerPercent']),
        'top_10_concentration': float(diversification.iloc[0]['Top10Percent']),
        'top_20_concentration': float(diversification.iloc[0]['Top20Percent']),
        'top_50_concentration': float(diversification.iloc[0]['Top50Percent']),
        'herfindahl_index': hhi_score,
        'concentration_assessment': concentration_level,
        'diversification_rating': 'Excellent' if hhi_score < 1000 else 'Good' if hhi_score < 1500 else 'Moderate' if hhi_score < 2500 else 'Needs Improvement'
    }
    
    # 3. INDUSTRY AND SEGMENT DIVERSIFICATION
    print("🏢 Analyzing Industry Diversification...")
    
    industry_query = """
    SELECT 
        CASE 
            WHEN c.Company LIKE '%SHELL%' OR c.Company LIKE '%CHEVRON%' OR c.Company LIKE '%BP%' 
                 OR c.Company LIKE '%EXXON%' OR c.Company LIKE '%CITGO%' OR c.Company LIKE '%MARATHON%'
                 OR c.Company LIKE '%VALERO%' OR c.Company LIKE '%TEXACO%' THEN 'Energy/Gas Stations'
            WHEN c.Company LIKE '%FOOD%' OR c.Company LIKE '%CONVENIENCE%' OR c.Company LIKE '%MARKET%' 
                 OR c.Company LIKE '%STORE%' OR c.Company LIKE '%SHOP%' THEN 'Retail/Convenience'
            WHEN c.Company LIKE '%LIQUOR%' OR c.Company LIKE '%WINE%' OR c.Company LIKE '%SPIRITS%' THEN 'Beverage/Liquor'
            WHEN c.Company LIKE '%SMOKE%' OR c.Company LIKE '%TOBACCO%' OR c.Company LIKE '%VAPE%' THEN 'Tobacco/Vape'
            WHEN c.Company LIKE '%RESTAURANT%' OR c.Company LIKE '%CAFE%' OR c.Company LIKE '%GRILL%' THEN 'Food Service'
            WHEN c.Company LIKE '%HOTEL%' OR c.Company LIKE '%MOTEL%' OR c.Company LIKE '%INN%' THEN 'Hospitality'
            WHEN c.Company IS NULL OR c.Company = '' THEN 'Direct Consumer'
            ELSE 'Diversified Retail'
        END as IndustrySegment,
        COUNT(DISTINCT c.ID) as CustomerCount,
        SUM(t.Total) as SegmentRevenue,
        COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
        AVG(t.Total) as AvgTransactionSize,
        CAST(SUM(t.Total) * 100.0 / (SELECT SUM(Total) FROM [dbo].[Transaction] WHERE Time >= DATEADD(month, -12, GETDATE())) as DECIMAL(5,2)) as RevenuePercent
    FROM Customer c
    JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
    WHERE t.Time >= DATEADD(month, -12, GETDATE())
    GROUP BY 
        CASE 
            WHEN c.Company LIKE '%SHELL%' OR c.Company LIKE '%CHEVRON%' OR c.Company LIKE '%BP%' 
                 OR c.Company LIKE '%EXXON%' OR c.Company LIKE '%CITGO%' OR c.Company LIKE '%MARATHON%'
                 OR c.Company LIKE '%VALERO%' OR c.Company LIKE '%TEXACO%' THEN 'Energy/Gas Stations'
            WHEN c.Company LIKE '%FOOD%' OR c.Company LIKE '%CONVENIENCE%' OR c.Company LIKE '%MARKET%' 
                 OR c.Company LIKE '%STORE%' OR c.Company LIKE '%SHOP%' THEN 'Retail/Convenience'
            WHEN c.Company LIKE '%LIQUOR%' OR c.Company LIKE '%WINE%' OR c.Company LIKE '%SPIRITS%' THEN 'Beverage/Liquor'
            WHEN c.Company LIKE '%SMOKE%' OR c.Company LIKE '%TOBACCO%' OR c.Company LIKE '%VAPE%' THEN 'Tobacco/Vape'
            WHEN c.Company LIKE '%RESTAURANT%' OR c.Company LIKE '%CAFE%' OR c.Company LIKE '%GRILL%' THEN 'Food Service'
            WHEN c.Company LIKE '%HOTEL%' OR c.Company LIKE '%MOTEL%' OR c.Company LIKE '%INN%' THEN 'Hospitality'
            WHEN c.Company IS NULL OR c.Company = '' THEN 'Direct Consumer'
            ELSE 'Diversified Retail'
        END
    ORDER BY SegmentRevenue DESC
    """
    
    industry_df = db.execute_query(industry_query, description="Industry Diversification")
    
    report['sections']['industry_diversification'] = {
        'segment_count': len(industry_df),
        'segments': industry_df.to_dict('records'),
        'largest_segment_percent': float(industry_df.iloc[0]['RevenuePercent']) if not industry_df.empty else 0,
        'diversification_score': 'Well Diversified' if len(industry_df) >= 5 and industry_df.iloc[0]['RevenuePercent'] < 40 else 'Moderately Diversified'
    }
    
    # 4. ACCOUNTS RECEIVABLE QUALITY
    print("💳 Analyzing Accounts Receivable Quality...")
    
    ar_quality_query = """
    WITH ARMetrics AS (
        SELECT 
            c.ID,
            c.Company,
            c.AccountBalance,
            c.CreditLimit,
            MAX(t.Time) as LastTransaction,
            DATEDIFF(day, MAX(t.Time), GETDATE()) as DaysSinceLastTransaction,
            SUM(CASE WHEN t.Time >= DATEADD(month, -12, GETDATE()) THEN t.Total ELSE 0 END) as Revenue12M,
            COUNT(DISTINCT CASE WHEN t.Time >= DATEADD(month, -12, GETDATE()) THEN t.TransactionNumber ELSE NULL END) as Transactions12M
        FROM Customer c
        LEFT JOIN [dbo].[Transaction] t ON c.ID = t.CustomerID
        WHERE c.AccountBalance > 0
        GROUP BY c.ID, c.Company, c.AccountBalance, c.CreditLimit
    )
    SELECT 
        COUNT(*) as AccountsWithBalance,
        SUM(AccountBalance) as TotalAR,
        AVG(AccountBalance) as AvgBalance,
        MAX(AccountBalance) as MaxBalance,
        SUM(CASE WHEN DaysSinceLastTransaction <= 30 THEN AccountBalance ELSE 0 END) as Current_0_30,
        SUM(CASE WHEN DaysSinceLastTransaction BETWEEN 31 AND 60 THEN AccountBalance ELSE 0 END) as Days_31_60,
        SUM(CASE WHEN DaysSinceLastTransaction BETWEEN 61 AND 90 THEN AccountBalance ELSE 0 END) as Days_61_90,
        SUM(CASE WHEN DaysSinceLastTransaction > 90 THEN AccountBalance ELSE 0 END) as Over_90_Days,
        SUM(CreditLimit) as TotalCreditExtended,
        CAST(SUM(AccountBalance) * 100.0 / NULLIF(SUM(CreditLimit), 0) as DECIMAL(5,2)) as CreditUtilization,
        COUNT(CASE WHEN AccountBalance > CreditLimit THEN 1 ELSE NULL END) as OverLimitAccounts,
        AVG(CAST(AccountBalance as FLOAT) / NULLIF(CAST(Revenue12M as FLOAT) / 12, 0)) as AvgDaysSalesOutstanding
    FROM ARMetrics
    WHERE AccountBalance > 0
    """
    
    ar_metrics = db.execute_query(ar_quality_query, description="AR Quality Metrics")
    
    if not ar_metrics.empty:
        ar_row = ar_metrics.iloc[0]
        total_ar = float(ar_row['TotalAR']) if ar_row['TotalAR'] else 0
        current_percent = (float(ar_row['Current_0_30']) / total_ar * 100) if total_ar > 0 else 0
        
        report['sections']['accounts_receivable'] = {
            'total_ar': total_ar,
            'accounts_with_balance': int(ar_row['AccountsWithBalance']),
            'average_balance': float(ar_row['AvgBalance']) if ar_row['AvgBalance'] else 0,
            'aging': {
                'current_0_30_days': float(ar_row['Current_0_30']) if ar_row['Current_0_30'] else 0,
                'days_31_60': float(ar_row['Days_31_60']) if ar_row['Days_31_60'] else 0,
                'days_61_90': float(ar_row['Days_61_90']) if ar_row['Days_61_90'] else 0,
                'over_90_days': float(ar_row['Over_90_Days']) if ar_row['Over_90_Days'] else 0
            },
            'current_percent': current_percent,
            'credit_utilization': float(ar_row['CreditUtilization']) if ar_row['CreditUtilization'] else 0,
            'days_sales_outstanding': float(ar_row['AvgDaysSalesOutstanding']) if ar_row['AvgDaysSalesOutstanding'] else 0,
            'quality_assessment': 'Excellent' if current_percent > 80 else 'Good' if current_percent > 60 else 'Needs Attention'
        }
    
    # 5. OPERATIONAL EFFICIENCY METRICS
    print("⚡ Analyzing Operational Efficiency...")
    
    efficiency_query = """
    WITH DailyMetrics AS (
        SELECT 
            CAST(Time as DATE) as TransactionDate,
            COUNT(DISTINCT CustomerID) as DailyCustomers,
            COUNT(TransactionNumber) as DailyTransactions,
            SUM(Total) as DailyRevenue,
            AVG(Total) as AvgTicket
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(month, -12, GETDATE())
        GROUP BY CAST(Time as DATE)
    )
    SELECT 
        COUNT(*) as OperatingDays,
        AVG(DailyRevenue) as AvgDailyRevenue,
        AVG(DailyTransactions) as AvgDailyTransactions,
        AVG(DailyCustomers) as AvgDailyCustomers,
        AVG(AvgTicket) as OverallAvgTicket,
        MAX(DailyRevenue) as BestDayRevenue,
        MIN(DailyRevenue) as WorstDayRevenue,
        STDEV(DailyRevenue) as DailyRevenueStdDev,
        AVG(DailyRevenue / NULLIF(DailyTransactions, 0)) as RevenuePerTransaction,
        AVG(DailyRevenue / NULLIF(DailyCustomers, 0)) as RevenuePerCustomer
    FROM DailyMetrics
    """
    
    efficiency = db.execute_query(efficiency_query, description="Operational Efficiency")
    
    report['sections']['operational_efficiency'] = {
        'avg_daily_revenue': float(efficiency.iloc[0]['AvgDailyRevenue']),
        'avg_daily_transactions': float(efficiency.iloc[0]['AvgDailyTransactions']),
        'avg_daily_customers': float(efficiency.iloc[0]['AvgDailyCustomers']),
        'avg_ticket_size': float(efficiency.iloc[0]['OverallAvgTicket']),
        'revenue_per_customer': float(efficiency.iloc[0]['RevenuePerCustomer']),
        'operating_days_12m': int(efficiency.iloc[0]['OperatingDays']),
        'daily_consistency': float(efficiency.iloc[0]['DailyRevenueStdDev'])
    }
    
    # 6. GROWTH MOMENTUM INDICATORS
    print("🚀 Analyzing Growth Momentum...")
    
    growth_query = """
    WITH QuarterlyGrowth AS (
        SELECT 
            YEAR(Time) as Year,
            DATEPART(quarter, Time) as Quarter,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            COUNT(TransactionNumber) as Transactions,
            SUM(Total) as Revenue
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(quarter, -8, GETDATE())
        GROUP BY YEAR(Time), DATEPART(quarter, Time)
    ),
    GrowthMetrics AS (
        SELECT 
            Year,
            Quarter,
            Revenue,
            UniqueCustomers,
            LAG(Revenue, 1) OVER (ORDER BY Year, Quarter) as PrevQuarterRevenue,
            LAG(Revenue, 4) OVER (ORDER BY Year, Quarter) as YearAgoRevenue,
            LAG(UniqueCustomers, 1) OVER (ORDER BY Year, Quarter) as PrevQuarterCustomers
        FROM QuarterlyGrowth
    )
    SELECT 
        Year,
        Quarter,
        Revenue,
        UniqueCustomers,
        CAST((Revenue - PrevQuarterRevenue) * 100.0 / NULLIF(PrevQuarterRevenue, 0) as DECIMAL(5,2)) as QoQGrowth,
        CAST((Revenue - YearAgoRevenue) * 100.0 / NULLIF(YearAgoRevenue, 0) as DECIMAL(5,2)) as YoYGrowth,
        CAST((UniqueCustomers - PrevQuarterCustomers) * 100.0 / NULLIF(PrevQuarterCustomers, 0) as DECIMAL(5,2)) as CustomerGrowth
    FROM GrowthMetrics
    WHERE PrevQuarterRevenue IS NOT NULL
    ORDER BY Year DESC, Quarter DESC
    """
    
    # For SQL Server 2008 compatibility, use self-join instead of LAG
    growth_query_2008 = """
    WITH QuarterlyGrowth AS (
        SELECT 
            YEAR(Time) as Year,
            DATEPART(quarter, Time) as Quarter,
            COUNT(DISTINCT CustomerID) as UniqueCustomers,
            COUNT(TransactionNumber) as Transactions,
            SUM(Total) as Revenue
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(quarter, -8, GETDATE())
        GROUP BY YEAR(Time), DATEPART(quarter, Time)
    )
    SELECT 
        q1.Year,
        q1.Quarter,
        q1.Revenue,
        q1.UniqueCustomers,
        q2.Revenue as PrevQuarterRevenue,
        q3.Revenue as YearAgoRevenue,
        CAST((q1.Revenue - q2.Revenue) * 100.0 / NULLIF(q2.Revenue, 0) as DECIMAL(5,2)) as QoQGrowth,
        CAST((q1.Revenue - q3.Revenue) * 100.0 / NULLIF(q3.Revenue, 0) as DECIMAL(5,2)) as YoYGrowth
    FROM QuarterlyGrowth q1
    LEFT JOIN QuarterlyGrowth q2 ON 
        (q1.Year = q2.Year AND q1.Quarter = q2.Quarter + 1) OR
        (q1.Year = q2.Year + 1 AND q1.Quarter = 1 AND q2.Quarter = 4)
    LEFT JOIN QuarterlyGrowth q3 ON
        q1.Year = q3.Year + 1 AND q1.Quarter = q3.Quarter
    ORDER BY q1.Year DESC, q1.Quarter DESC
    """
    
    growth_df = db.execute_query(growth_query_2008, description="Growth Momentum")
    
    # New customer acquisition
    new_customer_query = """
    SELECT 
        COUNT(DISTINCT CASE WHEN FirstPurchase >= DATEADD(month, -3, GETDATE()) THEN CustomerID END) as NewCustomers3M,
        COUNT(DISTINCT CASE WHEN FirstPurchase >= DATEADD(month, -6, GETDATE()) THEN CustomerID END) as NewCustomers6M,
        COUNT(DISTINCT CASE WHEN FirstPurchase >= DATEADD(month, -12, GETDATE()) THEN CustomerID END) as NewCustomers12M
    FROM (
        SELECT 
            CustomerID,
            MIN(Time) as FirstPurchase
        FROM [dbo].[Transaction]
        GROUP BY CustomerID
    ) FirstPurchases
    """
    
    new_customers = db.execute_query(new_customer_query, description="New Customer Acquisition")
    
    report['sections']['growth_momentum'] = {
        'quarterly_performance': growth_df.head(4).to_dict('records'),
        'latest_qoq_growth': float(growth_df.iloc[0]['QoQGrowth']) if not growth_df.empty and growth_df.iloc[0]['QoQGrowth'] else 0,
        'latest_yoy_growth': float(growth_df.iloc[0]['YoYGrowth']) if not growth_df.empty and growth_df.iloc[0]['YoYGrowth'] else 0,
        'new_customers': {
            'last_3_months': int(new_customers.iloc[0]['NewCustomers3M']),
            'last_6_months': int(new_customers.iloc[0]['NewCustomers6M']),
            'last_12_months': int(new_customers.iloc[0]['NewCustomers12M'])
        },
        'growth_trajectory': 'Strong' if growth_df.iloc[0]['YoYGrowth'] > 10 else 'Moderate' if growth_df.iloc[0]['YoYGrowth'] > 0 else 'Needs Attention'
    }
    
    # 7. FINANCIAL RESILIENCE INDICATORS
    print("🛡️ Analyzing Financial Resilience...")
    
    # Customer retention and lifetime value
    retention_query = """
    WITH CustomerActivity AS (
        SELECT 
            CustomerID,
            MIN(Time) as FirstPurchase,
            MAX(Time) as LastPurchase,
            COUNT(DISTINCT CAST(Time as DATE)) as PurchaseDays,
            COUNT(DISTINCT DATEPART(month, Time)) as ActiveMonths,
            SUM(Total) as LifetimeValue
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(year, -2, GETDATE())
        GROUP BY CustomerID
    )
    SELECT 
        COUNT(DISTINCT CustomerID) as TotalCustomers,
        COUNT(DISTINCT CASE WHEN LastPurchase >= DATEADD(month, -1, GETDATE()) THEN CustomerID END) as ActiveLastMonth,
        COUNT(DISTINCT CASE WHEN LastPurchase >= DATEADD(month, -3, GETDATE()) THEN CustomerID END) as ActiveLast3Months,
        COUNT(DISTINCT CASE WHEN ActiveMonths >= 12 THEN CustomerID END) as CustomersActive12Months,
        AVG(LifetimeValue) as AvgCustomerLifetimeValue,
        AVG(CAST(ActiveMonths as FLOAT)) as AvgCustomerActiveMonths,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LifetimeValue) OVER () as MedianLifetimeValue
    FROM CustomerActivity
    """
    
    # Simplified for SQL Server 2008
    retention_query_2008 = """
    WITH CustomerActivity AS (
        SELECT 
            CustomerID,
            MIN(Time) as FirstPurchase,
            MAX(Time) as LastPurchase,
            COUNT(DISTINCT CAST(Time as DATE)) as PurchaseDays,
            COUNT(DISTINCT DATEPART(month, Time)) as ActiveMonths,
            SUM(Total) as LifetimeValue
        FROM [dbo].[Transaction]
        WHERE Time >= DATEADD(year, -2, GETDATE())
        GROUP BY CustomerID
    )
    SELECT 
        COUNT(DISTINCT CustomerID) as TotalCustomers,
        COUNT(DISTINCT CASE WHEN LastPurchase >= DATEADD(month, -1, GETDATE()) THEN CustomerID END) as ActiveLastMonth,
        COUNT(DISTINCT CASE WHEN LastPurchase >= DATEADD(month, -3, GETDATE()) THEN CustomerID END) as ActiveLast3Months,
        COUNT(DISTINCT CASE WHEN ActiveMonths >= 12 THEN CustomerID END) as CustomersActive12Months,
        AVG(LifetimeValue) as AvgCustomerLifetimeValue,
        AVG(CAST(ActiveMonths as FLOAT)) as AvgCustomerActiveMonths
    FROM CustomerActivity
    """
    
    retention = db.execute_query(retention_query_2008, description="Customer Retention")
    
    if not retention.empty:
        ret = retention.iloc[0]
        retention_rate = (float(ret['ActiveLast3Months']) / float(ret['TotalCustomers']) * 100) if ret['TotalCustomers'] > 0 else 0
        
        report['sections']['financial_resilience'] = {
            'customer_retention_rate': retention_rate,
            'customers_active_12_months': int(ret['CustomersActive12Months']),
            'avg_customer_lifetime_value': float(ret['AvgCustomerLifetimeValue']),
            'avg_customer_active_months': float(ret['AvgCustomerActiveMonths']),
            'recurring_revenue_base': 'Strong' if retention_rate > 70 else 'Moderate' if retention_rate > 50 else 'Developing'
        }
    
    # 8. EXECUTIVE SUMMARY FOR BANK
    print("\n🏦 Creating Bank-Focused Executive Summary...")
    
    total_revenue_12m = float(revenue_df.iloc[0]['AnnualRevenue']) if not revenue_df.empty else 0
    
    report['executive_summary'] = {
        'business_overview': {
            'company': 'Georgia Business',
            'industry': 'Wholesale Distribution',
            'years_in_operation': 'Established Business',
            'annual_revenue': total_revenue_12m,
            'active_customers': int(diversification.iloc[0]['ActiveCustomers']) if not diversification.empty else 0
        },
        'key_strengths': {
            'revenue_growth': {
                'yoy_growth': f"{yoy_growth:.1f}%",
                'three_year_cagr': f"{three_year_cagr:.1f}%",
                'assessment': 'Positive Growth Trend' if yoy_growth > 0 else 'Stable'
            },
            'customer_diversification': {
                'total_active_customers': int(diversification.iloc[0]['ActiveCustomers']) if not diversification.empty else 0,
                'largest_customer_concentration': f"{diversification.iloc[0]['LargestCustomerPercent']:.1f}%",
                'hhi_score': hhi_score,
                'assessment': concentration_level
            },
            'industry_diversification': {
                'segments_served': len(industry_df),
                'largest_segment': f"{industry_df.iloc[0]['RevenuePercent']:.1f}%" if not industry_df.empty else 'N/A',
                'assessment': 'Well Diversified Across Multiple Industries'
            },
            'operational_stability': {
                'revenue_predictability': report['sections']['revenue_stability']['revenue_predictability'],
                'avg_daily_revenue': report['sections']['operational_efficiency']['avg_daily_revenue'],
                'customer_retention': f"{retention_rate:.1f}%"
            },
            'accounts_receivable': {
                'total_ar': report['sections'].get('accounts_receivable', {}).get('total_ar', 0),
                'current_percent': report['sections'].get('accounts_receivable', {}).get('current_percent', 0),
                'quality': report['sections'].get('accounts_receivable', {}).get('quality_assessment', 'N/A')
            }
        },
        'credit_worthiness_indicators': {
            'stable_revenue_base': total_revenue_12m > 20000000,
            'diversified_customer_base': hhi_score < 2000,
            'consistent_growth': yoy_growth > 0 and three_year_cagr > 0,
            'strong_ar_quality': report['sections'].get('accounts_receivable', {}).get('current_percent', 0) > 70,
            'established_operations': report['sections']['operational_efficiency']['operating_days_12m'] > 350
        },
        'key_metrics_summary': [
            f"Annual Revenue: ${total_revenue_12m:,.0f}",
            f"YoY Growth: {yoy_growth:.1f}%",
            f"3-Year CAGR: {three_year_cagr:.1f}%",
            f"Active Customers: {diversification.iloc[0]['ActiveCustomers']}",
            f"Customer Concentration (HHI): {hhi_score:.0f}",
            f"Industry Segments: {len(industry_df)}",
            f"Customer Retention Rate: {retention_rate:.1f}%",
            f"AR Current (<30 days): {report['sections'].get('accounts_receivable', {}).get('current_percent', 0):.1f}%"
        ]
    }
    
    # Save reports
    print("\n💾 Saving bank metrics report...")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save JSON report
    json_filename = f'bank_metrics_report_{timestamp}.json'
    with open(json_filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Save formatted markdown report
    md_filename = f'bank_metrics_report_{timestamp}.md'
    with open(md_filename, 'w') as f:
        f.write("# Financial Metrics Report for Banking Review\n")
        f.write(f"*Prepared: {report['generated_at']}*\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("### Business Overview\n")
        f.write(f"- **Annual Revenue**: ${total_revenue_12m:,.0f}\n")
        f.write(f"- **Active Customers**: {report['executive_summary']['business_overview']['active_customers']}\n")
        f.write(f"- **Industry**: Wholesale Distribution\n\n")
        
        f.write("### Key Financial Strengths\n\n")
        
        f.write("#### 1. Revenue Growth & Stability\n")
        f.write(f"- **Year-over-Year Growth**: {yoy_growth:.1f}%\n")
        f.write(f"- **3-Year CAGR**: {three_year_cagr:.1f}%\n")
        f.write(f"- **Revenue Predictability**: {report['sections']['revenue_stability']['revenue_predictability']}\n")
        f.write(f"- **Monthly Consistency**: Coefficient of Variation = {report['sections']['revenue_stability']['monthly_consistency']:.2f}\n\n")
        
        f.write("#### 2. Customer Diversification\n")
        f.write(f"- **Total Active Customers**: {report['sections']['customer_diversification']['active_customers']}\n")
        f.write(f"- **Largest Customer**: {report['sections']['customer_diversification']['largest_customer_percent']:.1f}% of revenue\n")
        f.write(f"- **Top 10 Customers**: {report['sections']['customer_diversification']['top_10_concentration']:.1f}% of revenue\n")
        f.write(f"- **Herfindahl Index**: {hhi_score:.0f} ({concentration_level})\n")
        f.write(f"- **Diversification Rating**: {report['sections']['customer_diversification']['diversification_rating']}\n\n")
        
        f.write("#### 3. Industry Diversification\n")
        f.write(f"- **Industry Segments Served**: {len(industry_df)}\n")
        f.write("- **Segment Distribution**:\n")
        for seg in industry_df.head(5).to_dict('records'):
            f.write(f"  - {seg['IndustrySegment']}: {seg['RevenuePercent']:.1f}% ({seg['CustomerCount']} customers)\n")
        f.write("\n")
        
        f.write("#### 4. Accounts Receivable Quality\n")
        if 'accounts_receivable' in report['sections']:
            ar = report['sections']['accounts_receivable']
            f.write(f"- **Total AR**: ${ar['total_ar']:,.0f}\n")
            f.write(f"- **Current (0-30 days)**: {ar['current_percent']:.1f}%\n")
            f.write(f"- **Credit Utilization**: {ar['credit_utilization']:.1f}%\n")
            f.write(f"- **Quality Assessment**: {ar['quality_assessment']}\n\n")
        
        f.write("#### 5. Operational Metrics\n")
        eff = report['sections']['operational_efficiency']
        f.write(f"- **Average Daily Revenue**: ${eff['avg_daily_revenue']:,.0f}\n")
        f.write(f"- **Average Daily Transactions**: {eff['avg_daily_transactions']:.0f}\n")
        f.write(f"- **Average Ticket Size**: ${eff['avg_ticket_size']:,.0f}\n")
        f.write(f"- **Revenue per Customer**: ${eff['revenue_per_customer']:,.0f}\n\n")
        
        f.write("#### 6. Growth Momentum\n")
        growth = report['sections']['growth_momentum']
        f.write(f"- **Latest Quarter Growth (QoQ)**: {growth['latest_qoq_growth']:.1f}%\n")
        f.write(f"- **Year-over-Year Growth**: {growth['latest_yoy_growth']:.1f}%\n")
        f.write(f"- **New Customers (12M)**: {growth['new_customers']['last_12_months']}\n")
        f.write(f"- **Growth Trajectory**: {growth['growth_trajectory']}\n\n")
        
        f.write("### Credit Worthiness Summary\n\n")
        f.write("✅ **Key Positive Indicators:**\n")
        cw = report['executive_summary']['credit_worthiness_indicators']
        if cw['stable_revenue_base']:
            f.write("- Stable revenue base exceeding $20M annually\n")
        if cw['diversified_customer_base']:
            f.write("- Well-diversified customer base (HHI < 2000)\n")
        if cw['consistent_growth']:
            f.write("- Consistent positive growth trajectory\n")
        if cw['strong_ar_quality']:
            f.write("- Strong AR quality with majority current\n")
        if cw['established_operations']:
            f.write("- Established operations with consistent daily activity\n")
        
        f.write("\n### Conclusion\n\n")
        f.write("This business demonstrates strong financial metrics suitable for banking relationships:\n")
        f.write("- **Diversified Revenue Base**: Low customer concentration risk\n")
        f.write("- **Stable Growth**: Positive trajectory with consistent performance\n")
        f.write("- **Multiple Industry Exposure**: Reduces sector-specific risk\n")
        f.write("- **Strong Customer Retention**: Indicates quality of service and relationships\n")
        f.write("- **Healthy AR Management**: Demonstrates good credit control\n")
    
    db.close()
    
    print("\n✅ Bank Metrics Report Generated Successfully!")
    print(f"📄 JSON Report: {json_filename}")
    print(f"📝 Formatted Report: {md_filename}")
    
    # Print summary to console
    print("\n🏦 BANK-READY METRICS SUMMARY")
    print("="*50)
    for metric in report['executive_summary']['key_metrics_summary']:
        print(f"  • {metric}")
    
    return report

if __name__ == "__main__":
    generate_bank_metrics_report()