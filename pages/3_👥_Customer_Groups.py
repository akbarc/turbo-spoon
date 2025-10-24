"""Customer Groups Dashboard - SOUNDEX grouping with fresh analytics."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.database.sql_server import test_connection, execute_query
from src.modules.customer_groups import customer_group_manager

# Page configuration
st.set_page_config(
    page_title="Customer Groups",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Customer Groups")
st.markdown("**SOUNDEX-based customer grouping** - Analytics calculated fresh each time")

# Test database connection
if not test_connection():
    st.error("❌ Cannot connect to database. Please check your connection settings.")
    st.stop()

# Sidebar controls
st.sidebar.header("⚙️ Controls")

# Time Period Selector
st.sidebar.subheader("📅 Time Period")
days = st.sidebar.selectbox(
    "Days to analyze",
    [7, 30, 60, 90],
    index=1,
    help="Number of days to look back for analytics"
)

# Sync groups button
if st.sidebar.button("🔄 Sync Groups", help="Update customer groups from database", use_container_width=True):
    with st.spinner("Syncing customer groups..."):
        result = customer_group_manager.sync_customer_groups(force_rebuild=False)
        if result['status'] == 'success':
            st.success(f"✅ {result['customers_processed']} customers synced")
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
st.sidebar.caption("💡 **Tip**: Analytics are calculated fresh each time you change the date filter.")

# Initialize session state for selected group
if 'selected_group_id' not in st.session_state:
    st.session_state.selected_group_id = None

# Load groups list (just names and IDs, no analytics yet)
with st.spinner("Loading customer groups..."):
    groups_list = customer_group_manager.overlay.get_soundex_groups()

if groups_list.empty:
    st.warning("⚠️ No customer groups found. Click 'Sync Groups' to create groups.")
    st.stop()

# Calculate date range for queries
end_date = datetime.now().date()
start_date = end_date - timedelta(days=days)
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

# Calculate analytics for all groups (fresh, not cached)
with st.spinner(f"Calculating analytics for last {days} days..."):
    groups_with_analytics = []

    for _, group in groups_list.iterrows():
        group_id = group['id']

        # Get group members
        members = customer_group_manager.get_group_members(group_id)
        if members.empty:
            continue

        customer_ids = members['customer_id'].tolist()
        customer_ids_str = ','.join([str(cid) for cid in customer_ids])

        try:
            # Calculate financial metrics
            financial_query = f"""
                SELECT
                    COUNT(DISTINCT t.TransactionNumber) as transaction_count,
                    ISNULL(SUM(t.Total), 0) as total_sales
                FROM dbo.[Transaction] t
                WHERE t.CustomerID IN ({customer_ids_str})
                    AND t.Time >= '{start_date_str}'
                    AND t.Time <= '{end_date_str}'
            """
            financial_df = execute_query(financial_query)

            # Calculate GP
            gp_query = f"""
                SELECT
                    ISNULL(SUM((te.Price - te.Cost) * te.Quantity), 0) as gross_profit
                FROM dbo.TransactionEntry te
                INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                WHERE t.CustomerID IN ({customer_ids_str})
                    AND t.Time >= '{start_date_str}'
                    AND t.Time <= '{end_date_str}'
            """
            gp_df = execute_query(gp_query)

            # Get AR balance (current)
            ar_query = f"""
                SELECT
                    ISNULL(SUM(AccountBalance), 0) as total_ar
                FROM dbo.Customer
                WHERE ID IN ({customer_ids_str})
            """
            ar_df = execute_query(ar_query)

            # Get PD checks from Payment table
            pd_query = f"""
                SELECT
                    COUNT(*) as pd_count,
                    ISNULL(SUM(Amount), 0) as pd_total
                FROM dbo.Payment
                WHERE CustomerID IN ({customer_ids_str})
                    AND (
                        UPPER(Comment) LIKE '%PD%'
                        OR UPPER(Comment) LIKE '%POST DATE%'
                        OR UPPER(Comment) LIKE '%P D%'
                        OR UPPER(Comment) LIKE '%POSTDATE%'
                    )
                    AND Amount > 0
            """
            pd_df = execute_query(pd_query)

            total_sales = float(financial_df.iloc[0]['total_sales'] or 0)
            gross_profit = float(gp_df.iloc[0]['gross_profit'] or 0)

            groups_with_analytics.append({
                'group_id': group_id,
                'group_name': group['group_name'],
                'member_count': len(members),
                'total_sales': total_sales,
                'gross_profit': gross_profit,
                'gp_percentage': (gross_profit / total_sales * 100) if total_sales > 0 else 0,
                'ar_balance': float(ar_df.iloc[0]['total_ar'] or 0),
                'pd_checks_amount': float(pd_df.iloc[0]['pd_total'] or 0),
                'pd_checks_count': int(pd_df.iloc[0]['pd_count'] or 0),
                'transaction_count': int(financial_df.iloc[0]['transaction_count'] or 0)
            })
        except Exception as e:
            st.error(f"Error calculating analytics for {group['group_name']}: {str(e)}")
            continue

    groups_df = pd.DataFrame(groups_with_analytics)

# Apply filters
if not groups_df.empty:
    groups_df = groups_df[groups_df['total_sales'] >= min_sales]

    if search_term:
        groups_df = groups_df[groups_df['group_name'].str.contains(search_term, case=False, na=False)]

if groups_df.empty:
    st.warning("No groups match your filters.")
    st.stop()

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
    st.subheader(f"📊 Customer Groups (Last {days} Days)")

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
    st.caption(f"{int(group_row['member_count'])} stores in this group • Last {days} days")

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
            st.metric("PD Checks", f"${group_row['pd_checks_amount']:,.0f}",
                     delta=f"{group_row['pd_checks_count']} checks")
        else:
            st.metric("PD Checks", "$0")

    st.markdown("---")

    # Individual Store Details
    st.subheader("🏪 Individual Stores")

    with st.spinner("Loading store details..."):
        # Get individual store metrics
        members = customer_group_manager.get_group_members(group_id)

        if not members.empty:
            # Calculate analytics for each store
            store_analytics = []

            for _, member in members.iterrows():
                customer_id = member['customer_id']

                # Get analytics for this store
                try:
                    # Sales query
                    sales_query = f"""
                        SELECT
                            COUNT(DISTINCT TransactionNumber) as transaction_count,
                            ISNULL(SUM(Total), 0) as total_sales,
                            MAX(Time) as last_purchase
                        FROM dbo.[Transaction]
                        WHERE CustomerID = {customer_id}
                            AND Time >= '{start_date_str}'
                            AND Time <= '{end_date_str}'
                    """
                    sales_df = execute_query(sales_query)

                    # GP query
                    gp_query = f"""
                        SELECT
                            ISNULL(SUM((te.Price - te.Cost) * te.Quantity), 0) as gross_profit
                        FROM dbo.TransactionEntry te
                        INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
                        WHERE t.CustomerID = {customer_id}
                            AND t.Time >= '{start_date_str}'
                            AND t.Time <= '{end_date_str}'
                    """
                    gp_df = execute_query(gp_query)

                    # AR query
                    ar_query = f"""
                        SELECT ISNULL(AccountBalance, 0) as ar_balance
                        FROM dbo.Customer
                        WHERE ID = {customer_id}
                    """
                    ar_df = execute_query(ar_query)

                    # PD Checks from Payment table - get individual checks with details
                    pd_query = f"""
                        SELECT
                            Time as check_date,
                            Amount,
                            Comment
                        FROM dbo.Payment
                        WHERE CustomerID = {customer_id}
                            AND (
                                UPPER(Comment) LIKE '%PD%'
                                OR UPPER(Comment) LIKE '%POST DATE%'
                                OR UPPER(Comment) LIKE '%P D%'
                                OR UPPER(Comment) LIKE '%POSTDATE%'
                            )
                            AND Amount > 0
                        ORDER BY Time DESC
                    """
                    pd_checks_df = execute_query(pd_query)

                    total_sales = float(sales_df.iloc[0]['total_sales'] or 0)
                    gross_profit = float(gp_df.iloc[0]['gross_profit'] or 0)

                    # Calculate PD check totals
                    pd_checks_total = float(pd_checks_df['Amount'].sum()) if not pd_checks_df.empty else 0
                    pd_checks_count = len(pd_checks_df)

                    store_analytics.append({
                        'customer_name': member['customer_name'],
                        'company': member.get('customer_company', ''),
                        'total_sales': total_sales,
                        'gross_profit': gross_profit,
                        'gp_percentage': (gross_profit / total_sales * 100) if total_sales > 0 else 0,
                        'ar_balance': float(ar_df.iloc[0]['ar_balance'] or 0),
                        'pd_checks_total': pd_checks_total,
                        'pd_checks_count': pd_checks_count,
                        'pd_checks_details': pd_checks_df,  # Store the full details
                        'transaction_count': int(sales_df.iloc[0]['transaction_count'] or 0),
                        'last_purchase': sales_df.iloc[0]['last_purchase']
                    })
                except Exception as e:
                    st.error(f"Error loading analytics for {member['customer_name']}: {str(e)}")
                    continue

            # Sort by sales
            store_analytics.sort(key=lambda x: x['total_sales'], reverse=True)

            # Display each store with metrics
            for store in store_analytics:
                title = f"**{store['customer_name']}**"
                if store.get('company'):
                    title += f" ({store['company']})"
                title += f" - ${store['total_sales']:,.0f}"

                with st.expander(title, expanded=False):
                    col1, col2, col3, col4, col5 = st.columns(5)

                    with col1:
                        st.metric("Sales", f"${store['total_sales']:,.0f}")

                    with col2:
                        st.metric("GP", f"${store['gross_profit']:,.0f}",
                                 delta=f"{store['gp_percentage']:.1f}%")

                    with col3:
                        st.metric("AR", f"${store['ar_balance']:,.0f}")

                    with col4:
                        if store['pd_checks_total'] > 0:
                            st.metric("PD Checks", f"${store['pd_checks_total']:,.0f}",
                                     delta=f"{store['pd_checks_count']} checks")
                        else:
                            st.metric("PD Checks", "-")

                    with col5:
                        st.metric("Transactions", f"{store['transaction_count']:,}")

                    if store.get('last_purchase'):
                        st.caption(f"Last purchase: {store['last_purchase']}")

                    # Show individual PD check details if any
                    if store['pd_checks_count'] > 0 and not store['pd_checks_details'].empty:
                        st.markdown("---")
                        st.markdown("**📝 PD Checks Details:**")

                        pd_checks = store['pd_checks_details']
                        for idx, check in pd_checks.iterrows():
                            check_date = check['check_date'].strftime('%Y-%m-%d') if pd.notna(check['check_date']) else 'N/A'
                            amount = check['Amount']
                            comment = check['Comment'] if pd.notna(check['Comment']) else ''

                            st.text(f"• {check_date} - ${amount:,.2f} - {comment}")
        else:
            st.info("No store details available")

    st.markdown("---")
    st.caption(f"📅 Data for period: {start_date_str} to {end_date_str}")

# Footer
st.markdown("---")
st.caption(f"💡 Groups are automatically created using SOUNDEX phonetic matching. Analytics calculated fresh for last {days} days.")
