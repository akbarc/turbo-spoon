"""
Date utility functions for API endpoints.
"""
from datetime import datetime, timedelta
from typing import Tuple

def parse_period(period: str = None, start_date: str = None, end_date: str = None) -> Tuple[datetime, datetime]:
    """
    Parse period parameter or custom date range into start and end datetime objects.

    Args:
        period: Predefined period (today, 7d, 30d, MTD, YTD, etc.)
        start_date: Custom start date (YYYY-MM-DD)
        end_date: Custom end date (YYYY-MM-DD)

    Returns:
        Tuple of (start_datetime, end_datetime)

    Raises:
        ValueError: If dates are invalid or period is unknown
    """
    today = datetime.now()

    # If custom dates provided, use those
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            return start, end
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")

    # Parse predefined periods
    if not period:
        period = 'today'

    period = period.lower()

    if period == 'today':
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'yesterday':
        start = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
    elif period == '7d' or period == 'last_7_days':
        start = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == '30d' or period == 'last_30_days':
        start = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'this_week':
        start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'last_week':
        start = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == 'mtd' or period == 'this_month':
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'last_month':
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_last_month.replace(hour=23, minute=59, second=59)
    elif period == 'this_quarter':
        quarter = (today.month - 1) // 3
        start = today.replace(month=quarter*3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'ytd' or period == 'this_year':
        start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    else:
        raise ValueError(f"Unknown period: {period}. Use: today, 7d, 30d, MTD, YTD, etc.")

    return start, end

def get_comparison_period(start: datetime, end: datetime) -> Tuple[datetime, datetime]:
    """
    Calculate comparison period (same duration, shifted back).

    Args:
        start: Start of current period
        end: End of current period

    Returns:
        Tuple of (comparison_start, comparison_end)
    """
    duration = end - start
    comp_end = start - timedelta(seconds=1)
    comp_start = comp_end - duration

    return comp_start, comp_end

def format_date_for_sql(dt: datetime) -> str:
    """
    Format datetime for SQL Server query.

    Args:
        dt: datetime object

    Returns:
        String formatted as 'YYYY-MM-DD HH:MM:SS'
    """
    return dt.strftime('%Y-%m-%d %H:%M:%S')
