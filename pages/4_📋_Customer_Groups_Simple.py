"""Simple CSV-based Customer Groups - Fast and comprehensive analytics."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.database.sql_server import test_connection
from src.modules.customer_groups_simple import simple_customer_group_manager

# Page configuration
st.set_page_config(
    page_title="Customer Groups (CSV)",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Customer Groups (CSV-Based)")
st.markdown("**Manual groups from `customer_groups.csv`** - Edit the file to update groups")

# Test database connection
if not test_connection():
    st.error("❌ Cannot connect to database. Please check your connection settings.")
    st.stop()

# Check if CSV exists and has data
import os
if not os.path.exists('customer_groups.csv'):
    st.error("""
    ❌ **CSV file not found!**

    Create `customer_groups.csv` with this format:
    ```
    GroupName,CustomerID,CustomerName,Company
    ABC Stores,1234,John Smith,ABC Store 1
    ABC Stores,1235,John Smith,ABC Store 2
    XYZ Gas,5678,Jane Doe,XYZ Gas Station
    ```
    """)
    st.stop()

# Load to check if empty
test_df = simple_customer_group_manager.load_groups_from_csv()
if test_df.empty:
    st.warning("""
    ⚠️ **CSV file is empty!**

    Your `customer_groups.csv` file exists but has no customer data.

    **Option 1: Export from database**
    ```bash
    python3 export_groups_to_csv.py
    ```

    **Option 2: Add customers manually**

    Edit `customer_groups.csv` and add customers in this format:
    ```
    GroupName,CustomerID,CustomerName,Company
    ABC Stores,1234,John Smith,ABC Store 1
    ABC Stores,1235,John Smith,ABC Store 2
    ```

    Where:
    - **GroupName**: Any name you want for the group
    - **CustomerID**: The customer ID from your database
    - **CustomerName**: Customer's name (optional, but helpful)
    - **Company**: Company name (optional, but helpful)

    You can add multiple customers to the same group by using the same GroupName.
    """)
    st.stop()

# ===== SIDEBAR =====
st.sidebar.header("⚙️ Controls")

# Time Period Selector
st.sidebar.subheader("📅 Time Period")
time_period_type = st.sidebar.radio(
    "Select period:",
    ["Last N Days", "Year to Date", "All Time", "Custom Range"],
    help="Choose how to filter the time period"
)

start_date = None
end_date = None
days = None

if time_period_type == "Last N Days":
    days = st.sidebar.selectbox(
        "Days",
        [7, 30, 60, 90],
        index=1,
        help="Number of days to look back"
    )
elif time_period_type == "Year to Date":
    # YTD: from Jan 1 of current year to today
    today = datetime.now().date()
    start_date = datetime(today.year, 1, 1).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    st.sidebar.info(f"📅 {start_date} to {end_date}")
elif time_period_type == "All Time":
    # All time: from 2000-01-01 to today
    start_date = "2000-01-01"
    end_date = datetime.now().date().strftime('%Y-%m-%d')
    st.sidebar.info(f"📅 {start_date} to {end_date}")
elif time_period_type == "Custom Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input(
            "From",
            value=datetime.now().date() - timedelta(days=30)
        )
    with col2:
        end = st.date_input(
            "To",
            value=datetime.now().date()
        )
    start_date = start.strftime('%Y-%m-%d')
    end_date = end.strftime('%Y-%m-%d')

st.sidebar.markdown("---")
search = st.sidebar.text_input("🔍 Search Group", "", help="Filter by group name")

st.sidebar.markdown("---")
st.sidebar.caption("""
💡 **Tips:**
- Edit `customer_groups.csv` to update groups
- Click "Refresh Analytics" to reload data
- Analytics load once and filter by group
""")

if st.sidebar.button("🔄 Refresh Analytics", use_container_width=True):
    # Clear cache to force reload
    if 'analytics_cache' in st.session_state:
        del st.session_state['analytics_cache']
    if 'analytics_cache_key' in st.session_state:
        del st.session_state['analytics_cache_key']
    st.rerun()

# ===== INITIALIZE SESSION STATE =====
if 'selected_group' not in st.session_state:
    st.session_state.selected_group = None

# ===== LOAD ALL STORE ANALYTICS (CACHED) =====
def get_analytics_cache_key():
    """Generate cache key based on time period selection."""
    if time_period_type == "Last N Days":
        return f"days_{days}"
    elif time_period_type == "Year to Date":
        return f"ytd_{datetime.now().year}"
    elif time_period_type == "All Time":
        return "all_time"
    else:  # Custom Range
        return f"custom_{start_date}_{end_date}"

cache_key = get_analytics_cache_key()

# Load analytics if not cached or cache key changed
if ('analytics_cache' not in st.session_state or
    'analytics_cache_key' not in st.session_state or
    st.session_state.analytics_cache_key != cache_key):

    with st.spinner("Loading all store analytics... (this may take a moment)"):
        if days:
            analytics_data = simple_customer_group_manager.load_all_store_analytics(days=days)
        else:
            analytics_data = simple_customer_group_manager.load_all_store_analytics(
                start_date=start_date,
                end_date=end_date
            )

        st.session_state.analytics_cache = analytics_data
        st.session_state.analytics_cache_key = cache_key

        if analytics_data:
            st.success(f"✅ Loaded analytics for {len(analytics_data)} stores")
else:
    analytics_data = st.session_state.analytics_cache

# Load group summary (fast - just reads CSV)
groups_df = simple_customer_group_manager.get_group_summary()

if groups_df.empty:
    st.warning("No groups found in customer_groups.csv")
    st.stop()

# Apply search
if search:
    groups_df = groups_df[groups_df['GroupName'].str.contains(search, case=False, na=False)]

# ===== MAIN VIEW =====
if st.session_state.selected_group is None:
    # ===== GROUP LIST VIEW =====
    st.subheader(f"📊 Groups ({len(groups_df)} total)")

    # Show groups
    for _, row in groups_df.iterrows():
        col1, col2, col3 = st.columns([4, 2, 1])

        with col1:
            st.markdown(f"**{row['GroupName']}**")

        with col2:
            st.caption(f"{int(row['member_count'])} stores")

        with col3:
            if st.button("View →", key=f"btn_{row['GroupName']}"):
                st.session_state.selected_group = row['GroupName']
                st.rerun()

        st.markdown("---")

else:
    # ===== GROUP DETAIL VIEW =====
    group_name = st.session_state.selected_group

    # Back button
    if st.button("← Back to Groups"):
        st.session_state.selected_group = None
        st.rerun()

    st.markdown("---")

    st.header(f"👥 {group_name}")

    # Get period description
    if time_period_type == "Last N Days":
        period_desc = f"Last {days} days"
    elif time_period_type == "Year to Date":
        period_desc = "Year to Date"
    elif time_period_type == "All Time":
        period_desc = "All Time"
    else:
        period_desc = f"{start_date} to {end_date}"

    st.caption(f"{period_desc} • Individual store breakdown")

    # Filter analytics data for this group
    groups_csv_df = simple_customer_group_manager.load_groups_from_csv()
    group_customers = groups_csv_df[groups_csv_df['GroupName'] == group_name]

    if group_customers.empty:
        st.error("No customers found in this group")
        st.stop()

    # Get analytics for stores in this group
    group_customer_ids = group_customers['CustomerID'].tolist()
    stores_in_group = [
        analytics_data[cid] for cid in group_customer_ids
        if cid in analytics_data
    ]

    if not stores_in_group:
        st.warning("No analytics data available for this group")
        st.stop()

    # Calculate group totals
    total_sales = sum(s['total_sales'] for s in stores_in_group)
    total_gp = sum(s['gross_profit'] for s in stores_in_group)
    total_ar = sum(s['ar_balance'] for s in stores_in_group)
    total_pd_checks = sum(s['pd_checks_total'] for s in stores_in_group)
    total_pd_count = sum(s['pd_checks_count'] for s in stores_in_group)
    total_transactions = sum(s['transaction_count'] for s in stores_in_group)
    gp_percentage = (total_gp / total_sales * 100) if total_sales > 0 else 0

    # ===== GROUP TOTALS =====
    st.subheader("📈 Group Totals")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Sales", f"${total_sales:,.2f}")

    with col2:
        st.metric(
            "Gross Profit",
            f"${total_gp:,.2f}",
            delta=f"{gp_percentage:.1f}%"
        )

    with col3:
        st.metric("AR Balance", f"${total_ar:,.2f}")

    with col4:
        if total_pd_checks > 0:
            st.metric(
                "PD Checks",
                f"${total_pd_checks:,.2f}",
                delta=f"{total_pd_count} checks"
            )
        else:
            st.metric("PD Checks", "$0.00")

    with col5:
        st.metric("Transactions", f"{total_transactions:,}")

    st.markdown("---")

    # ===== CATEGORY ANALYSIS =====
    st.subheader("📊 Category Analysis")

    with st.spinner("Loading category breakdown..."):
        if days:
            categories = simple_customer_group_manager.get_group_category_analysis(
                group_name, days=days, limit=5
            )
        else:
            # Need to add support for date ranges in category analysis
            # For now, use approximate days
            days_approx = (datetime.strptime(end_date, '%Y-%m-%d') -
                          datetime.strptime(start_date, '%Y-%m-%d')).days
            categories = simple_customer_group_manager.get_group_category_analysis(
                group_name, days=days_approx, limit=5
            )

    if categories:
        # Show top 5 categories
        st.markdown("**Top 5 Categories by Sales:**")

        for idx, cat in enumerate(categories, 1):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                with col1:
                    st.markdown(f"**{idx}. {cat['category_name']}**")

                with col2:
                    st.metric("Sales", f"${cat['group_sales']:,.2f}")

                with col3:
                    st.metric("GP", f"${cat['group_gp']:,.2f}",
                             delta=f"{cat['gp_percentage']:.1f}%")

                with col4:
                    st.metric("% of Category", f"{cat['pct_of_total_category_sales']:.1f}%",
                             help="This group's share of total market sales in this category")

        # Show all categories button
        if st.button("📋 Show All Categories"):
            with st.spinner("Loading all categories..."):
                if days:
                    all_categories = simple_customer_group_manager.get_group_category_analysis(
                        group_name, days=days, limit=0
                    )
                else:
                    all_categories = simple_customer_group_manager.get_group_category_analysis(
                        group_name, days=days_approx, limit=0
                    )

            if all_categories:
                # Create DataFrame for display
                cat_df = pd.DataFrame(all_categories)
                cat_df = cat_df.rename(columns={
                    'category_name': 'Category',
                    'group_sales': 'Sales',
                    'group_gp': 'Gross Profit',
                    'gp_percentage': 'GP %',
                    'transaction_count': 'Transactions',
                    'pct_of_total_category_sales': '% of Total Category'
                })

                # Format currency columns
                cat_df['Sales'] = cat_df['Sales'].apply(lambda x: f"${x:,.2f}")
                cat_df['Gross Profit'] = cat_df['Gross Profit'].apply(lambda x: f"${x:,.2f}")
                cat_df['GP %'] = cat_df['GP %'].apply(lambda x: f"{x:.1f}%")
                cat_df['% of Total Category'] = cat_df['% of Total Category'].apply(lambda x: f"{x:.1f}%")

                st.dataframe(cat_df, use_container_width=True, hide_index=True)

                # Category chart
                chart_df = pd.DataFrame(all_categories)
                fig = px.bar(
                    chart_df.head(10),
                    x='category_name',
                    y='group_sales',
                    title='Top 10 Categories by Sales',
                    labels={'category_name': 'Category', 'group_sales': 'Sales ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category data available for this time period")

    st.markdown("---")

    # ===== INDIVIDUAL STORES =====
    st.subheader(f"🏪 Individual Stores ({len(stores_in_group)})")

    # Sort by sales
    stores_sorted = sorted(stores_in_group, key=lambda x: x['total_sales'], reverse=True)

    for store in stores_sorted:
        # Build expander title
        title = f"**{store['customer_name']}**"
        if store['company'] and store['company'] != store['customer_name']:
            title += f" ({store['company']})"
        title += f" - ${store['total_sales']:,.2f}"

        with st.expander(title, expanded=False):
            # Store metrics in columns
            col1, col2, col3, col4, col5, col6 = st.columns(6)

            with col1:
                st.metric("Sales", f"${store['total_sales']:,.2f}")

            with col2:
                st.metric(
                    "GP",
                    f"${store['gross_profit']:,.2f}",
                    delta=f"{store['gp_percentage']:.1f}%"
                )

            with col3:
                st.metric("AR Balance", f"${store['ar_balance']:,.2f}")

            with col4:
                if store['pd_checks_total'] > 0:
                    st.metric(
                        "PD Checks",
                        f"${store['pd_checks_total']:,.2f}",
                        delta=f"{store['pd_checks_count']} checks"
                    )
                else:
                    st.metric("PD Checks", "$0.00")

            with col5:
                st.metric("Transactions", f"{store['transaction_count']:,}")

            with col6:
                if store['last_purchase']:
                    last_purchase_date = store['last_purchase'].split()[0]  # Get just the date
                    st.metric("Last Purchase", last_purchase_date)
                else:
                    st.metric("Last Purchase", "Never")

            # Show CustomerID for reference
            st.caption(f"Customer ID: {store['customer_id']}")

# Footer
st.markdown("---")
st.caption("""
💡 **Edit customer_groups.csv to update groups** •
Click "Refresh Analytics" to reload data •
Fast loading with bulk query (3.9x faster!)
""")
