"""Main Streamlit dashboard application."""
import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.sql_server_pyodbc import db
from database.overlay_db import overlay_db

# Page configuration
st.set_page_config(
    page_title="GAWDB Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def test_connections():
    """Test database connections on startup."""
    if 'connections_tested' not in st.session_state:
        # Overlay DB is always available (SQLite)
        st.session_state.overlay_db_connected = True
        st.sidebar.success("✅ Overlay DB ready")

        # SQL Server connection test with timeout handling
        try:
            with st.spinner("Testing SQL Server connection..."):
                success, message = db.test_connection()
                if success:
                    st.session_state.sql_server_connected = True
                    st.sidebar.success("✅ SQL Server connected")
                else:
                    st.session_state.sql_server_connected = False
                    st.sidebar.warning(f"⚠️ SQL Server: {message}")
        except Exception as e:
            st.session_state.sql_server_connected = False
            st.sidebar.error(f"❌ SQL Server connection failed: {str(e)}")
            st.sidebar.info("💡 You can still use overlay features. Check your connection settings in .env")

        st.session_state.connections_tested = True


def main():
    """Main application entry point."""

    # Sidebar
    st.sidebar.title("📊 GAWDB Dashboard")
    st.sidebar.markdown("---")

    # Test connections
    test_connections()

    # Main content
    st.markdown('<p class="main-header">📊 GAWDB Analytics Dashboard</p>', unsafe_allow_html=True)

    st.markdown("""
    Welcome to the GAWDB Analytics Dashboard! This tool provides deep insights into your data
    with custom overlays for enhanced analysis.

    ## Features
    - 📈 **Data Explorer**: Browse and query your SQL Server data
    - 🏷️ **Product Categories**: Manage custom product categorizations
    - 👥 **Customer Groups**: Create and analyze customer segments
    - 💰 **Excise Tax Analysis**: View and calculate excise taxes
    - 📊 **Sales Analytics**: Deep dive into sales metrics and trends
    - 🎯 **Custom Metrics**: Define and track your own KPIs

    ## Getting Started
    Use the navigation menu above to explore different sections of the dashboard.
    """)

    # Quick stats if connected
    if st.session_state.get('sql_server_connected', False):
        st.markdown("---")
        st.subheader("Quick System Info")

        col1, col2 = st.columns(2)

        with col1:
            with st.expander("📋 Database Tables", expanded=False):
                try:
                    tables = db.get_tables()
                    st.dataframe(tables, use_container_width=True, height=300)
                    st.caption(f"Total tables: {len(tables)}")
                except Exception as e:
                    st.error(f"Error loading tables: {str(e)}")

        with col2:
            with st.expander("🏷️ Overlay Statistics", expanded=False):
                try:
                    cat_count = len(overlay_db.get_product_categories())
                    group_count = len(overlay_db.get_customer_groups())
                    tax_count = len(overlay_db.get_excise_tax_rules())

                    st.metric("Custom Product Categories", cat_count)
                    st.metric("Customer Groups", group_count)
                    st.metric("Excise Tax Rules", tax_count)
                except Exception as e:
                    st.error(f"Error loading overlay stats: {str(e)}")

    # Footer
    st.markdown("---")
    st.caption("GAWDB Analytics Dashboard | Powered by Streamlit")


if __name__ == "__main__":
    main()
