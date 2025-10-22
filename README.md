# GAWDB Analytics Dashboard

A comprehensive analytics dashboard for the GAWDB SQL Server database, built with Streamlit. This dashboard provides deep insights into your data with custom overlay features that don't modify the source database.

## Features

- **📊 Data Explorer**: Browse tables, run custom SQL queries, and explore your database
- **🏷️ Product Categories**: Create custom product categorizations without modifying source data
- **👥 Customer Groups**: Segment customers for targeted analysis
- **💰 Excise Tax Analysis**: Configure and calculate excise taxes on products and categories
- **📈 Sales Analytics**: Deep dive into sales metrics, trends, and customer behavior
- **🔒 Read-Only Source**: All overlays stored in local SQLite database, source DB remains untouched

## Quick Start

### Prerequisites

- Python 3.8+
- Access to SQL Server database
- Network connectivity (including Tailscale if applicable)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd turbo-spoon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database connection:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run the dashboard:
```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Configuration

Edit the `.env` file with your SQL Server connection details:

```env
MSSQL_SERVER=10.1.10.105
MSSQL_USER=your_username
MSSQL_PASSWORD=your_password
MSSQL_DATABASE=GAWDB
MSSQL_TDS_VERSION=7.0
MSSQL_TIMEOUT=30
```

**Note**: The `.env` file is git-ignored for security. Never commit credentials to the repository.

## Project Structure

```
turbo-spoon/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── .env                           # Database credentials (not in git)
├── .env.example                   # Example configuration
├── src/
│   ├── database/
│   │   ├── sql_server.py          # SQL Server connection module
│   │   └── overlay_db.py          # SQLite overlay database
│   └── utils/
│       └── data_processing.py     # Data analysis utilities
├── pages/                          # Streamlit pages (auto-navigation)
│   ├── 1_📊_Data_Explorer.py
│   ├── 2_🏷️_Product_Categories.py
│   ├── 3_👥_Customer_Groups.py
│   ├── 4_💰_Excise_Tax_Analysis.py
│   └── 5_📈_Sales_Analytics.py
└── data/
    └── overlay.db                 # SQLite database for overlays
```

## Usage Guide

### Data Explorer

1. Browse available tables in your database
2. Select a table and view its structure
3. Load data with custom limits and sorting
4. Run custom SQL queries
5. Download results as CSV

### Product Categories

**Create custom categorizations:**
- Add categories one-by-one or bulk upload via CSV
- Categories are stored separately from source database
- Use custom categories in analytics and reporting

**CSV Format for bulk upload:**
```csv
product_id,custom_category,subcategory,original_category,notes
PROD001,Electronics,Phones,Gadgets,High-margin item
PROD002,Clothing,Shirts,Apparel,Seasonal
```

### Customer Groups

**Segment customers:**
- Create named groups (e.g., "VIP", "Wholesale", "Retail")
- Add customers individually or via bulk upload
- Use groups for targeted analysis

### Excise Tax Analysis

**Configure tax rules:**
- Product-specific: Apply tax to individual products
- Category-based: Apply tax to all products in a category
- Multiple tax types: Excise, VAT, Sales, Luxury, etc.

**Calculate taxes:**
- Load sales data from Data Explorer
- Apply tax rules automatically
- View tax breakdown and totals

### Sales Analytics

**Quick Stats:**
- Summary metrics (total, average, median sales)
- Distribution analysis
- Category breakdowns

**Trends:**
- Time-based aggregation (daily, weekly, monthly, quarterly, yearly)
- Growth rate calculations
- Visual trend charts

**Customer Analysis:**
- Customer lifetime value
- Transaction frequency
- RFM (Recency, Frequency, Monetary) segmentation
- Top customers

## Database Schema

### Overlay Database (SQLite)

**product_categories**
- Custom product categorizations
- Fields: product_id, original_category, custom_category, subcategory, notes

**customer_groups**
- Named customer segments
- Fields: id, group_name, description

**customer_group_members**
- Group membership
- Fields: customer_id, group_id

**excise_tax_rules**
- Tax configuration
- Fields: product_id, product_category, tax_rate, tax_type, description

**custom_metrics**
- User-defined KPIs (future feature)
- Fields: metric_name, metric_sql, description

## Data Processing Utilities

The `data_processing.py` module provides reusable functions:

- `merge_with_overlay_categories()` - Apply custom categories to source data
- `calculate_excise_tax()` - Calculate taxes based on rules
- `calculate_time_based_metrics()` - Time-series aggregation
- `calculate_growth_rates()` - Period-over-period growth
- `calculate_customer_metrics()` - Customer behavior analysis
- `apply_filters()` - Multi-column filtering

## Security Notes

1. **Credentials**: Never commit the `.env` file
2. **Read-Only**: Dashboard uses SELECT queries only (UPDATE/DELETE/DROP not allowed)
3. **Local Storage**: Overlay data stored locally in SQLite
4. **Network**: Ensure secure connection to SQL Server (VPN/Tailscale)

## Performance Tips

1. **Query Limits**: Use LIMIT/TOP clauses for large tables
2. **Date Ranges**: Filter by date to reduce data volume
3. **Indexing**: Ensure source database has proper indexes
4. **Caching**: Streamlit automatically caches data between reruns

## Troubleshooting

### Connection Issues

**Error: "Connection failed"**
- Verify SQL Server is accessible from your machine
- Check firewall rules
- Confirm Tailscale is connected (if applicable)
- Validate credentials in `.env`

**Error: "TDS version mismatch"**
- For older SQL Servers, keep `MSSQL_TDS_VERSION=7.0`
- For newer versions, try `8.0` or remove the setting

### Installation Issues

**Error: "No module named 'pymssql'"**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Error: "freetds not found" (Linux/Mac)**
```bash
# Ubuntu/Debian
sudo apt-get install freetds-dev

# Mac
brew install freetds
```

## Development

### Adding New Features

1. **New Page**: Add file to `pages/` directory (e.g., `6_New_Feature.py`)
2. **New Overlay Table**: Add schema to `overlay_db.py`
3. **New Utility**: Add function to `data_processing.py`

### Code Style

- Follow PEP 8
- Use type hints where applicable
- Add docstrings to functions
- Keep functions focused and reusable

## Contributing

This is a custom internal tool. For major changes, discuss with the team first.

## License

Internal use only.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Streamlit documentation: https://docs.streamlit.io
3. Check pymssql documentation: https://pymssql.readthedocs.io

---

**Built with:**
- [Streamlit](https://streamlit.io) - Dashboard framework
- [pymssql](https://pymssql.readthedocs.io) - SQL Server connector
- [Pandas](https://pandas.pydata.org) - Data analysis
- [Plotly](https://plotly.com) - Interactive charts
