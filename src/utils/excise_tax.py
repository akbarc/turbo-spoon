"""
Excise tax calculation using PUExciseEntry table.

This module calculates excise tax by querying the PUExciseEntry table directly.
The PriceC field contains the actual excise tax amount (already calculated).

Key fields in PUExciseEntry:
- PriceC: The actual excise tax amount per unit
- Quantity: Number of units sold
- SubDescription3: Tax category code (e.g., LC23PAID, VD07COLL)
- TransactionTime: Date/time of transaction (use for filtering)

Total excise tax = SUM(PriceC * Quantity)
"""

import pandas as pd
from typing import Tuple, Optional


def calculate_excise_tax(db_connection, start_date: str, end_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate total excise tax paid to state for a date range.

    Queries PUExciseEntry table directly and uses PriceC field (actual tax amount).

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Tuple of (total_excise_paid, error_message)
        - If successful: (float_amount, None)
        - If failed: (None, error_string)
    """
    # Add index hints for better performance
    query = f"""
    SELECT SUM(PriceC * Quantity) as TotalExcisePaid
    FROM PUExciseEntry WITH (NOLOCK, INDEX(0))
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%PAID'
    """

    max_retries = 2
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            with db_connection.get_connection() as conn:
                df = pd.read_sql(query, conn)

            if df.empty or df['TotalExcisePaid'].iloc[0] is None:
                return 0.0, None

            total_excise = df['TotalExcisePaid'].iloc[0]
            return float(total_excise), None

        except Exception as e:
            error_str = str(e)

            # Check if it's a timeout or connection error
            if 'timeout' in error_str.lower() or 'dead' in error_str.lower():
                if attempt < max_retries - 1:
                    # Retry on timeout
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed
                    return None, "Query timeout - try a smaller date range or check database connection"
            else:
                # Non-timeout error, don't retry
                return None, f"Query failed: {error_str}"

    return None, "Query failed after retries"


def calculate_excise_collected(db_connection, start_date: str, end_date: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate total excise tax collected from customers for a date range.

    Queries PUExciseEntry table for COLL codes (collected from customers).

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)

    Returns:
        Tuple of (total_excise_collected, error_message)
        - If successful: (float_amount, None)
        - If failed: (None, error_string)
    """
    # Add index hints for better performance
    query = f"""
    SELECT SUM(PriceC * Quantity) as TotalExciseCollected
    FROM PUExciseEntry WITH (NOLOCK, INDEX(0))
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%COLL'
    """

    max_retries = 2
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            with db_connection.get_connection() as conn:
                df = pd.read_sql(query, conn)

            if df.empty or df['TotalExciseCollected'].iloc[0] is None:
                return 0.0, None

            total_excise = df['TotalExciseCollected'].iloc[0]
            return float(total_excise), None

        except Exception as e:
            error_str = str(e)

            # Check if it's a timeout or connection error
            if 'timeout' in error_str.lower() or 'dead' in error_str.lower():
                if attempt < max_retries - 1:
                    # Retry on timeout
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed
                    return None, "Query timeout - try a smaller date range or check database connection"
            else:
                # Non-timeout error, don't retry
                return None, f"Query failed: {error_str}"

    return None, "Query failed after retries"


def get_excise_breakdown(db_connection, start_date: str, end_date: str, tax_type: str = 'PAID') -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Get detailed breakdown of excise tax by category.

    Args:
        db_connection: Database connection context manager
        start_date: Start date (YYYY-MM-DD HH:MM:SS)
        end_date: End date (YYYY-MM-DD HH:MM:SS)
        tax_type: 'PAID' or 'COLL' (default: 'PAID')

    Returns:
        Tuple of (DataFrame, error_message)
        - If successful: (DataFrame with columns: Category, TotalExcise, EntryCount, None)
        - If failed: (None, error_string)
    """
    query = f"""
    SELECT
        SubDescription3,
        COUNT(*) as EntryCount,
        SUM(PriceC * Quantity) as TotalExcise
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= '{start_date}'
      AND TransactionTime <= '{end_date}'
      AND SubDescription3 LIKE '%{tax_type}'
    GROUP BY SubDescription3
    ORDER BY TotalExcise DESC
    """

    try:
        with db_connection.get_connection() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return pd.DataFrame(columns=['Category', 'TotalExcise', 'EntryCount']), None

        df.columns = ['Category', 'EntryCount', 'TotalExcise']
        return df, None

    except Exception as e:
        error_msg = f"Excise breakdown failed: {str(e)}"
        return None, error_msg
