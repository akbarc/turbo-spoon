"""Customer Groups Dashboard - Fast cached analytics with SOUNDEX grouping."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from src.database.sql_server import test_connection
from src.modules.customer_groups import customer_group_manager

# Page configuration
st.set_page_config(
    page_title="Customer Groups",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Customer Groups")
st.markdown("**SOUNDEX-based customer grouping** - Last 30 days analytics")

# Test database connection
if not test_connection():
    st.error("❌ Cannot connect to database. Please check your connection settings.")
    st.stop()

# Sidebar controls
st.sidebar.header("⚙️ Controls")

# Sync and refresh buttons
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("🔄 Sync Groups", help="Update customer groups from database"):
        with st.spinner("Syncing customer groups..."):
            result = customer_group_manager.sync_customer_groups(force_rebuild=False)
            if result['status'] == 'success':
                st.success(f"✅ {result['customers_processed']} customers synced")
                st.rerun()
            else:
                st.error(f"❌ Error: {result.get('message', 'Unknown error')}")

with col2:
    if st.button("📊 Refresh Analytics", help="Recalculate all analytics (may take a minute)"):
        with st.spinner("Calculating analytics for all groups..."):
            result = customer_group_manager.calculate_and_cache_all_analytics()
            if result['status'] == 'success':
                st.success(f"✅ Calculated {result['groups_processed']} groups")
                st.rerun()
            else:
                st.error(f"❌ Error: {result.get('message', 'Unknown error')}")

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

st.sidebar.markdown("---")
st.sidebar.caption("💡 **Tip**: Analytics are cached for fast loading. Click 'Refresh Analytics' to update.")

# Initialize session state for selected group
if 'selected_group_id' not in st.session_state:
    st.session_state.selected_group_id = None

# Load groups data from cache (fast!)
with st.spinner("Loading customer groups..."):
    groups_df = customer_group_manager.get_cached_groups_summary(min_sales=min_sales)

if groups_df.empty:
    st.warning("⚠️ No customer groups found. Click 'Sync Groups' then 'Refresh Analytics' to build the cache.")
    st.stop()

# Check if cache is empty (no analytics calculated yet)
if groups_df['total_sales'].isna().all():
    st.warning("⚠️ Analytics not calculated yet. Click 'Refresh Analytics' to calculate group metrics.")
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
    total_sales = groups_df['total_sales'].sum()
    st.metric(
        "Total Sales",
        f"${total_sales:,.0f}"
    )

with col3:
    total_gp = groups_df['gross_profit'].sum()
    avg_gp_pct = groups_df['gp_percentage'].mean()
    st.metric(
        "Total GP",
        f"${total_gp:,.0f}",
        delta=f"{avg_gp_pct:.1f}% avg"
    )

with col4:
    total_ar = groups_df['ar_balance'].sum()
    st.metric(
        "Total AR",
        f"${total_ar:,.0f}"
    )

with col5:
    total_pd_checks = groups_df['pd_checks_amount'].sum()
    st.metric(
        "PD Checks",
        f"${total_pd_checks:,.0f}" if total_pd_checks > 0 else "$0"
    )

st.markdown("---")

# Main view or drill-down view
if st.session_state.selected_group_id is None:
    # ===== GROUP LIST VIEW =====
    st.subheader("📊 Customer Groups (Last 30 Days)")

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

    # Display groups table with better formatting
    for idx, row in groups_df_sorted.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])

            with col1:
                st.markdown(f"**{row['group_name']}**")
                st.caption(f"{int(row['member_count'])} stores")

            with col2:
                st.metric("Sales", f"${row['total_sales']/1000:.1f}K" if row['total_sales'] >= 1000 else f"${row['total_sales']:.0f}")

            with col3:
                gp_color = "normal" if row['gp_percentage'] >= 0 else "inverse"
                st.metric("GP", f"${row['gross_profit']/1000:.1f}K" if abs(row['gross_profit']) >= 1000 else f"${row['gross_profit']:.0f}",
                         delta=f"{row['gp_percentage']:.1f}%", delta_color=gp_color)

            with col4:
                ar = row['ar_balance']
                st.metric("AR", f"${ar/1000:.1f}K" if ar >= 1000 else f"${ar:.0f}")

            with col5:
                pd_checks = row['pd_checks_amount']
                if pd_checks > 0:
                    st.metric("PD Checks", f"${pd_checks/1000:.1f}K" if pd_checks >= 1000 else f"${pd_checks:.0f}")
                else:
                    st.metric("PD Checks", "-")

            with col6:
                if st.button("View →", key=f"btn_{row['group_id']}"):
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

    # Find group info
    group_row = groups_df[groups_df['group_id'] == group_id]

    if group_row.empty:
        st.error("Group not found")
        if st.button("Back"):
            st.session_state.selected_group_id = None
            st.rerun()
        st.stop()

    group_row = group_row.iloc[0]

    st.header(f"👥 {group_row['group_name']}")
    st.caption(f"{int(group_row['member_count'])} stores in this group • Last 30 days")

    # Overview metrics
    st.subheader("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Sales", f"${group_row['total_sales']:,.0f}")

    with col2:
        gp_color = "normal" if group_row['gp_percentage'] >= 0 else "inverse"
        st.metric("Gross Profit", f"${group_row['gross_profit']:,.0f}",
                 delta=f"{group_row['gp_percentage']:.1f}%", delta_color=gp_color)

    with col3:
        st.metric("AR Balance", f"${group_row['ar_balance']:,.0f}")

    with col4:
        if group_row['pd_checks_amount'] > 0:
            st.metric("PD Checks", f"${group_row['pd_checks_amount']:,.0f}")
        else:
            st.metric("PD Checks", "$0")

    st.markdown("---")

    # Individual Store Details
    st.subheader("🏪 Individual Stores")

    with st.spinner("Loading store details..."):
        # Get individual store metrics from overlay
        members = customer_group_manager.get_group_members(group_id)

        if not members.empty:
            st.dataframe(
                members[['customer_name', 'customer_company']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No store details available")

    st.markdown("---")
    st.caption(f"📅 Last updated: {group_row.get('last_updated', 'Unknown')}")

# Footer
st.markdown("---")
st.caption("💡 Groups are automatically created using SOUNDEX phonetic matching. "
          "Analytics are cached for fast loading (30 day rolling window).")
