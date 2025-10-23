"""API Server Test Page - Test the REST API endpoints."""
import streamlit as st
import sys
from pathlib import Path
import requests
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

st.set_page_config(page_title="API Server Test", page_icon="🔧", layout="wide")

st.title("🔧 API Server Test")
st.markdown("Test the REST API endpoints running on `api_server.py`")

# API Configuration
st.sidebar.header("API Configuration")
api_host = st.sidebar.text_input("API Host", value="http://localhost:5000")

# Check if API is running
try:
    response = requests.get(f"{api_host}/", timeout=2)
    if response.status_code == 200:
        st.sidebar.success("✅ API is running")
        api_info = response.json()
        st.sidebar.json(api_info)
    else:
        st.sidebar.error("❌ API returned error")
except requests.exceptions.ConnectionError:
    st.sidebar.error("❌ API is not running")
    st.error("**API Server is not running!**")
    st.info("Start the API server with: `python3 api_server.py`")
    st.stop()
except Exception as e:
    st.sidebar.error(f"❌ Error: {str(e)}")
    st.stop()

# Test Endpoints
st.markdown("---")

# Health Check
st.header("1️⃣ Health Check")
col1, col2 = st.columns([1, 3])

with col1:
    if st.button("Test /api/health", type="primary"):
        try:
            response = requests.get(f"{api_host}/api/health")
            st.session_state.health_response = response
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    if 'health_response' in st.session_state:
        resp = st.session_state.health_response
        if resp.status_code == 200:
            st.success(f"✅ Status: {resp.status_code}")
        else:
            st.error(f"❌ Status: {resp.status_code}")

        st.json(resp.json())

# Executive Summary
st.markdown("---")
st.header("2️⃣ Executive Summary")

col1, col2 = st.columns([1, 3])

with col1:
    period = st.selectbox(
        "Period:",
        options=["today", "7d", "30d", "mtd", "ytd", "last_month"],
        index=1
    )

    if st.button("Test /api/executive-summary", type="primary"):
        try:
            response = requests.get(
                f"{api_host}/api/executive-summary",
                params={"period": period}
            )
            st.session_state.exec_response = response
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    if 'exec_response' in st.session_state:
        resp = st.session_state.exec_response
        if resp.status_code == 200:
            st.success(f"✅ Status: {resp.status_code}")
            data = resp.json()

            # Display metrics
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Revenue", f"${data.get('revenue', 0):,.2f}")
            with col_b:
                st.metric("Transactions", f"{data.get('transactions', 0):,}")
            with col_c:
                st.metric("Customers", f"{data.get('unique_customers', 0):,}")
            with col_d:
                st.metric("Gross Profit", f"${data.get('gross_profit', 0):,.2f}")

            st.json(data)
        else:
            st.error(f"❌ Status: {resp.status_code}")
            st.json(resp.json())

# Sales Performance
st.markdown("---")
st.header("3️⃣ Sales Performance")

col1, col2 = st.columns([1, 3])

with col1:
    sales_period = st.selectbox(
        "Period:",
        options=["today", "7d", "30d", "mtd", "ytd", "last_month"],
        index=2,
        key="sales_period"
    )

    limit = st.number_input("Limit", min_value=5, max_value=100, value=10)

    if st.button("Test /api/sales-performance", type="primary"):
        try:
            response = requests.get(
                f"{api_host}/api/sales-performance",
                params={"period": sales_period, "limit": limit}
            )
            st.session_state.sales_response = response
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    if 'sales_response' in st.session_state:
        resp = st.session_state.sales_response
        if resp.status_code == 200:
            st.success(f"✅ Status: {resp.status_code}")
            data = resp.json()

            # Show top products
            if data.get('products'):
                st.subheader(f"Top {len(data['products'])} Products")
                import pandas as pd
                df = pd.DataFrame(data['products'])
                st.dataframe(df, use_container_width=True)

            # Show categories
            if data.get('categories'):
                st.subheader(f"Categories ({len(data['categories'])})")
                df_cat = pd.DataFrame(data['categories'])
                st.dataframe(df_cat, use_container_width=True)

            with st.expander("📋 Full JSON Response"):
                st.json(data)
        else:
            st.error(f"❌ Status: {resp.status_code}")
            st.json(resp.json())

# Excise Tax
st.markdown("---")
st.header("4️⃣ Excise Tax Report")

col1, col2 = st.columns([1, 3])

with col1:
    excise_period = st.selectbox(
        "Period:",
        options=["today", "7d", "30d", "mtd", "ytd", "last_month"],
        index=5,
        key="excise_period"
    )

    if st.button("Test /api/excise-tax", type="primary"):
        try:
            response = requests.get(
                f"{api_host}/api/excise-tax",
                params={"period": excise_period}
            )
            st.session_state.excise_response = response
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    if 'excise_response' in st.session_state:
        resp = st.session_state.excise_response
        if resp.status_code == 200:
            st.success(f"✅ Status: {resp.status_code}")
            data = resp.json()

            # Display metrics
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Excise Paid", f"${data.get('excise_paid', 0):,.2f}")
            with col_b:
                st.metric("Excise Collected", f"${data.get('excise_collected', 0):,.2f}")
            with col_c:
                st.metric("Difference", f"${data.get('difference', 0):,.2f}")
            with col_d:
                st.metric("Recovery Rate", f"{data.get('recovery_rate', 0):.1f}%")

            st.json(data)
        else:
            st.error(f"❌ Status: {resp.status_code}")
            st.json(resp.json())

# Raw API Tester
st.markdown("---")
st.header("5️⃣ Raw API Request")

col1, col2 = st.columns([1, 3])

with col1:
    endpoint = st.text_input("Endpoint", value="/api/health")
    method = st.selectbox("Method", ["GET", "POST"])

    if st.button("Send Request", type="primary"):
        try:
            url = f"{api_host}{endpoint}"
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url)

            st.session_state.raw_response = response
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    if 'raw_response' in st.session_state:
        resp = st.session_state.raw_response

        st.write(f"**Status Code:** {resp.status_code}")
        st.write(f"**URL:** {resp.url}")
        st.write(f"**Response Time:** {resp.elapsed.total_seconds():.3f}s")

        st.subheader("Headers")
        st.json(dict(resp.headers))

        st.subheader("Response Body")
        try:
            st.json(resp.json())
        except:
            st.code(resp.text)

# Instructions
st.markdown("---")
st.info("""
**🚀 To start the API server:**

```bash
cd /Users/akbarchranya/turbo-spoon-dashboard/turbo-spoon
python3 api_server.py
```

The API will run on `http://localhost:5000`
""")

# Footer
st.markdown("---")
st.caption(f"API Test Page | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
