"""Cigarette & Tobacco Ordering - Inventory management and ordering tool for tobacco products."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import io

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db

st.set_page_config(page_title="Cigarette Ordering", page_icon="🚬", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("🚬 Cigarette & Tobacco Ordering")
st.markdown("**Inventory management and ordering tool for excise-taxed tobacco products**")

# Calculate date ranges
today = datetime.now()
seven_days_ago = today - timedelta(days=7)
thirty_days_ago = today - timedelta(days=30)

# Get Murad Ali customer group IDs
st.markdown("---")
with st.spinner("Loading Murad Ali customer group..."):
    murad_query = """
    SELECT ID, FirstName, LastName, Company
    FROM Customer WITH (NOLOCK)
    WHERE (FirstName LIKE '%murad%' OR LastName LIKE '%murad%'
           OR FirstName LIKE '%ali%' OR LastName LIKE '%ali%'
           OR Company LIKE '%murad%' OR Company LIKE '%ali%')
    """
    murad_customers = db.execute_query(murad_query)

    if not murad_customers.empty:
        murad_ids = murad_customers['ID'].tolist()
        murad_ids_str = ','.join(map(str, murad_ids))
        st.info(f"📋 Found {len(murad_customers)} customers in Murad Ali group")
    else:
        murad_ids_str = "0"
        st.warning("⚠️ No customers found in Murad Ali group")

# Main data query
st.markdown("---")
with st.spinner("Loading cigarette inventory data..."):
    try:
        # Get all items that have excise tax entries (cigarettes/tobacco products)
        main_query = f"""
        WITH CigaretteItems AS (
            SELECT DISTINCT i.ID, i.ItemLookupCode, i.Description,
                   i.Price, i.Cost, i.Quantity as QuantityOnHand,
                   i.SupplierID, i.LastReceived,
                   s.SupplierName
            FROM Item i WITH (NOLOCK)
            INNER JOIN PUExciseEntry pue WITH (NOLOCK) ON pue.ItemID = i.ID
            LEFT JOIN Supplier s WITH (NOLOCK) ON s.ID = i.SupplierID
        ),
        Sales7Days AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as Units7Days,
                SUM(CASE WHEN t.CustomerID IN ({murad_ids_str}) THEN te.Quantity ELSE 0 END) as Units7DaysMurad
            FROM TransactionEntry te WITH (NOLOCK)
            INNER JOIN [Transaction] t WITH (NOLOCK) ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= '{seven_days_ago.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{today.strftime('%Y-%m-%d %H:%M:%S')}'
              AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID
        ),
        Sales30Days AS (
            SELECT
                te.ItemID,
                SUM(te.Quantity) as Units30Days,
                SUM(CASE WHEN t.CustomerID IN ({murad_ids_str}) THEN te.Quantity ELSE 0 END) as Units30DaysMurad
            FROM TransactionEntry te WITH (NOLOCK)
            INNER JOIN [Transaction] t WITH (NOLOCK) ON t.TransactionNumber = te.TransactionNumber
            WHERE t.Time >= '{thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S')}'
              AND t.Time <= '{today.strftime('%Y-%m-%d %H:%M:%S')}'
              AND te.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY te.ItemID
        ),
        LastCost AS (
            SELECT
                re.ItemID,
                MAX(r.ReceiptNumber) as LastReceiptNumber
            FROM ReceiptEntry re WITH (NOLOCK)
            INNER JOIN Receipt r WITH (NOLOCK) ON r.ID = re.ReceiptID
            WHERE re.ItemID IN (SELECT ID FROM CigaretteItems)
            GROUP BY re.ItemID
        ),
        LastCostDetails AS (
            SELECT
                lc.ItemID,
                re.Cost as LastCost
            FROM LastCost lc
            INNER JOIN Receipt r WITH (NOLOCK) ON r.ReceiptNumber = lc.LastReceiptNumber
            INNER JOIN ReceiptEntry re WITH (NOLOCK) ON re.ReceiptID = r.ID AND re.ItemID = lc.ItemID
        )
        SELECT
            ci.ID,
            ci.ItemLookupCode as SKU,
            ci.Description as Product,
            ci.Price,
            ci.Cost,
            ci.QuantityOnHand,
            ISNULL(s7.Units7Days, 0) as Units7Days,
            ISNULL(s7.Units7DaysMurad, 0) as Units7DaysMurad,
            ISNULL(s30.Units30Days, 0) as Units30Days,
            ISNULL(s30.Units30DaysMurad, 0) as Units30DaysMurad,
            ci.SupplierName as LastSupplier,
            ci.LastReceived,
            ISNULL(lcd.LastCost, ci.Cost) as LastCost
        FROM CigaretteItems ci
        LEFT JOIN Sales7Days s7 ON s7.ItemID = ci.ID
        LEFT JOIN Sales30Days s30 ON s30.ItemID = ci.ID
        LEFT JOIN LastCostDetails lcd ON lcd.ItemID = ci.ID
        ORDER BY ci.Description
        """

        df = db.execute_query(main_query)

        if df.empty:
            st.warning("⚠️ No cigarette/tobacco products found")
            st.stop()

        # Calculate projected quantity needed (7 day sales - on hand + 15% buffer)
        df['ProjectedQtyNeeded'] = ((df['Units7Days'] - df['QuantityOnHand']) * 1.15).clip(lower=0)

        # Round to nearest whole number
        df['ProjectedQtyNeeded'] = df['ProjectedQtyNeeded'].round(0).astype(int)

        # Format dates
        df['LastReceived'] = pd.to_datetime(df['LastReceived']).dt.strftime('%Y-%m-%d')
        df['LastReceived'] = df['LastReceived'].fillna('Never')
        df['LastSupplier'] = df['LastSupplier'].fillna('Unknown')

        st.success(f"✅ Loaded {len(df)} cigarette/tobacco products")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Products",
                f"{len(df):,}",
                help="Total number of cigarette/tobacco products"
            )

        with col2:
            total_value = (df['QuantityOnHand'] * df['Cost']).sum()
            st.metric(
                "Inventory Value",
                f"${total_value:,.2f}",
                help="Total value of on-hand inventory at cost"
            )

        with col3:
            total_7day_sales = df['Units7Days'].sum()
            st.metric(
                "7-Day Sales",
                f"{total_7day_sales:,.0f} units",
                help="Total units sold in last 7 days"
            )

        with col4:
            total_projected = df['ProjectedQtyNeeded'].sum()
            st.metric(
                "Total Projected Need",
                f"{total_projected:,} units",
                help="Total units needed to restock (7-day sales - on hand + 15%)"
            )

        st.markdown("---")
        st.subheader("📦 Product Inventory & Ordering")

        # Initialize order quantities in session state if not exists
        if 'order_quantities' not in st.session_state:
            st.session_state.order_quantities = {}

        # Create a container for the data table
        # Build display dataframe
        display_df = df.copy()

        # Format numeric columns for display
        display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:,.2f}")
        display_df['Cost'] = display_df['Cost'].apply(lambda x: f"${x:,.2f}")
        display_df['LastCost'] = display_df['LastCost'].apply(lambda x: f"${x:,.2f}")
        display_df['QuantityOnHand'] = display_df['QuantityOnHand'].apply(lambda x: f"{x:,.0f}")
        display_df['Units7Days'] = display_df['Units7Days'].apply(lambda x: f"{x:,.0f}")
        display_df['Units7DaysMurad'] = display_df['Units7DaysMurad'].apply(lambda x: f"{x:,.0f}")
        display_df['Units30Days'] = display_df['Units30Days'].apply(lambda x: f"{x:,.0f}")
        display_df['Units30DaysMurad'] = display_df['Units30DaysMurad'].apply(lambda x: f"{x:,.0f}")
        display_df['ProjectedQtyNeeded'] = display_df['ProjectedQtyNeeded'].apply(lambda x: f"{x:,}")

        # Reorder columns for display
        display_cols = [
            'Product', 'SKU', 'Price', 'Cost', 'QuantityOnHand',
            'Units7Days', 'Units7DaysMurad', 'Units30Days', 'Units30DaysMurad',
            'ProjectedQtyNeeded', 'LastSupplier', 'LastReceived', 'LastCost'
        ]

        st.dataframe(
            display_df[display_cols],
            use_container_width=True,
            height=600
        )

        st.markdown("---")
        st.subheader("📝 Order Entry")
        st.markdown("Enter quantities to order for each product:")

        # Create order entry form
        order_data = []

        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])

            with col1:
                st.text(row['Product'][:50])  # Truncate long names

            with col2:
                st.text(f"Proj: {row['ProjectedQtyNeeded']:,.0f}")

            with col3:
                order_qty = st.number_input(
                    f"Order Qty",
                    min_value=0,
                    value=int(st.session_state.order_quantities.get(row['ID'], 0)),
                    step=1,
                    key=f"order_{row['ID']}",
                    label_visibility="collapsed"
                )
                st.session_state.order_quantities[row['ID']] = order_qty

            with col4:
                st.text(f"${row['Cost']:.2f}")

            with col5:
                total = order_qty * row['Cost']
                st.text(f"${total:.2f}")

            with col6:
                st.text(f"{row['LastSupplier'][:15]}")  # Truncate supplier name

            if order_qty > 0:
                order_data.append({
                    'Product': row['Product'],
                    'SKU': row['SKU'],
                    'OrderQty': order_qty,
                    'UnitCost': row['Cost'],
                    'TotalCost': total,
                    'LastSupplier': row['LastSupplier'],
                    'LastReceived': row['LastReceived'],
                    'LastCost': row['LastCost']
                })

        # Order summary
        if order_data:
            st.markdown("---")
            st.subheader("📊 Order Summary")

            order_df = pd.DataFrame(order_data)
            total_order_cost = order_df['TotalCost'].sum()
            total_order_units = order_df['OrderQty'].sum()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Order Units", f"{total_order_units:,}")

            with col2:
                st.metric("Total Order Cost", f"${total_order_cost:,.2f}")

            with col3:
                st.metric("Products to Order", f"{len(order_df)}")

            st.dataframe(
                order_df.style.format({
                    'OrderQty': '{:,.0f}',
                    'UnitCost': '${:,.2f}',
                    'TotalCost': '${:,.2f}',
                    'LastCost': '${:,.2f}'
                }),
                use_container_width=True
            )

            # Export order
            csv_buffer = io.StringIO()
            order_df.to_csv(csv_buffer, index=False)

            st.download_button(
                label="📥 Download Order CSV",
                data=csv_buffer.getvalue(),
                file_name=f"cigarette_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Export full inventory
        st.markdown("---")
        st.subheader("📥 Export Full Inventory")

        # Prepare export dataframe with numeric values (not formatted strings)
        export_df = df[[
            'Product', 'SKU', 'Price', 'Cost', 'QuantityOnHand',
            'Units7Days', 'Units7DaysMurad', 'Units30Days', 'Units30DaysMurad',
            'ProjectedQtyNeeded', 'LastSupplier', 'LastReceived', 'LastCost'
        ]].copy()

        csv_buffer = io.StringIO()
        export_df.to_csv(csv_buffer, index=False)

        st.download_button(
            label="📥 Download Full Inventory CSV",
            data=csv_buffer.getvalue(),
            file_name=f"cigarette_inventory_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Clear order button
        if st.button("🗑️ Clear All Order Quantities", type="secondary"):
            st.session_state.order_quantities = {}
            st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading cigarette data: {str(e)}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption(f"""
**Notes:**
- Projected Qty = (7-day sales - quantity on hand) × 1.15 (15% buffer)
- Murad Ali group identified by customer name matching 'Murad' or 'Ali'
- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
