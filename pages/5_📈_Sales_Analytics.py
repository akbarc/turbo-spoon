"""Sales Analytics - Deep dive into sales metrics and trends."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server_pyodbc import db
from database.overlay_db import overlay_db
from utils.data_processing import (
    calculate_time_based_metrics,
    calculate_growth_rates,
    calculate_customer_metrics,
    merge_with_overlay_categories,
    apply_filters
)

st.set_page_config(page_title="Sales Analytics", page_icon="📈", layout="wide")

st.title("📈 Sales Analytics")
st.markdown("Deep insights into sales performance, trends, and customer behavior.")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Quick Stats", "📈 Trends", "👥 Customer Analysis", "🎯 Custom Query"])

with tab1:
    st.subheader("Quick Sales Statistics")

    st.markdown("""
    Run quick analytics on your sales data. First, load your sales table from the Data Explorer,
    or use the custom query below.
    """)

    # Check if data is loaded
    if 'current_data' in st.session_state and not st.session_state.current_data.empty:
        data = st.session_state.current_data

        st.success(f"✅ Using loaded data: {st.session_state.get('current_table', 'Unknown')} ({len(data)} rows)")

        # Let user specify columns
        st.markdown("#### Configure Columns")

        col1, col2, col3 = st.columns(3)

        with col1:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            amount_col = st.selectbox("Amount/Sales Column:", options=numeric_cols)

        with col2:
            date_cols = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
            if not date_cols:
                date_cols = data.columns.tolist()
            date_col = st.selectbox("Date Column:", options=date_cols)

        with col3:
            category_cols = ['None'] + data.columns.tolist()
            category_col = st.selectbox("Category Column (optional):", options=category_cols)

        if st.button("📊 Calculate Stats", type="primary"):
            try:
                with st.spinner("Calculating statistics..."):
                    # Basic stats
                    st.markdown("---")
                    st.markdown("### 📊 Summary Metrics")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Sales", f"${data[amount_col].sum():,.2f}")

                    with col2:
                        st.metric("Average Sale", f"${data[amount_col].mean():,.2f}")

                    with col3:
                        st.metric("Transaction Count", f"{len(data):,}")

                    with col4:
                        st.metric("Median Sale", f"${data[amount_col].median():,.2f}")

                    # Distribution stats
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Min Sale", f"${data[amount_col].min():,.2f}")

                    with col2:
                        st.metric("Max Sale", f"${data[amount_col].max():,.2f}")

                    with col3:
                        st.metric("Std Dev", f"${data[amount_col].std():,.2f}")

                    with col4:
                        percentile_95 = data[amount_col].quantile(0.95)
                        st.metric("95th Percentile", f"${percentile_95:,.2f}")

                    # Distribution chart
                    st.markdown("---")
                    st.markdown("### 📊 Sales Distribution")

                    fig = px.histogram(
                        data,
                        x=amount_col,
                        nbins=50,
                        title="Distribution of Sales Amounts",
                        labels={amount_col: "Amount ($)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Category breakdown if available
                    if category_col != 'None':
                        st.markdown("---")
                        st.markdown(f"### 📊 Breakdown by {category_col}")

                        category_stats = data.groupby(category_col)[amount_col].agg([
                            ('Total', 'sum'),
                            ('Average', 'mean'),
                            ('Count', 'count')
                        ]).sort_values('Total', ascending=False)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.dataframe(
                                category_stats.style.format({
                                    'Total': '${:,.2f}',
                                    'Average': '${:,.2f}',
                                    'Count': '{:,.0f}'
                                }),
                                use_container_width=True
                            )

                        with col2:
                            fig = px.pie(
                                values=category_stats['Total'],
                                names=category_stats.index,
                                title="Sales by Category"
                            )
                            st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Error calculating stats: {str(e)}")
                st.exception(e)

    else:
        st.info("📊 Load data from the Data Explorer first, or use the Custom Query tab.")

with tab2:
    st.subheader("📈 Time-Based Trends")

    if 'current_data' in st.session_state and not st.session_state.current_data.empty:
        data = st.session_state.current_data

        st.markdown("#### Configure Trend Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            amount_col = st.selectbox("Value Column:", options=numeric_cols, key='trend_amount')

        with col2:
            date_cols = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
            if not date_cols:
                date_cols = data.columns.tolist()
            date_col = st.selectbox("Date Column:", options=date_cols, key='trend_date')

        with col3:
            freq = st.selectbox(
                "Aggregation:",
                options=['D', 'W', 'M', 'Q', 'Y'],
                format_func=lambda x: {'D': 'Daily', 'W': 'Weekly', 'M': 'Monthly', 'Q': 'Quarterly', 'Y': 'Yearly'}[x]
            )

        if st.button("📈 Generate Trends", type="primary"):
            try:
                with st.spinner("Calculating trends..."):
                    # Calculate time-based metrics
                    trends = calculate_time_based_metrics(data, date_col, amount_col, freq=freq)

                    # Calculate growth rates
                    trends = calculate_growth_rates(trends, 'total', periods=1)

                    st.markdown("---")

                    # Display trend chart
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=trends[date_col],
                        y=trends['total'],
                        mode='lines+markers',
                        name='Total',
                        line=dict(width=3)
                    ))

                    fig.update_layout(
                        title="Sales Over Time",
                        xaxis_title="Date",
                        yaxis_title="Total ($)",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Growth rate chart
                    fig2 = go.Figure()

                    fig2.add_trace(go.Bar(
                        x=trends[date_col],
                        y=trends['total_growth_rate'],
                        name='Growth Rate (%)',
                        marker_color=['red' if x < 0 else 'green' for x in trends['total_growth_rate']]
                    ))

                    fig2.update_layout(
                        title="Period-over-Period Growth Rate",
                        xaxis_title="Date",
                        yaxis_title="Growth Rate (%)",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig2, use_container_width=True)

                    # Display data table
                    st.markdown("### 📊 Detailed Trends")
                    st.dataframe(
                        trends.style.format({
                            'total': '${:,.2f}',
                            'average': '${:,.2f}',
                            'count': '{:,.0f}',
                            'std_dev': '${:,.2f}',
                            'total_growth_rate': '{:.2f}%',
                            'total_growth_absolute': '${:,.2f}'
                        }),
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"❌ Error generating trends: {str(e)}")
                st.exception(e)

    else:
        st.info("📊 Load data from the Data Explorer first.")

with tab3:
    st.subheader("👥 Customer Analysis")

    if 'current_data' in st.session_state and not st.session_state.current_data.empty:
        data = st.session_state.current_data

        st.markdown("#### Configure Customer Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            customer_cols = [col for col in data.columns if 'customer' in col.lower() or 'client' in col.lower()]
            if not customer_cols:
                customer_cols = data.columns.tolist()
            customer_col = st.selectbox("Customer ID Column:", options=customer_cols)

        with col2:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            amount_col = st.selectbox("Amount Column:", options=numeric_cols, key='cust_amount')

        with col3:
            date_cols = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
            if not date_cols:
                date_cols = data.columns.tolist()
            date_col = st.selectbox("Date Column:", options=date_cols, key='cust_date')

        if st.button("👥 Analyze Customers", type="primary"):
            try:
                with st.spinner("Analyzing customer behavior..."):
                    # Calculate customer metrics
                    customer_metrics = calculate_customer_metrics(
                        data,
                        customer_id_col=customer_col,
                        date_col=date_col,
                        amount_col=amount_col
                    )

                    st.markdown("---")
                    st.markdown("### 🏆 Top Customers by Spend")

                    top_customers = customer_metrics.nlargest(20, 'total_spent')

                    fig = px.bar(
                        top_customers,
                        x=customer_col,
                        y='total_spent',
                        title="Top 20 Customers by Total Spend",
                        labels={customer_col: "Customer", 'total_spent': "Total Spent ($)"}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Customer segments
                    st.markdown("---")
                    st.markdown("### 📊 Customer Segments")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Customers", f"{len(customer_metrics):,}")

                    with col2:
                        avg_ltv = customer_metrics['total_spent'].mean()
                        st.metric("Avg Customer LTV", f"${avg_ltv:,.2f}")

                    with col3:
                        avg_freq = customer_metrics['transaction_count'].mean()
                        st.metric("Avg Transaction Frequency", f"{avg_freq:.1f}")

                    # RFM analysis
                    st.markdown("---")
                    st.markdown("### 🎯 RFM Analysis")

                    # Create RFM segments
                    customer_metrics['R_Score'] = pd.qcut(customer_metrics['recency_days'], q=4, labels=[4, 3, 2, 1])
                    customer_metrics['F_Score'] = pd.qcut(customer_metrics['transaction_count'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
                    customer_metrics['M_Score'] = pd.qcut(customer_metrics['total_spent'], q=4, labels=[1, 2, 3, 4])

                    customer_metrics['RFM_Score'] = (
                        customer_metrics['R_Score'].astype(int) +
                        customer_metrics['F_Score'].astype(int) +
                        customer_metrics['M_Score'].astype(int)
                    )

                    # Segment distribution
                    rfm_dist = customer_metrics['RFM_Score'].value_counts().sort_index()

                    fig = px.bar(
                        x=rfm_dist.index,
                        y=rfm_dist.values,
                        title="RFM Score Distribution",
                        labels={'x': 'RFM Score', 'y': 'Number of Customers'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Display customer data
                    st.markdown("---")
                    st.markdown("### 📋 Customer Details")

                    display_metrics = customer_metrics.sort_values('total_spent', ascending=False)

                    st.dataframe(
                        display_metrics.style.format({
                            'total_spent': '${:,.2f}',
                            'avg_transaction': '${:,.2f}',
                            'transaction_count': '{:,.0f}',
                            'recency_days': '{:,.0f}',
                            'customer_lifetime_days': '{:,.0f}',
                            'avg_days_between_purchases': '{:.1f}'
                        }),
                        use_container_width=True,
                        height=400
                    )

                    # Download
                    csv = display_metrics.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Customer Metrics",
                        data=csv,
                        file_name=f"customer_metrics_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"❌ Error analyzing customers: {str(e)}")
                st.exception(e)

    else:
        st.info("📊 Load data from the Data Explorer first.")

with tab4:
    st.subheader("🎯 Custom Sales Query")

    st.markdown("""
    Write custom SQL queries specifically for sales analysis. Results will be automatically loaded
    for use in other tabs.
    """)

    # Query templates
    if st.button("📋 Show Query Templates"):
        st.session_state.show_templates = not st.session_state.get('show_templates', False)

    if st.session_state.get('show_templates', False):
        with st.expander("📋 Query Templates", expanded=True):
            st.markdown("""
            **Sales by Date Range:**
            ```sql
            SELECT * FROM sales_table
            WHERE date_column >= '2024-01-01' AND date_column < '2025-01-01'
            ```

            **Sales with Aggregation:**
            ```sql
            SELECT
                category,
                SUM(amount) as total_sales,
                COUNT(*) as transaction_count,
                AVG(amount) as avg_sale
            FROM sales_table
            GROUP BY category
            ORDER BY total_sales DESC
            ```

            **Top Products:**
            ```sql
            SELECT TOP 50
                product_id,
                SUM(amount) as total_revenue,
                COUNT(*) as units_sold
            FROM sales_table
            GROUP BY product_id
            ORDER BY total_revenue DESC
            ```
            """)

    # Query input
    query = st.text_area(
        "Enter your sales query:",
        height=200,
        placeholder="SELECT * FROM your_sales_table WHERE date >= '2024-01-01'"
    )

    if st.button("▶️ Run Query", type="primary"):
        if not query.strip():
            st.error("❌ Please enter a query")
        elif not query.strip().upper().startswith('SELECT'):
            st.error("❌ Only SELECT queries are allowed")
        else:
            try:
                with st.spinner("Executing query..."):
                    result = db.execute_query(query)

                    st.success(f"✅ Query executed! ({len(result)} rows)")

                    # Store in session
                    st.session_state.current_data = result
                    st.session_state.current_table = "Custom Query"

                    # Display
                    st.dataframe(result, use_container_width=True, height=400)

                    # Download
                    csv = result.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Results",
                        data=csv,
                        file_name=f"sales_query_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                    st.info("💡 Data loaded! Use other tabs for analysis.")

            except Exception as e:
                st.error(f"❌ Query error: {str(e)}")
