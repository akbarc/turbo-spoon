#!/usr/bin/env python3
"""
Find customers with Ali in name and their cigarette purchases
"""

import os
os.environ['DB_SERVER'] = '10.1.10.105'

import database_pymssql as db
import pandas as pd

conn = db.SQLServerConnection()
if conn.connect():
    # Get ALL customers to search thoroughly
    search_query = '''
    SELECT
        c.ID,
        c.FirstName,
        c.LastName,
        c.Company,
        c.AccountNumber
    FROM Customer c
    '''

    customers_df = conn.execute_query(search_query, description='Get all customers')

    print(f'Total customers in database: {len(customers_df)}')

    if len(customers_df) > 0:
        # Convert to string and make uppercase for searching
        customers_df['FirstName'] = customers_df['FirstName'].fillna('').str.upper()
        customers_df['LastName'] = customers_df['LastName'].fillna('').str.upper()
        customers_df['Company'] = customers_df['Company'].fillna('').str.upper()

        # Search for Ali
        ali_mask = (
            customers_df['FirstName'].str.contains('ALI', na=False) |
            customers_df['LastName'].str.contains('ALI', na=False) |
            customers_df['Company'].str.contains('ALI', na=False)
        )

        ali_customers = customers_df[ali_mask]

        print(f'\\nCustomers with "ALI": {len(ali_customers)}')
        if len(ali_customers) > 0:
            print('\\nAll customers with ALI in their name/company:')
            for _, row in ali_customers.iterrows():
                print(f"  ID: {row['ID']} | {row['FirstName']} {row['LastName']} | Company: {row['Company']}")

            # Get cigarette purchases for ALL Ali customers
            customer_ids = ali_customers['ID'].tolist()
            customer_id_str = ','.join(map(str, customer_ids))

            purchases_query = f'''
            SELECT
                t.CustomerID,
                SUM(te.Quantity) as TotalCigaretteUnits,
                SUM(te.Price * te.Quantity) as TotalSpent,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                MIN(t.Time) as FirstPurchase,
                MAX(t.Time) as LastPurchase
            FROM TransactionEntry te
            INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber
            INNER JOIN Item i ON te.ItemID = i.ID
            LEFT JOIN Category c ON i.CategoryID = c.ID
            WHERE t.CustomerID IN ({customer_id_str})
                AND c.Name LIKE '%CIGARETTE%'
            GROUP BY t.CustomerID
            '''

            purchases_df = conn.execute_query(purchases_query, description='Get cigarette purchases')

            print('\\n**CIGARETTE PURCHASE SUMMARY:**')
            print('='*80)

            total_all_customers = 0

            if len(purchases_df) > 0:
                for _, row in purchases_df.iterrows():
                    cust_info = ali_customers[ali_customers['ID'] == row['CustomerID']].iloc[0]
                    units = float(row['TotalCigaretteUnits'])
                    total_all_customers += units

                    print(f"\\n{cust_info['FirstName']} {cust_info['LastName']} ({cust_info['Company']})")
                    print(f"  Total Cigarette Units: {units:,.0f}")
                    print(f"  Total Spent: ${float(row['TotalSpent']):,.2f}")
                    print(f"  Transactions: {row['Transactions']}")
                    print(f"  Date Range: {row['FirstPurchase']} to {row['LastPurchase']}")

                print('\\n' + '='*80)
                print(f'TOTAL CIGARETTE UNITS FOR ALL "ALI" CUSTOMERS: {total_all_customers:,.0f}')
            else:
                print('No cigarette purchases found for any Ali customers')
        else:
            print('No customers found with "ALI" in their name or company')

    conn.close()