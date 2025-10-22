"""Excise Tax Reporting - Detailed tax analysis and compliance reporting."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected, get_excise_breakdown

st.set_page_config(page_title="Excise Tax Reporting", page_icon="🚬", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("🚬 Excise Tax Reporting")
st.markdown("**Detailed excise tax analysis and compliance reporting**")

# Time filter section
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    time_filter = st.selectbox(
        "Time Period:",
        options=[
            "Today",
            "Yesterday",
            "Last 7 Days",
            "Last 30 Days",
            "This Week",
            "Last Week",
            "This Month",
            "Last Month",
            "This Quarter",
            "This Year",
            "Custom Range"
        ],
        index=7  # Default to Last Month
    )

# Calculate date range based on selection
today = datetime.now()
if time_filter == "Today":
    start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Yesterday":
    start_date = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date.replace(hour=23, minute=59, second=59)
elif time_filter == "Last 7 Days":
    start_date = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last 30 Days":
    start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "This Week":
    start_date = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last Week":
    start_date = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
elif time_filter == "This Month":
    start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "Last Month":
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    start_date = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = last_day_last_month.replace(hour=23, minute=59, second=59)
elif time_filter == "This Quarter":
    quarter = (today.month - 1) // 3
    start_date = today.replace(month=quarter*3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
elif time_filter == "This Year":
    start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = today
else:  # Custom Range
    with col2:
        custom_start = st.date_input("Start Date:", value=today - timedelta(days=30))
        start_date = datetime.combine(custom_start, datetime.min.time())
    with col3:
        custom_end = st.date_input("End Date:", value=today)
        end_date = datetime.combine(custom_end, datetime.max.time())

# Show selected date range
if time_filter != "Custom Range":
    with col2:
        st.info(f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

with col3:
    refresh = st.button("🔄 Refresh", type="primary", use_container_width=True)

st.markdown("---")

# Load data
with st.spinner("Loading excise tax data..."):
    try:
        # Calculate excise tax totals
        excise_paid, paid_error = calculate_excise_tax(
            db,
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S')
        )

        excise_collected, coll_error = calculate_excise_collected(
            db,
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S')
        )

        excise_paid = excise_paid or 0
        excise_collected = excise_collected or 0

        # Summary metrics
        st.subheader("📊 Excise Tax Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Excise Tax PAID",
                f"${excise_paid:,.2f}",
                help="Tax paid to state (subtract from gross profit)"
            )

        with col2:
            st.metric(
                "Excise Tax COLLECTED",
                f"${excise_collected:,.2f}",
                help="Tax collected from customers"
            )

        with col3:
            difference = excise_collected - excise_paid
            diff_pct = (difference / excise_collected * 100) if excise_collected > 0 else 0
            st.metric(
                "Difference",
                f"${difference:,.2f}",
                delta=f"{diff_pct:.1f}%",
                help="Collected - Paid (should be positive)"
            )

        with col4:
            recovery_rate = (excise_paid / excise_collected * 100) if excise_collected > 0 else 0
            st.metric(
                "Recovery Rate",
                f"{recovery_rate:.1f}%",
                help="Paid / Collected (what % of collected tax you pay to state)"
            )

        # Compliance check
        if difference < 0:
            st.error("⚠️ **COMPLIANCE WARNING**: Tax PAID exceeds tax COLLECTED. This should not happen - review your data!")
        elif difference > 0:
            st.success(f"✅ Tax reconciliation OK: Collecting ${difference:,.2f} more than paying to state")

        # Breakdown visualization
        st.markdown("---")
        st.subheader("💵 Tax Flow Visualization")

        fig = go.Figure(data=[
            go.Bar(
                name='Collected from Customers',
                x=['Excise Tax'],
                y=[excise_collected],
                marker_color='lightblue',
                text=[f'${excise_collected:,.0f}'],
                textposition='auto'
            ),
            go.Bar(
                name='Paid to State',
                x=['Excise Tax'],
                y=[excise_paid],
                marker_color='lightcoral',
                text=[f'${excise_paid:,.0f}'],
                textposition='auto'
            ),
            go.Bar(
                name='Difference (Margin)',
                x=['Excise Tax'],
                y=[difference],
                marker_color='lightgreen',
                text=[f'${difference:,.0f}'],
                textposition='auto'
            )
        ])

        fig.update_layout(
            barmode='group',
            title="Excise Tax Flow",
            yaxis_title="Amount ($)",
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

        # Breakdown by category
        st.markdown("---")
        st.subheader("📋 Breakdown by Tax Category")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### PAID to State")
            paid_breakdown, paid_error = get_excise_breakdown(
                db,
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'PAID'
            )

            if paid_breakdown is not None and not paid_breakdown.empty:
                # Add percentage
                paid_breakdown['Percentage'] = (paid_breakdown['TotalExcise'] / paid_breakdown['TotalExcise'].sum() * 100)

                st.dataframe(
                    paid_breakdown.style.format({
                        'TotalExcise': '${:,.2f}',
                        'EntryCount': '{:,}',
                        'Percentage': '{:.1f}%'
                    }).background_gradient(subset=['TotalExcise'], cmap='Reds'),
                    use_container_width=True,
                    height=350
                )

                # Pie chart
                fig = px.pie(
                    paid_breakdown,
                    values='TotalExcise',
                    names='Category',
                    title='PAID by Category'
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No PAID tax data available")

        with col2:
            st.markdown("### COLLECTED from Customers")
            coll_breakdown, coll_error = get_excise_breakdown(
                db,
                start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'COLL'
            )

            if coll_breakdown is not None and not coll_breakdown.empty:
                # Add percentage
                coll_breakdown['Percentage'] = (coll_breakdown['TotalExcise'] / coll_breakdown['TotalExcise'].sum() * 100)

                st.dataframe(
                    coll_breakdown.style.format({
                        'TotalExcise': '${:,.2f}',
                        'EntryCount': '{:,}',
                        'Percentage': '{:.1f}%'
                    }).background_gradient(subset=['TotalExcise'], cmap='Blues'),
                    use_container_width=True,
                    height=350
                )

                # Pie chart
                fig = px.pie(
                    coll_breakdown,
                    values='TotalExcise',
                    names='Category',
                    title='COLLECTED by Category'
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No COLLECTED tax data available")

        # Product-level excise details
        st.markdown("---")
        st.subheader("📦 Top Products by Excise Tax")

        product_excise_query = f"""
        SELECT TOP 20
            i.Description as Product,
            i.ItemLookupCode as SKU,
            pue.SubDescription3 as TaxCategory,
            COUNT(*) as Transactions,
            SUM(pue.Quantity) as TotalQuantity,
            SUM(pue.PriceC * pue.Quantity) as TotalExciseTax,
            AVG(pue.PriceC) as AvgTaxPerUnit,
            SUM(pue.Price * pue.Quantity) as TotalSales
        FROM PUExciseEntry pue WITH (NOLOCK)
        INNER JOIN Item i WITH (NOLOCK)
            ON pue.ItemID = i.ID
        WHERE pue.TransactionTime >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
          AND pue.TransactionTime <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
          AND pue.SubDescription3 LIKE '%PAID'
        GROUP BY i.Description, i.ItemLookupCode, pue.SubDescription3
        ORDER BY TotalExciseTax DESC
        """

        product_excise = db.execute_query(product_excise_query)

        if not product_excise.empty:
            product_excise['TaxPctOfSales'] = (product_excise['TotalExciseTax'] / product_excise['TotalSales'] * 100).fillna(0)

            st.dataframe(
                product_excise.style.format({
                    'Transactions': '{:,}',
                    'TotalQuantity': '{:,.0f}',
                    'TotalExciseTax': '${:,.2f}',
                    'AvgTaxPerUnit': '${:,.2f}',
                    'TotalSales': '${:,.2f}',
                    'TaxPctOfSales': '{:.1f}%'
                }),
                use_container_width=True,
                height=400
            )

        # Monthly trend
        st.markdown("---")
        st.subheader("📈 Excise Tax Trend (Last 12 Months)")

        # Calculate start date for 12 months ago
        twelve_months_ago = today - timedelta(days=365)

        trend_query = f"""
        SELECT
            YEAR(TransactionTime) as Year,
            MONTH(TransactionTime) as Month,
            SUM(CASE WHEN SubDescription3 LIKE '%PAID' THEN PriceC * Quantity ELSE 0 END) as TotalPaid,
            SUM(CASE WHEN SubDescription3 LIKE '%COLL' THEN PriceC * Quantity ELSE 0 END) as TotalCollected
        FROM PUExciseEntry WITH (NOLOCK)
        WHERE TransactionTime >= '{twelve_months_ago.strftime('%Y-%m-%d %H:%M:%S')}'
          AND TransactionTime <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY YEAR(TransactionTime), MONTH(TransactionTime)
        ORDER BY Year, Month
        """

        trend = db.execute_query(trend_query)

        if not trend.empty:
            # Create date column for better visualization
            trend['Date'] = pd.to_datetime(trend['Year'].astype(str) + '-' + trend['Month'].astype(str) + '-01')

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=trend['Date'],
                y=trend['TotalPaid'],
                mode='lines+markers',
                name='PAID to State',
                line=dict(color='red', width=2),
                fill='tozeroy'
            ))

            fig.add_trace(go.Scatter(
                x=trend['Date'],
                y=trend['TotalCollected'],
                mode='lines+markers',
                name='COLLECTED from Customers',
                line=dict(color='blue', width=2),
                fill='tozeroy'
            ))

            fig.update_layout(
                title="Monthly Excise Tax Trend",
                xaxis_title="Month",
                yaxis_title="Amount ($)",
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

        # Export section
        st.markdown("---")
        st.subheader("📥 Export for State Filing")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Export PAID Summary (CSV)", use_container_width=True):
                if paid_breakdown is not None and not paid_breakdown.empty:
                    csv = paid_breakdown.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"excise_tax_paid_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

        with col2:
            if st.button("📊 Export COLLECTED Summary (CSV)", use_container_width=True):
                if coll_breakdown is not None and not coll_breakdown.empty:
                    csv = coll_breakdown.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"excise_tax_collected_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

        # Tax category reference
        st.markdown("---")
        st.subheader("📚 Tax Category Reference")

        tax_reference = pd.DataFrame({
            'Code': ['LC23PAID/COLL', 'LC25PAID/COLL', 'LT10PAID/COLL', 'SL10PAID/COLL',
                     'VD07PAID/COLL', 'VO07PAID/COLL', 'VC05PAID/COLL'],
            'Description': ['Large Cigars', 'Little Cigars', 'Loose Tobacco', 'Smokeless Tobacco',
                           'Vape Device', 'Vapors Open', 'Vapors Closed'],
            'Approx Rate': ['~23%', '~25%', '~10%', '~10%', '~7%', '~7%', '~5%'],
            'Note': ['Based on product cost', 'Based on product cost', 'Based on product cost',
                    'Based on product cost', 'Based on product cost', 'Based on product cost',
                    'Based on product cost']
        })

        st.dataframe(tax_reference, use_container_width=True)

        st.info("""
        **Note on PAID vs. COLLECTED:**
        - **PAID** = Tax you pay to the state (subtract from gross profit)
        - **COLLECTED** = Tax collected from customers (built into sale price)
        - The difference represents your margin on the tax collection
        """)

    except Exception as e:
        st.error(f"❌ Error loading excise tax data: {str(e)}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
