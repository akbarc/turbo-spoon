# Gross Profit Dashboard - Technical Documentation

## Overview
The Gross Profit Dashboard running on **port 8081** is a Flask-based web application that provides real-time profitability analysis for the Georgia Dashboard system. It's designed to be fast, accurate, and easy to use.

**Access URLs:**
- Local: http://localhost:8081
- Tailscale: http://100.126.106.37:8081

## Architecture

### 1. Application Structure

```
gp_dashboard.py                          # Flask application (main entry point)
data_foundation/gross_profit.py          # Core GP calculation logic
templates/gp_analysis.html              # Frontend UI
modules/gp_analysis.py                  # Advanced analytics (not used in simple dashboard)
```

### 2. Technology Stack

- **Backend**: Flask (Python 3.11)
- **Database**: SQL Server via pymssql (NO pandas for speed)
- **Frontend**: Vanilla JavaScript with Chart.js
- **Styling**: Custom CSS with glassmorphism design
- **Network**: Tailscale for secure remote access

## Database Layer

### Key Database Objects

1. **PUVIEWEXCISETRANSACTION** (Main View)
   - Pre-calculated view with excise tax data
   - Used for real-time GP calculations
   - Contains: PRICE, COST, QUANTITY, PUEPRICEC (excise tax)

2. **GP_Daily_Summary** (Summary Table)
   - Pre-aggregated daily GP data by category
   - Used for category and department breakdowns
   - Requires population via `populate_gp_summary.py`
   - Fields: BusinessDate, CategoryName, Revenue, COGS, ExciseTax, GrossProfit, ItemCount

3. **Supporting Tables**
   - CategoryMapping: Links categories to departments
   - Departments: Department hierarchy and metadata

### GP Calculation Formula

```
Gross Profit = (Price × Quantity) - (Cost × Quantity) - Excise Tax

GP Margin % = (Gross Profit / Revenue) × 100

Where:
  Revenue = Price × Quantity
  COGS = Cost × Quantity
  Excise Tax = PUEPRICEC (from PUVIEWEXCISETRANSACTION)
```

## API Endpoints

### 1. GET /api/gp/summary
**Purpose**: Get overall GP summary for date range

**Query Parameters**:
- `start_date` (optional): YYYY-MM-DD format, defaults to today
- `end_date` (optional): YYYY-MM-DD format, defaults to today

**Response**:
```json
{
  "total_revenue": 29009769.15,
  "total_cogs": 26583139.45,
  "total_excise_tax": 451676.15,
  "total_gross_profit": 1974953.55,
  "gp_margin_percent": 6.81,
  "transaction_count": 13783,
  "items_with_excise_tax": 294431,
  "return_count": 4568
}
```

**Data Source**: `PUVIEWEXCISETRANSACTION` view
**Function**: `get_gross_profit_summary()` in gross_profit.py:59

---

### 2. GET /api/gp/categories
**Purpose**: Get GP breakdown by category

**Query Parameters**:
- `start_date`, `end_date` (same as above)

**Response**:
```json
[
  {
    "CategoryName": "Cigarettes",
    "revenue": 15000000.00,
    "cogs": 14000000.00,
    "excise_tax": 250000.00,
    "gross_profit": 750000.00,
    "gp_margin_percent": 5.0,
    "item_count": 50000
  }
]
```

**Data Source**: `GP_Daily_Summary` table (pre-aggregated)
**Function**: `get_gp_by_category()` in gross_profit.py:133

---

### 3. GET /api/gp/departments
**Purpose**: Get GP breakdown by department (high-level groupings)

**Query Parameters**:
- `start_date`, `end_date` (same as above)

**Response**:
```json
[
  {
    "DepartmentCode": "TOBACCO",
    "DepartmentName": "Tobacco Products",
    "revenue": 20000000.00,
    "cogs": 18500000.00,
    "excise_tax": 400000.00,
    "gross_profit": 1100000.00,
    "gp_margin_percent": 5.5,
    "item_count": 150000,
    "category_count": 5
  }
]
```

**Data Source**: `GP_Daily_Summary` + `CategoryMapping` + `Departments`
**Function**: `get_gp_by_department()` in gross_profit.py:185

---

### 4. GET /api/gp/excise
**Purpose**: Get excise tax breakdown by type

**Query Parameters**:
- `start_date`, `end_date` (same as above)

**Response**:
```json
[
  {
    "ExciseTaxType": "LC23COLL",
    "transaction_count": 5000,
    "total_excise_tax": 250000.00,
    "total_revenue": 5000000.00
  }
]
```

**Data Source**: `PUVIEWEXCISETRANSACTION` view
**Function**: `get_excise_tax_breakdown()` in gross_profit.py:276

---

### 5. Legacy Endpoints

- **GET /api/gp/today**: Alias for `/api/gp/summary` (defaults to today)
- **GET /api/gp/week**: Last 7 days summary

## Frontend Architecture

### Dashboard UI (gp_analysis.html)

#### Layout Structure

1. **Sidebar Navigation**
   - Fixed left sidebar (260px wide)
   - Links to main dashboard, AR, Sales/Ops, etc.
   - Current page highlighted

2. **Header**
   - Page title with icon
   - Timeframe buttons: MTD, QTD, YTD, 12M

3. **Metrics Grid**
   - 4 key metric cards: Total GP, GP Margin %, Best Category, GP per Customer
   - Hover effects with elevation
   - Color-coded changes (green/red arrows)

4. **Tab System**
   - GP Trending: Line chart showing GP over time
   - Category Analysis: Doughnut chart + table
   - Customer Profitability: Searchable table
   - Product Performance: Top products and low-margin products
   - GP Opportunities: AI-generated improvement suggestions

#### JavaScript Functionality

**Key Functions**:
- `setTimeframe(timeframe)`: Change date range (MTD/QTD/YTD/12M)
- `showTab(tabName)`: Switch between analysis tabs
- `loadAllData()`: Initial data load
- `loadExecutiveSummary()`: Load top metrics
- `loadTrendingData()`: Load and chart GP trends
- `loadCategoryData()`: Load category breakdown
- `loadCustomerData()`: Load customer profitability
- `loadProductData()`: Load product analysis
- `loadOpportunities()`: Load GP improvement opportunities

**Chart.js Integration**:
- Line chart for trending (dual Y-axis: GP amount + margin %)
- Doughnut chart for category breakdown
- Responsive and animated

## Data Flow

```
User Request
    ↓
Flask Route (gp_dashboard.py)
    ↓
Parse date parameters (parse_date_range)
    ↓
Call data function (gross_profit.py)
    ↓
Execute SQL query (pymssql)
    ↓
Query PUVIEWEXCISETRANSACTION or GP_Daily_Summary
    ↓
Convert Decimal to float
    ↓
Return JSON to frontend
    ↓
JavaScript renders charts/tables
```

## Performance Optimizations

### 1. NO Pandas
- Direct pymssql queries for minimal overhead
- Faster startup and lower memory usage

### 2. Pre-Aggregated Data
- `GP_Daily_Summary` table stores daily rollups
- Category queries are instant (no on-the-fly aggregation)

### 3. Indexed Views
- `PUVIEWEXCISETRANSACTION` is a pre-calculated view
- Excise tax already computed

### 4. Connection Management
- Fresh connections per request (no connection pooling needed for small load)
- Proper cursor cleanup

### 5. Frontend Optimizations
- Chart caching (charts.trending, charts.category)
- Lazy tab loading (load data only when tab is clicked)
- Debounced search

## Configuration

### Database Connection
Located in `data_foundation/gross_profit.py`:

```python
DB_CONFIG = {
    'server': '10.1.10.105',      # SQL Server via Tailscale
    'user': 'amchranya',
    'password': '2000Akbar!',
    'database': 'GAWDB',
    'tds_version': '7.0',
    'timeout': 30,
    'login_timeout': 10
}
```

### Flask Server
Located in `gp_dashboard.py`:

```python
app.run(
    host='0.0.0.0',    # Bind to all interfaces (Tailscale accessible)
    port=8081,         # Different from main dashboard (8080)
    debug=False,       # Production mode
    threaded=True      # Support concurrent requests
)
```

## Running the Dashboard

### Start Server
```bash
cd /Users/akbarchranya/georgiadashboard
python3 gp_dashboard.py
```

### Expected Output
```
============================================================
Gross Profit Dashboard
============================================================

Starting server...
Dashboard: http://localhost:8081
Tailscale: http://100.126.106.37:8081

Press Ctrl+C to stop
============================================================
```

### Testing
```bash
# Test summary endpoint
curl "http://localhost:8081/api/gp/summary?start_date=2025-01-01&end_date=2025-10-15"

# Test categories endpoint
curl "http://localhost:8081/api/gp/categories?start_date=2025-01-01&end_date=2025-10-15"
```

## Key Design Decisions

### 1. Why Port 8081?
- Main dashboard runs on 8080
- Separate port allows independent operation
- Can run both dashboards simultaneously

### 2. Why No Pandas?
- Pandas + pymssql import order conflicts
- Pandas adds 5+ seconds to startup
- Direct pymssql is faster and simpler for this use case

### 3. Why GP_Daily_Summary Table?
- Category queries can be slow on raw transaction data
- Pre-aggregation provides instant results
- Trade-off: needs daily population (batch job)

### 4. Why PUVIEWEXCISETRANSACTION?
- Already exists in database
- Excise tax calculation is complex and pre-computed
- Accurate and validated by business

### 5. Why Separate from Main Dashboard?
- Focused use case (GP analysis only)
- Fast startup (no AI dependencies)
- Easy to deploy and maintain
- Can be shared with finance team without full dashboard access

## Limitations & Considerations

### 1. GP_Daily_Summary Population
- Requires running `populate_gp_summary.py` for category data
- Not automatically updated (manual or scheduled job)
- If not populated, category/department endpoints return empty

### 2. Date Range Performance
- Large date ranges (1+ year) can be slow on PUVIEWEXCISETRANSACTION
- Consider using GP_Daily_Summary for long-term analysis

### 3. Excise Tax Accuracy
- Depends on PUVIEWEXCISETRANSACTION view being up-to-date
- View definition managed by DBA

### 4. No Authentication
- Dashboard is open access (Tailscale network security only)
- Consider adding auth for sensitive financial data

## Future Enhancements

### Potential Improvements
1. **Real-time Updates**: WebSocket support for live GP updates
2. **Export Functionality**: CSV/Excel export of reports
3. **GP Alerts**: Email notifications for margin drops
4. **Comparison Views**: Period-over-period comparison
5. **Drill-downs**: Click category to see products
6. **User Preferences**: Save favorite timeframes/views
7. **Mobile Optimization**: Better responsive design
8. **Caching Layer**: Redis for frequently accessed data

### Integration Opportunities
1. **Main Dashboard Link**: Add GP widget to executive dashboard
2. **AR Dashboard**: Show GP alongside AR aging
3. **Sales Dashboard**: Integrate with sales velocity analysis
4. **Inventory System**: Show GP by inventory turns

## Troubleshooting

### Dashboard Not Loading
1. Check if process is running: `lsof -i :8081`
2. Check logs for errors
3. Verify Tailscale connection to database

### API Returns Empty Data
1. Check date range parameters
2. Verify GP_Daily_Summary is populated
3. Test direct SQL query in SSMS

### Slow Performance
1. Check GP_Daily_Summary population
2. Verify database indexes
3. Consider shorter date ranges
4. Check network latency to SQL Server

### Import Errors
1. Ensure TDS version set BEFORE pymssql import
2. Check pymssql installation
3. Verify Python 3.11 compatibility

## Related Documentation

- `PANDAS_PYMSSQL_FIX.md`: Import order issue resolution
- `FAST_STARTUP.md`: Performance optimization guide
- `CORRECT_EXCISE_TAX_STRUCTURE.md`: Excise tax calculation details
- `DATA_FOUNDATION_PLAN.md`: Overall data architecture

## Contact & Support

For questions or issues with the GP Dashboard:
- Check existing documentation in project root
- Review SQL views in SSMS (PUVIEWEXCISETRANSACTION)
- Test API endpoints with curl for debugging
