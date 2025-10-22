"""Executive Dashboard - Key business metrics and KPIs."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server_pyodbc import db

st.set_page_config(page_title="Executive Dashboard", page_icon="📊", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("📊 Executive Dashboard")

# Time filter section
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    time_filter = st.selectbox(
        "Time Period:",
        options=[
            "Today",
            "Yesterday",
            "Last 7 Days",
            "Last 30 Days",
            "This Week",
            "Last Week",
            "This Month",
            "Last Month",
            "This Quarter",
            "This Year",
            "Custom Range"
        ],
        index=2  # Default to Last 7 Days
    )

# Calculate date range based on selection
today = datetime.now()
if time_filter == "Today":
    start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Yesterday":
    start_date = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date.replace(hour=23, minute=59, second=59)
elif time_filter == "Last 7 Days":
    start_date = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last 30 Days":
    start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "This Week":
    start_date = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last Week":
    start_date = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
elif time_filter == "This Month":
    start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last Month":
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    start_date = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = last_day_last_month.replace(hour=23, minute=59, second=59)
elif time_filter == "This Quarter":
    quarter = (today.month - 1) // 3
    start_date = today.replace(month=quarter*3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "This Year":
    start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
else:  # Custom Range
    with col2:
        custom_start = st.date_input("Start Date:", value=today - timedelta(days=30))
        start_date = datetime.combine(custom_start, datetime.min.time())
    with col3:
        custom_end = st.date_input("End Date:", value=today)
        end_date = datetime.combine(custom_end, datetime.max.time())

# Show selected date range
if time_filter != "Custom Range":
    with col2:
        st.info(f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

with col3:
    refresh = st.button("🔄 Refresh", type="primary", use_container_width=True)

st.markdown("---")

# Load data
with st.spinner("Loading metrics..."):
    try:
        # Key metrics query
        metrics_query = f"""
        SELECT
            COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
            SUM(t.Total) as TotalSales,
            SUM(t.SalesTax) as TotalSalesTax,
            AVG(t.Total) as AvgTransactionValue,
            SUM(te.Quantity) as TotalItemsSold,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM [Transaction] t
        LEFT JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        """

        metrics = db.execute_query(metrics_query)

        if not metrics.empty and metrics['TotalTransactions'].iloc[0] > 0:
            # Display key metrics
            st.subheader("📈 Key Performance Indicators")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_sales = metrics['TotalSales'].iloc[0] or 0
                st.metric(
                    "Total Sales",
                    f"${total_sales:,.2f}",
                    help="Total revenue for selected period"
                )

                gross_profit = metrics['GrossProfit'].iloc[0] or 0
                margin = (gross_profit / total_sales * 100) if total_sales > 0 else 0
                st.metric(
                    "Gross Profit",
                    f"${gross_profit:,.2f}",
                    delta=f"{margin:.1f}% margin",
                    help="Total profit (Revenue - COGS)"
                )

            with col2:
                total_trans = metrics['TotalTransactions'].iloc[0] or 0
                st.metric(
                    "Transactions",
                    f"{total_trans:,}",
                    help="Number of completed transactions"
                )

                avg_trans = metrics['AvgTransactionValue'].iloc[0] or 0
                st.metric(
                    "Avg Transaction",
                    f"${avg_trans:,.2f}",
                    help="Average transaction value"
                )

            with col3:
                unique_customers = metrics['UniqueCustomers'].iloc[0] or 0
                st.metric(
                    "Unique Customers",
                    f"{unique_customers:,}",
                    help="Number of unique customers"
                )

                items_sold = metrics['TotalItemsSold'].iloc[0] or 0
                st.metric(
                    "Items Sold",
                    f"{items_sold:,.0f}",
                    help="Total quantity of items sold"
                )

            with col4:
                sales_tax = metrics['TotalSalesTax'].iloc[0] or 0
                st.metric(
                    "Sales Tax",
                    f"${sales_tax:,.2f}",
                    help="Total sales tax collected"
                )

                items_per_trans = items_sold / total_trans if total_trans > 0 else 0
                st.metric(
                    "Items/Transaction",
                    f"{items_per_trans:.1f}",
                    help="Average items per transaction"
                )

            # Excise Tax Summary
            st.markdown("---")
            st.subheader("💰 Excise Tax Summary")

            excise_query = f"""
            SELECT
                SUM(LOOSETOBACCO) as LooseTobacco,
                SUM(SMOKELESS) as Smokeless,
                SUM(LARGECIGARS) as LargeCigars,
                SUM(LITTLECIGARS) as LittleCigars,
                SUM(VAPORSOPEN) as VaporsOpen,
                SUM(VAPORSDEVICE) as VaporsDevice,
                SUM(VAPORSCLOSED) as VaporsClosed,
                SUM(TOTALEXCISECOLLECT) as TotalCollected
            FROM VIEWEXCISETAXCOLLECT
            WHERE Date >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND Date <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            """

            excise = db.execute_query(excise_query)

            if not excise.empty:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_excise = excise['TotalCollected'].iloc[0] or 0
                    st.metric("Total Excise Collected", f"${total_excise:,.2f}")

                with col2:
                    loose_tobacco = excise['LooseTobacco'].iloc[0] or 0
                    st.metric("Loose Tobacco", f"${loose_tobacco:,.2f}")

                with col3:
                    smokeless = excise['Smokeless'].iloc[0] or 0
                    st.metric("Smokeless", f"${smokeless:,.2f}")

                with col4:
                    cigars = (excise['LargeCigars'].iloc[0] or 0) + (excise['LittleCigars'].iloc[0] or 0)
                    st.metric("Cigars (All)", f"${cigars:,.2f}")

            # Sales Trend
            st.markdown("---")
            st.subheader("📈 Sales Trend")

            trend_query = f"""
            SELECT
                CAST(t.Time as DATE) as SalesDate,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(t.Total) as DailySales,
                SUM((te.Price - te.Cost) * te.Quantity) as DailyProfit
            FROM [Transaction] t
            LEFT JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY CAST(t.Time as DATE)
            ORDER BY SalesDate
            """

            trend = db.execute_query(trend_query)

            if not trend.empty:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=trend['SalesDate'],
                    y=trend['DailySales'],
                    mode='lines+markers',
                    name='Sales',
                    line=dict(color='#1f77b4', width=3),
                    fill='tozeroy'
                ))

                fig.update_layout(
                    title="Daily Sales Trend",
                    xaxis_title="Date",
                    yaxis_title="Sales ($)",
                    hovermode='x unified',
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

            # Top Categories
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🏆 Top Categories")

                category_query = f"""
                SELECT TOP 10
                    c.Name as Category,
                    COUNT(DISTINCT t.TransactionNumber) as Transactions,
                    SUM(te.Quantity) as QuantitySold,
                    SUM(te.Price * te.Quantity) as Sales,
                    SUM((te.Price - te.Cost) * te.Quantity) as Profit
                FROM [Transaction] t
                JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                JOIN Item i ON te.ItemID = i.ID
                JOIN Category c ON i.CategoryID = c.ID
                WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                GROUP BY c.Name
                ORDER BY Sales DESC
                """

                categories = db.execute_query(category_query)

                if not categories.empty:
                    st.dataframe(
                        categories.style.format({
                            'Transactions': '{:,}',
                            'QuantitySold': '{:,.0f}',
                            'Sales': '${:,.2f}',
                            'Profit': '${:,.2f}'
                        }),
                        use_container_width=True,
                        height=400
                    )

            with col2:
                st.subheader("🌟 Top Products")

                product_query = f"""
                SELECT TOP 10
                    i.Description as Product,
                    i.ItemLookupCode as SKU,
                    SUM(te.Quantity) as QuantitySold,
                    SUM(te.Price * te.Quantity) as Sales,
                    SUM((te.Price - te.Cost) * te.Quantity) as Profit
                FROM [Transaction] t
                JOIN TransactionEntry te ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                JOIN Item i ON te.ItemID = i.ID
                WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                GROUP BY i.Description, i.ItemLookupCode
                ORDER BY Sales DESC
                """

                products = db.execute_query(product_query)

                if not products.empty:
                    st.dataframe(
                        products.style.format({
                            'QuantitySold': '{:,.0f}',
                            'Sales': '${:,.2f}',
                            'Profit': '${:,.2f}'
                        }),
                        use_container_width=True,
                        height=400
                    )

        else:
            st.warning(f"⚠️ No data found for the selected time period ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
            st.info("Try selecting a different time range or check if transactions exist in your database.")

    except Exception as e:
        st.error(f"❌ Error loading dashboard data: {str(e)}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
