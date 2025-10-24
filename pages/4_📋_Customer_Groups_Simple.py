"""Simple CSV-based Customer Groups - Fast and easy to maintain."""

import streamlit as st
import pandas as pd
from datetime import datetime

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

# Check if CSV exists
import os
if not os.path.exists('customer_groups.csv'):
    st.warning("""
    ⚠️ **CSV file not found!**

    Run this command to export your existing groups to CSV:
    ```
    python3 export_groups_to_csv.py
    ```

    Or create `customer_groups.csv` manually with this format:
    ```
    GroupName,CustomerID,CustomerName,Company
    ABC Stores,1234,John Smith,ABC Store 1
    ABC Stores,1235,John Smith,ABC Store 2
    XYZ Gas,5678,Jane Doe,XYZ Gas Station
    ```
    """)
    st.stop()

# Sidebar
st.sidebar.header("⚙️ Controls")

days = st.sidebar.selectbox(
    "Time Period",
    [7, 30, 60, 90],
    index=1,
    help="Days to analyze"
)

search = st.sidebar.text_input("Search Group", "", help="Filter by group name")

st.sidebar.markdown("---")
st.sidebar.caption("""
💡 **Tips:**
- Edit `customer_groups.csv` to update groups
- Reload page to see changes
- Analytics calculate only when viewing a group
""")

# Initialize session state
if 'selected_group' not in st.session_state:
    st.session_state.selected_group = None

# Load group summary (fast - just reads CSV)
groups_df = simple_customer_group_manager.get_group_summary()

if groups_df.empty:
    st.warning("No groups found in customer_groups.csv")
    st.stop()

# Apply search
if search:
    groups_df = groups_df[groups_df['GroupName'].str.contains(search, case=False, na=False)]

# Main view
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
    st.caption(f"Last {days} days • Individual store breakdown")

    # Load analytics (calculates now)
    with st.spinner("Calculating analytics by store..."):
        group_data = simple_customer_group_manager.get_group_totals(group_name, days=days)

    if group_data['store_count'] == 0:
        st.error("No data found for this group")
        st.stop()

    # Group totals
    st.subheader("📈 Group Totals")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Sales", f"${group_data['total_sales']:,.0f}")

    with col2:
        gp_color = "normal" if group_data['gp_percentage'] >= 0 else "inverse"
        st.metric("Gross Profit", f"${group_data['gross_profit']:,.0f}",
                 delta=f"{group_data['gp_percentage']:.1f}%", delta_color=gp_color)

    with col3:
        st.metric("AR Balance", f"${group_data['ar_balance']:,.0f}")

    with col4:
        if group_data['pd_checks_total'] > 0:
            st.metric("PD Checks", f"${group_data['pd_checks_total']:,.0f}",
                     delta=f"{group_data['pd_checks_count']} checks")
        else:
            st.metric("PD Checks", "$0")

    st.markdown("---")

    # Individual stores
    st.subheader(f"🏪 Individual Stores ({group_data['store_count']})")

    stores = group_data['stores']

    # Sort by sales
    stores_sorted = sorted(stores, key=lambda x: x['total_sales'], reverse=True)

    for store in stores_sorted:
        with st.expander(
            f"**{store['customer_name']}** {f\"({store['company']})\" if store['company'] else ''} "
            f"- ${store['total_sales']:,.0f}",
            expanded=False
        ):
            # Store metrics in columns
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Sales", f"${store['total_sales']:,.0f}")

            with col2:
                gp_color = "normal" if store['gp_percentage'] >= 0 else "inverse"
                st.metric("GP", f"${store['gross_profit']:,.0f}",
                         delta=f"{store['gp_percentage']:.1f}%", delta_color=gp_color)

            with col3:
                st.metric("AR", f"${store['ar_balance']:,.0f}")

            with col4:
                if store['pd_checks_total'] > 0:
                    st.metric("PD Checks", f"${store['pd_checks_total']:,.0f}")
                else:
                    st.metric("PD Checks", "-")

            with col5:
                st.metric("Transactions", f"{store['transaction_count']:,}")

            if store['last_purchase']:
                st.caption(f"Last purchase: {store['last_purchase']}")

# Footer
st.markdown("---")
st.caption("""
💡 **Edit customer_groups.csv to update groups** •
Reload page to see changes •
Fast loading (no database caching needed)
""")
