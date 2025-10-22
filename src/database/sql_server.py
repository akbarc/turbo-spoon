"""SQL Server database connection module."""
import os
import pymssql
import pandas as pd
from typing import Optional, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set TDS version for older SQL Server
os.environ['TDSVER'] = os.getenv('MSSQL_TDS_VERSION', '7.0')


class SQLServerConnection:
    """Manages connections to the SQL Server database."""

    def __init__(self):
        self.server = os.getenv('MSSQL_SERVER')
        self.user = os.getenv('MSSQL_USER')
        self.password = os.getenv('MSSQL_PASSWORD')
        self.database = os.getenv('MSSQL_DATABASE')
        self.tds_version = os.getenv('MSSQL_TDS_VERSION', '7.0')
        self.timeout = int(os.getenv('MSSQL_TIMEOUT', '30'))

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = pymssql.connect(
                server=self.server,
                user=self.user,
                password=self.password,
                database=self.database,
                tds_version=self.tds_version,
                timeout=self.timeout
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as a DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return rows affected."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def test_connection(self) -> tuple[bool, str]:
        """Test the database connection."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                return True, f"Connected successfully!\n{version}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_tables(self) -> pd.DataFrame:
        """Get list of all tables in the database."""
        query = """
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        return self.execute_query(query)

    def get_table_info(self, table_name: str, schema: str = 'dbo') -> pd.DataFrame:
        """Get column information for a specific table."""
        query = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s
        ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(query, (table_name, schema))


# Global instance
db = SQLServerConnection()
