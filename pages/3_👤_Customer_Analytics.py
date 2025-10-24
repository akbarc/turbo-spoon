"""Customer Analytics - Deep dive into individual customer behavior and store preferences."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db
from database.overlay_db import overlay_db
from utils.excise_tax import calculate_excise_collected

st.set_page_config(page_title="Customer Analytics", page_icon="👤", layout="wide")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

st.title("👤 Customer Analytics")
st.markdown("**Comprehensive customer behavior analysis with per-store deep dive**")

# Main tabs
tab1, tab2, tab3 = st.tabs(["🔍 Customer Lookup", "📊 Customer Segments", "📈 Bulk Comparison"])

# ============================================================================
# TAB 1: CUSTOMER LOOKUP
# ============================================================================
with tab1:
    st.markdown("---")

    # Section A0: Customer Overview/List
    st.subheader("📊 All Customers Overview")

    show_all_customers = st.checkbox("Show all customers with stats", value=False, key="show_all_customers")

    if show_all_customers:
        with st.spinner("Loading all customers..."):
            try:
                # Get all customers with basic stats
                all_customers_query = """
                SELECT
                    c.ID as CustomerID,
                    c.FirstName + ' ' + c.LastName as CustomerName,
                    c.Company,
                    c.PhoneNumber,
                    c.EmailAddress,
                    c.City,
                    c.State,
                    c.AccountOpened,
                    c.LastVisit,
                    c.TotalVisits,
                    c.TotalSales,
                    c.AccountBalance,
                    c.CreditLimit,
                    CASE WHEN c.TaxExempt = 1 THEN 'Yes' ELSE 'No' END as TaxExempt
                FROM Customer c WITH (NOLOCK)
                WHERE c.TotalVisits > 0
                ORDER BY c.TotalSales DESC
                """

                all_customers = db.execute_query(all_customers_query)

                if not all_customers.empty:
                    st.success(f"✅ Loaded {len(all_customers)} customers")

                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Customers", f"{len(all_customers):,}")

                    with col2:
                        total_sales = all_customers['TotalSales'].sum()
                        st.metric("Total Lifetime Sales", f"${total_sales:,.2f}")

                    with col3:
                        avg_sales = all_customers['TotalSales'].mean()
                        st.metric("Avg Customer Value", f"${avg_sales:,.2f}")

                    with col4:
                        total_ar = all_customers['AccountBalance'].sum()
                        st.metric("Total A/R Balance", f"${total_ar:,.2f}")

                    # Display table
                    st.dataframe(
                        all_customers.style.format({
                            'TotalVisits': '{:,}',
                            'TotalSales': '${:,.2f}',
                            'AccountBalance': '${:,.2f}',
                            'CreditLimit': '${:,.2f}',
                            'AccountOpened': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'N/A',
                            'LastVisit': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'Never'
                        }).background_gradient(subset=['TotalSales'], cmap='Blues'),
                        use_container_width=True,
                        height=500
                    )

                    # Export button
                    csv = all_customers.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download All Customers CSV",
                        data=csv,
                        file_name=f"all_customers_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ No customers found")

            except Exception as e:
                st.error(f"❌ Error loading customers: {str(e)}")

    st.markdown("---")

    # Section A: Customer Search
    st.subheader("🔍 Customer Search")

    col1, col2 = st.columns([1, 3])

    with col1:
        search_type = st.selectbox(
            "Search By:",
            options=["Customer ID", "Name", "Phone", "Email", "Company"],
            key="search_type"
        )

    with col2:
        search_value = st.text_input(
            "Search Value:",
            placeholder=f"Enter {search_type.lower()}...",
            key="search_value"
        )

    # Search button
    if st.button("🔍 Search", type="primary") or search_value:
        if not search_value:
            st.warning("⚠️ Please enter a search value")
        else:
            try:
                # Build search query based on type
                if search_type == "Customer ID":
                    search_query = f"""
                    SELECT TOP 20
                        ID, FirstName, LastName, Company, PhoneNumber, EmailAddress,
                        Address, City, State, Zip, AccountNumber,
                        AccountOpened, LastVisit, TotalVisits, TotalSales,
                        AccountBalance, CreditLimit, TaxExempt, StoreID
                    FROM Customer
                    WHERE ID = '{search_value}'
                    """
                elif search_type == "Name":
                    search_query = f"""
                    SELECT TOP 20
                        ID, FirstName, LastName, Company, PhoneNumber, EmailAddress,
                        Address, City, State, Zip, AccountNumber,
                        AccountOpened, LastVisit, TotalVisits, TotalSales,
                        AccountBalance, CreditLimit, TaxExempt, StoreID
                    FROM Customer
                    WHERE FirstName LIKE '%{search_value}%' OR LastName LIKE '%{search_value}%'
                    ORDER BY LastVisit DESC
                    """
                elif search_type == "Phone":
                    search_query = f"""
                    SELECT TOP 20
                        ID, FirstName, LastName, Company, PhoneNumber, EmailAddress,
                        Address, City, State, Zip, AccountNumber,
                        AccountOpened, LastVisit, TotalVisits, TotalSales,
                        AccountBalance, CreditLimit, TaxExempt, StoreID
                    FROM Customer
                    WHERE PhoneNumber LIKE '%{search_value}%'
                    ORDER BY LastVisit DESC
                    """
                elif search_type == "Email":
                    search_query = f"""
                    SELECT TOP 20
                        ID, FirstName, LastName, Company, PhoneNumber, EmailAddress,
                        Address, City, State, Zip, AccountNumber,
                        AccountOpened, LastVisit, TotalVisits, TotalSales,
                        AccountBalance, CreditLimit, TaxExempt, StoreID
                    FROM Customer
                    WHERE EmailAddress LIKE '%{search_value}%'
                    ORDER BY LastVisit DESC
                    """
                else:  # Company
                    search_query = f"""
                    SELECT TOP 20
                        ID, FirstName, LastName, Company, PhoneNumber, EmailAddress,
                        Address, City, State, Zip, AccountNumber,
                        AccountOpened, LastVisit, TotalVisits, TotalSales,
                        AccountBalance, CreditLimit, TaxExempt, StoreID
                    FROM Customer
                    WHERE Company LIKE '%{search_value}%'
                    ORDER BY LastVisit DESC
                    """

                search_results = db.execute_query(search_query)

                if search_results.empty:
                    st.warning(f"⚠️ No customers found matching '{search_value}'")
                else:
                    st.success(f"✅ Found {len(search_results)} customer(s)")

                    # Display results
                    if len(search_results) == 1:
                        st.session_state.selected_customer_id = search_results['ID'].iloc[0]
                    else:
                        # Multiple results - let user select
                        st.markdown("**Select a customer:**")

                        # Format display
                        display_df = search_results.copy()
                        display_df['Display'] = (
                            display_df['FirstName'].fillna('') + ' ' +
                            display_df['LastName'].fillna('') + ' (' +
                            display_df['Company'].fillna('No Company') + ') - ID: ' +
                            display_df['ID'].astype(str)
                        )

                        selected = st.selectbox(
                            "Choose customer:",
                            options=display_df['ID'].tolist(),
                            format_func=lambda x: display_df[display_df['ID'] == x]['Display'].iloc[0]
                        )

                        st.session_state.selected_customer_id = selected

            except Exception as e:
                st.error(f"❌ Search error: {str(e)}")

    # If customer is selected, show full analysis
    if st.session_state.get('selected_customer_id'):
        customer_id = st.session_state.selected_customer_id

        st.markdown("---")

        try:
            # Load customer profile
            profile_query = f"""
            SELECT
                ID, FirstName, LastName, Company, PhoneNumber, EmailAddress, FaxNumber,
                Address, Address2, City, State, Zip, Country,
                AccountNumber, AccountOpened, LastVisit, TotalVisits, TotalSales,
                AccountBalance, CreditLimit, TaxExempt, TaxNumber, CurrentDiscount,
                PriceLevel, TotalSavings, StoreID
            FROM Customer
            WHERE ID = {customer_id}
            """

            profile = db.execute_query(profile_query)

            if profile.empty:
                st.error("❌ Customer not found")
                st.stop()

            customer = profile.iloc[0]

            # Section B: Customer Profile Card
            st.subheader(f"👤 {customer['FirstName']} {customer['LastName']}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"""
                **Company:** {customer['Company'] or 'N/A'}
                **Account #:** {customer['AccountNumber']}
                **Phone:** {customer['PhoneNumber'] or 'N/A'}
                **Email:** {customer['EmailAddress'] or 'N/A'}
                **Fax:** {customer['FaxNumber'] or 'N/A'}

                **Address:**
                {customer['Address'] or 'N/A'}
                {customer['Address2'] or ''}
                {customer['City']}, {customer['State']} {customer['Zip']}
                {customer['Country'] or 'USA'}
                """)

            with col2:
                st.markdown(f"""
                **Account Opened:** {customer['AccountOpened'].strftime('%Y-%m-%d') if pd.notna(customer['AccountOpened']) else 'N/A'}
                **Last Visit:** {customer['LastVisit'].strftime('%Y-%m-%d') if pd.notna(customer['LastVisit']) else 'Never'}
                **Total Visits (Lifetime):** {customer['TotalVisits']:,}
                **Total Sales (Lifetime):** ${customer['TotalSales']:,.2f}
                **Account Balance:** ${customer['AccountBalance']:,.2f}
                **Credit Limit:** ${customer['CreditLimit']:,.2f}
                **Tax Exempt:** {'Yes' if customer['TaxExempt'] else 'No'}
                **Tax Number:** {customer['TaxNumber'] or 'N/A'}
                **Price Level:** {customer['PriceLevel']}
                **Total Savings (Lifetime):** ${customer['TotalSavings']:,.2f}
                """)

            # Section C: Time Period Filter
            st.markdown("---")
            st.subheader("📅 Analysis Period")

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                time_filter = st.selectbox(
                    "Time Period:",
                    options=[
                        "Last 7 Days",
                        "Last 30 Days",
                        "Last 90 Days",
                        "This Month",
                        "Last Month",
                        "This Quarter",
                        "This Year",
                        "Last Year",
                        "All Time",
                        "Custom Range"
                    ],
                    index=1,  # Default to Last 30 Days
                    key="customer_time_filter"
                )

            # Calculate date range
            today = datetime.now()
            if time_filter == "Last 7 Days":
                start_date = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = today
            elif time_filter == "Last 30 Days":
                start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = today
            elif time_filter == "Last 90 Days":
                start_date = (today - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = today
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
            elif time_filter == "Last Year":
                start_date = today.replace(year=today.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = today.replace(year=today.year-1, month=12, day=31, hour=23, minute=59, second=59)
            elif time_filter == "All Time":
                start_date = datetime(2000, 1, 1)
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
                refresh = st.button("🔄 Refresh", type="primary", use_container_width=True, key="customer_refresh")

            # Section D: Overall Customer Metrics for Period
            st.markdown("---")

            with st.spinner("Analyzing customer activity..."):
                # Overall metrics query
                overall_query = f"""
                SELECT
                    COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                    SUM(t.Total) as TotalRevenue,
                    AVG(t.Total) as AvgTransactionSize,
                    SUM(te.Quantity) as ItemsPurchased,
                    SUM((te.Price - te.Cost) * te.Quantity) as GrossProfitBeforeExcise
                FROM [Transaction] t WITH (NOLOCK)
                LEFT JOIN TransactionEntry te WITH (NOLOCK)
                    ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                WHERE t.CustomerID = {customer_id}
                  AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                """

                overall = db.execute_query(overall_query)

                if not overall.empty and overall['TotalTransactions'].iloc[0] and overall['TotalTransactions'].iloc[0] > 0:
                    # Calculate excise tax for this customer (simplified - no complex joins)
                    # Using a simpler approach to avoid timeouts
                    try:
                        excise_query = f"""
                        SELECT
                            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                                THEN pue.PriceC * pue.Quantity
                                ELSE 0 END), 0) as ExciseCollected
                        FROM PUExciseEntry pue WITH (NOLOCK)
                        WHERE pue.TransactionNumber IN (
                            SELECT TransactionNumber
                            FROM [Transaction] WITH (NOLOCK)
                            WHERE CustomerID = {customer_id}
                              AND Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                              AND Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        )
                        """

                        excise_result = db.execute_query(excise_query)
                        excise_collected = excise_result['ExciseCollected'].iloc[0] if not excise_result.empty else 0
                    except:
                        # If excise calculation fails/times out, skip it
                        excise_collected = 0
                        st.warning("⚠️ Excise tax calculation skipped (query timeout). Profit shown is before excise tax.")

                    total_revenue = overall['TotalRevenue'].iloc[0] or 0
                    total_transactions = overall['TotalTransactions'].iloc[0] or 0
                    avg_transaction = overall['AvgTransactionSize'].iloc[0] or 0
                    items_purchased = overall['ItemsPurchased'].iloc[0] or 0
                    gross_profit_before = overall['GrossProfitBeforeExcise'].iloc[0] or 0
                    gross_profit = gross_profit_before - excise_collected

                    st.subheader(f"📊 Customer Activity: {time_filter}")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric(
                            "Total Spent",
                            f"${total_revenue:,.2f}",
                            help="Total revenue from this customer in selected period"
                        )

                    with col2:
                        st.metric(
                            "Total Transactions",
                            f"{total_transactions:,}",
                            help="Number of visits/purchases in selected period"
                        )

                    with col3:
                        st.metric(
                            "Avg Transaction Size",
                            f"${avg_transaction:,.2f}",
                            help="Average basket size per visit"
                        )

                    with col4:
                        st.metric(
                            "Items Purchased",
                            f"{items_purchased:,.0f}",
                            help="Total quantity of items bought"
                        )

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
                        st.metric(
                            "Gross Profit",
                            f"${gross_profit:,.2f}",
                            delta=f"{margin:.1f}% margin",
                            help="Profit after COGS and excise tax"
                        )

                    with col2:
                        st.metric(
                            "Excise Tax Collected",
                            f"${excise_collected:,.2f}",
                            help="Excise tax collected from customer"
                        )

                    with col3:
                        avg_items = items_purchased / total_transactions if total_transactions > 0 else 0
                        st.metric(
                            "Avg Items per Visit",
                            f"{avg_items:.1f}",
                            help="Average quantity per transaction"
                        )

                    with col4:
                        # Calculate days active
                        days_query = f"""
                        SELECT
                            DATEDIFF(day, MIN(Time), MAX(Time)) as DaysSpan,
                            COUNT(DISTINCT CAST(Time as DATE)) as DaysActive
                        FROM [Transaction]
                        WHERE CustomerID = {customer_id}
                          AND Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        """
                        days_result = db.execute_query(days_query)
                        days_active = days_result['DaysActive'].iloc[0] if not days_result.empty else 0

                        st.metric(
                            "Days Active",
                            f"{days_active:,}",
                            help="Number of unique days with purchases"
                        )

                    # Section E: PER-STORE BREAKDOWN ⭐ PRIMARY FEATURE
                    st.markdown("---")
                    st.subheader("🏪 Per-Store Breakdown")

                    store_query = f"""
                    SELECT
                        t.StoreID,
                        COUNT(DISTINCT t.TransactionNumber) as TotalVisits,
                        SUM(t.Total) as TotalRevenue,
                        AVG(t.Total) as AvgBasketSize,
                        SUM(te.Quantity) as ItemsPurchased,
                        SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
                        MAX(t.Time) as LastVisitDate,
                        MIN(t.Time) as FirstVisitDate,
                        COUNT(DISTINCT CAST(t.Time as DATE)) as DaysActive
                    FROM [Transaction] t WITH (NOLOCK)
                    INNER JOIN TransactionEntry te WITH (NOLOCK)
                        ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                    WHERE t.CustomerID = {customer_id}
                      AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                      AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    GROUP BY t.StoreID
                    ORDER BY TotalRevenue DESC
                    """

                    store_breakdown = db.execute_query(store_query)

                    if not store_breakdown.empty:
                        st.dataframe(
                            store_breakdown.style.format({
                                'TotalVisits': '{:,}',
                                'TotalRevenue': '${:,.2f}',
                                'AvgBasketSize': '${:,.2f}',
                                'ItemsPurchased': '{:,.0f}',
                                'GrossProfit': '${:,.2f}',
                                'LastVisitDate': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'N/A',
                                'FirstVisitDate': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'N/A',
                                'DaysActive': '{:,}'
                            }).background_gradient(subset=['TotalRevenue'], cmap='Blues'),
                            use_container_width=True,
                            height=min(len(store_breakdown) * 35 + 38, 400)
                        )

                        # Expandable details for each store
                        st.markdown("**📍 Store Details** (click to expand)")

                        for idx, store_row in store_breakdown.iterrows():
                            store_id = store_row['StoreID']

                            with st.expander(f"Store {store_id} - ${store_row['TotalRevenue']:,.2f} revenue"):
                                # Top categories for this store
                                st.markdown("**Top 5 Categories at This Store:**")

                                cat_query = f"""
                                SELECT TOP 5
                                    c.Name as Category,
                                    SUM(te.Quantity) as Quantity,
                                    SUM(te.Price * te.Quantity) as TotalSpent,
                                    COUNT(DISTINCT t.TransactionNumber) as Transactions
                                FROM [Transaction] t WITH (NOLOCK)
                                INNER JOIN TransactionEntry te WITH (NOLOCK)
                                    ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                                INNER JOIN Item i WITH (NOLOCK)
                                    ON te.ItemID = i.ID
                                INNER JOIN Category c WITH (NOLOCK)
                                    ON i.CategoryID = c.ID
                                WHERE t.CustomerID = {customer_id}
                                  AND t.StoreID = {store_id}
                                  AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                GROUP BY c.Name
                                ORDER BY TotalSpent DESC
                                """

                                top_cats = db.execute_query(cat_query)

                                if not top_cats.empty:
                                    st.dataframe(
                                        top_cats.style.format({
                                            'Quantity': '{:,.0f}',
                                            'TotalSpent': '${:,.2f}',
                                            'Transactions': '{:,}'
                                        }),
                                        use_container_width=True,
                                        hide_index=True
                                    )

                                st.markdown("**Top 10 Products at This Store:**")

                                prod_query = f"""
                                SELECT TOP 10
                                    i.Description as Product,
                                    i.ItemLookupCode as SKU,
                                    SUM(te.Quantity) as Quantity,
                                    SUM(te.Price * te.Quantity) as TotalSpent,
                                    AVG(te.Price) as AvgPrice,
                                    COUNT(DISTINCT t.TransactionNumber) as TimesPurchased
                                FROM [Transaction] t WITH (NOLOCK)
                                INNER JOIN TransactionEntry te WITH (NOLOCK)
                                    ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                                INNER JOIN Item i WITH (NOLOCK)
                                    ON te.ItemID = i.ID
                                WHERE t.CustomerID = {customer_id}
                                  AND t.StoreID = {store_id}
                                  AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                GROUP BY i.Description, i.ItemLookupCode
                                ORDER BY TotalSpent DESC
                                """

                                top_prods = db.execute_query(prod_query)

                                if not top_prods.empty:
                                    st.dataframe(
                                        top_prods.style.format({
                                            'Quantity': '{:,.0f}',
                                            'TotalSpent': '${:,.2f}',
                                            'AvgPrice': '${:,.2f}',
                                            'TimesPurchased': '{:,}'
                                        }),
                                        use_container_width=True,
                                        hide_index=True,
                                        height=300
                                    )

                                # Visit patterns for this store
                                st.markdown("**Visit Pattern at This Store:**")

                                pattern_query = f"""
                                SELECT
                                    DATENAME(WEEKDAY, t.Time) as DayOfWeek,
                                    COUNT(DISTINCT t.TransactionNumber) as Visits,
                                    SUM(t.Total) as TotalSpent
                                FROM [Transaction] t WITH (NOLOCK)
                                WHERE t.CustomerID = {customer_id}
                                  AND t.StoreID = {store_id}
                                  AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                  AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                GROUP BY DATENAME(WEEKDAY, t.Time), DATEPART(WEEKDAY, t.Time)
                                ORDER BY DATEPART(WEEKDAY, t.Time)
                                """

                                day_pattern = db.execute_query(pattern_query)

                                if not day_pattern.empty:
                                    col1, col2 = st.columns(2)

                                    with col1:
                                        st.markdown("*By Day of Week:*")
                                        st.dataframe(
                                            day_pattern.style.format({
                                                'Visits': '{:,}',
                                                'TotalSpent': '${:,.2f}'
                                            }),
                                            use_container_width=True,
                                            hide_index=True,
                                            height=200
                                        )

                                    with col2:
                                        # Time of day pattern
                                        time_query = f"""
                                        SELECT
                                            CASE
                                                WHEN DATEPART(HOUR, t.Time) BETWEEN 6 AND 9 THEN 'Early (6am-10am)'
                                                WHEN DATEPART(HOUR, t.Time) BETWEEN 10 AND 11 THEN 'Morning (10am-12pm)'
                                                WHEN DATEPART(HOUR, t.Time) BETWEEN 12 AND 16 THEN 'Afternoon (12pm-5pm)'
                                                WHEN DATEPART(HOUR, t.Time) BETWEEN 17 AND 20 THEN 'Evening (5pm-9pm)'
                                                WHEN DATEPART(HOUR, t.Time) BETWEEN 21 AND 23 THEN 'Night (9pm-11pm)'
                                                ELSE 'Other'
                                            END as TimePeriod,
                                            COUNT(DISTINCT t.TransactionNumber) as Visits,
                                            SUM(t.Total) as TotalSpent
                                        FROM [Transaction] t WITH (NOLOCK)
                                        WHERE t.CustomerID = {customer_id}
                                          AND t.StoreID = {store_id}
                                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                                        GROUP BY CASE
                                            WHEN DATEPART(HOUR, t.Time) BETWEEN 6 AND 9 THEN 'Early (6am-10am)'
                                            WHEN DATEPART(HOUR, t.Time) BETWEEN 10 AND 11 THEN 'Morning (10am-12pm)'
                                            WHEN DATEPART(HOUR, t.Time) BETWEEN 12 AND 16 THEN 'Afternoon (12pm-5pm)'
                                            WHEN DATEPART(HOUR, t.Time) BETWEEN 17 AND 20 THEN 'Evening (5pm-9pm)'
                                            WHEN DATEPART(HOUR, t.Time) BETWEEN 21 AND 23 THEN 'Night (9pm-11pm)'
                                            ELSE 'Other'
                                        END
                                        ORDER BY Visits DESC
                                        """

                                        time_pattern = db.execute_query(time_query)

                                        if not time_pattern.empty:
                                            st.markdown("*By Time of Day:*")
                                            st.dataframe(
                                                time_pattern.style.format({
                                                    'Visits': '{:,}',
                                                    'TotalSpent': '${:,.2f}'
                                                }),
                                                use_container_width=True,
                                                hide_index=True,
                                                height=200
                                            )
                    else:
                        st.info("No store activity in selected period")

                    # Section F: Category & Product Analysis (Global)
                    st.markdown("---")
                    st.subheader("📦 Category & Product Analysis")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Category breakdown
                        cat_global_query = f"""
                        SELECT
                            c.Name as Category,
                            SUM(te.Quantity) as Quantity,
                            SUM(te.Price * te.Quantity) as TotalSpent,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions
                        FROM [Transaction] t WITH (NOLOCK)
                        INNER JOIN TransactionEntry te WITH (NOLOCK)
                            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                        INNER JOIN Item i WITH (NOLOCK)
                            ON te.ItemID = i.ID
                        INNER JOIN Category c WITH (NOLOCK)
                            ON i.CategoryID = c.ID
                        WHERE t.CustomerID = {customer_id}
                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        GROUP BY c.Name
                        ORDER BY TotalSpent DESC
                        """

                        cat_global = db.execute_query(cat_global_query)

                        if not cat_global.empty:
                            st.markdown("**Spending by Category:**")

                            # Pie chart
                            fig = px.pie(
                                cat_global.head(10),
                                values='TotalSpent',
                                names='Category',
                                title="Top 10 Categories by Spend"
                            )
                            st.plotly_chart(fig, use_container_width=True)

                    with col2:
                        # Excise vs Non-Excise
                        excise_mix_query = f"""
                        SELECT
                            CASE
                                WHEN pue.SubDescription3 IS NOT NULL THEN 'Excise Products'
                                ELSE 'Non-Excise Products'
                            END as ProductType,
                            SUM(te.Price * te.Quantity) as TotalSpent,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions
                        FROM [Transaction] t WITH (NOLOCK)
                        INNER JOIN TransactionEntry te WITH (NOLOCK)
                            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
                            ON t.TransactionNumber = pue.TransactionNumber
                            AND te.ItemID = pue.ItemID
                        WHERE t.CustomerID = {customer_id}
                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        GROUP BY CASE
                            WHEN pue.SubDescription3 IS NOT NULL THEN 'Excise Products'
                            ELSE 'Non-Excise Products'
                        END
                        """

                        excise_mix = db.execute_query(excise_mix_query)

                        if not excise_mix.empty:
                            st.markdown("**Excise vs Non-Excise Mix:**")

                            fig = px.pie(
                                excise_mix,
                                values='TotalSpent',
                                names='ProductType',
                                title="Product Mix by Type",
                                color='ProductType',
                                color_discrete_map={
                                    'Excise Products': '#ff7f0e',
                                    'Non-Excise Products': '#1f77b4'
                                }
                            )
                            st.plotly_chart(fig, use_container_width=True)

                    # Top products table
                    st.markdown("**Top 20 Products:**")

                    top_products_query = f"""
                    SELECT TOP 20
                        i.Description as Product,
                        i.ItemLookupCode as SKU,
                        c.Name as Category,
                        SUM(te.Quantity) as Quantity,
                        SUM(te.Price * te.Quantity) as TotalSpent,
                        AVG(te.Price) as AvgPrice,
                        COUNT(DISTINCT t.TransactionNumber) as TimesPurchased,
                        COUNT(DISTINCT t.StoreID) as StoresVisited
                    FROM [Transaction] t WITH (NOLOCK)
                    INNER JOIN TransactionEntry te WITH (NOLOCK)
                        ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                    INNER JOIN Item i WITH (NOLOCK)
                        ON te.ItemID = i.ID
                    INNER JOIN Category c WITH (NOLOCK)
                        ON i.CategoryID = c.ID
                    WHERE t.CustomerID = {customer_id}
                      AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                      AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    GROUP BY i.Description, i.ItemLookupCode, c.Name
                    ORDER BY TotalSpent DESC
                    """

                    top_products = db.execute_query(top_products_query)

                    if not top_products.empty:
                        st.dataframe(
                            top_products.style.format({
                                'Quantity': '{:,.0f}',
                                'TotalSpent': '${:,.2f}',
                                'AvgPrice': '${:,.2f}',
                                'TimesPurchased': '{:,}',
                                'StoresVisited': '{:,}'
                            }).background_gradient(subset=['TotalSpent'], cmap='Greens'),
                            use_container_width=True,
                            height=400
                        )

                    # Section G: Purchase Behavior Patterns
                    st.markdown("---")
                    st.subheader("🕒 Purchase Behavior Patterns")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Day of week pattern (global across all stores)
                        dow_query = f"""
                        SELECT
                            DATENAME(WEEKDAY, t.Time) as DayOfWeek,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions,
                            SUM(t.Total) as TotalSpent,
                            AVG(t.Total) as AvgBasket
                        FROM [Transaction] t WITH (NOLOCK)
                        WHERE t.CustomerID = {customer_id}
                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        GROUP BY DATENAME(WEEKDAY, t.Time), DATEPART(WEEKDAY, t.Time)
                        ORDER BY DATEPART(WEEKDAY, t.Time)
                        """

                        dow_pattern = db.execute_query(dow_query)

                        if not dow_pattern.empty:
                            st.markdown("**Day of Week Preference:**")
                            st.dataframe(
                                dow_pattern.style.format({
                                    'Transactions': '{:,}',
                                    'TotalSpent': '${:,.2f}',
                                    'AvgBasket': '${:,.2f}'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                    with col2:
                        # Time of day pattern (global)
                        tod_query = f"""
                        SELECT
                            CASE
                                WHEN DATEPART(HOUR, t.Time) BETWEEN 6 AND 9 THEN 'Early (6am-10am)'
                                WHEN DATEPART(HOUR, t.Time) BETWEEN 10 AND 11 THEN 'Morning (10am-12pm)'
                                WHEN DATEPART(HOUR, t.Time) BETWEEN 12 AND 16 THEN 'Afternoon (12pm-5pm)'
                                WHEN DATEPART(HOUR, t.Time) BETWEEN 17 AND 20 THEN 'Evening (5pm-9pm)'
                                WHEN DATEPART(HOUR, t.Time) BETWEEN 21 AND 23 THEN 'Night (9pm-11pm)'
                                ELSE 'Other'
                            END as TimePeriod,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions,
                            SUM(t.Total) as TotalSpent
                        FROM [Transaction] t WITH (NOLOCK)
                        WHERE t.CustomerID = {customer_id}
                          AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                        GROUP BY CASE
                            WHEN DATEPART(HOUR, t.Time) BETWEEN 6 AND 9 THEN 'Early (6am-10am)'
                            WHEN DATEPART(HOUR, t.Time) BETWEEN 10 AND 11 THEN 'Morning (10am-12pm)'
                            WHEN DATEPART(HOUR, t.Time) BETWEEN 12 AND 16 THEN 'Afternoon (12pm-5pm)'
                            WHEN DATEPART(HOUR, t.Time) BETWEEN 17 AND 20 THEN 'Evening (5pm-9pm)'
                            WHEN DATEPART(HOUR, t.Time) BETWEEN 21 AND 23 THEN 'Night (9pm-11pm)'
                            ELSE 'Other'
                        END
                        ORDER BY Transactions DESC
                        """

                        tod_pattern = db.execute_query(tod_query)

                        if not tod_pattern.empty:
                            st.markdown("**Time of Day Pattern:**")
                            st.dataframe(
                                tod_pattern.style.format({
                                    'Transactions': '{:,}',
                                    'TotalSpent': '${:,.2f}'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                    # Visit frequency trend
                    st.markdown("**Visit Frequency Trend:**")

                    freq_query = f"""
                    SELECT
                        CAST(t.Time as DATE) as Date,
                        COUNT(DISTINCT t.TransactionNumber) as Visits,
                        SUM(t.Total) as Spent
                    FROM [Transaction] t WITH (NOLOCK)
                    WHERE t.CustomerID = {customer_id}
                      AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                      AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    GROUP BY CAST(t.Time as DATE)
                    ORDER BY Date DESC
                    """

                    freq_trend = db.execute_query(freq_query)

                    if not freq_trend.empty:
                        st.dataframe(
                            freq_trend.head(30).style.format({
                                'Date': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'N/A',
                                'Visits': '{:,}',
                                'Spent': '${:,.2f}'
                            }),
                            use_container_width=True,
                            hide_index=True,
                            height=300
                        )

                    # Section H: Period Comparison
                    st.markdown("---")
                    st.subheader("📊 Period-over-Period Comparison")

                    # Calculate previous period
                    period_length = (end_date - start_date).days
                    prev_start = start_date - timedelta(days=period_length)
                    prev_end = start_date - timedelta(seconds=1)

                    prev_query = f"""
                    SELECT
                        COUNT(DISTINCT t.TransactionNumber) as TotalTransactions,
                        SUM(t.Total) as TotalRevenue,
                        AVG(t.Total) as AvgTransactionSize,
                        SUM(te.Quantity) as ItemsPurchased,
                        SUM((te.Price - te.Cost) * te.Quantity) as GrossProfitBeforeExcise
                    FROM [Transaction] t WITH (NOLOCK)
                    LEFT JOIN TransactionEntry te WITH (NOLOCK)
                        ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                    WHERE t.CustomerID = {customer_id}
                      AND t.Time >= '{prev_start.strftime('%Y-%m-%d %H:%M:%S')}'
                      AND t.Time <= '{prev_end.strftime('%Y-%m-%d %H:%M:%S')}'
                    """

                    prev_overall = db.execute_query(prev_query)

                    if not prev_overall.empty and prev_overall['TotalTransactions'].iloc[0] and prev_overall['TotalTransactions'].iloc[0] > 0:
                        prev_revenue = prev_overall['TotalRevenue'].iloc[0] or 0
                        prev_transactions = prev_overall['TotalTransactions'].iloc[0] or 0
                        prev_avg_basket = prev_overall['AvgTransactionSize'].iloc[0] or 0
                        prev_gross_profit_before = prev_overall['GrossProfitBeforeExcise'].iloc[0] or 0

                        # Get prev excise
                        prev_excise_query = f"""
                        SELECT
                            ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
                                THEN pue.PriceC * pue.Quantity
                                ELSE 0 END), 0) as ExciseCollected
                        FROM [Transaction] t WITH (NOLOCK)
                        INNER JOIN TransactionEntry te WITH (NOLOCK)
                            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                        LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
                            ON t.TransactionNumber = pue.TransactionNumber
                            AND te.ItemID = pue.ItemID
                        WHERE t.CustomerID = {customer_id}
                          AND t.Time >= '{prev_start.strftime('%Y-%m-%d %H:%M:%S')}'
                          AND t.Time <= '{prev_end.strftime('%Y-%m-%d %H:%M:%S')}'
                        """
                        prev_excise_result = db.execute_query(prev_excise_query)
                        prev_excise = prev_excise_result['ExciseCollected'].iloc[0] if not prev_excise_result.empty else 0
                        prev_gross_profit = prev_gross_profit_before - prev_excise

                        # Build comparison table
                        comparison_data = {
                            'Metric': ['Total Spent', 'Transactions', 'Avg Basket', 'Gross Profit'],
                            'This Period': [
                                f'${total_revenue:,.2f}',
                                f'{total_transactions:,}',
                                f'${avg_transaction:,.2f}',
                                f'${gross_profit:,.2f}'
                            ],
                            'Last Period': [
                                f'${prev_revenue:,.2f}',
                                f'{prev_transactions:,}',
                                f'${prev_avg_basket:,.2f}',
                                f'${prev_gross_profit:,.2f}'
                            ],
                            'Change $': [
                                f'${total_revenue - prev_revenue:,.2f}',
                                f'{total_transactions - prev_transactions:,}',
                                f'${avg_transaction - prev_avg_basket:,.2f}',
                                f'${gross_profit - prev_gross_profit:,.2f}'
                            ],
                            'Change %': [
                                f'{((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0:+.1f}%',
                                f'{((total_transactions - prev_transactions) / prev_transactions * 100) if prev_transactions > 0 else 0:+.1f}%',
                                f'{((avg_transaction - prev_avg_basket) / prev_avg_basket * 100) if prev_avg_basket > 0 else 0:+.1f}%',
                                f'{((gross_profit - prev_gross_profit) / prev_gross_profit * 100) if prev_gross_profit > 0 else 0:+.1f}%'
                            ]
                        }

                        comparison_df = pd.DataFrame(comparison_data)

                        st.markdown(f"**Comparing:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} vs {prev_start.strftime('%Y-%m-%d')} to {prev_end.strftime('%Y-%m-%d')}")

                        st.dataframe(
                            comparison_df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No data available for previous period comparison")

                    # Section I: Transaction Ledger
                    st.markdown("---")
                    st.subheader("📜 Transaction Ledger")

                    ledger_query = f"""
                    SELECT
                        t.Time as DateTime,
                        t.StoreID,
                        t.TransactionNumber,
                        t.Total as Amount,
                        t.SalesTax,
                        (SELECT SUM((te2.Price - te2.Cost) * te2.Quantity)
                         FROM TransactionEntry te2
                         WHERE te2.TransactionNumber = t.TransactionNumber
                           AND te2.StoreID = t.StoreID) as GrossProfit,
                        (SELECT COUNT(*)
                         FROM TransactionEntry te3
                         WHERE te3.TransactionNumber = t.TransactionNumber
                           AND te3.StoreID = t.StoreID) as ItemCount
                    FROM [Transaction] t WITH (NOLOCK)
                    WHERE t.CustomerID = {customer_id}
                      AND t.Time >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                      AND t.Time <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    ORDER BY t.Time DESC
                    """

                    ledger = db.execute_query(ledger_query)

                    if not ledger.empty:
                        st.markdown(f"**{len(ledger)} transactions in selected period**")

                        # Show summary first
                        st.dataframe(
                            ledger.style.format({
                                'DateTime': lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else 'N/A',
                                'Amount': '${:,.2f}',
                                'SalesTax': '${:,.2f}',
                                'GrossProfit': '${:,.2f}',
                                'ItemCount': '{:,}'
                            }),
                            use_container_width=True,
                            height=400
                        )

                        # Expandable line items for each transaction
                        st.markdown("**📋 Transaction Details** (click to expand)")

                        # Show first 20 transactions with expandable details
                        for idx, trans_row in ledger.head(20).iterrows():
                            trans_num = trans_row['TransactionNumber']
                            store_id = trans_row['StoreID']

                            with st.expander(f"Transaction #{trans_num} - {trans_row['DateTime'].strftime('%Y-%m-%d %H:%M')} - ${trans_row['Amount']:,.2f}"):
                                # Get line items
                                lines_query = f"""
                                SELECT
                                    i.Description as Product,
                                    i.ItemLookupCode as SKU,
                                    c.Name as Category,
                                    te.Quantity,
                                    te.Price,
                                    te.Cost,
                                    (te.Price - te.Cost) * te.Quantity as LineProfit
                                FROM TransactionEntry te WITH (NOLOCK)
                                INNER JOIN Item i WITH (NOLOCK)
                                    ON te.ItemID = i.ID
                                INNER JOIN Category c WITH (NOLOCK)
                                    ON i.CategoryID = c.ID
                                WHERE te.TransactionNumber = {trans_num}
                                  AND te.StoreID = {store_id}
                                ORDER BY LineProfit DESC
                                """

                                lines = db.execute_query(lines_query)

                                if not lines.empty:
                                    st.dataframe(
                                        lines.style.format({
                                            'Quantity': '{:,.0f}',
                                            'Price': '${:,.2f}',
                                            'Cost': '${:,.2f}',
                                            'LineProfit': '${:,.2f}'
                                        }),
                                        use_container_width=True,
                                        hide_index=True
                                    )

                        if len(ledger) > 20:
                            st.info(f"Showing first 20 of {len(ledger)} transactions. Download full ledger for complete history.")

                        # Download button
                        csv = ledger.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Full Transaction Ledger",
                            data=csv,
                            file_name=f"customer_{customer_id}_ledger_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No transactions in selected period")

                else:
                    st.info(f"No activity for this customer in the selected period ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")

        except Exception as e:
            st.error(f"❌ Error loading customer data: {str(e)}")
            st.exception(e)
    else:
        st.info("👆 Search for a customer above to begin analysis")

# ============================================================================
# TAB 2: CUSTOMER SEGMENTS
# ============================================================================
with tab2:
    st.subheader("📊 Customer Segment Analysis")
    st.markdown("Analyze groups of customers with similar characteristics")

    st.markdown("---")

    # Section A: Segment Selector
    col1, col2 = st.columns([2, 1])

    with col1:
        segment_type = st.selectbox(
            "Select Segment Type:",
            options=[
                "Customer Group (from Groups page)",
                "Top 10% by Lifetime Sales (VIP)",
                "New Customers (First purchase in period)",
                "At-Risk (No purchase in 90+ days)",
                "High Credit Balance",
                "Tax Exempt Customers"
            ],
            key="segment_type"
        )

    # If customer group, let them select which one
    if segment_type == "Customer Group (from Groups page)":
        try:
            groups = overlay_db.get_customer_groups()

            if not groups.empty:
                with col2:
                    selected_group = st.selectbox(
                        "Select Group:",
                        options=groups['id'].tolist(),
                        format_func=lambda x: groups[groups['id'] == x]['group_name'].iloc[0]
                    )
            else:
                st.warning("⚠️ No customer groups defined. Create groups on the Customer Groups page first.")
                st.stop()
        except Exception as e:
            st.error(f"❌ Error loading groups: {str(e)}")
            st.stop()

    if st.button("📊 Analyze Segment", type="primary", key="analyze_segment"):
        with st.spinner("Analyzing segment..."):
            try:
                # Build customer ID list based on segment type
                if segment_type == "Customer Group (from Groups page)":
                    # Get members from group
                    members_query = """
                    SELECT customer_id
                    FROM customer_group_members
                    WHERE group_id = ?
                    """
                    members = overlay_db.execute_query(members_query, (selected_group,))

                    if members.empty:
                        st.warning("⚠️ No members in this group")
                        st.stop()

                    customer_ids = members['customer_id'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = groups[groups['id'] == selected_group]['group_name'].iloc[0]

                elif segment_type == "Top 10% by Lifetime Sales (VIP)":
                    # Get top 10% customers
                    top_customers_query = """
                    SELECT TOP 10 PERCENT ID
                    FROM Customer
                    WHERE TotalSales > 0
                    ORDER BY TotalSales DESC
                    """
                    top_customers = db.execute_query(top_customers_query)
                    customer_ids = top_customers['ID'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = "VIP Customers (Top 10%)"

                elif segment_type == "New Customers (First purchase in period)":
                    # Time period for "new"
                    days_back = st.slider("Days back to consider 'new':", 7, 90, 30)
                    cutoff_date = datetime.now() - timedelta(days=days_back)

                    new_customers_query = f"""
                    SELECT DISTINCT c.ID
                    FROM Customer c
                    WHERE c.AccountOpened >= '{cutoff_date.strftime('%Y-%m-%d')}'
                    """
                    new_customers = db.execute_query(new_customers_query)
                    customer_ids = new_customers['ID'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = f"New Customers (Last {days_back} days)"

                elif segment_type == "At-Risk (No purchase in 90+ days)":
                    cutoff_date = datetime.now() - timedelta(days=90)

                    atrisk_query = f"""
                    SELECT ID
                    FROM Customer
                    WHERE LastVisit < '{cutoff_date.strftime('%Y-%m-%d')}'
                      AND TotalVisits > 0
                    """
                    atrisk_customers = db.execute_query(atrisk_query)
                    customer_ids = atrisk_customers['ID'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = "At-Risk Customers (90+ days inactive)"

                elif segment_type == "High Credit Balance":
                    threshold = st.number_input("Minimum Account Balance:", value=1000.0, step=100.0)

                    highbalance_query = f"""
                    SELECT ID
                    FROM Customer
                    WHERE AccountBalance >= {threshold}
                    """
                    highbalance_customers = db.execute_query(highbalance_query)
                    customer_ids = highbalance_customers['ID'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = f"High Credit Balance (>= ${threshold:,.2f})"

                else:  # Tax Exempt
                    taxexempt_query = """
                    SELECT ID
                    FROM Customer
                    WHERE TaxExempt = 1
                    """
                    taxexempt_customers = db.execute_query(taxexempt_query)
                    customer_ids = taxexempt_customers['ID'].tolist()
                    customer_filter = f"t.CustomerID IN ({','.join(map(str, customer_ids))})"
                    segment_name = "Tax Exempt Customers"

                if not customer_ids:
                    st.warning("⚠️ No customers found in this segment")
                    st.stop()

                # Section B: Segment Overview
                st.markdown("---")
                st.subheader(f"📊 {segment_name}")
                st.info(f"Analyzing {len(customer_ids)} customers in this segment...")

                # Overall segment metrics - Optimized query without huge IN clause
                # First get transaction-level metrics
                segment_trans_query = f"""
                SELECT
                    COUNT(DISTINCT t.CustomerID) as TotalCustomers,
                    SUM(t.Total) as TotalRevenue,
                    AVG(t.Total) as AvgTransactionSize,
                    COUNT(DISTINCT t.TransactionNumber) as TotalTransactions
                FROM [Transaction] t WITH (NOLOCK)
                WHERE {customer_filter}
                """

                # Separate query for items and profit to avoid row multiplication
                segment_items_query = f"""
                SELECT
                    SUM(te.Quantity) as ItemsPurchased,
                    SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
                FROM [Transaction] t WITH (NOLOCK)
                INNER JOIN TransactionEntry te WITH (NOLOCK)
                    ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                WHERE {customer_filter}
                """

                segment_trans = db.execute_query(segment_trans_query)
                segment_items = db.execute_query(segment_items_query)

                # Combine results
                segment_overview = segment_trans.copy()
                if not segment_items.empty:
                    segment_overview['ItemsPurchased'] = segment_items['ItemsPurchased'].iloc[0]
                    segment_overview['GrossProfit'] = segment_items['GrossProfit'].iloc[0]
                else:
                    segment_overview['ItemsPurchased'] = 0
                    segment_overview['GrossProfit'] = 0

                if not segment_overview.empty and segment_overview['TotalCustomers'].iloc[0]:
                    total_customers = segment_overview['TotalCustomers'].iloc[0] or 0
                    total_revenue = segment_overview['TotalRevenue'].iloc[0] or 0
                    avg_customer_value = total_revenue / total_customers if total_customers > 0 else 0
                    total_profit = segment_overview['GrossProfit'].iloc[0] or 0

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric(
                            "Total Customers",
                            f"{total_customers:,}",
                            help="Number of customers in this segment"
                        )

                    with col2:
                        st.metric(
                            "Total Revenue",
                            f"${total_revenue:,.2f}",
                            help="Total revenue from segment"
                        )

                    with col3:
                        st.metric(
                            "Avg Customer Value",
                            f"${avg_customer_value:,.2f}",
                            help="Average revenue per customer"
                        )

                    with col4:
                        st.metric(
                            "Total Profit",
                            f"${total_profit:,.2f}",
                            help="Total gross profit from segment"
                        )

                    # Section C: Segment Leaderboard
                    st.markdown("---")
                    st.subheader("🏆 Customer Leaderboard")

                    leaderboard_query = f"""
                    SELECT
                        c.ID as CustomerID,
                        c.FirstName + ' ' + c.LastName as CustomerName,
                        c.Company,
                        SUM(t.Total) as TotalSpent,
                        COUNT(DISTINCT t.TransactionNumber) as Transactions,
                        AVG(t.Total) as AvgBasket,
                        MAX(t.Time) as LastVisit,
                        COUNT(DISTINCT t.StoreID) as StoresVisited
                    FROM [Transaction] t WITH (NOLOCK)
                    INNER JOIN Customer c WITH (NOLOCK)
                        ON t.CustomerID = c.ID
                    WHERE {customer_filter}
                    GROUP BY c.ID, c.FirstName, c.LastName, c.Company
                    ORDER BY TotalSpent DESC
                    """

                    leaderboard = db.execute_query(leaderboard_query)

                    if not leaderboard.empty:
                        st.dataframe(
                            leaderboard.style.format({
                                'TotalSpent': '${:,.2f}',
                                'Transactions': '{:,}',
                                'AvgBasket': '${:,.2f}',
                                'LastVisit': lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'Never',
                                'StoresVisited': '{:,}'
                            }).background_gradient(subset=['TotalSpent'], cmap='Blues'),
                            use_container_width=True,
                            height=500
                        )

                        # Download
                        csv = leaderboard.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Segment Data",
                            data=csv,
                            file_name=f"segment_{segment_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )

                    # Section D: Segment Insights
                    st.markdown("---")
                    st.subheader("💡 Segment Insights")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Top store for segment
                        st.markdown("**Top Stores for This Segment:**")

                        top_stores_query = f"""
                        SELECT TOP 5
                            t.StoreID,
                            COUNT(DISTINCT t.CustomerID) as UniqueCustomers,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions,
                            SUM(t.Total) as TotalRevenue
                        FROM [Transaction] t WITH (NOLOCK)
                        WHERE {customer_filter}
                        GROUP BY t.StoreID
                        ORDER BY TotalRevenue DESC
                        """

                        top_stores = db.execute_query(top_stores_query)

                        if not top_stores.empty:
                            st.dataframe(
                                top_stores.style.format({
                                    'UniqueCustomers': '{:,}',
                                    'Transactions': '{:,}',
                                    'TotalRevenue': '${:,.2f}'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                    with col2:
                        # Top categories for segment
                        st.markdown("**Top Categories for This Segment:**")

                        top_categories_query = f"""
                        SELECT TOP 5
                            c.Name as Category,
                            COUNT(DISTINCT t.CustomerID) as Customers,
                            SUM(te.Price * te.Quantity) as TotalSales
                        FROM [Transaction] t WITH (NOLOCK)
                        INNER JOIN TransactionEntry te WITH (NOLOCK)
                            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                        INNER JOIN Item i WITH (NOLOCK)
                            ON te.ItemID = i.ID
                        INNER JOIN Category c WITH (NOLOCK)
                            ON i.CategoryID = c.ID
                        WHERE {customer_filter}
                        GROUP BY c.Name
                        ORDER BY TotalSales DESC
                        """

                        top_categories = db.execute_query(top_categories_query)

                        if not top_categories.empty:
                            st.dataframe(
                                top_categories.style.format({
                                    'Customers': '{:,}',
                                    'TotalSales': '${:,.2f}'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                    # Average behavior
                    st.markdown("**Average Behavior:**")

                    avg_visits = segment_overview['TotalTransactions'].iloc[0] / total_customers if total_customers > 0 else 0
                    avg_spend = total_revenue / total_customers if total_customers > 0 else 0

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Avg Visits per Customer", f"{avg_visits:.1f}")

                    with col2:
                        st.metric("Avg Spend per Customer", f"${avg_spend:,.2f}")

                    with col3:
                        avg_basket = segment_overview['AvgTransactionSize'].iloc[0] or 0
                        st.metric("Avg Basket Size", f"${avg_basket:,.2f}")

                else:
                    st.warning("⚠️ No transaction data found for this segment")

            except Exception as e:
                st.error(f"❌ Error analyzing segment: {str(e)}")
                st.exception(e)

# ============================================================================
# TAB 3: BULK COMPARISON
# ============================================================================
with tab3:
    st.subheader("📈 Bulk Customer Comparison")
    st.markdown("Compare multiple customers side-by-side")

    st.markdown("---")

    # Section A: Multi-Customer Selector
    selection_method = st.radio(
        "Select customers by:",
        options=["Paste Customer IDs", "Upload CSV", "Select from Group"],
        horizontal=True
    )

    customer_ids_to_compare = []

    if selection_method == "Paste Customer IDs":
        bulk_ids = st.text_area(
            "Enter Customer IDs (one per line):",
            height=150,
            placeholder="12345\n67890\n11223\n..."
        )

        if bulk_ids:
            customer_ids_to_compare = [int(cid.strip()) for cid in bulk_ids.split('\n') if cid.strip().isdigit()]

    elif selection_method == "Upload CSV":
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
                    customer_ids_to_compare = df['customer_id'].astype(int).tolist()
                    st.success(f"✅ Loaded {len(customer_ids_to_compare)} customer IDs")
            except Exception as e:
                st.error(f"❌ Error reading CSV: {str(e)}")

    else:  # Select from Group
        try:
            groups = overlay_db.get_customer_groups()

            if not groups.empty:
                selected_group = st.selectbox(
                    "Select Group:",
                    options=groups['id'].tolist(),
                    format_func=lambda x: groups[groups['id'] == x]['group_name'].iloc[0],
                    key="bulk_group_select"
                )

                # Get members
                members_query = """
                SELECT customer_id
                FROM customer_group_members
                WHERE group_id = ?
                """
                members = overlay_db.execute_query(members_query, (selected_group,))

                if not members.empty:
                    customer_ids_to_compare = members['customer_id'].astype(int).tolist()
                    st.success(f"✅ Loaded {len(customer_ids_to_compare)} customers from group")
                else:
                    st.warning("⚠️ No members in this group")
            else:
                st.warning("⚠️ No customer groups defined")
        except Exception as e:
            st.error(f"❌ Error loading groups: {str(e)}")

    if customer_ids_to_compare:
        st.info(f"📊 Ready to compare {len(customer_ids_to_compare)} customers")

        if st.button("📊 Compare Customers", type="primary", key="compare_customers"):
            with st.spinner("Comparing customers..."):
                try:
                    # Build comparison query - use CTE to avoid nested aggregate error
                    customer_filter = f"CustomerID IN ({','.join(map(str, customer_ids_to_compare))})"

                    comparison_query = f"""
                    WITH CustomerMetrics AS (
                        SELECT
                            t.CustomerID,
                            SUM(t.Total) as TotalSpent,
                            COUNT(DISTINCT t.TransactionNumber) as Transactions,
                            AVG(t.Total) as AvgBasket
                        FROM [Transaction] t WITH (NOLOCK)
                        WHERE t.{customer_filter}
                        GROUP BY t.CustomerID
                    ),
                    CustomerProfit AS (
                        SELECT
                            t.CustomerID,
                            SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit
                        FROM [Transaction] t WITH (NOLOCK)
                        INNER JOIN TransactionEntry te WITH (NOLOCK)
                            ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                        WHERE t.{customer_filter}
                        GROUP BY t.CustomerID
                    ),
                    FavoriteStores AS (
                        SELECT
                            CustomerID,
                            StoreID as FavoriteStore
                        FROM (
                            SELECT
                                CustomerID,
                                StoreID,
                                ROW_NUMBER() OVER (PARTITION BY CustomerID ORDER BY COUNT(*) DESC) as rn
                            FROM [Transaction] WITH (NOLOCK)
                            WHERE {customer_filter}
                            GROUP BY CustomerID, StoreID
                        ) ranked
                        WHERE rn = 1
                    ),
                    TopCategories AS (
                        SELECT
                            t.CustomerID,
                            cat.Name as TopCategory
                        FROM (
                            SELECT
                                t.CustomerID,
                                i.CategoryID,
                                SUM(te.Price * te.Quantity) as CategoryTotal,
                                ROW_NUMBER() OVER (PARTITION BY t.CustomerID ORDER BY SUM(te.Price * te.Quantity) DESC) as rn
                            FROM [Transaction] t WITH (NOLOCK)
                            INNER JOIN TransactionEntry te WITH (NOLOCK)
                                ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
                            INNER JOIN Item i WITH (NOLOCK)
                                ON te.ItemID = i.ID
                            WHERE t.{customer_filter}
                            GROUP BY t.CustomerID, i.CategoryID
                        ) ranked
                        INNER JOIN Category cat WITH (NOLOCK) ON ranked.CategoryID = cat.ID
                        WHERE ranked.rn = 1
                    )
                    SELECT
                        c.ID as CustomerID,
                        c.FirstName + ' ' + c.LastName as CustomerName,
                        c.Company,
                        ISNULL(cm.TotalSpent, 0) as TotalSpent,
                        ISNULL(cm.Transactions, 0) as Transactions,
                        ISNULL(cm.AvgBasket, 0) as AvgBasket,
                        ISNULL(cp.GrossProfit, 0) as GrossProfit,
                        fs.FavoriteStore,
                        tc.TopCategory
                    FROM Customer c WITH (NOLOCK)
                    LEFT JOIN CustomerMetrics cm ON c.ID = cm.CustomerID
                    LEFT JOIN CustomerProfit cp ON c.ID = cp.CustomerID
                    LEFT JOIN FavoriteStores fs ON c.ID = fs.CustomerID
                    LEFT JOIN TopCategories tc ON c.ID = tc.CustomerID
                    WHERE c.{customer_filter}
                    ORDER BY ISNULL(cm.TotalSpent, 0) DESC
                    """

                    comparison = db.execute_query(comparison_query)

                    if not comparison.empty:
                        st.markdown("---")
                        st.subheader("📊 Customer Comparison")

                        st.dataframe(
                            comparison.style.format({
                                'TotalSpent': '${:,.2f}',
                                'Transactions': '{:,}',
                                'AvgBasket': '${:,.2f}',
                                'GrossProfit': '${:,.2f}'
                            }).background_gradient(subset=['TotalSpent', 'GrossProfit'], cmap='RdYlGn'),
                            use_container_width=True,
                            height=500
                        )

                        # Download
                        csv = comparison.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Comparison",
                            data=csv,
                            file_name=f"customer_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ No data found for these customers")

                except Exception as e:
                    st.error(f"❌ Error comparing customers: {str(e)}")
                    st.exception(e)
    else:
        st.info("👆 Select customers above to begin comparison")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
