#!/usr/bin/env python3
"""
Check total inventory quantities across different categories
"""

from database_pymssql import connection_pool

def check_total_inventory():
    """Calculate total inventory quantities"""
    
    print("=" * 80)
    print("TOTAL INVENTORY ANALYSIS")
    print("=" * 80)
    
    conn = connection_pool.get_connection()
    cursor = conn.cursor(as_dict=True)
    
    try:
        # 1. Total quantity across ALL products
        print("\n1. OVERALL INVENTORY:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_products,
                SUM(Quantity) as total_quantity,
                SUM(CASE WHEN Quantity > 0 THEN 1 ELSE 0 END) as products_in_stock,
                SUM(CASE WHEN Quantity = 0 THEN 1 ELSE 0 END) as products_out_of_stock,
                SUM(CASE WHEN Quantity < 0 THEN 1 ELSE 0 END) as products_negative
            FROM Item
        """)
        
        result = cursor.fetchone()
        print(f"Total Products:           {result['total_products']:,}")
        print(f"Total Quantity On Hand:   {result['total_quantity']:,.0f} units")
        print(f"Products In Stock:        {result['products_in_stock']:,}")
        print(f"Products Out of Stock:    {result['products_out_of_stock']:,}")
        print(f"Products Negative Stock:  {result['products_negative']:,}")
        
        # 2. MSA categories only
        print("\n2. MSA CATEGORIES INVENTORY:")
        print("-" * 40)
        msa_categories = [48, 23, 45, 11, 31, 56, 57, 81, 83, 49, 51]
        
        cursor.execute("""
            SELECT 
                COUNT(*) as msa_products,
                SUM(Quantity) as msa_quantity,
                SUM(CASE WHEN Quantity > 0 THEN 1 ELSE 0 END) as msa_in_stock
            FROM Item
            WHERE CategoryID IN ({})
        """.format(','.join(str(c) for c in msa_categories)))
        
        result = cursor.fetchone()
        print(f"MSA Products:             {result['msa_products']:,}")
        print(f"MSA Total Quantity:       {result['msa_quantity']:,.0f} units")
        print(f"MSA Products In Stock:    {result['msa_in_stock']:,}")
        
        # 3. Top categories by quantity
        print("\n3. TOP CATEGORIES BY QUANTITY:")
        print("-" * 40)
        cursor.execute("""
            SELECT TOP 10
                c.Name as CategoryName,
                COUNT(i.ID) as ProductCount,
                SUM(i.Quantity) as TotalQuantity
            FROM Item i
            JOIN Category c ON i.CategoryID = c.ID
            GROUP BY c.Name
            ORDER BY SUM(i.Quantity) DESC
        """)
        
        print(f"{'Category':<30} {'Products':>10} {'Total Qty':>15}")
        print("-" * 55)
        for row in cursor.fetchall():
            print(f"{row['CategoryName'][:30]:<30} {row['ProductCount']:>10,} {row['TotalQuantity']:>15,.0f}")
        
        # 4. Top products by quantity
        print("\n4. TOP PRODUCTS BY QUANTITY:")
        print("-" * 40)
        cursor.execute("""
            SELECT TOP 10
                ItemLookupCode,
                Description,
                Quantity
            FROM Item
            WHERE Quantity > 0
            ORDER BY Quantity DESC
        """)
        
        print(f"{'Item Code':<20} {'Description':<40} {'Quantity':>10}")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"{row['ItemLookupCode']:<20} {row['Description'][:40]:<40} {row['Quantity']:>10,.0f}")
        
        # 5. Inventory value (if cost data available)
        print("\n5. INVENTORY VALUE:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                SUM(Quantity * Cost) as total_cost_value,
                SUM(Quantity * Price) as total_retail_value,
                AVG(Cost) as avg_cost,
                AVG(Price) as avg_price
            FROM Item
            WHERE Quantity > 0
        """)
        
        result = cursor.fetchone()
        if result['total_cost_value']:
            print(f"Total Cost Value:         ${result['total_cost_value']:,.2f}")
            print(f"Total Retail Value:       ${result['total_retail_value']:,.2f}")
            print(f"Average Cost per Item:    ${result['avg_cost']:.2f}")
            print(f"Average Price per Item:   ${result['avg_price']:.2f}")
            print(f"Potential Margin:         ${result['total_retail_value'] - result['total_cost_value']:,.2f}")
        
    finally:
        cursor.close()
        connection_pool.return_connection(conn)

if __name__ == '__main__':
    check_total_inventory()