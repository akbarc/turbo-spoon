#!/usr/bin/env python3

from database_pymssql import SQLServerConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_customer_tables():
    """Find tables related to customers and transactions"""
    
    query = """
    SELECT 
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
        AND (
            LOWER(TABLE_NAME) LIKE '%customer%'
            OR LOWER(TABLE_NAME) LIKE '%client%'
            OR LOWER(TABLE_NAME) LIKE '%transaction%'
            OR LOWER(TABLE_NAME) LIKE '%sales%'
            OR LOWER(TABLE_NAME) LIKE '%order%'
            OR LOWER(TABLE_NAME) LIKE '%invoice%'
            OR LOWER(TABLE_NAME) LIKE '%receipt%'
            OR LOWER(TABLE_NAME) LIKE '%payment%'
            OR LOWER(TABLE_NAME) LIKE '%ledger%'
        )
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    try:
        with SQLServerConnection() as db:
            df = db.execute_query(query, description="Find customer/transaction tables")
            
            if not df.empty:
                print("\nTables related to customers and transactions:")
                print("=" * 70)
                for _, row in df.iterrows():
                    print(f"  {row['TABLE_SCHEMA']}.{row['TABLE_NAME']}")
            else:
                print("No tables found matching the criteria")
                
            # Also get all tables to see what's available
            all_tables_query = """
            SELECT TOP 50
                TABLE_SCHEMA,
                TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
            
            df_all = db.execute_query(all_tables_query, description="Get all tables")
            
            if not df_all.empty:
                print("\n\nFirst 50 tables in database:")
                print("=" * 70)
                for _, row in df_all.iterrows():
                    print(f"  {row['TABLE_SCHEMA']}.{row['TABLE_NAME']}")
                    
            return df, df_all
            
    except Exception as e:
        logger.error(f"Error finding tables: {e}")
        return None, None

if __name__ == "__main__":
    customer_tables, all_tables = find_customer_tables()