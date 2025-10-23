# Georgia Dashboard REST API

Flask-based REST API providing programmatic access to the GAWDB database.
Complements the Streamlit dashboard with API endpoints for integrations and automation.

## Features

- **Business Overview APIs**: Executive summary, sales performance, sales trends
- **Excise Tax Reporting**: PAID/COLLECTED breakdown, product-level tax details
- **Profitability Analysis**: Overall profitability, category/product breakdown, loss leaders
- **Health Monitoring**: Health check and ping endpoints
- **Flexible Date Ranges**: Predefined periods (today, 7d, 30d, MTD, YTD) or custom dates
- **CORS Support**: Cross-origin requests enabled
- **Response Caching**: Automatic caching for improved performance

## Installation

1. **Install dependencies:**
```bash
cd api
pip install -r requirements.txt
```

2. **Configure environment:**

Create a `.env` file in the project root with:
```bash
# SQL Server Connection
MSSQL_SERVER=10.1.10.105
MSSQL_USER=your_username
MSSQL_PASSWORD=your_password
MSSQL_DATABASE=GAWDB
MSSQL_TDS_VERSION=7.0
MSSQL_TIMEOUT=30

# API Configuration (optional)
API_PORT=5000
API_HOST=0.0.0.0
API_DEBUG=False

# Caching (optional)
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
```

## Running the API

### Development Mode

```bash
cd api
python app.py
```

The API will be available at `http://localhost:5000`

### Production Mode

Use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API Endpoints

### Health Check

```bash
# Check API and database status
GET /api/health

# Simple ping (no DB check)
GET /api/ping
```

### Business Overview

```bash
# Executive summary with KPIs
GET /api/business-overview/executive-summary?period=30d

# Sales performance by product/category
GET /api/business-overview/sales-performance?period=MTD&limit=50

# Daily sales trends
GET /api/business-overview/sales-trends?period=YTD
```

**Query Parameters:**
- `period`: today | 7d | 30d | MTD | YTD | last_month | this_week | etc.
- `start_date`: YYYY-MM-DD (custom start)
- `end_date`: YYYY-MM-DD (custom end)
- `limit`: Number of results (where applicable)

### Excise Tax

```bash
# Comprehensive tax report
GET /api/excise-tax/report?period=last_month

# Product-level tax details
GET /api/excise-tax/products?limit=50

# Tax category reference
GET /api/excise-tax/categories
```

### Profitability

```bash
# Overall profitability analysis
GET /api/profitability/analysis?period=30d

# Top products by profit
GET /api/profitability/top-products?limit=20

# Loss leaders (low margin products)
GET /api/profitability/loss-leaders?min_quantity=10
```

## Example Requests

### Using cURL

```bash
# Get executive summary for last 30 days
curl http://localhost:5000/api/business-overview/executive-summary?period=30d

# Get excise tax report for September 2025
curl "http://localhost:5000/api/excise-tax/report?start_date=2025-09-01&end_date=2025-09-30"

# Get top 10 products by profit
curl http://localhost:5000/api/profitability/top-products?limit=10
```

### Using Python

```python
import requests

# Get executive summary
response = requests.get(
    'http://localhost:5000/api/business-overview/executive-summary',
    params={'period': '30d'}
)
data = response.json()

print(f"Revenue: ${data['current_period']['revenue']:,.2f}")
print(f"Gross Profit: ${data['current_period']['gross_profit']:,.2f}")
print(f"Revenue Change: {data['changes']['revenue_change']:+.2f}%")
```

### Using JavaScript

```javascript
// Get sales performance
fetch('http://localhost:5000/api/business-overview/sales-performance?period=MTD')
  .then(response => response.json())
  .then(data => {
    console.log('Top Products:', data.top_products);
    console.log('Categories:', data.categories);
  });
```

## Response Format

All endpoints return JSON with the following structure:

**Success Response:**
```json
{
  "current_period": { ... },
  "comparison_period": { ... },
  "changes": { ... },
  "period_info": {
    "start_date": "2025-09-23",
    "end_date": "2025-10-23"
  }
}
```

**Error Response:**
```json
{
  "error": "Invalid parameters",
  "message": "Unknown period: invalid",
  "status_code": 400
}
```

## Architecture

```
api/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── routes/                     # API route blueprints
│   ├── health.py              # Health check endpoints
│   ├── business_overview.py  # Business overview endpoints
│   ├── excise_tax.py          # Excise tax endpoints
│   └── profitability.py       # Profitability endpoints
├── utils/                      # Utility modules
│   └── date_utils.py          # Date parsing and formatting
└── tests/                      # Test suite
    └── test_api.py            # API tests
```

## Data Sources

The API queries the same GAWDB SQL Server 2008 R2 database used by the Streamlit dashboard:

- **Transaction** (238K records) - Sales transactions
- **TransactionEntry** (4.7M records) - Line items
- **PUExciseEntry** (4.7M records) - Excise tax details
- **Item** (12.7K records) - Product catalog
- **Category** (83 records) - Product categories
- **Customer** (2.8K records) - Customer data

## Business Logic

### Excise Tax Calculation

The API uses the same excise tax logic as the Streamlit dashboard:

- **PAID**: Tax paid to state (from `PUExciseEntry` where `SubDescription3 LIKE '%PAID'`)
- **COLLECTED**: Tax collected from customers (from `PUExciseEntry` where `SubDescription3 LIKE '%COLL'`)
- **Formula**: `SUM(PriceC * Quantity)`

### Gross Profit Calculation

```
Gross Profit = Revenue - COGS - Excise Tax COLLECTED
```

- Excise PAID is already included in COGS
- Excise COLLECTED must be subtracted (owed to state)

### Period Comparisons

All business overview endpoints automatically calculate comparison periods:
- Same duration as current period, shifted back
- Example: Last 7 days compared to previous 7 days
- Percentage changes calculated for all metrics

## Performance

- **Response Caching**: 5-minute cache TTL (configurable)
- **Query Optimization**: Uses `WITH (NOLOCK)` hints for read queries
- **Typical Response Times**:
  - Health check: < 100ms
  - Executive summary (30d): < 1s
  - Sales performance (YTD): 2-3s
  - Excise tax report (monthly): 1-2s

## CORS Configuration

CORS is enabled for all `/api/*` endpoints. For production, update `app.py` to restrict origins:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://your-frontend-domain.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

## Authentication (Future)

Authentication is not currently implemented. For production deployment, consider adding:

- API key authentication
- JWT tokens
- Rate limiting
- IP whitelisting

## Monitoring

### Health Checks

```bash
# Full health check (includes DB)
curl http://localhost:5000/api/health

# Quick ping (no DB check)
curl http://localhost:5000/api/ping
```

### Logging

The API logs to stdout by default. Configure logging in production:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/georgia-api/api.log'),
        logging.StreamHandler()
    ]
)
```

## Testing

Run the test suite:

```bash
cd api
python -m pytest tests/
```

## Documentation

- **API Reference**: See `/docs/API_REFERENCE.md` for complete endpoint documentation
- **Database Schema**: See `/GAWDB_SYSTEM_ANALYSIS.md`
- **Excise Tax Details**: See `/EXCISE_TAX_SOLUTION.md`

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY src/ ./src/
COPY .env .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api.app:app"]
```

Build and run:
```bash
docker build -t georgia-api .
docker run -p 5000:5000 --env-file .env georgia-api
```

### systemd Service

Create `/etc/systemd/system/georgia-api.service`:

```ini
[Unit]
Description=Georgia Dashboard API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/georgia-dashboard
Environment="PATH=/opt/georgia-dashboard/venv/bin"
ExecStart=/opt/georgia-dashboard/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 api.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable georgia-api
sudo systemctl start georgia-api
```

## Troubleshooting

### Database Connection Issues

```bash
# Test SQL Server connection
python src/database/test_connection.py
```

### Port Already in Use

```bash
# Change port in .env
API_PORT=5001
```

### Import Errors

```bash
# Ensure src/ is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/turbo-spoon"
```

## Support

For issues, questions, or feature requests, refer to:
- API Reference Documentation: `/docs/API_REFERENCE.md`
- Streamlit Dashboard: Run `streamlit run app.py`
- Database Documentation: `GAWDB_SYSTEM_ANALYSIS.md`

## Version

**Version**: 1.0.0
**Last Updated**: October 23, 2025
**Status**: ✅ Phase 1 Complete (Core Business APIs)
