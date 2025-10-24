"""Customer Groups - Create and analyze customer segments."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Correct imports - db is the instance, not individual functions
from database.sql_server import db
from database.overlay_db import overlay_db

st.set_page_config(page_title="Customer Groups", page_icon="👥", layout="wide")

st.title("👥 Customer Groups Management")
st.markdown("Create custom customer segments for targeted analysis.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 View Groups", "➕ Create Group", "👤 Manage Members"])

with tab1:
    st.subheader("Existing Customer Groups")

    try:
        groups = overlay_db.get_customer_groups()

        if groups.empty:
            st.info("No customer groups defined yet. Use the 'Create Group' tab to add some.")
        else:
            st.dataframe(
                groups,
                use_container_width=True,
                column_config={
                    "created_at": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm")
                }
            )

            # Show member counts
            st.markdown("---")
            st.subheader("Group Membership")

            for _, group in groups.iterrows():
                with st.expander(f"📁 {group['group_name']} (ID: {group['id']})"):
                    st.markdown(f"**Description:** {group['description'] or 'No description'}")

                    # Get members
                    members_query = """
                    SELECT customer_id, added_at
                    FROM customer_group_members
                    WHERE group_id = ?
                    ORDER BY added_at DESC
                    """
                    members = overlay_db.execute_query(members_query, (group['id'],))

                    if not members.empty:
                        st.dataframe(members, use_container_width=True)
                        st.caption(f"Total members: {len(members)}")
                    else:
                        st.info("No members in this group yet.")

    except Exception as e:
        st.error(f"❌ Error loading groups: {str(e)}")

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
                    overlay_db.create_customer_group(
                        group_name=group_name,
                        description=description if description else None
                    )
                    st.success(f"✅ Group '{group_name}' created successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error creating group: {str(e)}")

with tab3:
    st.subheader("Manage Group Membership")

    try:
        groups = overlay_db.get_customer_groups()

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
                    customer_id = st.text_input("Customer ID:")

                with col2:
                    st.markdown("")  # Spacing
                    st.markdown("")  # Spacing
                    if st.button("➕ Add Customer", type="primary"):
                        if customer_id:
                            try:
                                overlay_db.add_customer_to_group(customer_id, selected_group)
                                st.success(f"✅ Customer {customer_id} added to group!")
                                st.rerun()
                            except Exception as e:
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

                        for idx, cid in enumerate(customer_ids):
                            try:
                                overlay_db.add_customer_to_group(cid, selected_group)
                                success_count += 1
                            except Exception as e:
                                error_count += 1

                            progress_bar.progress((idx + 1) / len(customer_ids))
                            status_text.text(f"Processing: {idx + 1}/{len(customer_ids)}")

                        st.success(f"✅ Added {success_count} customers ({error_count} duplicates/errors)")
                        st.rerun()

                # Upload CSV
                st.markdown("---")
                st.subheader("📄 Upload CSV")

                uploaded_file = st.file_uploader(
                    "Upload CSV with 'customer_id' column",
                    type=['csv']
                )

                if uploaded_file is not None:
                    try:
                        df = pd.read_csv(uploaded_file)

                        if 'customer_id' not in df.columns:
                            st.error("❌ CSV must have a 'customer_id' column")
                        else:
                            st.dataframe(df.head(10), use_container_width=True)

                            if st.button("📥 Import Customers", type="primary"):
                                success_count = 0
                                error_count = 0

                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                for idx, row in df.iterrows():
                                    try:
                                        overlay_db.add_customer_to_group(
                                            str(row['customer_id']),
                                            selected_group
                                        )
                                        success_count += 1
                                    except Exception:
                                        error_count += 1

                                    progress_bar.progress((idx + 1) / len(df))
                                    status_text.text(f"Processing: {idx + 1}/{len(df)}")

                                st.success(f"✅ Import complete! {success_count} added, {error_count} skipped.")
                                st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error reading file: {str(e)}")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
