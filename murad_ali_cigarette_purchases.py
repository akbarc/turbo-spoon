#!/usr/bin/env python3
"""
Murad Ali Cigarette Purchase Analysis
Total units purchased by Murad Ali and his customer group
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd
from datetime import datetime

def get_murad_ali_purchases():
    """Get all cigarette purchases by Murad Ali and associated customers"""

    conn = db.SQLServerConnection()
    if not conn.connect():
        print("Failed to connect to database")
        return None

    try:
        # First, find Murad Ali customer ID(s)
        customer_query = """
        SELECT
            c.ID as CustomerID,
            c.FirstName,
            c.LastName,
            c.Company,
            c.CustomerID as CustomerCode,
            c.PriceLevel,
            c.TaxExempt,
            c.AccountNumber
        FROM Customer c
        WHERE (UPPER(c.FirstName) LIKE '%MURAD%' AND UPPER(c.LastName) LIKE '%ALI%')
           OR UPPER(c.Company) LIKE '%MURAD ALI%'
           OR UPPER(c.Company) LIKE '%MURAD%ALI%'
           OR (UPPER(c.FirstName) = 'MURAD' AND UPPER(c.LastName) = 'ALI')
        """

        customers_df = conn.execute_query(customer_query, description="Find Murad Ali customers")

        if len(customers_df) == 0:
            # Try alternate search
            customer_query2 = """
            SELECT TOP 100
                c.ID as CustomerID,
                c.FirstName,
                c.LastName,
                c.Company,
                c.CustomerID as CustomerCode
            FROM Customer c
            WHERE UPPER(c.FirstName) LIKE '%MURAD%'
               OR UPPER(c.LastName) LIKE '%MURAD%'
               OR UPPER(c.Company) LIKE '%MURAD%'
            """
            customers_df = conn.execute_query(customer_query2, description="Search for Murad variations")

        print(f"Found {len(customers_df)} customer records related to Murad Ali")

        if len(customers_df) > 0:
            print("\nCustomer Records Found:")
            for _, cust in customers_df.iterrows():
                print(f"  ID: {cust['CustomerID']} | Name: {cust['FirstName']} {cust['LastName']} | Company: {cust['Company']}")

            # Get customer IDs
            customer_ids = customers_df['CustomerID'].tolist()
            customer_id_str = ','.join(map(str, customer_ids))

            # Query for cigarette purchases by these customers
            purchases_query = f"""
            SELECT
                t.CustomerID,
                c.FirstName,
                c.LastName,
                c.Company,
                t.TransactionNumber,
                t.Time as PurchaseDate,
                i.ItemLookupCode as SKU,
                i.Description as Product,
                te.Quantity as UnitsPurchased,
                te.Price as UnitPrice,
                (te.Price * te.Quantity) as TotalAmount,
                CASE
                    WHEN UPPER(i.Description) LIKE '%MARLBORO%' OR UPPER(i.Description) LIKE '%MARL %' THEN 'MARLBORO'
                    WHEN UPPER(i.Description) LIKE '%NEWPORT%' THEN 'NEWPORT'
                    WHEN UPPER(i.Description) LIKE '%CAMEL%' THEN 'CAMEL'
                    WHEN UPPER(i.Description) LIKE '%AMERICAN SPIRIT%' THEN 'AMERICAN SPIRIT'
                    WHEN UPPER(i.Description) LIKE '%WINSTON%' THEN 'WINSTON'
                    WHEN UPPER(i.Description) LIKE '%KOOL%' THEN 'KOOL'
                    WHEN UPPER(i.Description) LIKE '%SALEM%' THEN 'SALEM'
                    WHEN UPPER(i.Description) LIKE '%VIRGINIA SLIM%' OR UPPER(i.Description) LIKE '%VIRG SL%' THEN 'VIRGINIA SLIMS'
                    WHEN UPPER(i.Description) LIKE '%PALL MALL%' THEN 'PALL MALL'
                    WHEN UPPER(i.Description) LIKE '%LUCKY STRIKE%' THEN 'LUCKY STRIKE'
                    WHEN UPPER(i.Description) LIKE '%PARLIAMENT%' THEN 'PARLIAMENT'
                    WHEN UPPER(i.Description) LIKE '%MAVERICK%' THEN 'MAVERICK'
                    WHEN UPPER(i.Description) LIKE '%L&M%' OR UPPER(i.Description) LIKE '%L & M%' THEN 'L&M'
                    ELSE 'OTHER'
                END as Brand
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            INNER JOIN Item i ON te.ItemID = i.ID
            INNER JOIN Customer c ON t.CustomerID = c.ID
            LEFT JOIN Category cat ON i.CategoryID = cat.ID
            WHERE t.CustomerID IN ({customer_id_str})
                AND cat.Name LIKE '%CIGARETTE%'
                AND i.Description NOT LIKE '%LIGHTER%'
                AND i.Description NOT LIKE '%TORCH%'
                AND i.Description NOT LIKE '%PAPER%'
                AND i.Description NOT LIKE '%TUBE%'
                AND i.Description NOT LIKE '%MACHINE%'
                AND i.Description NOT LIKE '%CASE%'
            ORDER BY t.Time DESC
            """

            purchases_df = conn.execute_query(purchases_query, description="Get Murad Ali cigarette purchases")

            # Also check if there's a customer group
            group_query = f"""
            SELECT DISTINCT
                cg.Name as GroupName,
                c.ID as CustomerID,
                c.FirstName,
                c.LastName,
                c.Company
            FROM Customer c
            LEFT JOIN CustomerGroup cg ON c.CustomerGroupID = cg.ID
            WHERE c.ID IN ({customer_id_str})
               OR c.CustomerGroupID IN (
                   SELECT CustomerGroupID
                   FROM Customer
                   WHERE ID IN ({customer_id_str})
                   AND CustomerGroupID IS NOT NULL
               )
            """

            group_df = conn.execute_query(group_query, description="Check customer group")

            return purchases_df, customers_df, group_df
        else:
            print("No customers found matching 'Murad Ali'")
            return None, None, None

    finally:
        conn.close()

def main():
    print("="*80)
    print("MURAD ALI CIGARETTE PURCHASE ANALYSIS")
    print("="*80)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Get purchase data
    purchases_df, customers_df, group_df = get_murad_ali_purchases()

    if purchases_df is not None and len(purchases_df) > 0:
        # Convert numeric columns
        purchases_df['UnitsPurchased'] = pd.to_numeric(purchases_df['UnitsPurchased'], errors='coerce')
        purchases_df['UnitPrice'] = pd.to_numeric(purchases_df['UnitPrice'], errors='coerce')
        purchases_df['TotalAmount'] = pd.to_numeric(purchases_df['TotalAmount'], errors='coerce')

        # Overall summary
        total_units = purchases_df['UnitsPurchased'].sum()
        total_amount = purchases_df['TotalAmount'].sum()
        total_transactions = purchases_df['TransactionNumber'].nunique()
        date_range = f"{purchases_df['PurchaseDate'].min()} to {purchases_df['PurchaseDate'].max()}"

        print("OVERALL SUMMARY")
        print("-"*80)
        print(f"Total Cigarette Units Purchased: {total_units:,.0f}")
        print(f"Total Amount Spent: ${total_amount:,.2f}")
        print(f"Total Transactions: {total_transactions}")
        print(f"Date Range: {date_range}\n")

        # Check for customer group
        if group_df is not None and len(group_df) > 0:
            print("CUSTOMER GROUP INFORMATION")
            print("-"*80)
            for _, row in group_df.iterrows():
                if row['GroupName']:
                    print(f"Group: {row['GroupName']}")
                print(f"  Customer: {row['FirstName']} {row['LastName']} - {row['Company']}")
            print()

        # Summary by brand
        print("PURCHASES BY BRAND")
        print("-"*80)
        brand_summary = purchases_df.groupby('Brand').agg({
            'UnitsPurchased': 'sum',
            'TotalAmount': 'sum',
            'TransactionNumber': 'nunique'
        }).round(2)
        brand_summary.columns = ['Units', 'Total_Amount', 'Transactions']
        brand_summary = brand_summary.sort_values('Units', ascending=False)

        print(f"{'Brand':<20} {'Units':>10} {'Amount':>12} {'Transactions':>12}")
        print("-"*80)
        for brand, row in brand_summary.iterrows():
            print(f"{brand:<20} {row['Units']:10.0f} ${row['Total_Amount']:11,.2f} {row['Transactions']:12.0f}")

        # Summary by customer if multiple
        if len(customers_df) > 1:
            print("\nPURCHASES BY CUSTOMER")
            print("-"*80)
            customer_summary = purchases_df.groupby(['CustomerID', 'CustomerName', 'Company']).agg({
                'UnitsPurchased': 'sum',
                'TotalAmount': 'sum',
                'TransactionNumber': 'nunique'
            }).round(2)

            for (cust_id, name, company), row in customer_summary.iterrows():
                print(f"\n{name} ({company})")
                print(f"  Units: {row['UnitsPurchased']:,.0f}")
                print(f"  Amount: ${row['TotalAmount']:,.2f}")
                print(f"  Transactions: {row['TransactionNumber']:.0f}")

        # Monthly trend
        purchases_df['Month'] = pd.to_datetime(purchases_df['PurchaseDate']).dt.to_period('M')
        monthly_summary = purchases_df.groupby('Month').agg({
            'UnitsPurchased': 'sum',
            'TotalAmount': 'sum'
        }).round(2)

        if len(monthly_summary) > 0:
            print("\nMONTHLY PURCHASE TREND")
            print("-"*80)
            print(f"{'Month':<15} {'Units':>10} {'Amount':>12}")
            print("-"*80)
            for month, row in monthly_summary.tail(12).iterrows():
                print(f"{str(month):<15} {row['UnitsPurchased']:10.0f} ${row['TotalAmount']:11,.2f}")

        # Save to Excel
        with pd.ExcelWriter('murad_ali_cigarette_purchases.xlsx', engine='openpyxl') as writer:
            purchases_df.to_excel(writer, sheet_name='All_Purchases', index=False)
            brand_summary.to_excel(writer, sheet_name='By_Brand')
            monthly_summary.to_excel(writer, sheet_name='Monthly_Trend')

            if group_df is not None and len(group_df) > 0:
                group_df.to_excel(writer, sheet_name='Customer_Group', index=False)

        print(f"\n✅ Detailed report saved to: murad_ali_cigarette_purchases.xlsx")

    elif purchases_df is not None and len(purchases_df) == 0:
        print("No cigarette purchases found for Murad Ali")

        if customers_df is not None and len(customers_df) > 0:
            print(f"\nCustomer record exists but no cigarette purchases found")
            print("Customer details:")
            for _, cust in customers_df.iterrows():
                print(f"  {cust['FirstName']} {cust['LastName']} - {cust['Company']}")
    else:
        print("Could not find customer 'Murad Ali' in the database")
        print("\nSearching for similar names...")

        # Try to find similar customer names
        conn = db.SQLServerConnection()
        if conn.connect():
            similar_query = """
            SELECT TOP 20
                FirstName,
                LastName,
                Company,
                CustomerID
            FROM Customer
            WHERE FirstName LIKE 'M%'
               OR LastName LIKE 'ALI%'
            ORDER BY LastName, FirstName
            """
            similar_df = conn.execute_query(similar_query, description="Find similar names")

            if len(similar_df) > 0:
                print("\nSimilar customer names in database:")
                for _, row in similar_df.iterrows():
                    print(f"  {row['FirstName']} {row['LastName']} - {row['Company']}")

            conn.close()

if __name__ == "__main__":
    main()