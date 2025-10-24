# 🔧 Georgia Auto Dashboard - Technical Documentation

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Current Application Structure](#current-application-structure)
- [Module Documentation](#module-documentation)
- [API Documentation](#api-documentation)
- [AI Assistant Integration](#ai-assistant-integration)
- [Database Schema](#database-schema)
- [Development Guidelines](#development-guidelines)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

## Current Application Structure

The Georgia Dashboard codebase now contains multiple application variants:

### 1. `dashboard_app.py` - **Primary Business Dashboard**
- **Purpose**: Clean, business-focused dashboard with AI assistant
- **Features**:
  - **Executive Dashboard Frontend**: Modern, responsive web interface
  - Executive summary with KPI tracking and trend analysis
  - Sales performance analysis
  - Inventory health monitoring
  - Customer intelligence
  - Performance trends analysis
  - AI-powered SQL query assistant
- **Frontend**: `templates/executive_dashboard.html` - Comprehensive executive summary
- **Target Users**: Business executives and managers
- **AI Integration**: Full OpenAI GPT-4 integration with streaming responses

### 2. `simple_app.py` - **Legacy/Fallback Dashboard**
- **Purpose**: Simplified dashboard for basic operations
- **Features**: Basic sales data, fallback functionality
- **Template Dependencies**: References legacy templates (many deleted)
- **Status**: Partially functional, needs template updates

### 3. `advanced_app.py` - **Technical/Analytics Dashboard**
- **Purpose**: Advanced analytics and detailed reporting
- **Features**: Complex analytics, historical trends
- **Status**: Advanced features for technical users

### 4. Core Support Modules
- **`ai_sql_assistant.py`**: OpenAI GPT-4 integration for natural language queries
- **`database_pymssql.py`**: Robust database connectivity with connection pooling
- **`modules/analytics_engine.py`**: Core business intelligence engine
- **`advanced_analytics.py`**: Advanced statistical analysis

### 5. Database Discovery Tools
- **`database_discovery.py`**: Schema exploration
- **`database_focused_discovery.py`**: Focused table analysis
- **`comprehensive_historical_calculator.py`**: Historical data processing

### File Structure Status
```
✅ Active Core Files:
- dashboard_app.py (PRIMARY)
- templates/executive_dashboard.html (FRONTEND)
- database_pymssql.py
- ai_sql_assistant.py
- modules/analytics_engine.py
- DATABASE_CATALOG_FOR_AI.md

⚠️ Legacy Files:
- simple_app.py (needs template updates)
- app.py (DELETED)

❌ Deleted Files:
- Most templates/ files
- Most static/ files
- Various legacy dashboard versions
```

### System Architecture
The Georgia Dashboard has evolved into a multi-application architecture with specialized endpoints:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend APIs   │    │   Database      │
│                 │    │                  │    │                 │
│ Multiple Apps   │◄──►│ dashboard_app.py │◄──►│  SQL Server     │
│ Templates       │    │ simple_app.py    │    │  2008 R2        │
│ (Removed)       │    │ advanced_app.py  │    │  GAWDB          │
│                 │    │ ai_sql_assistant │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Architectural Changes
- **Multiple Application Variants**: Three distinct Flask applications serving different needs
- **AI Integration**: OpenAI GPT-4 integration for natural language database queries
- **Business Intelligence Focus**: Clean, business-focused endpoints for executive dashboard
- **Template Cleanup**: Legacy templates removed, streamlined architecture

### Component Responsibilities

#### 1. Frontend Layer (`templates/` + `static/`)
- **unified_dashboard.html**: Main dashboard interface with responsive design
- **dashboard.js**: Dynamic data loading, chart rendering, UI interactions
- **styles.css**: Modern responsive styling with mobile support

#### 2. Backend API Layer (`app.py`)
- **Flask Application**: RESTful API endpoints for data access
- **Route Organization**: Logically grouped endpoints (sales, profit, AR, inventory)
- **Error Handling**: Comprehensive error recovery and status reporting
- **Response Format**: Consistent JSON API responses with status codes

#### 3. Business Logic Layer (`modules/analytics_engine.py`)
- **UnifiedAnalyticsEngine**: Core business intelligence calculations
- **Data Processing**: Complex aggregations, trend analysis, forecasting
- **Business Rules**: Tobacco excise tax compliance, category consolidation
- **Caching**: Query result caching for performance optimization

#### 4. Data Access Layer (`database_pymssql.py`)
- **SQLServerConnection**: Robust database connectivity with retry logic
- **Connection Management**: Connection pooling, automatic reconnection
- **Query Execution**: Parameterized queries with SQL injection protection
- **Error Recovery**: Comprehensive error handling and logging

#### 5. Deployment Layer (`api/index.py`, `unified_dashboard.py`)
- **Vercel Compatibility**: Serverless function deployment support
- **Legacy Support**: Backward compatibility with existing imports
- **Environment Detection**: Development vs. production configuration

## Module Documentation

### UnifiedAnalyticsEngine (`modules/analytics_engine.py`)

The core business intelligence engine that handles all data analysis and calculations.

**Key Features**:
- Direct SQL Server connection with retry logic
- Business intelligence calculations
- Tobacco excise tax compliance
- Trend analysis and comparisons
- Caching for performance optimization
- Comprehensive error handling

**Architecture**:
- Inherits from database connection layer
- Implements business-specific calculations
- Provides consistent data formatting
- Handles complex aggregations and analytics

**Performance Optimizations**:
- Connection pooling
- Query result caching  
- Efficient SQL query construction
- Minimal data transfer

#### Key Methods

##### Sales Analytics
```python
def get_sales_summary(time_filter='today'):
    """
    Get comprehensive sales summary with trend analysis
    
    Args:
        time_filter (str): 'today', 'yesterday', '7d', '30d', 'mtd', 'ytd', or custom range
    
    Returns:
        dict: Sales metrics with trend indicators and comparison data
    """
```

##### Profit Analysis
```python
def get_profit_analysis_by_category(time_filter='30d'):
    """
    Analyze profit performance by product category
    
    Features:
        - Tobacco excise tax cost uplifts (CIGARS: +23%, LT-TAX-COLLECTED: +10%)
        - Category consolidation logic
        - Trend analysis vs. previous period
    
    Returns:
        dict: Profit analysis with category breakdowns and trends
    """
```

##### Accounts Receivable
```python
def get_ar_aging(period='30d'):
    """
    Comprehensive AR aging analysis
    
    Aging Buckets:
        - Current (0-30 days)
        - 31-60 days
        - 61-90 days  
        - 91-120 days
        - Over 120 days
    
    Returns:
        dict: AR aging analysis with risk assessment
    """
```

### Database Connection (`database_pymssql.py`)

Robust database connectivity with connection pooling and comprehensive error handling.

#### Key Classes

**`SQLServerConnection`**: Main database interface
- Connection pooling for performance
- Automatic reconnection on failures
- Thread-safe operations with locking
- Comprehensive error handling and logging
- SQL Server 2008 R2 compatibility

**`ConnectionPool`**: Connection pool management
- Pool size management
- Connection health monitoring
- Automatic cleanup of stale connections

**Custom Exception Classes**:
- `DatabaseConnectionError`: Connection failures
- `DatabaseQueryError`: Query execution failures  
- `ConnectionPoolError`: Pool management issues
- `DatabaseTimeoutError`: Timeout-related errors

#### Connection Configuration
```python
# Environment Variables
DB_SERVER = os.getenv('DB_SERVER', '10.1.10.105')
DB_NAME = os.getenv('DB_NAME', 'GAWDB')
DB_USER = os.getenv('DB_USER', 'dashboard')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# SQL Server 2008 R2 Compatibility
os.environ['TDSVER'] = '7.0'
CONNECTION_TIMEOUT = 30
QUERY_TIMEOUT = 60
MAX_RETRIES = 3
```

#### Error Handling Strategy
```python
# Connection Error Patterns
CONNECTION_ERRORS = [
    'timeout', 'dead', 'not connected', 'connection',
    'unknown error', 'datastream processing', 'bad token'
]

# Retry Logic: Exponential backoff
retry_delay = 2 ** (retry_count - 1)  # 2, 4, 8 seconds

# Thread-safe database operations
with db_lock:
    result = db.execute_query(query, params)
```

## API Documentation

### Business Overview Endpoints (dashboard_app.py)

#### GET `/api/business-overview/executive-summary`
Comprehensive executive dashboard with KPI tracking and trend analysis.

**Parameters:**
- `period` (optional): 'today', '7d', '30d', 'MTD', 'YTD'

**Response:**
```json
{
    "revenue": {
        "current": 15420.50,
        "trend": 8.5,
        "comparison": "vs 30 days ago"
    },
    "profit": {
        "current": 3245.75,
        "margin": 21.0,
        "trend": 12.3
    },
    "transactions": {
        "current": 89,
        "avg_ticket": 173.26,
        "trend": -2.1
    },
    "customers": {
        "current": 45,
        "avg_visits": 1.98,
        "trend": 5.7
    },
    "cashflow": {
        "ar_balance": 12450.00,
        "payments_received": 8750.25,
        "customers_with_balance": 23
    }
}
```

#### GET `/api/business-overview/sales-performance`
Detailed sales performance analysis by products and categories.

**Parameters:**
- `period` (optional): Time period for analysis

**Response:**
```json
{
    "top_products": [
        {
            "item_id": 12345,
            "name": "Product Name",
            "revenue": 2450.75,
            "units_sold": 125,
            "gross_profit": 450.25
        }
    ],
    "categories": [
        {
            "category_name": "TOBACCO",
            "revenue": 8750.50,
            "units_sold": 340,
            "product_count": 25,
            "gross_profit": 1650.75
        }
    ]
}
```

#### GET `/api/business-overview/inventory-health`
Inventory health monitoring including low stock and deadstock analysis.

**Response:**
```json
{
    "low_stock": [
        {
            "item_id": 12345,
            "name": "Product Name",
            "current_qty": 3,
            "selling_price": 15.99,
            "unit_cost": 12.50,
            "inventory_value": 37.50,
            "last_sold": "2025-08-05T14:30:00"
        }
    ],
    "deadstock": [],
    "fast_movers": [],
    "slow_movers": [],
    "category_values": []
}
```

#### GET `/api/business-overview/customer-intelligence`
Customer analysis including top customers and new customer acquisition.

**Response:**
```json
{
    "top_customers": [
        {
            "customer_id": 1001,
            "customer_name": "ABC Store Inc",
            "revenue": 5420.75,
            "transaction_count": 15,
            "avg_transaction": 361.38,
            "account_balance": 1250.00,
            "last_visit": "2025-08-07T10:15:00"
        }
    ],
    "new_customers": []
}
```

#### GET `/api/business-overview/performance-trends`
Week-over-week comparisons and profit center analysis.

**Response:**
```json
{
    "wow_comparison": {
        "sales_change": 8.5,
        "transaction_change": -2.1,
        "customer_change": 12.3,
        "avg_ticket_change": 10.7,
        "current_sales": 15420.50,
        "previous_sales": 14200.25
    },
    "profit_centers": [
        {
            "center_name": "TOBACCO",
            "revenue": 8750.50,
            "gross_profit": 1650.75,
            "profit_margin": 18.9,
            "transactions": 45
        }
    ]
}
```

#### GET `/api/item/<item_id>/details`
Detailed item information for drill-down analysis.

**Response:**
```json
{
    "item_info": {
        "id": 12345,
        "description": "Product Name",
        "lookup_code": "SKU123",
        "price": 15.99,
        "cost": 12.50,
        "quantity": 25,
        "last_sold": "2025-08-05T14:30:00",
        "category": "TOBACCO",
        "department": "CONVENIENCE"
    },
    "sales_history": [],
    "recent_transactions": []
}
```

## AI Assistant Integration

The dashboard includes a sophisticated AI assistant powered by OpenAI GPT-4 for natural language database queries.

### AI Assistant Endpoints

#### POST `/api/ai/query`
Process natural language business questions using AI.

**Request Body:**
```json
{
    "question": "What were our top selling products last month?",
    "stream": false
}
```

**Response:**
```json
{
    "status": "success",
    "sql_query": "SELECT TOP 10 i.Description...",
    "explanation": "This query finds the top-selling products...",
    "results": [
        {"product": "Product A", "sales": 1250.00},
        {"product": "Product B", "sales": 980.50}
    ],
    "query_id": "uuid-12345",
    "execution_time": 0.85
}
```

**Streaming Response** (when `stream: true`):
Server-sent events with real-time feedback:
```
data: {"type": "feedback", "message": "Analyzing your question..."}
data: {"type": "feedback", "message": "Generating SQL query..."}
data: {"type": "result", "data": {...}}
data: {"type": "complete"}
```

#### GET `/api/ai/export/<query_id>`
Export AI query results as CSV file.

**Response:**
CSV file download with query results.

### AI Assistant Features

1. **Natural Language Processing**: Converts business questions to SQL
2. **Database Schema Awareness**: Uses comprehensive database catalog
3. **SQL Server 2008 R2 Compatibility**: Generates compatible queries
4. **Business Rule Application**: Applies tobacco tax calculations
5. **Result Caching**: Caches results for export functionality
6. **Streaming Responses**: Real-time query processing feedback
7. **Error Handling**: Graceful error handling and user feedback

### Supported Query Types

- **Sales Analysis**: Revenue trends, period comparisons
- **Product Performance**: Best/worst sellers, inventory analysis
- **Customer Insights**: Top customers, buying patterns
- **Financial Reports**: Profit margins, cost analysis
- **Operational Metrics**: Transaction volumes, average tickets

### AI Configuration

```python
# Required Environment Variable
OPENAI_API_KEY=your_openai_api_key_here..."

# Model Configuration
model = "gpt-4"
max_tokens = 2000
temperature = 0.1  # Low temperature for consistent SQL generation
```

### Legacy Endpoints (simple_app.py)

The simple_app.py provides basic dashboard functionality with template rendering:

### Primary Dashboard Frontend Routes (dashboard_app.py)

#### Main Routes
- `GET /` - **Executive Dashboard** (templates/executive_dashboard.html)
  - Modern, responsive executive summary interface
  - Real-time KPI tracking with trend indicators
  - Time period filtering (Today, 7D, 30D, MTD, YTD, Custom)
  - Revenue, profit, transactions, customers, cash flow metrics
- `GET /api` - API status and available endpoints

### Legacy Template Routes (simple_app.py)
- `GET /` - Main dashboard (working_dashboard.html) 
- `GET /simple` - Simple dashboard fallback
- `GET /analytics` - Analytics page
- `GET /customers` - Customer insights
- `GET /inventory` - Inventory management
- `GET /financial` - Financial reports

**Note**: Many template files have been deleted, causing some routes to fail. Use dashboard_app.py instead.

## Database Schema

### Database Overview
- **Database Name**: GAWDB
- **Server**: SQL Server 2008 R2
- **Total Records**: 4.6+ million transaction line items
- **Date Range**: 2012-12-07 to present (13+ years)
- **Business Type**: C-store distributor/wholesaler Point of Sale System

### Core Tables

#### [dbo].[Transaction] - Transaction Headers
```sql
[dbo].[Transaction] (
    TransactionNumber INT PRIMARY KEY,    -- Unique transaction ID
    Time DATETIME,                        -- Transaction timestamp
    CustomerID INT,                       -- Links to Customer.ID
    CashierID INT,                        -- Employee who processed sale
    Total MONEY,                          -- Final transaction total
    SalesTax MONEY,                       -- Tax amount
    BatchNumber INT,                      -- Daily batch grouping
    StoreID INT,                          -- Store identifier
    Comment NVARCHAR(255),                -- Transaction comments (delivery, pickup)
    ReferenceNumber NVARCHAR(50),         -- Reference or order number
    Status INT                            -- Transaction status code
)
```

#### dbo.TransactionEntry - Transaction Line Items
```sql
dbo.TransactionEntry (
    TransactionNumber INT,                -- Links to Transaction.TransactionNumber
    ItemID INT,                           -- Links to Item.ID
    Quantity DECIMAL(10,4),               -- Quantity sold/returned
    Price MONEY,                          -- Selling price per unit
    Cost MONEY,                           -- Cost per unit
    SalesTax MONEY,                       -- Tax amount for this line
    Comment NVARCHAR(255),                -- Line item comments
    DetailID INT,                         -- Unique line item ID
    ItemType INT,                         -- Item type code
    Taxable BIT                           -- Whether item is taxable
)
```

#### dbo.Customer - Customer Master
```sql
dbo.Customer (
    ID INT PRIMARY KEY,                   -- Unique customer ID
    Company NVARCHAR(100),                -- Company name
    FirstName NVARCHAR(50),               -- First name
    LastName NVARCHAR(50),                -- Last name
    AccountBalance MONEY,                 -- Current account balance
    Address NVARCHAR(100),                -- Street address
    City NVARCHAR(50),                    -- City
    State NVARCHAR(2),                    -- State code
    Zip NVARCHAR(10),                     -- ZIP code
    Phone NVARCHAR(20),                   -- Phone number
    CustomerType INT,                     -- Customer type code
    PriceLevel INT,                       -- Pricing level
    TaxExempt BIT                         -- Tax exempt status
)
```

#### dbo.Item - Product Master
```sql
dbo.Item (
    ID INT PRIMARY KEY,                   -- Unique item ID
    ItemLookupCode NVARCHAR(20),          -- SKU/Barcode
    Description NVARCHAR(100),            -- Product description
    Price MONEY,                          -- Current selling price
    Cost MONEY,                           -- Current cost
    Quantity DECIMAL(10,4),               -- Current inventory quantity
    CategoryID INT,                       -- Links to Category.ID
    DepartmentID INT,                     -- Links to Department.ID
    LastSold DATETIME,                    -- Last sale date
    LastReceived DATETIME,                -- Last received date
    Inactive BIT,                         -- Whether item is inactive
    ItemType INT,                         -- Item type code
    Taxable BIT                           -- Whether item is taxable
)
```

#### dbo.Category - Product Categories
```sql
dbo.Category (
    ID INT PRIMARY KEY,                   -- Unique category ID
    Name NVARCHAR(50),                    -- Category name
    DepartmentID INT,                     -- Links to Department.ID
    Code NVARCHAR(10)                     -- Category code
)
```

#### dbo.Payment - Payment Records
```sql
dbo.Payment (
    ID INT PRIMARY KEY,                   -- Unique payment ID
    CustomerID INT,                       -- Links to Customer.ID
    Amount MONEY,                         -- Payment amount
    Time DATETIME,                        -- Payment timestamp
    PaymentType INT,                      -- Payment method code
    ReferenceNumber NVARCHAR(50),         -- Check/reference number
    Comment NVARCHAR(255)                 -- Payment comments
)
```

### Business Logic Rules

#### Tobacco Excise Tax Compliance
Special cost calculations for tobacco products:
```sql
-- Gross profit calculation with tobacco tax uplifts
SUM(te.Price * te.Quantity - 
    CASE 
        WHEN c.Name = 'CIGARS' THEN te.Cost * te.Quantity * 1.23     -- +23%
        WHEN c.Name = 'LT-TAX-COLLECTED' THEN te.Cost * te.Quantity * 1.10  -- +10%
        ELSE te.Cost * te.Quantity
    END) as gross_profit
```

#### SQL Server 2008 R2 Compatibility Requirements
- Use `CAST(date_field AS DATE)` instead of `FORMAT()` function
- Use `%s` parameterization, not `?`
- Always bracket reserved keywords: `[dbo].[Transaction]`
- Avoid complex CTEs and window functions
- Use `ISNULL()` instead of `COALESCE()` when possible
- Set TDS version to 7.0 for compatibility

#### Connection String Configuration
```python
# SQL Server 2008 R2 Compatibility Settings
TDS_VERSION = '7.0'                    # TDS protocol version
CONNECTION_TIMEOUT = 30                # Connection timeout in seconds  
QUERY_TIMEOUT = 60                     # Query timeout in seconds
MAX_RETRIES = 3                        # Maximum retry attempts
```

## Development Guidelines

### Code Organization
1. **Primary Application**: `dashboard_app.py` - main business dashboard
2. **Modular Structure**: Keep business logic in `modules/analytics_engine.py`
3. **AI Integration**: `ai_sql_assistant.py` - natural language processing
4. **Database Layer**: All database operations through `database_pymssql.py`
5. **Error Handling**: Comprehensive error handling at each layer
6. **Thread Safety**: Use decorators for database operation locking

### Adding New Features
1. **Primary Application**: Use `dashboard_app.py` as the main application
2. **Analytics**: Add methods to `UnifiedAnalyticsEngine` class in `modules/`
3. **AI Queries**: Extend `AISQLAssistant` for new query types
4. **API Endpoints**: Create new Flask routes in `dashboard_app.py`
5. **Database**: Update `DATABASE_CATALOG_FOR_AI.md` for schema changes
6. **Documentation**: Update this file with new API endpoints

### Application Selection Guide
- **Production Use**: `dashboard_app.py` (recommended)
- **Legacy Support**: `simple_app.py` (requires template fixes)
- **Advanced Analytics**: `advanced_app.py` (technical users)

### AI Assistant Development
1. **Schema Updates**: Modify `DATABASE_CATALOG_FOR_AI.md`
2. **Query Templates**: Add business rule examples
3. **Error Handling**: Extend exception handling in `ai_sql_assistant.py`
4. **Testing**: Use natural language queries against actual database

### Performance Considerations
1. **Database Queries**: Use indexes, limit result sets, parameterized queries
2. **Connection Pooling**: Implemented in `database_pymssql.py`
3. **Caching**: Query result caching in AI assistant and analytics engine
4. **Thread Safety**: Database operations use global locking
5. **AI Queries**: Streaming responses for better user experience
6. **SQL Optimization**: SQL Server 2008 R2 compatible queries only

### Security Considerations
1. **API Key Management**: OpenAI API key in environment variables
2. **Database Credentials**: Store in environment variables, not code
3. **SQL Injection**: Use parameterized queries exclusively
4. **Input Validation**: Validate all user inputs in AI assistant
5. **Error Messages**: Don't expose sensitive database information
6. **CORS**: Properly configure CORS for frontend access

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Error: "Connection timeout" or "Database not available"
```
**Solution:** 
- Check database server status (10.1.10.105)
- Verify SQL Server 2008 R2 is running
- Check credentials: dashboard user permissions
- Ensure TDS version 7.0 is set: `os.environ['TDSVER'] = '7.0'`
- Check pymssql installation: `pip install pymssql`
- Review connection pool status
- Check network connectivity and firewall rules

#### AI Assistant Errors
```
Error: "AI Assistant not available" or "OpenAI API key not configured"
```
**Solution:**
- Set OpenAI API key: `export OPENAI_API_KEY=your_openai_api_key_here..."`
- Check API key validity and credits
- Verify internet connectivity for OpenAI API
- Review `DATABASE_CATALOG_FOR_AI.md` file existence
- Check AI assistant initialization in application startup

#### Template Missing Errors (simple_app.py)
```
Error: "TemplateNotFound: working_dashboard.html"
```
**Solution:**
- Many templates were deleted during cleanup
- Use `dashboard_app.py` instead (no templates required)
- Or restore needed templates from backup
- Update template references in simple_app.py routes

#### Data Display Issues
```
Issue: Dashboard shows "No data available"
```  
**Solution:**
- Check browser console for API errors
- Verify database connectivity via `/api/database/status`
- Review server logs for query execution errors
- Test API endpoints directly via browser/Postman

### Performance Issues
```
Issue: Slow dashboard loading times
```
**Solution:**
- Review database query performance
- Check for missing database indexes
- Implement query result caching
- Optimize frontend data loading patterns

### Debug Endpoints

#### dashboard_app.py Debug Endpoints
- `GET /` - API status and available endpoints
- Database connectivity tested through live queries
- AI availability status included in root endpoint

#### Diagnostic Commands
```bash
# Test database connection
python test_connection_pymssql.py

# Test AI assistant
python -c "from ai_sql_assistant import AISQLAssistant; ai = AISQLAssistant(); print('AI OK')"

# Check environment variables
echo $OPENAI_API_KEY
echo $DB_PASSWORD

# Test main application
python dashboard_app.py
```

### Monitoring and Logs
- Application logs: Python logging module
- Database query logs: Detailed query execution tracking
- AI query logs: Natural language processing steps
- Error logs: Comprehensive error tracking with stack traces
- Performance logs: Query execution times and caching hits

### Quick Start Guide

1. **Environment Setup**:
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export DB_PASSWORD="your-db-password"
   pip install -r requirements.txt
   ```

2. **Start Primary Dashboard**:
   ```bash
   python dashboard_app.py
   ```

3. **Access Endpoints**:
   - API Status: `http://localhost:8080/`
   - Executive Summary: `http://localhost:8080/api/business-overview/executive-summary`
   - AI Query: `POST http://localhost:8080/api/ai/query`

4. **Test AI Assistant**:
   ```bash
   curl -X POST http://localhost:8080/api/ai/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What were our sales yesterday?"}'
   ```

---

**Last Updated:** August 2025  
**Maintainer:** AI Assistant (Claude)  
**Primary Application:** dashboard_app.py  
**Database:** GAWDB (SQL Server 2008 R2)  
**AI Integration:** OpenAI GPT-4