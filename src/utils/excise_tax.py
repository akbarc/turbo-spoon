"""
Fast excise tax calculation using Item.SubDescription3 instead of slow PUExciseEntry queries.

This module calculates excise tax paid to the state by:
1. Querying Transaction → TransactionEntry → Item (fast, with date filter)
2. Using Item.SubDescription3 to identify taxable products
3. Calculating tax in Python: Cost * Quantity * Tax Rate

This is 100x faster than querying the PUExciseEntry table.
"""

import pandas as pd
from typing import Tuple, Optional


# Excise tax rates encoded in SubDescription3 codes
# Format: {code: rate_decimal}
# PAID suffix = tax paid to government (what we want for gross profit)
EXCISE_TAX_RATES = {
    'LT10PAID': 0.10,   # Loose Tobacco 10%
    'LT10COLL': 0.10,   # Loose Tobacco 10% collected
    'SL10PAID': 0.10,   # Smokeless 10%
    'SL10COLL': 0.10,   # Smokeless 10% collected
    'LC23PAID': 0.23,   # Large Cigars 23%
    'LC23COLL': 0.23,   # Large Cigars 23% collected
    'LC25PAID': 0.25,   # Little Cigars 25%
    'LC25COLL': 0.25,   # Little Cigars 25% collected
    'VO07PAID': 0.07,   # Vapors Open 7%
    'VO07COLL': 0.07,   # Vapors Open 7% collected
    'VD07PAID': 0.07,   # Vape Device 7%
    'VD07COLL': 0.07,   # Vape Device 7% collected
    'VC05PAID': 0.05,   # Vapors Closed 5%
    'VC05COLL': 0.05,   # Vapors Closed 5% collected
}


def calculate_excise_tax(db_connection, start_date: str, end_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate total excise tax paid to state for a date range.

    Uses fast query approach: Transaction → TransactionEntry → Item
    Calculates tax in Python based on Item.SubDescription3 codes.

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Tuple of (total_excise_paid, error_message)
        - If successful: (float_amount, None)
        - If failed: (None, error_string)
    """
    query = f"""
    SELECT
        i.SubDescription3,
        te.Cost,
        te.Quantity
    FROM [Transaction] t WITH (NOLOCK)
    INNER JOIN TransactionEntry te WITH (NOLOCK)
        ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i WITH (NOLOCK)
        ON te.ItemID = i.ID
    WHERE t.Time >= '{start_date}'
      AND t.Time <= '{end_date}'
      AND i.SubDescription3 IS NOT NULL
      AND i.SubDescription3 LIKE '%PAID'
    """

    try:
        with db_connection.get_connection() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return 0.0, None

        # Calculate excise tax in Python
        def calc_tax(row):
            code = row['SubDescription3']
            rate = EXCISE_TAX_RATES.get(code, 0.0)
            return row['Cost'] * row['Quantity'] * rate

        df['ExciseTax'] = df.apply(calc_tax, axis=1)
        total_excise = df['ExciseTax'].sum()

        return total_excise, None

    except Exception as e:
        error_msg = f"Excise tax calculation failed: {str(e)}"
        return None, error_msg


def calculate_excise_collected(db_connection, start_date: str, end_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate total excise tax collected from customers for a date range.

    This is the COLL codes (collected from customers), not PAID codes (paid to state).

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Tuple of (total_excise_collected, error_message)
        - If successful: (float_amount, None)
        - If failed: (None, error_string)
    """
    query = f"""
    SELECT
        i.SubDescription3,
        te.Cost,
        te.Quantity
    FROM [Transaction] t WITH (NOLOCK)
    INNER JOIN TransactionEntry te WITH (NOLOCK)
        ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i WITH (NOLOCK)
        ON te.ItemID = i.ID
    WHERE t.Time >= '{start_date}'
      AND t.Time <= '{end_date}'
      AND i.SubDescription3 IS NOT NULL
      AND i.SubDescription3 LIKE '%COLL'
    """

    try:
        with db_connection.get_connection() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return 0.0, None

        # Calculate excise tax in Python
        def calc_tax(row):
            code = row['SubDescription3']
            rate = EXCISE_TAX_RATES.get(code, 0.0)
            return row['Cost'] * row['Quantity'] * rate

        df['ExciseTax'] = df.apply(calc_tax, axis=1)
        total_excise = df['ExciseTax'].sum()

        return total_excise, None

    except Exception as e:
        error_msg = f"Excise tax collected calculation failed: {str(e)}"
        return None, error_msg


def get_excise_breakdown(db_connection, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Get detailed breakdown of excise tax by category.

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Tuple of (DataFrame, error_message)
        - If successful: (DataFrame with columns: Category, TotalExcise, TransactionCount, None)
        - If failed: (None, error_string)
    """
    query = f"""
    SELECT
        i.SubDescription3,
        te.Cost,
        te.Quantity,
        t.TransactionNumber
    FROM [Transaction] t WITH (NOLOCK)
    INNER JOIN TransactionEntry te WITH (NOLOCK)
        ON t.TransactionNumber = te.TransactionNumber
    INNER JOIN Item i WITH (NOLOCK)
        ON te.ItemID = i.ID
    WHERE t.Time >= '{start_date}'
      AND t.Time <= '{end_date}'
      AND i.SubDescription3 IS NOT NULL
      AND i.SubDescription3 LIKE '%PAID'
    """

    try:
        with db_connection.get_connection() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return pd.DataFrame(columns=['Category', 'TotalExcise', 'TransactionCount']), None

        # Calculate excise tax per row
        def calc_tax(row):
            code = row['SubDescription3']
            rate = EXCISE_TAX_RATES.get(code, 0.0)
            return row['Cost'] * row['Quantity'] * rate

        df['ExciseTax'] = df.apply(calc_tax, axis=1)

        # Group by category
        breakdown = df.groupby('SubDescription3').agg({
            'ExciseTax': 'sum',
            'TransactionNumber': 'nunique'
        }).reset_index()

        breakdown.columns = ['Category', 'TotalExcise', 'TransactionCount']
        breakdown = breakdown.sort_values('TotalExcise', ascending=False)

        return breakdown, None

    except Exception as e:
        error_msg = f"Excise breakdown failed: {str(e)}"
        return None, error_msg
