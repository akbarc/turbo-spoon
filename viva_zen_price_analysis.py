#!/usr/bin/env python3

import pandas as pd
from datetime import datetime, timedelta
from database_pymssql import SQLServerConnection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_viva_zen_prices():
    """Analyze Viva Zen product prices over the past 30 days"""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logger.info(f"Analyzing Viva Zen prices from {start_date_str} to {end_date_str}")
    
    # Query for Viva Zen products and their sales
    query = f"""
    WITH VivaSalesData AS (
        SELECT 
            i.ID as ItemID,
            i.ItemLookupCode,
            i.Description,
            i.Cost as CurrentCost,
            i.Price as CurrentRetailPrice,
            te.Price as SoldPrice,
            te.Cost as SoldCost,
            te.Quantity,
            t.[Time] as TransactionTime,
            t.TransactionNumber,
            c.Company as CustomerName
        FROM [Transaction] t
        INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
        INNER JOIN Item i ON te.ItemID = i.ID
        LEFT JOIN Customer c ON t.CustomerID = c.ID
        WHERE UPPER(i.Description) LIKE '%VIVA ZEN%'
            AND t.[Time] >= '{start_date_str}'
            AND t.[Time] <= '{end_date_str}'
            AND te.Quantity > 0
            AND te.Price > 0
    ),
    ItemSummary AS (
        SELECT 
            ItemID,
            ItemLookupCode,
            Description,
            CurrentCost,
            CurrentRetailPrice,
            COUNT(DISTINCT TransactionNumber) as TotalTransactions,
            SUM(Quantity) as TotalUnitsSold,
            MIN(SoldPrice) as MinPrice,
            MAX(SoldPrice) as MaxPrice,
            AVG(SoldPrice) as AvgPrice,
            MIN(SoldCost) as MinCost,
            MAX(SoldCost) as MaxCost,
            AVG(SoldCost) as AvgCost,
            MAX(TransactionTime) as LastSoldDate
        FROM VivaSalesData
        GROUP BY ItemID, ItemLookupCode, Description, CurrentCost, CurrentRetailPrice
    )
    SELECT 
        ItemLookupCode,
        Description,
        TotalTransactions,
        TotalUnitsSold,
        CurrentCost,
        CurrentRetailPrice,
        MinPrice,
        MaxPrice,
        AvgPrice,
        MinCost,
        MaxCost,
        AvgCost,
        LastSoldDate,
        (AvgPrice - AvgCost) as AvgMargin,
        CASE 
            WHEN AvgCost > 0 THEN ((AvgPrice - AvgCost) / AvgPrice) * 100 
            ELSE 0 
        END as AvgMarginPercent
    FROM ItemSummary
    ORDER BY Description, LastSoldDate DESC
    """
    
    # Query for detailed transaction history
    detail_query = f"""
    SELECT 
        i.ItemLookupCode,
        i.Description,
        t.[Time] as TransactionDate,
        te.Price as SoldPrice,
        te.Cost as SoldCost,
        te.Quantity,
        te.Price * te.Quantity as TotalRevenue,
        (te.Price - te.Cost) * te.Quantity as GrossProfit,
        c.Company as CustomerName,
        t.TransactionNumber
    FROM [Transaction] t
    INNER JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i ON te.ItemID = i.ID
    LEFT JOIN Customer c ON t.CustomerID = c.ID
    WHERE UPPER(i.Description) LIKE '%VIVA ZEN%'
        AND t.[Time] >= '{start_date_str}'
        AND t.[Time] <= '{end_date_str}'
        AND te.Quantity > 0
        AND te.Price > 0
    ORDER BY i.Description, t.[Time] DESC
    """
    
    try:
        with SQLServerConnection() as db:
            # Execute queries
            df_summary = db.execute_query(query, description="Viva Zen price summary")
            df_detail = db.execute_query(detail_query, description="Viva Zen transaction details")
            
            # Create output file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"viva_zen_price_report_{timestamp}.txt"
            
            with open(output_file, 'w') as f:
                # Header
                f.write("="*100 + "\n")
                f.write(" "*30 + "VIVA ZEN PRICE ANALYSIS REPORT\n")
                f.write("="*100 + "\n")
                f.write(f"Analysis Period: {start_date_str} to {end_date_str} (Last 30 Days)\n")
                f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*100 + "\n\n")
                
                if df_summary.empty:
                    f.write("No Viva Zen products sold in the past 30 days.\n")
                else:
                    # Overall summary
                    total_products = len(df_summary)
                    total_units = df_summary['TotalUnitsSold'].sum()
                    total_transactions = df_summary['TotalTransactions'].sum()
                    overall_avg_price = df_detail['SoldPrice'].mean() if not df_detail.empty else 0
                    overall_avg_cost = df_detail['SoldCost'].mean() if not df_detail.empty else 0
                    
                    f.write("EXECUTIVE SUMMARY\n")
                    f.write("-"*100 + "\n")
                    f.write(f"Total Viva Zen Products Found: {total_products}\n")
                    f.write(f"Total Units Sold: {total_units:,.0f}\n")
                    f.write(f"Total Transactions: {total_transactions:,}\n")
                    f.write(f"Overall Average Selling Price: ${overall_avg_price:.2f}\n")
                    f.write(f"Overall Average Cost: ${overall_avg_cost:.2f}\n")
                    f.write(f"Overall Average Margin: ${overall_avg_price - overall_avg_cost:.2f} ({((overall_avg_price - overall_avg_cost)/overall_avg_price*100) if overall_avg_price > 0 else 0:.1f}%)\n")
                    
                    # Product-by-product analysis
                    f.write("\n" + "="*100 + "\n")
                    f.write("PRODUCT-BY-PRODUCT PRICE ANALYSIS\n")
                    f.write("="*100 + "\n\n")
                    
                    for idx, row in df_summary.iterrows():
                        f.write(f"{'='*80}\n")
                        f.write(f"PRODUCT: {row['Description']}\n")
                        f.write(f"SKU: {row['ItemLookupCode']}\n")
                        f.write(f"{'='*80}\n")
                        
                        f.write(f"\nSALES ACTIVITY (Last 30 Days):\n")
                        f.write(f"  • Total Transactions: {row['TotalTransactions']:,}\n")
                        f.write(f"  • Total Units Sold: {row['TotalUnitsSold']:,.0f}\n")
                        f.write(f"  • Last Sold: {row['LastSoldDate']}\n")
                        
                        f.write(f"\nPRICE METRICS:\n")
                        f.write(f"  • Current Retail Price: ${row['CurrentRetailPrice']:.2f}\n")
                        f.write(f"  • Average Selling Price: ${row['AvgPrice']:.2f}\n")
                        f.write(f"  • Lowest Price: ${row['MinPrice']:.2f}\n")
                        f.write(f"  • Highest Price: ${row['MaxPrice']:.2f}\n")
                        f.write(f"  • Price Range: ${row['MaxPrice'] - row['MinPrice']:.2f}\n")
                        
                        f.write(f"\nCOST METRICS:\n")
                        f.write(f"  • Current Cost: ${row['CurrentCost']:.2f}\n")
                        f.write(f"  • Average Cost: ${row['AvgCost']:.2f}\n")
                        f.write(f"  • Lowest Cost: ${row['MinCost']:.2f}\n")
                        f.write(f"  • Highest Cost: ${row['MaxCost']:.2f}\n")
                        
                        f.write(f"\nPROFITABILITY:\n")
                        f.write(f"  • Average Margin: ${row['AvgMargin']:.2f}\n")
                        f.write(f"  • Average Margin %: {row['AvgMarginPercent']:.1f}%\n")
                        
                        # Get recent transactions for this product
                        product_details = df_detail[df_detail['Description'] == row['Description']].head(10)
                        if not product_details.empty:
                            f.write(f"\nRECENT TRANSACTIONS (Last 10):\n")
                            f.write(f"  {'Date':<20} {'Price':<10} {'Cost':<10} {'Qty':<6} {'Customer':<30}\n")
                            f.write(f"  {'-'*76}\n")
                            for _, detail in product_details.iterrows():
                                date_str = detail['TransactionDate'].strftime('%Y-%m-%d %H:%M')
                                customer = str(detail['CustomerName'])[:29] if detail['CustomerName'] else 'Walk-in'
                                f.write(f"  {date_str:<20} ${detail['SoldPrice']:<9.2f} ${detail['SoldCost']:<9.2f} {detail['Quantity']:<6.0f} {customer:<30}\n")
                        
                        f.write("\n")
                    
                    # Price variance analysis
                    if not df_detail.empty:
                        f.write("="*100 + "\n")
                        f.write("PRICE VARIANCE ANALYSIS\n")
                        f.write("="*100 + "\n\n")
                        
                        variance_analysis = df_detail.groupby('Description').agg({
                            'SoldPrice': ['std', 'count'],
                            'SoldCost': 'std'
                        }).round(2)
                        
                        f.write(f"{'Product':<50} {'Price StdDev':<15} {'Cost StdDev':<15} {'# Sales':<10}\n")
                        f.write("-"*90 + "\n")
                        
                        for product in variance_analysis.index:
                            price_std = variance_analysis.loc[product, ('SoldPrice', 'std')]
                            cost_std = variance_analysis.loc[product, ('SoldCost', 'std')]
                            count = variance_analysis.loc[product, ('SoldPrice', 'count')]
                            f.write(f"{product[:49]:<50} ${price_std:<14.2f} ${cost_std:<14.2f} {count:<10.0f}\n")
                
                f.write("\n" + "="*100 + "\n")
                f.write("END OF REPORT\n")
                f.write("="*100 + "\n")
            
            # Also save to CSV for detailed analysis
            csv_file = f"viva_zen_details_{timestamp}.csv"
            df_detail.to_csv(csv_file, index=False)
            
            print(f"\n✅ Viva Zen price analysis complete!")
            print(f"📄 Report saved to: {output_file}")
            print(f"📊 Details saved to: {csv_file}")
            
            # Display summary
            if not df_summary.empty:
                print("\nQUICK SUMMARY:")
                print("-"*50)
                print(f"Products Found: {total_products}")
                print(f"Total Units Sold (30 days): {total_units:,.0f}")
                print(f"Average Price: ${overall_avg_price:.2f}")
                print(f"Average Cost: ${overall_avg_cost:.2f}")
                print(f"Average Margin: {((overall_avg_price - overall_avg_cost)/overall_avg_price*100) if overall_avg_price > 0 else 0:.1f}%")
                
                print("\nPRODUCT BREAKDOWN:")
                for _, row in df_summary.iterrows():
                    print(f"\n{row['Description']}")
                    print(f"  Price Range: ${row['MinPrice']:.2f} - ${row['MaxPrice']:.2f} (Avg: ${row['AvgPrice']:.2f})")
                    print(f"  Cost: ${row['AvgCost']:.2f}")
                    print(f"  Units Sold: {row['TotalUnitsSold']:.0f}")
            else:
                print("\nNo Viva Zen products found in the past 30 days.")
            
            return output_file, csv_file
            
    except Exception as e:
        logger.error(f"Error analyzing Viva Zen prices: {e}")
        return None, None

if __name__ == "__main__":
    report_file, csv_file = analyze_viva_zen_prices()
    
    if report_file:
        print(f"\n✅ Analysis completed successfully!")
        print(f"📄 Full report: {report_file}")
        print(f"📊 Data file: {csv_file}")
    else:
        print("\n❌ Analysis failed. Please check the logs.")