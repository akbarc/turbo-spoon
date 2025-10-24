"""Customer Groups - Create and analyze customer segments."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from database.overlay_db import overlay_db

st.set_page_config(page_title="Customer Groups", page_icon="👥", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("👥 Customer Groups")
st.markdown("**Create and analyze custom customer segments**")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 View Groups", "➕ Create Group", "👤 Manage Members"])

with tab1:
    st.subheader("Customer Groups with Analytics")

    # Date range selector
    col1, col2 = st.columns([2, 1])
    with col1:
        date_range = st.selectbox(
            "Time Period:",
            ["Last 7 Days", "Last 30 Days", "Last 60 Days", "Last 90 Days", "This Month", "Last Month", "This Year"],
            index=1  # Default to Last 30 Days
        )

    # Calculate dates
    today = datetime.now()
    if date_range == "Last 7 Days":
        start_date = today - timedelta(days=7)
    elif date_range == "Last 30 Days":
        start_date = today - timedelta(days=30)
    elif date_range == "Last 60 Days":
        start_date = today - timedelta(days=60)
    elif date_range == "Last 90 Days":
        start_date = today - timedelta(days=90)
    elif date_range == "This Month":
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_range == "Last Month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        today = last_day_last_month.replace(hour=23, minute=59, second=59)
    else:  # This Year
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    end_date = today

    with col2:
        st.info(f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    try:
        # Get all groups from overlay database
        groups = overlay_db.execute_query("SELECT * FROM customer_groups ORDER BY group_name")

        if groups.empty:
            st.info("No customer groups defined yet. Use the 'Create Group' tab to add some.")
        else:
            st.markdown("---")

            # Calculate analytics for each group
            with st.spinner("Calculating analytics for all groups..."):
                group_analytics = []

                for _, group in groups.iterrows():
                    group_id = group['id']
                    group_name = group['group_name']

                    # Get members
                    members_query = "SELECT customer_id FROM customer_group_members WHERE group_id = ?"
                    members = overlay_db.execute_query(members_query, (group_id,))

                    if members.empty:
                        continue

                    customer_ids = members['customer_id'].tolist()
                    customer_ids_str = ','.join(map(str, customer_ids))

                    try:
                        # Get analytics
                        analytics_query = f"""
                        SELECT
                            COUNT(DISTINCT t.TransactionNumber) as TransactionCount,
                            COUNT(DISTINCT t.CustomerID) as ActiveCustomers,
                            SUM(t.Total) as TotalSales,
                            SUM(te.Quantity * (te.Price - te.Cost)) as GrossProfit,
                            SUM(c.AccountBalance) as TotalAR
                        FROM [Transaction] t WITH (NOLOCK)
                        LEFT JOIN TransactionEntry te WITH (NOLOCK) ON te.TransactionNumber = t.TransactionNumber
                        LEFT JOIN Customer c WITH (NOLOCK) ON c.ID = t.CustomerID
                        WHERE t.CustomerID IN ({customer_ids_str})
                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        """

                        result = db.execute_query(analytics_query)

                        if not result.empty:
                            total_sales = float(result.iloc[0]['TotalSales'] or 0)
                            gross_profit = float(result.iloc[0]['GrossProfit'] or 0)
                            gp_pct = (gross_profit / total_sales * 100) if total_sales > 0 else 0

                            group_analytics.append({
                                'Group': group_name,
                                'Members': len(customer_ids),
                                'Active': int(result.iloc[0]['ActiveCustomers'] or 0),
                                'Transactions': int(result.iloc[0]['TransactionCount'] or 0),
                                'Sales': total_sales,
                                'GrossProfit': gross_profit,
                                'GP%': gp_pct,
                                'AR Balance': float(result.iloc[0]['TotalAR'] or 0),
                                'group_id': group_id
                            })
                    except Exception as e:
                        st.error(f"Error calculating analytics for {group_name}: {str(e)}")
                        continue

                if group_analytics:
                    analytics_df = pd.DataFrame(group_analytics)

                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Groups", len(analytics_df))
                    with col2:
                        st.metric("Total Sales", f"${analytics_df['Sales'].sum():,.0f}")
                    with col3:
                        avg_gp = analytics_df['GP%'].mean()
                        st.metric("Avg GP%", f"{avg_gp:.1f}%")
                    with col4:
                        st.metric("Total AR", f"${analytics_df['AR Balance'].sum():,.0f}")

                    st.markdown("---")

                    # Display analytics table
                    display_df = analytics_df.drop(columns=['group_id'])
                    st.dataframe(
                        display_df.style.format({
                            'Members': '{:,}',
                            'Active': '{:,}',
                            'Transactions': '{:,}',
                            'Sales': '${:,.2f}',
                            'GrossProfit': '${:,.2f}',
                            'GP%': '{:.1f}%',
                            'AR Balance': '${:,.2f}'
                        }),
                        use_container_width=True,
                        height=400
                    )

                    # Export option
                    st.markdown("---")
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Group Analytics CSV",
                        data=csv,
                        file_name=f"customer_groups_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

                    # Show individual group details
                    st.markdown("---")
                    st.subheader("Group Details")

                    for _, row in analytics_df.iterrows():
                        with st.expander(f"📁 {row['Group']} - {row['Members']} customers, ${row['Sales']:,.0f} sales"):
                            # Get member details
                            members_query = """
                            SELECT customer_id FROM customer_group_members WHERE group_id = ?
                            """
                            members = overlay_db.execute_query(members_query, (row['group_id'],))

                            if not members.empty:
                                customer_ids_str = ','.join(map(str, members['customer_id'].tolist()))

                                # Get customer details with their sales
                                details_query = f"""
                                SELECT
                                    c.ID,
                                    c.FirstName + ' ' + c.LastName as CustomerName,
                                    c.Company,
                                    COUNT(DISTINCT t.TransactionNumber) as Transactions,
                                    SUM(t.Total) as Sales,
                                    c.AccountBalance as AR
                                FROM Customer c WITH (NOLOCK)
                                LEFT JOIN [Transaction] t WITH (NOLOCK) ON t.CustomerID = c.ID
                                    AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                    AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                WHERE c.ID IN ({customer_ids_str})
                                GROUP BY c.ID, c.FirstName, c.LastName, c.Company, c.AccountBalance
                                ORDER BY Sales DESC
                                """

                                details = db.execute_query(details_query)

                                if not details.empty:
                                    st.dataframe(
                                        details.style.format({
                                            'Transactions': '{:,}',
                                            'Sales': '${:,.2f}',
                                            'AR': '${:,.2f}'
                                        }),
                                        use_container_width=True
                                    )
                else:
                    st.info("No groups have members yet.")

    except Exception as e:
        st.error(f"❌ Error loading groups: {str(e)}")
        st.exception(e)

with tab2:
    st.subheader("Create New Customer Group")

    with st.form("create_group_form"):
        group_name = st.text_input(
            "Group Name:",
            help="Unique name for this customer group"
        )

        description = st.text_area(
            "Description:",
            help="Describe the purpose or criteria for this group"
        )

        submitted = st.form_submit_button("➕ Create Group", type="primary")

        if submitted:
            if not group_name:
                st.error("❌ Group name is required!")
            else:
                try:
                    # Insert into database
                    with overlay_db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO customer_groups (group_name, description) VALUES (?, ?)",
                            (group_name, description if description else None)
                        )
                        conn.commit()

                    st.success(f"✅ Group '{group_name}' created successfully!")
                    st.rerun()

                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        st.error(f"❌ Group name '{group_name}' already exists!")
                    else:
                        st.error(f"❌ Error creating group: {str(e)}")

with tab3:
    st.subheader("Manage Group Membership")

    try:
        groups = overlay_db.execute_query("SELECT * FROM customer_groups ORDER BY group_name")

        if groups.empty:
            st.info("Create a group first before adding members.")
        else:
            # Select group
            selected_group = st.selectbox(
                "Select Group:",
                options=groups['id'].tolist(),
                format_func=lambda x: groups[groups['id'] == x]['group_name'].iloc[0]
            )

            if selected_group:
                group_name = groups[groups['id'] == selected_group]['group_name'].iloc[0]

                st.markdown(f"**Adding members to:** {group_name}")

                # Single customer add
                col1, col2 = st.columns([3, 1])

                with col1:
                    customer_id = st.number_input("Customer ID:", min_value=1, step=1, value=1)

                with col2:
                    st.markdown("")  # Spacing
                    st.markdown("")  # Spacing
                    if st.button("➕ Add Customer", type="primary"):
                        try:
                            with overlay_db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO customer_group_members (customer_id, group_id) VALUES (?, ?)",
                                    (str(customer_id), selected_group)
                                )
                                conn.commit()
                            st.success(f"✅ Customer {customer_id} added to group!")
                            st.rerun()
                        except Exception as e:
                            if "UNIQUE constraint failed" in str(e):
                                st.warning(f"⚠️ Customer {customer_id} is already in this group")
                            else:
                                st.error(f"❌ Error: {str(e)}")

                st.markdown("---")

                # Bulk add
                st.subheader("📤 Bulk Add Customers")

                bulk_customers = st.text_area(
                    "Enter customer IDs (one per line):",
                    height=150,
                    help="Paste customer IDs, one per line"
                )

                if st.button("📥 Add All Customers", type="primary"):
                    if bulk_customers:
                        customer_ids = [cid.strip() for cid in bulk_customers.split('\n') if cid.strip()]

                        success_count = 0
                        error_count = 0

                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        with overlay_db.get_connection() as conn:
                            cursor = conn.cursor()

                            for idx, cid in enumerate(customer_ids):
                                try:
                                    cursor.execute(
                                        "INSERT INTO customer_group_members (customer_id, group_id) VALUES (?, ?)",
                                        (cid, selected_group)
                                    )
                                    success_count += 1
                                except:
                                    error_count += 1

                                progress_bar.progress((idx + 1) / len(customer_ids))
                                status_text.text(f"Processing {idx + 1}/{len(customer_ids)}...")

                            conn.commit()

                        st.success(f"✅ Added {success_count} customers ({error_count} duplicates skipped)")
                        st.rerun()

                st.markdown("---")

                # Show current members
                st.subheader("📋 Current Members")

                members_query = """
                SELECT cm.id, cm.customer_id, cm.added_at
                FROM customer_group_members cm
                WHERE cm.group_id = ?
                ORDER BY cm.added_at DESC
                """
                members = overlay_db.execute_query(members_query, (selected_group,))

                if not members.empty:
                    # Get customer details
                    customer_ids_str = ','.join(map(str, members['customer_id'].tolist()))

                    details_query = f"""
                    SELECT
                        c.ID,
                        c.FirstName + ' ' + c.LastName as Name,
                        c.Company,
                        c.AccountBalance as AR
                    FROM Customer c WITH (NOLOCK)
                    WHERE c.ID IN ({customer_ids_str})
                    """

                    details = db.execute_query(details_query)

                    if not details.empty:
                        st.dataframe(
                            details.style.format({
                                'AR': '${:,.2f}'
                            }),
                            use_container_width=True
                        )
                        st.caption(f"Total members: {len(details)}")

                        # Remove member functionality
                        st.markdown("---")
                        remove_id = st.number_input("Remove Customer ID:", min_value=1, step=1, value=1, key="remove_id")
                        if st.button("🗑️ Remove from Group", type="secondary"):
                            try:
                                with overlay_db.get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "DELETE FROM customer_group_members WHERE customer_id = ? AND group_id = ?",
                                        (str(remove_id), selected_group)
                                    )
                                    conn.commit()
                                st.success(f"✅ Customer {remove_id} removed from group!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                    else:
                        st.info("No customer details found.")
                else:
                    st.info("No members in this group yet.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
