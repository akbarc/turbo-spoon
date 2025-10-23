"""Profitability Analysis - Deep dive into margins and profit sources."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected

st.set_page_config(page_title="Profitability Analysis", page_icon="💰", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("💰 Profitability Analysis")
st.markdown("**Understand where you make and lose money**")

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
        index=3  # Default to Last 30 Days
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
with st.spinner("Analyzing profitability..."):
    try:
        # Overall profitability metrics
        overall_query = f"""
        SELECT
            SUM(te.Price * te.Quantity) as TotalRevenue,
            SUM(te.Cost * te.Quantity) as TotalCost,
            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
        FROM [Transaction] t WITH (NOLOCK)
        INNER JOIN TransactionEntry te WITH (NOLOCK)
            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
        WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        """

        overall = db.execute_query(overall_query)

        if not overall.empty and overall['TotalRevenue'].iloc[0] and overall['TotalRevenue'].iloc[0] > 0:
            revenue = overall['TotalRevenue'].iloc[0]
            cost = overall['TotalCost'].iloc[0]
            gross_profit = overall['GrossProfit'].iloc[0]
            gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

            # Get excise tax COLLECTED (what we owe to state)
            # Note: PAID is already in COGS
            excise_collected, _ = calculate_excise_collected(
                db,
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S')
            )
            excise_collected = excise_collected or 0

            net_profit = gross_profit - excise_collected
            net_margin = (net_profit / revenue * 100) if revenue > 0 else 0

            # Display overall metrics
            st.subheader("📊 Overall Profitability")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Revenue",
                    f"${revenue:,.2f}",
                    help="Total sales revenue"
                )
                st.metric(
                    "Gross Profit",
                    f"${gross_profit:,.2f}",
                    delta=f"{gross_margin:.1f}% margin",
                    help="Revenue - Cost of Goods Sold"
                )

            with col2:
                st.metric(
                    "Total Cost (COGS)",
                    f"${cost:,.2f}",
                    help="Cost of Goods Sold"
                )
                st.metric(
                    "Net Profit",
                    f"${net_profit:,.2f}",
                    delta=f"{net_margin:.1f}% margin",
                    help="Gross Profit - Excise Tax Collected (owed to state)"
                )

            with col3:
                st.metric(
                    "Gross Margin",
                    f"{gross_margin:.1f}%",
                    help="Gross Profit / Revenue"
                )
                st.metric(
                    "Excise Tax Collected",
                    f"${excise_collected:,.2f}",
                    help="Tax collected from customers (must remit to state)"
                )

            with col4:
                st.metric(
                    "Net Margin",
                    f"{net_margin:.1f}%",
                    help="Net Profit / Revenue (after excise)"
                )
                markup = ((revenue - cost) / cost * 100) if cost > 0 else 0
                st.metric(
                    "Average Markup",
                    f"{markup:.1f}%",
                    help="(Revenue - Cost) / Cost"
                )

            # Profit breakdown visualization
            st.markdown("---")
            st.subheader("💵 Profit Breakdown")

            fig = go.Figure(data=[
                go.Bar(
                    name='Revenue',
                    x=['Overall'],
                    y=[revenue],
                    marker_color='lightblue',
                    text=[f'${revenue:,.0f}'],
                    textposition='auto'
                ),
                go.Bar(
                    name='Cost (COGS)',
                    x=['Overall'],
                    y=[cost],
                    marker_color='lightcoral',
                    text=[f'${cost:,.0f}'],
                    textposition='auto'
                ),
                go.Bar(
                    name='Excise Tax (Collected)',
                    x=['Overall'],
                    y=[excise_collected],
                    marker_color='orange',
                    text=[f'${excise_collected:,.0f}'],
                    textposition='auto'
                ),
                go.Bar(
                    name='Net Profit',
                    x=['Overall'],
                    y=[net_profit],
                    marker_color='lightgreen',
                    text=[f'${net_profit:,.0f}'],
                    textposition='auto'
                )
            ])

            fig.update_layout(
                barmode='group',
                title="Revenue vs. Costs vs. Profit",
                yaxis_title="Amount ($)",
                height=400,
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

            # Category profitability analysis
            st.markdown("---")
            st.subheader("📦 Profitability by Category")

            category_query = f"""
            SELECT
                c.Name as Category,
                COUNT(DISTINCT t.TransactionNumber) as Transactions,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as Cost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                    THEN pue.PriceC * pue.Quantity
                    ELSE 0 END), 0) as ExciseTax
            FROM [Transaction] t WITH (NOLOCK)
            INNER JOIN TransactionEntry te WITH (NOLOCK)
                ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
            INNER JOIN Item i WITH (NOLOCK)
                ON te.ItemID = i.ID
            INNER JOIN Category c WITH (NOLOCK)
                ON i.CategoryID = c.ID
            LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
                ON t.TransactionNumber = pue.TransactionNumber
                AND te.ItemID = pue.ItemID
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY c.Name
            ORDER BY GrossProfit DESC
            """

            categories = db.execute_query(category_query)

            if not categories.empty:
                # Calculate net profit and margins
                categories['NetProfit'] = categories['GrossProfit'] - categories['ExciseTax']
                categories['GrossMargin%'] = (categories['GrossProfit'] / categories['Revenue'] * 100).fillna(0)
                categories['NetMargin%'] = (categories['NetProfit'] / categories['Revenue'] * 100).fillna(0)

                col1, col2 = st.columns([2, 1])

                with col1:
                    # Category table
                    st.dataframe(
                        categories.style.format({
                            'Transactions': '{:,}',
                            'UnitsSold': '{:,.0f}',
                            'Revenue': '${:,.2f}',
                            'Cost': '${:,.2f}',
                            'GrossProfit': '${:,.2f}',
                            'ExciseTax': '${:,.2f}',
                            'NetProfit': '${:,.2f}',
                            'GrossMargin%': '{:.1f}%',
                            'NetMargin%': '{:.1f}%'
                        }).background_gradient(subset=['NetMargin%'], cmap='RdYlGn', vmin=0, vmax=50),
                        use_container_width=True,
                        height=400
                    )

                with col2:
                    # Margin by category chart
                    fig = px.bar(
                        categories.head(10),
                        x='NetMargin%',
                        y='Category',
                        orientation='h',
                        title="Top 10 Categories by Net Margin %",
                        color='NetMargin%',
                        color_continuous_scale='RdYlGn',
                        labels={'NetMargin%': 'Net Margin %'}
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            # Product profitability analysis
            st.markdown("---")
            st.subheader("🏆 Top Products by Profit")

            product_query = f"""
            SELECT TOP 20
                i.Description as Product,
                i.ItemLookupCode as SKU,
                c.Name as Category,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as Cost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                    THEN pue.PriceC * pue.Quantity
                    ELSE 0 END), 0) as ExciseTax,
                AVG(te.Price) as AvgPrice,
                AVG(te.Cost) as AvgCost
            FROM [Transaction] t WITH (NOLOCK)
            INNER JOIN TransactionEntry te WITH (NOLOCK)
                ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
            INNER JOIN Item i WITH (NOLOCK)
                ON te.ItemID = i.ID
            INNER JOIN Category c WITH (NOLOCK)
                ON i.CategoryID = c.ID
            LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
                ON t.TransactionNumber = pue.TransactionNumber
                AND te.ItemID = pue.ItemID
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY i.Description, i.ItemLookupCode, c.Name
            ORDER BY GrossProfit DESC
            """

            top_products = db.execute_query(product_query)

            if not top_products.empty:
                # Calculate net profit and margins
                top_products['NetProfit'] = top_products['GrossProfit'] - top_products['ExciseTax']
                top_products['GrossMargin%'] = ((top_products['GrossProfit'] / top_products['Revenue']) * 100).fillna(0)
                top_products['NetMargin%'] = ((top_products['NetProfit'] / top_products['Revenue']) * 100).fillna(0)
                top_products['Markup%'] = (((top_products['AvgPrice'] - top_products['AvgCost']) / top_products['AvgCost']) * 100).fillna(0)

                st.dataframe(
                    top_products.style.format({
                        'UnitsSold': '{:,.0f}',
                        'Revenue': '${:,.2f}',
                        'Cost': '${:,.2f}',
                        'GrossProfit': '${:,.2f}',
                        'ExciseTax': '${:,.2f}',
                        'NetProfit': '${:,.2f}',
                        'AvgPrice': '${:,.2f}',
                        'AvgCost': '${:,.2f}',
                        'GrossMargin%': '{:.1f}%',
                        'NetMargin%': '{:.1f}%',
                        'Markup%': '{:.1f}%'
                    }).background_gradient(subset=['NetMargin%'], cmap='RdYlGn', vmin=0, vmax=50),
                    use_container_width=True,
                    height=500
                )

            # Loss leaders (low margin products)
            st.markdown("---")
            st.subheader("⚠️ Loss Leaders (Low Margin Products)")

            loss_leader_query = f"""
            SELECT TOP 20
                i.Description as Product,
                i.ItemLookupCode as SKU,
                c.Name as Category,
                SUM(te.Quantity) as UnitsSold,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as Cost,
                SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                    THEN pue.PriceC * pue.Quantity
                    ELSE 0 END), 0) as ExciseTax,
                AVG(te.Price) as AvgPrice,
                AVG(te.Cost) as AvgCost
            FROM [Transaction] t WITH (NOLOCK)
            INNER JOIN TransactionEntry te WITH (NOLOCK)
                ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
            INNER JOIN Item i WITH (NOLOCK)
                ON te.ItemID = i.ID
            INNER JOIN Category c WITH (NOLOCK)
                ON i.CategoryID = c.ID
            LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
                ON t.TransactionNumber = pue.TransactionNumber
                AND te.ItemID = pue.ItemID
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY i.Description, i.ItemLookupCode, c.Name
            HAVING SUM(te.Quantity) > 5
            ORDER BY ((SUM((te.Price - te.Cost) * te.Quantity) - ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL' THEN pue.PriceC * pue.Quantity ELSE 0 END), 0)) / NULLIF(SUM(te.Price * te.Quantity), 0)) ASC
            """

            loss_leaders = db.execute_query(loss_leader_query)

            if not loss_leaders.empty:
                # Calculate net profit and margins
                loss_leaders['NetProfit'] = loss_leaders['GrossProfit'] - loss_leaders['ExciseTax']
                loss_leaders['GrossMargin%'] = ((loss_leaders['GrossProfit'] / loss_leaders['Revenue']) * 100).fillna(0)
                loss_leaders['NetMargin%'] = ((loss_leaders['NetProfit'] / loss_leaders['Revenue']) * 100).fillna(0)
                loss_leaders['Markup%'] = (((loss_leaders['AvgPrice'] - loss_leaders['AvgCost']) / loss_leaders['AvgCost']) * 100).fillna(0)

                st.warning("These products have the lowest NET profit margins but decent sales volume. Consider price increases or promotions to improve profitability.")

                st.dataframe(
                    loss_leaders.style.format({
                        'UnitsSold': '{:,.0f}',
                        'Revenue': '${:,.2f}',
                        'Cost': '${:,.2f}',
                        'GrossProfit': '${:,.2f}',
                        'ExciseTax': '${:,.2f}',
                        'NetProfit': '${:,.2f}',
                        'AvgPrice': '${:,.2f}',
                        'AvgCost': '${:,.2f}',
                        'GrossMargin%': '{:.1f}%',
                        'NetMargin%': '{:.1f}%',
                        'Markup%': '{:.1f}%'
                    }).background_gradient(subset=['NetMargin%'], cmap='RdYlGn_r', vmin=0, vmax=50),
                    use_container_width=True,
                    height=400
                )

            # Profit trends over time
            st.markdown("---")
            st.subheader("📈 Profit Trend")

            trend_query = f"""
            SELECT
                CAST(t.Time as DATE) as Date,
                SUM(te.Price * te.Quantity) as Revenue,
                SUM(te.Cost * te.Quantity) as Cost,
                SUM((te.Price - te.Cost) * te.Quantity) as Profit
            FROM [Transaction] t WITH (NOLOCK)
            INNER JOIN TransactionEntry te WITH (NOLOCK)
                ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
            WHERE t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY CAST(t.Time as DATE)
            ORDER BY Date
            """

            trend = db.execute_query(trend_query)

            if not trend.empty:
                trend['Margin%'] = (trend['Profit'] / trend['Revenue'] * 100).fillna(0)

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=trend['Date'],
                    y=trend['Profit'],
                    mode='lines+markers',
                    name='Daily Profit',
                    line=dict(color='green', width=2),
                    yaxis='y'
                ))

                fig.add_trace(go.Scatter(
                    x=trend['Date'],
                    y=trend['Margin%'],
                    mode='lines',
                    name='Margin %',
                    line=dict(color='blue', width=2, dash='dash'),
                    yaxis='y2'
                ))

                fig.update_layout(
                    title="Daily Profit and Margin %",
                    xaxis_title="Date",
                    yaxis=dict(
                        title="Profit ($)",
                        side='left'
                    ),
                    yaxis2=dict(
                        title="Margin %",
                        side='right',
                        overlaying='y'
                    ),
                    hovermode='x unified',
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning(f"⚠️ No data found for the selected time period ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")

    except Exception as e:
        st.error(f"❌ Error loading profitability data: {str(e)}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
