"""Data Explorer - Browse and query SQL Server data."""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.sql_server import db

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")

st.title("📊 Data Explorer")
st.markdown("Browse tables and run custom SQL queries against your database.")

# Check connection
if not st.session_state.get('sql_server_connected', False):
    st.error("❌ Not connected to SQL Server. Please check your connection settings.")
    st.stop()

# Tabs for different exploration modes
tab1, tab2, tab3 = st.tabs(["📋 Table Browser", "🔍 Custom Query", "📈 Quick Stats"])

with tab1:
    st.subheader("Table Browser")

    try:
        # Get list of tables
        tables = db.get_tables()

        if tables.empty:
            st.warning("No tables found in the database.")
        else:
            # Table selector
            col1, col2 = st.columns([2, 1])

            with col1:
                selected_table = st.selectbox(
                    "Select a table to explore:",
                    options=tables['TABLE_NAME'].tolist(),
                    format_func=lambda x: f"{x}"
                )

            with col2:
                schema = st.selectbox(
                    "Schema:",
                    options=tables['TABLE_SCHEMA'].unique().tolist(),
                    index=0 if 'dbo' in tables['TABLE_SCHEMA'].unique() else 0
                )

            if selected_table:
                st.markdown("---")

                # Show table info
                with st.expander("📋 Table Structure", expanded=False):
                    table_info = db.get_table_info(selected_table, schema)
                    st.dataframe(table_info, use_container_width=True)

                # Query options
                col1, col2, col3 = st.columns(3)

                with col1:
                    limit = st.number_input("Row limit:", min_value=10, max_value=10000,
                                          value=100, step=10)

                with col2:
                    offset = st.number_input("Offset:", min_value=0, max_value=100000,
                                           value=0, step=100)

                with col3:
                    order_by = st.text_input("Order by (optional):", placeholder="column_name DESC")

                # Build and execute query
                if st.button("🔄 Load Data", type="primary"):
                    with st.spinner("Loading data..."):
                        try:
                            query = f"SELECT TOP {limit} * FROM [{schema}].[{selected_table}]"
                            if order_by:
                                query += f" ORDER BY {order_by}"

                            data = db.execute_query(query)

                            st.success(f"✅ Loaded {len(data)} rows")

                            # Store in session state for further analysis
                            st.session_state.current_data = data
                            st.session_state.current_table = selected_table

                        except Exception as e:
                            st.error(f"❌ Error loading data: {str(e)}")

                # Display data if available
                if 'current_data' in st.session_state and st.session_state.current_table == selected_table:
                    st.markdown("---")
                    st.subheader("Data Preview")

                    data = st.session_state.current_data

                    # Data stats
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Rows", len(data))
                    with col2:
                        st.metric("Columns", len(data.columns))
                    with col3:
                        st.metric("Memory", f"{data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
                    with col4:
                        st.metric("Numeric Cols", len(data.select_dtypes(include=['number']).columns))

                    # Display dataframe
                    st.dataframe(data, use_container_width=True, height=400)

                    # Download option
                    csv = data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

with tab2:
    st.subheader("Custom SQL Query")

    st.markdown("""
    Run custom SQL queries against your database. **Note:** Only SELECT queries are allowed for safety.
    """)

    # Query input
    query = st.text_area(
        "Enter your SQL query:",
        height=200,
        placeholder="SELECT * FROM your_table WHERE condition = 'value'"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        execute_button = st.button("▶️ Run Query", type="primary")

    with col2:
        if st.button("📋 Show Sample Queries"):
            st.session_state.show_samples = not st.session_state.get('show_samples', False)

    if st.session_state.get('show_samples', False):
        with st.expander("📋 Sample Queries", expanded=True):
            st.code("""
-- Get row count from a table
SELECT COUNT(*) as total_rows FROM your_table

-- Group by with aggregation
SELECT category, COUNT(*) as count, SUM(amount) as total
FROM your_table
GROUP BY category
ORDER BY total DESC

-- Date range query
SELECT * FROM your_table
WHERE date_column >= '2024-01-01'
  AND date_column < '2024-12-31'

-- Join example
SELECT a.*, b.name
FROM table_a a
LEFT JOIN table_b b ON a.id = b.ref_id
            """, language="sql")

    if execute_button and query.strip():
        # Basic safety check
        if not query.strip().upper().startswith('SELECT'):
            st.error("❌ Only SELECT queries are allowed.")
        else:
            with st.spinner("Executing query..."):
                try:
                    result = db.execute_query(query)

                    st.success(f"✅ Query executed successfully! ({len(result)} rows)")

                    # Display results
                    st.dataframe(result, use_container_width=True, height=400)

                    # Store in session state
                    st.session_state.query_result = result

                    # Download option
                    csv = result.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Results",
                        data=csv,
                        file_name=f"query_result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                except Exception as e:
                    st.error(f"❌ Query error: {str(e)}")

with tab3:
    st.subheader("Quick Database Statistics")

    if st.button("🔄 Refresh Stats", type="primary"):
        with st.spinner("Calculating statistics..."):
            try:
                # Get table sizes
                query = """
                SELECT
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME,
                    p.rows as row_count
                FROM INFORMATION_SCHEMA.TABLES t
                LEFT JOIN sys.partitions p ON p.object_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
                WHERE t.TABLE_TYPE = 'BASE TABLE'
                  AND p.index_id IN (0, 1)
                ORDER BY p.rows DESC
                """

                stats = db.execute_query(query)

                if not stats.empty:
                    st.markdown("### 📊 Table Statistics")

                    # Top tables by row count
                    st.markdown("#### Top 10 Largest Tables")
                    top_tables = stats.head(10)
                    st.dataframe(top_tables, use_container_width=True)

                    # Summary metrics
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Total Tables", len(stats))

                    with col2:
                        st.metric("Total Rows", f"{stats['row_count'].sum():,.0f}")

                    with col3:
                        st.metric("Avg Rows/Table", f"{stats['row_count'].mean():,.0f}")

            except Exception as e:
                st.error(f"❌ Error calculating stats: {str(e)}")
