#!/usr/bin/env python3
"""
Find Sameer customer in the database
"""

from database_pymssql import SQLServerConnection

def find_sameer():
    db = SQLServerConnection()
    
    # Search for Sameer
    query = """
    SELECT TOP 20
        c.ID,
        c.AccountNumber,
        c.FirstName,
        c.LastName,
        c.Company,
        c.AccountBalance
    FROM Customer c
    WHERE c.FirstName LIKE '%SAMEER%' 
       OR c.LastName LIKE '%SAMEER%'
       OR c.Company LIKE '%SAMEER%'
       OR c.Company LIKE '%5 STAR%'
       OR c.Company LIKE '%SOMANI%'
    ORDER BY c.AccountBalance DESC
    """
    
    result = db.execute_query(query, "Find Sameer")
    print("\nCustomers matching 'SAMEER' or '5 STAR' or 'SOMANI':")
    print(result.to_string() if not result.empty else "No customers found")
    
    # Also check by account number pattern
    query2 = """
    SELECT TOP 10
        c.ID,
        c.AccountNumber,
        c.FirstName,
        c.LastName,
        c.Company,
        c.AccountBalance
    FROM Customer c
    WHERE c.AccountBalance > 40000
    ORDER BY c.AccountBalance DESC
    """
    
    result2 = db.execute_query(query2, "Find high balance customers")
    print("\nCustomers with balance > $40,000:")
    print(result2.to_string() if not result2.empty else "No customers found")

if __name__ == "__main__":
    find_sameer()