"""SQLite database for overlay data (custom categories, mappings, etc.)."""
import sqlite3
import pandas as pd
from pathlib import Path
from contextlib import contextmanager
from typing import Optional


class OverlayDatabase:
    """Manages overlay data in SQLite."""

    def __init__(self, db_path: str = "data/overlay.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _initialize_database(self):
        """Create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Product recategorization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    original_category TEXT,
                    custom_category TEXT NOT NULL,
                    subcategory TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(product_id)
                )
            """)

            # Customer groups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES customer_groups(id),
                    UNIQUE(customer_id, group_id)
                )
            """)

            # Excise tax configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS excise_tax_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT,
                    product_category TEXT,
                    tax_rate REAL NOT NULL,
                    tax_type TEXT NOT NULL,
                    description TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Custom metrics/KPIs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL UNIQUE,
                    metric_sql TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as a DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=params or ())

    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount

    # Product category methods
    def add_product_category(self, product_id: str, custom_category: str,
                            subcategory: Optional[str] = None,
                            original_category: Optional[str] = None,
                            notes: Optional[str] = None):
        """Add or update a product's custom category."""
        query = """
            INSERT INTO product_categories
                (product_id, custom_category, subcategory, original_category, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(product_id) DO UPDATE SET
                custom_category = excluded.custom_category,
                subcategory = excluded.subcategory,
                original_category = excluded.original_category,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
        """
        return self.execute_non_query(query, (product_id, custom_category, subcategory,
                                               original_category, notes))

    def get_product_categories(self) -> pd.DataFrame:
        """Get all product category mappings."""
        return self.execute_query("SELECT * FROM product_categories ORDER BY custom_category")

    def get_product_category(self, product_id: str) -> Optional[dict]:
        """Get custom category for a specific product."""
        df = self.execute_query(
            "SELECT * FROM product_categories WHERE product_id = ?",
            (product_id,)
        )
        return df.to_dict('records')[0] if not df.empty else None

    # Customer group methods
    def create_customer_group(self, group_name: str, description: Optional[str] = None):
        """Create a new customer group."""
        query = "INSERT INTO customer_groups (group_name, description) VALUES (?, ?)"
        return self.execute_non_query(query, (group_name, description))

    def add_customer_to_group(self, customer_id: str, group_id: int):
        """Add a customer to a group."""
        query = "INSERT OR IGNORE INTO customer_group_members (customer_id, group_id) VALUES (?, ?)"
        return self.execute_non_query(query, (customer_id, group_id))

    def get_customer_groups(self) -> pd.DataFrame:
        """Get all customer groups."""
        return self.execute_query("SELECT * FROM customer_groups")

    # Excise tax methods
    def add_excise_tax_rule(self, tax_rate: float, tax_type: str,
                           product_id: Optional[str] = None,
                           product_category: Optional[str] = None,
                           description: Optional[str] = None):
        """Add an excise tax rule."""
        query = """
            INSERT INTO excise_tax_rules
                (product_id, product_category, tax_rate, tax_type, description)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_non_query(query, (product_id, product_category, tax_rate,
                                               tax_type, description))

    def get_excise_tax_rules(self, active_only: bool = True) -> pd.DataFrame:
        """Get all excise tax rules."""
        query = "SELECT * FROM excise_tax_rules"
        if active_only:
            query += " WHERE active = 1"
        return self.execute_query(query)


# Global instance
overlay_db = OverlayDatabase()
