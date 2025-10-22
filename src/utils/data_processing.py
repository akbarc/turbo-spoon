"""Data processing and analysis utilities."""
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime, timedelta


def merge_with_overlay_categories(df: pd.DataFrame, overlay_df: pd.DataFrame,
                                  product_id_col: str = 'product_id') -> pd.DataFrame:
    """
    Merge source data with custom product categories.

    Args:
        df: Source dataframe with products
        overlay_df: Overlay categories dataframe
        product_id_col: Column name for product ID in source data

    Returns:
        Merged dataframe with custom categories
    """
    if overlay_df.empty:
        df['custom_category'] = df.get('category', 'Uncategorized')
        return df

    merged = df.merge(
        overlay_df[['product_id', 'custom_category', 'subcategory']],
        left_on=product_id_col,
        right_on='product_id',
        how='left',
        suffixes=('', '_overlay')
    )

    # Use custom category if available, otherwise fall back to original
    if 'category' in merged.columns:
        merged['display_category'] = merged['custom_category'].fillna(merged['category'])
    else:
        merged['display_category'] = merged['custom_category'].fillna('Uncategorized')

    return merged


def calculate_excise_tax(df: pd.DataFrame, tax_rules: pd.DataFrame,
                        product_id_col: str = 'product_id',
                        amount_col: str = 'amount') -> pd.DataFrame:
    """
    Calculate excise taxes based on rules.

    Args:
        df: Source dataframe with sales/transactions
        tax_rules: Excise tax rules dataframe
        product_id_col: Column name for product ID
        amount_col: Column name for amount/price

    Returns:
        Dataframe with calculated excise taxes
    """
    if tax_rules.empty or amount_col not in df.columns:
        df['excise_tax'] = 0.0
        return df

    # Merge with tax rules
    result = df.copy()
    result['excise_tax'] = 0.0

    # Apply product-specific taxes
    product_taxes = tax_rules[tax_rules['product_id'].notna()]
    if not product_taxes.empty:
        for _, rule in product_taxes.iterrows():
            mask = result[product_id_col] == rule['product_id']
            result.loc[mask, 'excise_tax'] += result.loc[mask, amount_col] * rule['tax_rate']

    # Apply category-based taxes
    category_taxes = tax_rules[tax_rules['product_category'].notna()]
    if not category_taxes.empty and 'display_category' in result.columns:
        for _, rule in category_taxes.iterrows():
            mask = result['display_category'] == rule['product_category']
            result.loc[mask, 'excise_tax'] += result.loc[mask, amount_col] * rule['tax_rate']

    return result


def calculate_time_based_metrics(df: pd.DataFrame, date_col: str,
                                 value_col: str, freq: str = 'D') -> pd.DataFrame:
    """
    Calculate time-based aggregated metrics.

    Args:
        df: Source dataframe
        date_col: Column name for date/timestamp
        value_col: Column name for values to aggregate
        freq: Frequency for aggregation ('D'=daily, 'W'=weekly, 'M'=monthly)

    Returns:
        Aggregated dataframe
    """
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col])

    result = df_copy.groupby(pd.Grouper(key=date_col, freq=freq)).agg({
        value_col: ['sum', 'mean', 'count', 'std']
    }).reset_index()

    result.columns = [date_col, 'total', 'average', 'count', 'std_dev']
    result['std_dev'] = result['std_dev'].fillna(0)

    return result


def calculate_growth_rates(df: pd.DataFrame, value_col: str,
                          periods: int = 1) -> pd.DataFrame:
    """
    Calculate period-over-period growth rates.

    Args:
        df: Source dataframe (should be time-sorted)
        value_col: Column name for values
        periods: Number of periods for comparison

    Returns:
        Dataframe with growth rate column added
    """
    df_copy = df.copy()
    df_copy[f'{value_col}_growth_rate'] = df_copy[value_col].pct_change(periods=periods) * 100
    df_copy[f'{value_col}_growth_absolute'] = df_copy[value_col].diff(periods=periods)

    return df_copy


def get_top_n_by_category(df: pd.DataFrame, category_col: str,
                         value_col: str, n: int = 10) -> pd.DataFrame:
    """
    Get top N items by category.

    Args:
        df: Source dataframe
        category_col: Column name for category grouping
        value_col: Column name for ranking values
        n: Number of top items to return per category

    Returns:
        Filtered dataframe with top N items per category
    """
    return (df.sort_values([category_col, value_col], ascending=[True, False])
            .groupby(category_col)
            .head(n)
            .reset_index(drop=True))


def calculate_customer_metrics(df: pd.DataFrame, customer_id_col: str = 'customer_id',
                               date_col: str = 'date',
                               amount_col: str = 'amount') -> pd.DataFrame:
    """
    Calculate customer-level metrics (CLV, frequency, recency, etc.).

    Args:
        df: Source dataframe with transactions
        customer_id_col: Column name for customer ID
        date_col: Column name for transaction date
        amount_col: Column name for transaction amount

    Returns:
        Dataframe with customer metrics
    """
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col])

    # Calculate per-customer metrics
    customer_metrics = df_copy.groupby(customer_id_col).agg({
        amount_col: ['sum', 'mean', 'count'],
        date_col: ['min', 'max']
    }).reset_index()

    customer_metrics.columns = [
        customer_id_col, 'total_spent', 'avg_transaction', 'transaction_count',
        'first_purchase', 'last_purchase'
    ]

    # Calculate recency (days since last purchase)
    max_date = df_copy[date_col].max()
    customer_metrics['recency_days'] = (max_date - customer_metrics['last_purchase']).dt.days

    # Calculate customer lifetime (days between first and last purchase)
    customer_metrics['customer_lifetime_days'] = (
        customer_metrics['last_purchase'] - customer_metrics['first_purchase']
    ).dt.days

    # Calculate average days between purchases
    customer_metrics['avg_days_between_purchases'] = (
        customer_metrics['customer_lifetime_days'] / customer_metrics['transaction_count'].clip(lower=1)
    )

    return customer_metrics


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Apply multiple filters to a dataframe.

    Args:
        df: Source dataframe
        filters: Dictionary of {column: value} or {column: [list of values]}

    Returns:
        Filtered dataframe
    """
    result = df.copy()

    for col, value in filters.items():
        if col not in result.columns:
            continue

        if value is None or (isinstance(value, list) and not value):
            continue

        if isinstance(value, list):
            result = result[result[col].isin(value)]
        else:
            result = result[result[col] == value]

    return result
