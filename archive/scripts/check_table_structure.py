#!/usr/bin/env python3

from database_pymssql import SQLServerConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_table_structure():
    """Check the structure of relevant tables"""
    
    queries = {
        "Item columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Item'
        ORDER BY ORDINAL_POSITION
        """,
        
        "Department columns": """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Department'
        ORDER BY ORDINAL_POSITION
        """,
        
        "Category columns": """
        SELECT COLUMN_NAME, DATA_TYPE  
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'Category'
        ORDER BY ORDINAL_POSITION
        """,
        
        "TransactionEntry columns": """
        SELECT TOP 15 COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'TransactionEntry'
        ORDER BY ORDINAL_POSITION
        """,
        
        "Sample Item data": """
        SELECT TOP 3 * FROM Item
        """,
        
        "Sample Department data": """
        SELECT TOP 3 * FROM Department
        """,
        
        "Sample Category data": """
        SELECT TOP 3 * FROM Category
        """
    }
    
    try:
        with SQLServerConnection() as db:
            for name, query in queries.items():
                print(f"\n{'='*60}")
                print(f"{name}:")
                print('='*60)
                
                df = db.execute_query(query, description=name)
                if not df.empty:
                    print(df.to_string())
                else:
                    print(f"No data for {name}")
                    
    except Exception as e:
        logger.error(f"Error checking structure: {e}")

if __name__ == "__main__":
    check_table_structure()