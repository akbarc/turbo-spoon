"""Excise Tax Analysis - Manage and calculate excise taxes."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from database.overlay_db import overlay_db
from utils.data_processing import calculate_excise_tax

st.set_page_config(page_title="Excise Tax Analysis", page_icon="💰", layout="wide")

st.title("💰 Excise Tax Analysis")
st.markdown("Configure and calculate excise taxes for products and categories.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 View Tax Rules", "➕ Add Tax Rule", "💵 Calculate Taxes"])

with tab1:
    st.subheader("Current Excise Tax Rules")

    try:
        tax_rules = overlay_db.get_excise_tax_rules(active_only=False)

        if tax_rules.empty:
            st.info("No tax rules defined yet. Use the 'Add Tax Rule' tab to create some.")
        else:
            # Display rules
            st.dataframe(
                tax_rules,
                use_container_width=True,
                column_config={
                    "tax_rate": st.column_config.NumberColumn("Tax Rate", format="%.4f"),
                    "active": st.column_config.CheckboxColumn("Active"),
                    "created_at": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm"),
                    "updated_at": st.column_config.DatetimeColumn("Updated", format="YYYY-MM-DD HH:mm")
                }
            )

            # Stats
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Rules", len(tax_rules))

            with col2:
                active_count = tax_rules[tax_rules['active'] == 1].shape[0]
                st.metric("Active Rules", active_count)

            with col3:
                product_rules = tax_rules[tax_rules['product_id'].notna()].shape[0]
                st.metric("Product-Specific Rules", product_rules)

            # Download
            csv = tax_rules.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Tax Rules",
                data=csv,
                file_name=f"tax_rules_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ Error loading tax rules: {str(e)}")

with tab2:
    st.subheader("Add New Tax Rule")

    st.markdown("""
    Create tax rules based on:
    - **Product ID**: Apply to a specific product
    - **Product Category**: Apply to all products in a category

    Leave fields empty if not applicable.
    """)

    col1, col2 = st.columns(2)

    with col1:
        tax_type = st.selectbox(
            "Tax Type:",
            options=["Excise", "VAT", "Sales", "Luxury", "Environmental", "Other"],
            help="Type of tax being applied"
        )

        tax_rate = st.number_input(
            "Tax Rate (decimal):",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.001,
            format="%.4f",
            help="E.g., 0.15 for 15% tax"
        )

    with col2:
        product_id = st.text_input(
            "Product ID (optional):",
            help="Leave empty to apply to category instead"
        )

        product_category = st.text_input(
            "Product Category (optional):",
            help="Leave empty to apply to specific product instead"
        )

    description = st.text_area("Description:", help="Notes about this tax rule")

    if st.button("💾 Save Tax Rule", type="primary"):
        if tax_rate <= 0:
            st.error("❌ Tax rate must be greater than 0!")
        elif not product_id and not product_category:
            st.error("❌ Either Product ID or Product Category must be specified!")
        elif product_id and product_category:
            st.error("❌ Specify either Product ID or Product Category, not both!")
        else:
            try:
                overlay_db.add_excise_tax_rule(
                    tax_rate=tax_rate,
                    tax_type=tax_type,
                    product_id=product_id if product_id else None,
                    product_category=product_category if product_category else None,
                    description=description if description else None
                )
                st.success(f"✅ Tax rule created successfully!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error creating tax rule: {str(e)}")

    st.markdown("---")

    # Bulk upload
    st.subheader("📤 Bulk Upload Tax Rules")

    st.markdown("""
    Upload a CSV file with columns: `product_id` or `product_category`, `tax_rate`,
    `tax_type`, `description` (optional)
    """)

    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            st.dataframe(df.head(10), use_container_width=True)

            if st.button("📥 Import Tax Rules", type="primary"):
                success_count = 0
                error_count = 0

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, row in df.iterrows():
                    try:
                        overlay_db.add_excise_tax_rule(
                            tax_rate=float(row['tax_rate']),
                            tax_type=str(row['tax_type']),
                            product_id=row.get('product_id') if pd.notna(row.get('product_id')) else None,
                            product_category=row.get('product_category') if pd.notna(row.get('product_category')) else None,
                            description=row.get('description') if pd.notna(row.get('description')) else None
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
    st.subheader("💵 Calculate Taxes on Data")

    st.markdown("""
    Load data from the Data Explorer and calculate excise taxes based on your rules.
    """)

    # Check if we have data in session
    if 'current_data' not in st.session_state or st.session_state.current_data.empty:
        st.info("📊 Load data from the Data Explorer first, then come back here to calculate taxes.")
    else:
        data = st.session_state.current_data

        st.success(f"✅ Using data from: {st.session_state.get('current_table', 'Unknown')}")

        st.markdown("#### Configure Tax Calculation")

        col1, col2, col3 = st.columns(3)

        with col1:
            product_id_col = st.selectbox(
                "Product ID Column:",
                options=data.columns.tolist(),
                help="Column containing product IDs"
            )

        with col2:
            amount_col = st.selectbox(
                "Amount Column:",
                options=data.select_dtypes(include=['number']).columns.tolist(),
                help="Column containing amounts/prices to tax"
            )

        with col3:
            category_col = st.selectbox(
                "Category Column (optional):",
                options=['None'] + data.columns.tolist(),
                help="Column containing product categories"
            )

        if st.button("🧮 Calculate Taxes", type="primary"):
            try:
                with st.spinner("Calculating taxes..."):
                    # Get tax rules
                    tax_rules = overlay_db.get_excise_tax_rules(active_only=True)

                    if tax_rules.empty:
                        st.warning("⚠️ No active tax rules found!")
                    else:
                        # Prepare data
                        calc_data = data.copy()

                        if category_col != 'None' and category_col in calc_data.columns:
                            calc_data['display_category'] = calc_data[category_col]

                        # Calculate taxes
                        result = calculate_excise_tax(
                            calc_data,
                            tax_rules,
                            product_id_col=product_id_col,
                            amount_col=amount_col
                        )

                        st.success(f"✅ Taxes calculated for {len(result)} rows!")

                        # Display results
                        st.dataframe(result, use_container_width=True, height=400)

                        # Summary stats
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Total Amount", f"${result[amount_col].sum():,.2f}")

                        with col2:
                            st.metric("Total Tax", f"${result['excise_tax'].sum():,.2f}")

                        with col3:
                            avg_rate = (result['excise_tax'].sum() / result[amount_col].sum() * 100) if result[amount_col].sum() > 0 else 0
                            st.metric("Avg Tax Rate", f"{avg_rate:.2f}%")

                        with col4:
                            taxed_items = (result['excise_tax'] > 0).sum()
                            st.metric("Items Taxed", taxed_items)

                        # Download
                        csv = result.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download with Taxes",
                            data=csv,
                            file_name=f"with_taxes_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )

            except Exception as e:
                st.error(f"❌ Error calculating taxes: {str(e)}")
                st.exception(e)
