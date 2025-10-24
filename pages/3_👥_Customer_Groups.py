"""Customer Groups Dashboard - SOUNDEX-based grouping with comprehensive analytics."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Try pyodbc first (in requirements.txt), fall back to pymssql
try:
    from src.database.sql_server_pyodbc import test_connection
except ImportError:
    from src.database.sql_server import test_connection

from src.modules.customer_groups import customer_group_manager

# Page configuration
st.set_page_config(
    page_title="Customer Groups",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Customer Groups")
st.markdown("**SOUNDEX-based customer grouping** with comprehensive analytics by time period")

# Test database connection
if not test_connection():
    st.error("❌ Cannot connect to database. Please check your connection settings.")
    st.stop()

# Sidebar controls
st.sidebar.header("⚙️ Controls")

# Sync button
if st.sidebar.button("🔄 Sync Customer Groups", help="Update groups from database"):
    with st.spinner("Syncing customer groups..."):
        result = customer_group_manager.sync_customer_groups(force_rebuild=False)
        if result['status'] == 'success':
            st.sidebar.success(f"✅ Synced: {result['customers_processed']} customers, "
                             f"{result['groups_created']} groups created, "
                             f"{result['groups_updated']} groups updated")
        else:
            st.sidebar.error(f"❌ Error: {result.get('message', 'Unknown error')}")

# Force rebuild option
if st.sidebar.checkbox("Show Advanced Options"):
    if st.sidebar.button("🔨 Force Rebuild All Groups", help="Clear and rebuild all groups"):
        with st.spinner("Rebuilding all groups..."):
            result = customer_group_manager.sync_customer_groups(force_rebuild=True)
            if result['status'] == 'success':
                st.sidebar.success(f"✅ Rebuilt: {result['customers_processed']} customers, "
                                 f"{result['groups_created']} groups created")
            else:
                st.sidebar.error(f"❌ Error: {result.get('message', 'Unknown error')}")

st.sidebar.markdown("---")

# Time period selector
st.sidebar.header("📅 Time Period")
time_period = st.sidebar.selectbox(
    "Select Period",
    ["Last 7 Days", "Last 30 Days", "Last 60 Days", "Last 90 Days",
     "Year to Date", "All Time", "Custom Range"],
    index=1  # Default to Last 30 Days
)

# Calculate date range
today = datetime.now().date()
if time_period == "Last 7 Days":
    start_date = today - timedelta(days=7)
    end_date = today
elif time_period == "Last 30 Days":
    start_date = today - timedelta(days=30)
    end_date = today
elif time_period == "Last 60 Days":
    start_date = today - timedelta(days=60)
    end_date = today
elif time_period == "Last 90 Days":
    start_date = today - timedelta(days=90)
    end_date = today
elif time_period == "Year to Date":
    start_date = datetime(today.year, 1, 1).date()
    end_date = today
elif time_period == "Custom Range":
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", today - timedelta(days=30))
    end_date = col2.date_input("End Date", today)
else:  # All Time
    start_date = None
    end_date = None

# Display date range
if start_date and end_date:
    st.sidebar.info(f"📊 Analyzing: {start_date} to {end_date}")
else:
    st.sidebar.info("📊 Analyzing: All Time")

st.sidebar.markdown("---")

# Filters
st.sidebar.header("🔍 Filters")
min_sales = st.sidebar.number_input(
    "Minimum Sales ($)",
    min_value=0,
    value=1000,
    step=100,
    help="Only show groups with sales above this amount"
)

search_term = st.sidebar.text_input(
    "Search Group Name",
    "",
    help="Filter groups by name"
)

# Main content
# Initialize session state for selected group
if 'selected_group_id' not in st.session_state:
    st.session_state.selected_group_id = None

# Load groups data
with st.spinner("Loading customer groups..."):
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    groups_df = customer_group_manager.get_all_groups_summary(
        min_sales=min_sales,
        start_date=start_date_str,
        end_date=end_date_str
    )

if groups_df.empty:
    st.warning("⚠️ No customer groups found. Click 'Sync Customer Groups' to create groups.")
    st.stop()

# Apply search filter
if search_term:
    groups_df = groups_df[groups_df['group_name'].str.contains(search_term, case=False, na=False)]

# Summary metrics at top
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Total Groups",
        f"{len(groups_df):,}"
    )

with col2:
    st.metric(
        "Total Sales",
        f"${groups_df['total_sales'].sum():,.0f}"
    )

with col3:
    st.metric(
        "Total GP",
        f"${groups_df['gross_profit'].sum():,.0f}",
        delta=f"{groups_df['gp_percentage'].mean():.1f}% avg"
    )

with col4:
    st.metric(
        "Total AR",
        f"${groups_df['ar_balance'].sum():,.0f}"
    )

with col5:
    st.metric(
        "Avg Days to Pay",
        f"{groups_df['avg_days_to_pay'].mean():.0f} days"
    )

st.markdown("---")

# Main view or drill-down view
if st.session_state.selected_group_id is None:
    # ===== GROUP LIST VIEW =====
    st.subheader("📊 Customer Groups")

    # Sort options
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col1:
        sort_by = st.selectbox(
            "Sort by",
            ["Total Sales", "Gross Profit", "AR Balance", "Group Name", "Member Count"],
            key="sort_by"
        )
    with sort_col2:
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True, key="sort_order")

    # Map sort selection to column name
    sort_map = {
        "Total Sales": "total_sales",
        "Gross Profit": "gross_profit",
        "AR Balance": "ar_balance",
        "Group Name": "group_name",
        "Member Count": "member_count"
    }

    sort_column = sort_map[sort_by]
    ascending = (sort_order == "Ascending")

    groups_df_sorted = groups_df.sort_values(by=sort_column, ascending=ascending)

    # Display groups table
    for idx, row in groups_df_sorted.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 2, 2, 2, 1])

            with col1:
                st.markdown(f"**{row['group_name']}**")
                st.caption(f"{int(row['member_count'])} stores")

            with col2:
                st.metric("Sales", f"${row['total_sales']:,.0f}")

            with col3:
                st.metric("GP", f"${row['gross_profit']:,.0f}",
                         delta=f"{row['gp_percentage']:.1f}%")

            with col4:
                st.metric("AR Balance", f"${row['ar_balance']:,.0f}")

            with col5:
                pd_checks = row['pd_checks_amount']
                st.metric("PD Checks", f"${pd_checks:,.0f}" if pd_checks > 0 else "-")

            with col6:
                if st.button("View Details", key=f"btn_{row['group_id']}"):
                    st.session_state.selected_group_id = row['group_id']
                    st.rerun()

            st.markdown("---")

else:
    # ===== GROUP DETAIL VIEW =====
    group_id = st.session_state.selected_group_id

    # Back button
    if st.button("← Back to Groups"):
        st.session_state.selected_group_id = None
        st.rerun()

    st.markdown("---")

    # Load detailed analytics
    with st.spinner("Loading group details..."):
        analytics = customer_group_manager.get_group_analytics(
            group_id,
            start_date_str,
            end_date_str
        )

        categories = customer_group_manager.get_group_category_analysis(
            group_id,
            start_date_str,
            end_date_str,
            limit=5
        )

        members = customer_group_manager.get_group_member_details(
            group_id,
            start_date_str,
            end_date_str
        )

    # Find group name
    group_row = groups_df[groups_df['group_id'] == group_id].iloc[0]

    st.header(f"👥 {group_row['group_name']}")
    st.caption(f"{len(members)} stores in this group")

    # Overview metrics
    st.subheader("📈 Overview")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Sales", f"${analytics['financial']['total_sales']:,.0f}")

    with col2:
        st.metric("Gross Profit", f"${analytics['financial']['gross_profit']:,.0f}",
                 delta=f"{analytics['financial']['gp_percentage']:.1f}%")

    with col3:
        st.metric("AR Balance", f"${analytics['ar']['total_balance']:,.0f}")

    with col4:
        st.metric("PD Checks", f"${analytics['post_dated_checks']['total_amount']:,.0f}")

    with col5:
        st.metric("Avg Days to Pay", f"{analytics['payment_velocity']['avg_days_to_pay']:.0f} days")

    st.markdown("---")

    # Category Analysis
    st.subheader("📦 Top 5 Categories")

    if categories:
        # Create category chart
        cat_df = pd.DataFrame(categories)

        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Sales',
            x=cat_df['category_name'],
            y=cat_df['group_sales'],
            marker_color='lightblue'
        ))

        fig.update_layout(
            title="Sales by Category",
            xaxis_title="Category",
            yaxis_title="Sales ($)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Category details table
        st.markdown("**Category Details**")
        for cat in categories:
            with st.expander(f"📦 {cat['category_name']} - ${cat['group_sales']:,.0f}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Group Sales", f"${cat['group_sales']:,.0f}")
                    st.metric("Gross Profit", f"${cat['group_gp']:,.0f}")

                with col2:
                    st.metric("GP %", f"{cat['gp_percentage']:.1f}%")
                    st.metric("Transactions", f"{cat['transaction_count']:,}")

                with col3:
                    st.metric(
                        "% of Total Category Sales",
                        f"{cat['pct_of_total_category_sales']:.1f}%",
                        help="This group's percentage of your TOTAL sales in this category"
                    )
    else:
        st.info("No category data available for this period")

    # Show all categories option
    if st.checkbox("Show All Categories"):
        with st.spinner("Loading all categories..."):
            all_categories = customer_group_manager.get_group_category_analysis(
                group_id,
                start_date_str,
                end_date_str,
                limit=0  # Get all
            )

            if all_categories:
                all_cat_df = pd.DataFrame(all_categories)
                st.dataframe(
                    all_cat_df[['category_name', 'group_sales', 'group_gp',
                               'gp_percentage', 'pct_of_total_category_sales']],
                    use_container_width=True
                )

    st.markdown("---")

    # Individual Store Details
    st.subheader("🏪 Individual Stores")

    members_df = pd.DataFrame(members)

    for _, member in members_df.iterrows():
        with st.expander(
            f"{'⭐ ' if member['is_primary'] else ''}"
            f"{member['customer_name'] or member['company']} "
            f"(ID: {member['customer_id']})"
        ):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Sales", f"${member['total_sales']:,.0f}")

            with col2:
                st.metric("Gross Profit", f"${member['gross_profit']:,.0f}",
                         delta=f"{member['gp_percentage']:.1f}%")

            with col3:
                st.metric("AR Balance", f"${member['ar_balance']:,.0f}")

            with col4:
                st.metric("Transactions", f"{member['transaction_count']:,}")

            if member['last_purchase']:
                st.caption(f"Last purchase: {member['last_purchase']}")

# Footer
st.markdown("---")
st.caption("💡 Groups are automatically created using SOUNDEX phonetic matching. "
          "Click 'Sync Customer Groups' to update with new customers.")
