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

            # Customer groups - extended for SOUNDEX auto-grouping
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_key TEXT NOT NULL UNIQUE,
                    group_name TEXT NOT NULL,
                    description TEXT,
                    group_type TEXT DEFAULT 'manual',
                    soundex_last TEXT,
                    soundex_first TEXT,
                    member_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    customer_name TEXT,
                    customer_company TEXT,
                    soundex_last TEXT,
                    soundex_first TEXT,
                    is_primary BOOLEAN DEFAULT 0,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES customer_groups(id),
                    UNIQUE(customer_id, group_id)
                )
            """)

            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_groups_type
                ON customer_groups(group_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_group_members_customer
                ON customer_group_members(customer_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_group_members_group
                ON customer_group_members(group_id)
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

            # Customer group analytics cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_group_analytics (
                    group_id INTEGER PRIMARY KEY,
                    total_sales_30d REAL DEFAULT 0,
                    gross_profit_30d REAL DEFAULT 0,
                    gp_percentage_30d REAL DEFAULT 0,
                    ar_balance REAL DEFAULT 0,
                    pd_checks_count INTEGER DEFAULT 0,
                    pd_checks_total REAL DEFAULT 0,
                    transaction_count_30d INTEGER DEFAULT 0,
                    last_purchase DATE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES customer_groups(id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_group_analytics_sales
                ON customer_group_analytics(total_sales_30d DESC)
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
    def upsert_soundex_group(self, group_key: str, group_name: str,
                            soundex_last: str, soundex_first: str) -> int:
        """Create or update a SOUNDEX-based customer group."""
        query = """
            INSERT INTO customer_groups
                (group_key, group_name, group_type, soundex_last, soundex_first, updated_at)
            VALUES (?, ?, 'soundex', ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(group_key) DO UPDATE SET
                group_name = excluded.group_name,
                soundex_last = excluded.soundex_last,
                soundex_first = excluded.soundex_first,
                updated_at = CURRENT_TIMESTAMP
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (group_key, group_name, soundex_last, soundex_first))
            conn.commit()
            # Get the group_id
            cursor.execute("SELECT id FROM customer_groups WHERE group_key = ?", (group_key,))
            return cursor.fetchone()[0]

    def add_customer_to_soundex_group(self, group_id: int, customer_id: int,
                                     customer_name: str, customer_company: str,
                                     soundex_last: str, soundex_first: str,
                                     is_primary: bool = False):
        """Add a customer to a SOUNDEX group."""
        query = """
            INSERT INTO customer_group_members
                (customer_id, group_id, customer_name, customer_company,
                 soundex_last, soundex_first, is_primary, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(customer_id, group_id) DO UPDATE SET
                customer_name = excluded.customer_name,
                customer_company = excluded.customer_company,
                soundex_last = excluded.soundex_last,
                soundex_first = excluded.soundex_first,
                is_primary = excluded.is_primary,
                updated_at = CURRENT_TIMESTAMP
        """
        return self.execute_non_query(query, (customer_id, group_id, customer_name,
                                               customer_company, soundex_last,
                                               soundex_first, is_primary))

    def get_soundex_groups(self) -> pd.DataFrame:
        """Get all SOUNDEX-based customer groups."""
        query = """
            SELECT
                cg.*,
                COUNT(cgm.id) as actual_member_count
            FROM customer_groups cg
            LEFT JOIN customer_group_members cgm ON cg.id = cgm.group_id
            WHERE cg.group_type = 'soundex'
            GROUP BY cg.id
            ORDER BY actual_member_count DESC
        """
        return self.execute_query(query)

    def get_group_members(self, group_id: int) -> pd.DataFrame:
        """Get all members of a customer group."""
        query = """
            SELECT * FROM customer_group_members
            WHERE group_id = ?
            ORDER BY is_primary DESC, customer_name
        """
        return self.execute_query(query, (group_id,))

    def get_customer_group_id(self, customer_id: int) -> Optional[int]:
        """Get the group_id for a customer."""
        query = "SELECT group_id FROM customer_group_members WHERE customer_id = ?"
        df = self.execute_query(query, (customer_id,))
        return int(df.iloc[0]['group_id']) if not df.empty else None

    def update_group_member_counts(self):
        """Update member_count for all groups."""
        query = """
            UPDATE customer_groups
            SET member_count = (
                SELECT COUNT(*) FROM customer_group_members
                WHERE group_id = customer_groups.id
            ),
            updated_at = CURRENT_TIMESTAMP
        """
        return self.execute_non_query(query)

    def get_customers_not_in_groups(self) -> list:
        """Get list of customer IDs that aren't in any group yet."""
        query = """
            SELECT customer_id FROM customer_group_members
        """
        df = self.execute_query(query)
        return df['customer_id'].tolist() if not df.empty else []

    # Customer group analytics cache methods
    def cache_group_analytics(self, group_id: int, analytics: dict):
        """Cache analytics for a customer group."""
        query = """
            INSERT OR REPLACE INTO customer_group_analytics
                (group_id, total_sales_30d, gross_profit_30d, gp_percentage_30d,
                 ar_balance, pd_checks_count, pd_checks_total,
                 transaction_count_30d, last_purchase, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        return self.execute_non_query(query, (
            group_id,
            analytics.get('total_sales', 0),
            analytics.get('gross_profit', 0),
            analytics.get('gp_percentage', 0),
            analytics.get('ar_balance', 0),
            analytics.get('pd_checks_count', 0),
            analytics.get('pd_checks_total', 0),
            analytics.get('transaction_count', 0),
            analytics.get('last_purchase')
        ))

    def get_cached_analytics(self) -> pd.DataFrame:
        """Get all cached group analytics joined with group info."""
        query = """
            SELECT
                cg.id as group_id,
                cg.group_key,
                cg.group_name,
                cg.member_count,
                cga.total_sales_30d,
                cga.gross_profit_30d,
                cga.gp_percentage_30d,
                cga.ar_balance,
                cga.pd_checks_count,
                cga.pd_checks_total,
                cga.transaction_count_30d,
                cga.last_purchase,
                cga.last_updated
            FROM customer_groups cg
            LEFT JOIN customer_group_analytics cga ON cg.id = cga.group_id
            WHERE cg.group_type = 'soundex'
            ORDER BY cga.total_sales_30d DESC NULLS LAST
        """
        return self.execute_query(query)

    def clear_analytics_cache(self):
        """Clear all cached analytics."""
        return self.execute_non_query("DELETE FROM customer_group_analytics")

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
