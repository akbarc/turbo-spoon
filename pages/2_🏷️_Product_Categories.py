"""Product Categories - Manage custom product categorizations."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from database.overlay_db import overlay_db

st.set_page_config(page_title="Product Categories", page_icon="🏷️", layout="wide")

st.title("🏷️ Product Categories Management")
st.markdown("Create and manage custom product categorizations without modifying the source database.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 View Categories", "➕ Add/Edit Categories", "📊 Category Analysis"])

with tab1:
    st.subheader("Current Product Categories")

    try:
        categories = overlay_db.get_product_categories()

        if categories.empty:
            st.info("No custom categories defined yet. Use the 'Add/Edit Categories' tab to create some.")
        else:
            # Filter options
            col1, col2, col3 = st.columns(3)

            with col1:
                unique_categories = categories['custom_category'].unique().tolist()
                filter_category = st.multiselect(
                    "Filter by category:",
                    options=unique_categories,
                    default=[]
                )

            with col2:
                search_product = st.text_input("Search product ID:", "")

            with col3:
                sort_by = st.selectbox(
                    "Sort by:",
                    options=['custom_category', 'product_id', 'updated_at'],
                    index=0
                )

            # Apply filters
            filtered = categories.copy()

            if filter_category:
                filtered = filtered[filtered['custom_category'].isin(filter_category)]

            if search_product:
                filtered = filtered[filtered['product_id'].str.contains(search_product, case=False, na=False)]

            filtered = filtered.sort_values(sort_by)

            # Display
            st.dataframe(
                filtered,
                use_container_width=True,
                height=400,
                column_config={
                    "updated_at": st.column_config.DatetimeColumn("Last Updated", format="YYYY-MM-DD HH:mm"),
                    "created_at": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm")
                }
            )

            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Categorized Products", len(filtered))
            with col2:
                st.metric("Unique Categories", filtered['custom_category'].nunique())
            with col3:
                if 'subcategory' in filtered.columns:
                    st.metric("Unique Subcategories", filtered['subcategory'].nunique())

            # Download
            csv = filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Categories",
                data=csv,
                file_name=f"product_categories_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ Error loading categories: {str(e)}")

with tab2:
    st.subheader("Add or Edit Product Category")

    col1, col2 = st.columns(2)

    with col1:
        product_id = st.text_input("Product ID:", help="Enter the product ID from your database")

        custom_category = st.text_input(
            "Custom Category:",
            help="The new category name for this product"
        )

        subcategory = st.text_input("Subcategory (optional):", help="Optional subcategory")

    with col2:
        original_category = st.text_input(
            "Original Category (optional):",
            help="The original category from your database (for reference)"
        )

        notes = st.text_area("Notes (optional):", help="Any notes about this categorization")

    if st.button("💾 Save Category", type="primary"):
        if not product_id or not custom_category:
            st.error("❌ Product ID and Custom Category are required!")
        else:
            try:
                overlay_db.add_product_category(
                    product_id=product_id,
                    custom_category=custom_category,
                    subcategory=subcategory if subcategory else None,
                    original_category=original_category if original_category else None,
                    notes=notes if notes else None
                )
                st.success(f"✅ Category saved for product {product_id}!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error saving category: {str(e)}")

    st.markdown("---")

    # Bulk upload
    st.subheader("📤 Bulk Upload Categories")

    st.markdown("""
    Upload a CSV file with columns: `product_id`, `custom_category`, `subcategory` (optional),
    `original_category` (optional), `notes` (optional)
    """)

    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            st.dataframe(df.head(10), use_container_width=True)

            if st.button("📥 Import Categories", type="primary"):
                success_count = 0
                error_count = 0

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, row in df.iterrows():
                    try:
                        overlay_db.add_product_category(
                            product_id=str(row['product_id']),
                            custom_category=str(row['custom_category']),
                            subcategory=row.get('subcategory'),
                            original_category=row.get('original_category'),
                            notes=row.get('notes')
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        st.warning(f"Row {idx}: {str(e)}")

                    progress_bar.progress((idx + 1) / len(df))
                    status_text.text(f"Processing: {idx + 1}/{len(df)}")

                st.success(f"✅ Import complete! {success_count} succeeded, {error_count} failed.")
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")

with tab3:
    st.subheader("📊 Category Analysis")

    try:
        categories = overlay_db.get_product_categories()

        if categories.empty:
            st.info("No categories to analyze yet.")
        else:
            # Category distribution
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Distribution by Category")
                category_counts = categories['custom_category'].value_counts()

                st.bar_chart(category_counts)

                st.dataframe(
                    pd.DataFrame({
                        'Category': category_counts.index,
                        'Count': category_counts.values,
                        'Percentage': (category_counts.values / len(categories) * 100).round(2)
                    }),
                    use_container_width=True
                )

            with col2:
                if 'subcategory' in categories.columns:
                    st.markdown("#### Distribution by Subcategory")
                    subcat_counts = categories['subcategory'].value_counts()

                    st.bar_chart(subcat_counts.head(10))

                    st.caption("Top 10 subcategories shown")

    except Exception as e:
        st.error(f"❌ Error in analysis: {str(e)}")
