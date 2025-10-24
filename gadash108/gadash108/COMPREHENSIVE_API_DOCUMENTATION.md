# Georgia Dashboard - Developer-Specific API Documentation

## Overview
This document provides **exact specifications** for all APIs in the Georgia Dashboard application. Every parameter type, validation rule, and response format is documented with precision for seamless integration.

**Database**: SQL Server 2008 R2 (GAWDB)  
**Framework**: Flask with Python 3.x  
**Authentication**: None (currently open access)  
**Base URL**: `http://localhost:8080` (default)

---

## 🔧 TECHNICAL SPECIFICATIONS

### Data Types Used
- `int`: 32-bit signed integer
- `float`: Double-precision floating point
- `string`: UTF-8 encoded text
- `boolean`: true/false
- `datetime`: ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssZ)
- `money`: Decimal with 2 decimal places (stored as float in JSON)
- `array`: JSON array
- `object`: JSON object

### Standard Response Format
All APIs follow this exact pattern:

**Success Response:**
```json
{
  "success": true,
  "status": "success",
  "data": {}, // Actual response data
  "message": "string|null", // Optional success message
  "timestamp": "2025-01-06T15:30:45.123Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "status": "error", 
  "error": "string", // Error message
  "code": "string|null", // Optional error code
  "timestamp": "2025-01-06T15:30:45.123Z"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

---

## 1. MAIN APPLICATION ROUTES

### Page Routes (GET Only)
| Route | Method | Description | Template | Auth Required |
|-------|--------|-------------|----------|---------------|
| `/` | GET | Executive Dashboard | `executive_dashboard.html` | No |
| `/ai-assistant` | GET | AI Assistant interface | `ai_assistant.html` | No |
| `/customer-ledger` | GET | Customer ledger interface | `customer_ledger.html` | No |
| `/sales-ops` | GET | Sales operations dashboard | `sales_ops.html` | No |
| `/suppliers` | GET | Supplier management dashboard | `suppliers.html` | No |
| `/wholesale-retail` | GET | Wholesale vs retail analysis | `wholesale_retail_improved.html` | No |
| `/gp-analysis` | GET | Gross profit analysis dashboard | `gp_analysis.html` | No |
| `/inventory` | GET | Inventory management dashboard | `inventory.html` | No |

### System API

#### API Status
```http
GET /api
```

**Parameters**: None

**Response**:
```json
{
  "status": "running",
  "message": "Georgia Dashboard API is running", 
  "ai_available": boolean,
  "endpoints": {
    "dashboard": "/",
    "ai_query": "/api/ai/query",
    "executive_summary": "/api/business-overview/executive-summary"
  }
}
```

**Field Specifications**:
- `status`: Always "running" if API is operational
- `ai_available`: `true` if OpenAI API key configured, `false` otherwise
- `endpoints`: Object with key endpoint URLs

---

## 2. AI ASSISTANT APIs

### Natural Language Query
```http
POST /api/ai/query
Content-Type: application/json
```

**Request Body** (Required):
```json
{
  "question": "string", // REQUIRED: 1-1000 chars, natural language question
  "stream": boolean     // OPTIONAL: default false, enables streaming response
}
```

**Validation Rules**:
- `question`: Required, non-empty string, max 1000 characters
- `stream`: Optional boolean, defaults to `false`

**Success Response** (stream=false):
```json
{
  "success": true,
  "query_id": "string", // UUID format: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  "sql": "string",      // Generated SQL query
  "results": [          // Array of result objects
    {
      "column1": "value1",
      "column2": 123.45,
      "column3": "2025-01-06T15:30:45.123Z"
    }
  ],
  "explanation": "string", // AI explanation of results
  "row_count": int,        // Number of rows returned
  "execution_time_ms": int // Query execution time in milliseconds
}
```

**Streaming Response** (stream=true):
```
Content-Type: text/event-stream

data: {"type": "feedback", "message": "Analyzing your question..."}

data: {"type": "feedback", "message": "Generating SQL query..."}

data: {"type": "result", "data": { /* same as success response */ }}

data: {"type": "complete"}
```

**Error Conditions**:
- `400`: Missing or empty question
- `500`: AI service unavailable (OpenAI API key not configured)
- `500`: SQL execution error

### Query Refinement
```http
POST /api/ai/refine
Content-Type: application/json
```

**Request Body**:
```json
{
  "instruction": "string",    // REQUIRED: refinement instruction
  "previous_sql": "string",   // OPTIONAL: SQL to refine
  "query_id": "string"        // OPTIONAL: ID of cached query to refine
}
```

**Validation Rules**:
- `instruction`: Required, non-empty string, max 500 characters
- Must provide either `previous_sql` OR `query_id`
- If `query_id` provided, it must exist in cache

**Response**: Same format as `/api/ai/query`

### Export Query Results
```http
GET /api/ai/export/{query_id}
```

**URL Parameters**:
- `query_id`: String, UUID format, must exist in cache

**Response**: 
- **Content-Type**: `text/csv`
- **Content-Disposition**: `attachment; filename=query_results_{query_id}.csv`
- **Body**: CSV formatted data

**Error Conditions**:
- `404`: Query ID not found or expired
- `500`: AI service unavailable

### Get Cached SQL
```http
GET /api/ai/sql/{query_id}
```

**URL Parameters**:
- `query_id`: String, UUID format

**Response**:
```json
{
  "success": true,
  "sql": "string",           // Original SQL query
  "timestamp": "datetime",   // When query was cached
  "expires_at": "datetime"   // Cache expiration time
}
```

**Error Conditions**:
- `404`: Query ID not found or expired

---

## 3. BUSINESS OVERVIEW APIs

### Executive Summary
```http
GET /api/business-overview/executive-summary
```

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "total_sales": float,        // Total sales amount (money type)
    "total_customers": int,      // Count of active customers
    "avg_transaction": float,    // Average transaction value
    "transaction_count": int,    // Total number of transactions
    "top_categories": [          // Top 5 performing categories
      {
        "category_name": "string",
        "sales_amount": float,
        "transaction_count": int,
        "percentage_of_total": float // 0.0 to 100.0
      }
    ],
    "recent_activity": [         // Last 10 transactions
      {
        "transaction_number": int,
        "customer_name": "string",
        "amount": float,
        "date": "datetime"
      }
    ],
    "period": "string"           // "last_30_days"
  }
}
```

**Field Specifications**:
- All monetary values are in USD with 2 decimal precision
- `percentage_of_total` ranges from 0.0 to 100.0
- `recent_activity` is ordered by date descending

### Sales Performance
```http
GET /api/business-overview/sales-performance
```

**Query Parameters** (All Optional):
- `period`: Enum["today", "yesterday", "week", "month", "year"] (default: "today")
- `start_date`: String, ISO date format "YYYY-MM-DD"
- `end_date`: String, ISO date format "YYYY-MM-DD"

**Parameter Validation**:
- If `start_date` provided, `end_date` is required
- `start_date` must be <= `end_date`
- Date range cannot exceed 365 days
- `period` parameter ignored if date range provided

**Response**:
```json
{
  "success": true,
  "data": {
    "period_sales": float,           // Total sales for period
    "transaction_count": int,        // Number of transactions
    "avg_transaction": float,        // Average transaction value
    "unique_customers": int,         // Distinct customers in period
    "comparison": {
      "vs_previous_period": float,   // Difference from previous period
      "percentage_change": float,    // Percentage change (-100.0 to +∞)
      "trend": "string"              // "up", "down", "flat"
    },
    "daily_breakdown": [             // Daily sales within period
      {
        "date": "YYYY-MM-DD",
        "sales": float,
        "transactions": int
      }
    ],
    "period_info": {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD", 
      "days_in_period": int
    }
  }
}
```

**Error Conditions**:
- `400`: Invalid date format or date range

### Inventory Health
```http
GET /api/business-overview/inventory-health
```

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "total_items": int,              // Total items in inventory
    "low_stock_count": int,          // Items below reorder point
    "overstock_count": int,          // Items above max stock level
    "deadstock_count": int,          // Items with no sales in 90+ days
    "negative_quantity_count": int,  // Items with negative quantities
    "total_value": float,            // Total inventory value at cost
    "total_retail_value": float,     // Total inventory value at retail
    "turnover_rate": float,          // Annual inventory turnover rate
    "categories": [                  // Inventory by category
      {
        "category_name": "string",
        "item_count": int,
        "total_value": float,
        "percentage_of_total": float
      }
    ],
    "alerts": [                      // Inventory alerts
      {
        "type": "string",            // "low_stock", "overstock", "deadstock"
        "severity": "string",        // "high", "medium", "low"
        "count": int,
        "message": "string"
      }
    ]
  }
}
```

**Field Specifications**:
- `turnover_rate`: Calculated as COGS / Average Inventory Value
- `percentage_of_total`: 0.0 to 100.0
- Alert `severity` determines UI display priority

### Customer Intelligence
```http
GET /api/business-overview/customer-intelligence
```

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "total_customers": int,          // All customers in database
    "active_customers": int,         // Customers with transactions in last 90 days
    "new_customers": int,            // Customers added in last 30 days
    "returning_customers": int,      // Customers with 2+ transactions
    "customer_segments": [           // RFM-based segments
      {
        "segment_name": "string",    // "Champions", "At Risk", etc.
        "customer_count": int,
        "avg_order_value": float,
        "total_value": float,
        "percentage": float          // 0.0 to 100.0
      }
    ],
    "top_customers": [               // Top 10 by lifetime value
      {
        "customer_id": int,
        "customer_name": "string",
        "lifetime_value": float,
        "last_purchase": "datetime",
        "total_orders": int,
        "avg_order_value": float
      }
    ],
    "churn_risk": {
      "high_risk_count": int,        // Customers likely to churn
      "medium_risk_count": int,
      "low_risk_count": int
    }
  }
}
```

**Field Specifications**:
- `active_customers`: Based on transactions in last 90 days
- `new_customers`: First transaction within last 30 days
- Customer segments use standard RFM methodology

### Performance Trends
- **Endpoint**: `/api/business-overview/performance-trends`
- **Method**: GET
- **Description**: Performance trend analysis
- **Output**:
```json
{
  "status": "success",
  "data": {
    "sales_trend": array,
    "customer_trend": array,
    "inventory_trend": array,
    "profit_trend": array
  }
}
```

### Sales Trends
- **Endpoint**: `/api/business-overview/sales-trends`
- **Method**: GET
- **Description**: Sales trend data
- **Output**:
```json
{
  "status": "success",
  "data": {
    "daily_sales": array,
    "monthly_sales": array,
    "category_trends": array,
    "seasonal_patterns": array
  }
}
```

---

## 4. INVENTORY MANAGEMENT APIs

### Low Stock Items
- **Endpoint**: `/api/inventory-health/low-stock`
- **Method**: GET
- **Description**: Get items with low stock levels
- **Input Parameters**:
  - `threshold` (optional): Stock level threshold (default: 10)
- **Output**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "item_id": number,
        "description": "string",
        "current_stock": number,
        "reorder_point": number,
        "supplier": "string"
      }
    ],
    "total_count": number
  }
}
```

### Dead Stock Analysis
- **Endpoint**: `/api/inventory-health/deadstock`
- **Method**: GET
- **Description**: Items with no sales activity
- **Input Parameters**:
  - `days` (optional): Days without sales (default: 90)
- **Output**:
```json
{
  "status": "success",
  "data": {
    "items": array,
    "total_value": number,
    "total_count": number
  }
}
```

### Overstock Items
- **Endpoint**: `/api/inventory-health/overstock`
- **Method**: GET
- **Description**: Items with excessive stock levels
- **Output**: Similar to low-stock format

### Negative Quantity Items
- **Endpoint**: `/api/inventory-health/negative-quantity`
- **Method**: GET
- **Description**: Items with negative quantities
- **Output**: Array of items with negative stock

### Inventory Velocity
- **Endpoint**: `/api/inventory-health/velocity`
- **Method**: GET
- **Description**: Inventory turnover metrics
- **Output**:
```json
{
  "status": "success",
  "data": {
    "fast_movers": array,
    "slow_movers": array,
    "velocity_metrics": {
      "avg_turnover": number,
      "total_velocity": number
    }
  }
}
```

### Category Values
- **Endpoint**: `/api/inventory-health/category-values`
- **Method**: GET
- **Description**: Inventory values by category
- **Output**:
```json
{
  "status": "success",
  "data": {
    "categories": [
      {
        "category": "string",
        "total_value": number,
        "item_count": number,
        "percentage": number
      }
    ]
  }
}
```

### Item Details
- **Endpoint**: `/api/item/<int:item_id>/details`
- **Method**: GET
- **Description**: Detailed information for a specific item
- **Input**: item_id (URL parameter)
- **Output**:
```json
{
  "status": "success",
  "data": {
    "item_info": object,
    "sales_history": array,
    "purchase_history": array,
    "current_stock": number
  }
}
```

---

## 5. FINANCIAL APIs

### AR Aging Analysis
- **Endpoint**: `/api/financial/ar-aging`
- **Method**: GET
- **Description**: Accounts receivable aging analysis
- **Output**:
```json
{
  "status": "success",
  "data": {
    "aging_buckets": {
      "current": number,
      "30_days": number,
      "60_days": number,
      "90_days": number,
      "over_90": number
    },
    "total_ar": number,
    "customer_count": number
  }
}
```

### AR Aging Optimized
- **Endpoint**: `/api/financial/ar-aging-optimized`
- **Method**: GET
- **Description**: Optimized AR aging analysis with better performance
- **Output**: Enhanced version of standard AR aging

### NSF Details
- **Endpoint**: `/api/financial/nsf-details`
- **Method**: GET
- **Description**: Non-sufficient funds details
- **Output**:
```json
{
  "status": "success",
  "data": {
    "nsf_transactions": array,
    "total_nsf_amount": number,
    "affected_customers": number
  }
}
```

---

## 6. SALES OPERATIONS APIs

### Sales Overview
- **Endpoint**: `/api/sales-ops/overview`
- **Method**: GET
- **Description**: Sales operations overview
- **Input Parameters**:
  - `date` (optional): Specific date for analysis
- **Output**:
```json
{
  "status": "success",
  "data": {
    "daily_sales": number,
    "transaction_count": number,
    "avg_transaction": number,
    "top_items": array,
    "hourly_breakdown": array
  }
}
```

### Sales Detail
- **Endpoint**: `/api/sales-ops/sales-detail`
- **Method**: GET
- **Description**: Detailed sales data
- **Input Parameters**:
  - `start_date` (optional): Start date for range
  - `end_date` (optional): End date for range
- **Output**: Detailed sales transactions array

### Payments Detail
- **Endpoint**: `/api/sales-ops/payments-detail`
- **Method**: GET
- **Description**: Payment transaction details
- **Output**: Detailed payment transactions array

---

## 7. SUPPLIER MANAGEMENT APIs

### Suppliers Overview
- **Endpoint**: `/api/suppliers/overview`
- **Method**: GET
- **Description**: Supplier management overview
- **Output**:
```json
{
  "status": "success",
  "data": {
    "total_suppliers": number,
    "active_suppliers": number,
    "pending_orders": number,
    "total_payables": number
  }
}
```

### Suppliers List
- **Endpoint**: `/api/suppliers/list`
- **Method**: GET
- **Description**: List of all suppliers
- **Output**: Array of supplier objects

### Purchase Orders
- **Endpoint**: `/api/suppliers/purchase-orders`
- **Method**: GET
- **Description**: Purchase orders list
- **Output**: Array of purchase order objects

### Inventory Alerts
- **Endpoint**: `/api/suppliers/inventory-alerts`
- **Method**: GET
- **Description**: Inventory reorder alerts
- **Output**: Array of items needing reorder

### Top Products
- **Endpoint**: `/api/suppliers/top-products`
- **Method**: GET
- **Description**: Top ordered products by supplier
- **Output**: Array of top products with supplier info

---

## 8. WHOLESALE/RETAIL ANALYSIS APIs

### Analysis Overview
- **Endpoint**: `/api/wholesale-retail/analysis`
- **Method**: GET
- **Description**: Wholesale vs retail analysis
- **Output**:
```json
{
  "status": "success",
  "data": {
    "wholesale_sales": number,
    "retail_sales": number,
    "wholesale_percentage": number,
    "retail_percentage": number,
    "comparison_metrics": object
  }
}
```

### YTD Comparison
- **Endpoint**: `/api/wholesale-retail/ytd-comparison`
- **Method**: GET
- **Description**: Year-to-date comparison
- **Output**: YTD wholesale vs retail metrics

### Wholesale Customers
- **Endpoint**: `/api/wholesale-retail/wholesale-customers`
- **Method**: GET
- **Description**: Wholesale customer details
- **Output**: Array of wholesale customer objects

### Monthly Breakdown
- **Endpoint**: `/api/wholesale-retail/monthly/<int:year>`
- **Method**: GET
- **Description**: Monthly breakdown by year
- **Input**: year (URL parameter)
- **Output**: Monthly wholesale/retail breakdown

---

## 9. GROSS PROFIT ANALYSIS APIs

### GP Executive Summary
- **Endpoint**: `/api/gp/executive-summary`
- **Method**: GET
- **Description**: Gross profit executive summary
- **Output**:
```json
{
  "status": "success",
  "data": {
    "total_gp": number,
    "gp_percentage": number,
    "gp_trend": array,
    "top_categories": array
  }
}
```

### GP Trending
- **Endpoint**: `/api/gp/trending`
- **Method**: GET
- **Description**: GP trending analysis
- **Output**: GP trend data over time

### GP by Categories
- **Endpoint**: `/api/gp/categories`
- **Method**: GET
- **Description**: Gross profit by categories
- **Output**: Array of categories with GP metrics

### GP by Customers
- **Endpoint**: `/api/gp/customers`
- **Method**: GET
- **Description**: Gross profit by customers
- **Output**: Array of customers with GP metrics

### GP by Products
- **Endpoint**: `/api/gp/products`
- **Method**: GET
- **Description**: Gross profit by products
- **Output**: Array of products with GP metrics

### GP Opportunities
- **Endpoint**: `/api/gp/opportunities`
- **Method**: GET
- **Description**: GP improvement opportunities
- **Output**: Array of improvement opportunities

---

## 10. ACCOUNTS RECEIVABLE (AR) DASHBOARD APIs

### AR Summary
```http
GET /api/ar/summary
```

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "total_ar": float,               // Total outstanding AR balance
    "customer_count": int,           // Customers with AR balances
    "aging_summary": {
      "current": float,              // 0-30 days
      "days_31_60": float,           // 31-60 days
      "days_61_90": float,           // 61-90 days
      "over_90": float               // 90+ days
    },
    "recent_activity": [             // Last 10 AR transactions
      {
        "customer_id": int,
        "customer_name": "string",
        "transaction_type": "string", // "SALE", "PAYMENT", "ADJUSTMENT"
        "amount": float,
        "date": "datetime",
        "reference": "string"
      }
    ],
    "statistics": {
      "avg_balance": float,          // Average AR balance per customer
      "largest_balance": float,      // Highest individual balance
      "oldest_invoice_days": int     // Days since oldest unpaid invoice
    }
  }
}
```

### AR Customers
```http
GET /api/ar/customers
```

**Query Parameters** (All Optional):
- `min_balance`: Float, minimum balance to include (default: 0.0)
- `days_overdue`: Integer, minimum days overdue (default: none)
- `sort_by`: Enum["balance_desc", "balance_asc", "name_asc", "days_desc"] (default: "balance_desc")
- `limit`: Integer, max results to return (default: 100, max: 1000)
- `offset`: Integer, pagination offset (default: 0)

**Parameter Validation**:
- `min_balance`: Must be numeric, can be negative
- `days_overdue`: Must be positive integer if provided
- `limit`: 1 to 1000
- `offset`: Must be non-negative

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "customer_id": int,            // Customer.ID
      "customer_name": "string",     // Company or FirstName LastName
      "account_number": "string",    // Customer account number
      "current_balance": float,      // Current AR balance
      "credit_limit": float,         // Customer credit limit
      "days_overdue": int,           // Days since oldest unpaid invoice
      "last_payment": "datetime|null", // Last payment date
      "last_sale": "datetime|null",  // Last sale date
      "phone": "string",             // Phone number
      "email": "string",             // Email address
      "aging": {
        "current": float,            // 0-30 days balance
        "days_31_60": float,         // 31-60 days balance
        "days_61_90": float,         // 61-90 days balance
        "over_90": float             // 90+ days balance
      }
    }
  ],
  "pagination": {
    "total_records": int,            // Total matching records
    "returned_records": int,         // Records in this response
    "offset": int,                   // Current offset
    "has_more": boolean              // More records available
  }
}
```

**Field Specifications**:
- `customer_name`: Uses Company field if available, otherwise FirstName + LastName
- `days_overdue`: Calculated from oldest unpaid invoice date
- All monetary values in USD with 2 decimal precision

### Customer AR Details
- **Endpoint**: `/api/ar/customer/<int:customer_id>`
- **Method**: GET
- **Description**: Get specific customer AR details
- **Input**: customer_id (URL parameter)
- **Output**: Detailed customer AR information

### AR Aging
- **Endpoint**: `/api/ar/aging`
- **Method**: GET
- **Description**: Get AR aging analysis
- **Output**: Detailed aging buckets and analysis

### Customer Groups V2
- **Endpoint**: `/api/ar/groups/v2/summary`
- **Method**: GET
- **Description**: Get optimized customer groups summary
- **Output**: Customer grouping summary with lazy loading

### Group Preview
- **Endpoint**: `/api/ar/groups/v2/<group_key>/preview`
- **Method**: GET
- **Description**: Get preview of specific customer group
- **Input**: group_key (URL parameter)
- **Output**: Preview of customer group data

### Group Full Details
- **Endpoint**: `/api/ar/groups/v2/<group_key>/full`
- **Method**: GET
- **Description**: Get full details of specific customer group
- **Input**: group_key (URL parameter)
- **Output**: Complete customer group data

### Group Search
- **Endpoint**: `/api/ar/groups/v2/search`
- **Method**: GET
- **Description**: Search customer groups
- **Input Parameters**:
  - `q`: Search query string
- **Output**: Matching customer groups

### Cache Statistics
- **Endpoint**: `/api/ar/groups/v2/cache/stats`
- **Method**: GET
- **Description**: Get cache statistics for customer groups
- **Output**: Cache performance metrics

### Clear Cache
- **Endpoint**: `/api/ar/groups/v2/cache/clear`
- **Method**: POST
- **Description**: Clear customer groups cache
- **Output**: Cache clear confirmation

### Cash Flow Prediction
- **Endpoint**: `/api/ar/cashflow/simple`
- **Method**: GET
- **Description**: Get cash flow predictions
- **Input Parameters**:
  - `days` (optional): Number of days to predict (default: 30)
- **Output**:
```json
{
  "success": boolean,
  "data": {
    "predictions": array,
    "total_expected": number,
    "confidence_level": string
  }
}
```

### Risk Analysis
- **Endpoint**: `/api/ar/risks`
- **Method**: GET
- **Description**: Get customer risk analysis
- **Output**: Array of customers with risk scores

### AR Export
- **Endpoint**: `/api/ar/export/<export_type>`
- **Method**: GET
- **Description**: Export AR data
- **Input**: export_type ("csv", "excel")
- **Output**: File download

### AR Metrics
- **Endpoint**: `/api/ar/metrics`
- **Method**: GET
- **Description**: Get AR performance metrics
- **Output**: Key AR performance indicators

### Model Accuracy
- **Endpoint**: `/api/ar/model-accuracy`
- **Method**: GET
- **Description**: Get prediction model accuracy metrics
- **Output**: Model performance statistics

### NSF Returns
- **Endpoint**: `/api/ar/nsf-returns`
- **Method**: GET
- **Description**: Get NSF return analysis
- **Output**: NSF transaction analysis

### NSF Data
- **Endpoint**: `/api/ar/nsf-data`
- **Method**: GET
- **Description**: Get detailed NSF data
- **Output**: Detailed NSF transaction data

### PD Checks
- **Endpoint**: `/api/ar/pd-checks`
- **Method**: GET
- **Description**: Get post-dated check information
- **Output**: Post-dated check data

---

## 11. CUSTOMER SEGMENTATION APIs

### Segmentation Overview
- **Endpoint**: `/api/segmentation/overview`
- **Method**: GET
- **Description**: Get comprehensive segmentation overview
- **Output**:
```json
{
  "success": boolean,
  "data": {
    "total_customers": number,
    "segments": array,
    "rfm_summary": object,
    "key_insights": array
  }
}
```

### RFM Analysis
- **Endpoint**: `/api/segmentation/rfm-analysis`
- **Method**: GET
- **Description**: Get detailed RFM analysis
- **Output**: RFM (Recency, Frequency, Monetary) analysis data

### Segment Details
- **Endpoint**: `/api/segmentation/segment-details/<segment>`
- **Method**: GET
- **Description**: Get details for specific customer segment
- **Input**: segment (URL parameter)
- **Output**: Detailed segment information

### Customer List
- **Endpoint**: `/api/segmentation/customer-list`
- **Method**: GET
- **Description**: Get segmented customer list
- **Input Parameters**:
  - `segment` (optional): Filter by segment
  - `limit` (optional): Number of results
- **Output**: Array of customers with segment information

### Segmentation Actions
- **Endpoint**: `/api/segmentation/actions`
- **Method**: GET
- **Description**: Get recommended actions for segments
- **Output**: Array of recommended marketing actions

### Segmentation Trends
- **Endpoint**: `/api/segmentation/trends`
- **Method**: GET
- **Description**: Get segmentation trend analysis
- **Output**: Trend data for customer segments

### At-Risk Customers
- **Endpoint**: `/api/segmentation/at-risk`
- **Method**: GET
- **Description**: Get at-risk customer analysis
- **Output**: Array of at-risk customers with recommendations

### Segmentation Export
- **Endpoint**: `/api/segmentation/export`
- **Method**: GET
- **Description**: Export segmentation data
- **Input Parameters**:
  - `format`: "csv" or "excel"
- **Output**: File download

### Segmentation Health Check
- **Endpoint**: `/api/segmentation/health-check`
- **Method**: GET
- **Description**: Get segmentation system health check
- **Output**: System health and data quality metrics

---

## 12. CUSTOMER LEDGER APIs

### Customer List
- **Endpoint**: `/api/ledger/customers`
- **Method**: GET
- **Description**: Get list of customers for ledger
- **Input Parameters**:
  - `search` (optional): Search term
  - `limit` (optional): Number of results
- **Output**: Array of customer objects

### Generate Ledger
- **Endpoint**: `/api/ledger/generate/<int:customer_id>`
- **Method**: GET
- **Description**: Generate customer ledger
- **Input**: customer_id (URL parameter)
- **Output**:
```json
{
  "success": boolean,
  "data": {
    "customer_info": object,
    "ledger": array,
    "summary": object
  }
}
```

### Export Ledger
- **Endpoint**: `/api/ledger/export/<int:customer_id>`
- **Method**: GET
- **Description**: Export customer ledger as Excel
- **Input**: customer_id (URL parameter)
- **Output**: Excel file download

### Verify Ledger
- **Endpoint**: `/api/ledger/verify/<int:customer_id>`
- **Method**: GET
- **Description**: Verify ledger accuracy
- **Input**: customer_id (URL parameter)
- **Output**: Verification results

---

## 13. COHORT ANALYSIS APIs

### Cohort Analysis
- **Endpoint**: `/api/cohort/analysis`
- **Method**: GET
- **Description**: Get cohort analysis data
- **Output**: Cohort analysis with retention metrics

### Cohort Waterfall
- **Endpoint**: `/api/cohort/waterfall`
- **Method**: GET
- **Description**: Get cohort waterfall analysis
- **Output**: Waterfall chart data for cohorts

### Cohort Velocity
- **Endpoint**: `/api/cohort/velocity`
- **Method**: GET
- **Description**: Get cohort velocity metrics
- **Output**: Velocity analysis for customer cohorts

### Cohort Aging
- **Endpoint**: `/api/cohort/aging`
- **Method**: GET
- **Description**: Get cohort aging analysis
- **Output**: Aging analysis for customer cohorts

### Cohort DSO
- **Endpoint**: `/api/cohort/dso`
- **Method**: GET
- **Description**: Get Days Sales Outstanding by cohort
- **Output**: DSO metrics by customer cohort

### Cohort Predictions
- **Endpoint**: `/api/cohort/predictions`
- **Method**: GET
- **Description**: Get cohort-based predictions
- **Output**: Predictive analytics for cohorts

### Cohort Pattern Summary
- **Endpoint**: `/api/cohort/pattern-summary`
- **Method**: GET
- **Description**: Get cohort pattern summary
- **Output**: Summary of cohort patterns and insights

---

## 14. CATEGORY ANALYSIS APIs

### Category Analysis Data
- **Endpoint**: `/api/category-analysis/data`
- **Method**: GET
- **Description**: Get comprehensive category analysis
- **Output**:
```json
{
  "success": boolean,
  "data": {
    "categories": array,
    "performance_metrics": object,
    "trends": array
  }
}
```

### Category Top Products
- **Endpoint**: `/api/category-analysis/top-products/<category_name>`
- **Method**: GET
- **Description**: Get top products for specific category
- **Input**: category_name (URL parameter)
- **Output**: Array of top products in category

---

## 15. CUSTOMER BALANCE APIs

### Customer Balance
```http
GET /api/customer/{customer_id}/balance
```

**URL Parameters**:
- `customer_id`: Integer, must be valid customer ID from Customer table

**Parameter Validation**:
- `customer_id`: Required, positive integer, must exist in database

**Response**:
```json
{
  "success": true,
  "data": {
    "customer_id": int,              // Validated customer ID
    "current_balance": float,        // Current AR balance (+ = customer owes)
    "methodology": "AR_HISTORY_SUM", // Always this value
    "confidence": "HIGH",            // Always "HIGH" for this method
    "last_updated": "datetime",      // When balance was calculated
    "currency": "USD"                // Always USD
  }
}
```

**Field Specifications**:
- `current_balance`: Positive = customer owes money, Negative = customer credit
- `methodology`: Uses AccountReceivableHistory table summation
- `confidence`: Always "HIGH" as this uses authoritative data source

**Error Conditions**:
- `400`: Invalid customer_id format (not integer)
- `404`: Customer ID not found in database
- `500`: Database connection error

### Comprehensive Balance
- **Endpoint**: `/api/customer/<int:customer_id>/balance/comprehensive`
- **Method**: GET
- **Description**: Get comprehensive balance analysis
- **Input**: customer_id (URL parameter)
- **Output**: Detailed balance analysis with all methodologies

### Balance Timeline
- **Endpoint**: `/api/customer/<int:customer_id>/balance/timeline`
- **Method**: GET
- **Description**: Get complete balance timeline
- **Input**: 
  - customer_id (URL parameter)
  - `start_date` (optional): Filter start date
  - `end_date` (optional): Filter end date
- **Output**: Timeline of balance changes

### Balance Verification
- **Endpoint**: `/api/customer/<int:customer_id>/balance/verification`
- **Method**: GET
- **Description**: Verify balance accuracy using multiple methods
- **Input**: customer_id (URL parameter)
- **Output**: Balance verification results

### Balance Events
- **Endpoint**: `/api/customer/<int:customer_id>/balance/events`
- **Method**: GET
- **Description**: Get decoded business events from AR History
- **Input**: 
  - customer_id (URL parameter)
  - `event_type` (optional): Filter by event type
- **Output**: Array of business events

### Balance Patterns
- **Endpoint**: `/api/customer/<int:customer_id>/balance/patterns`
- **Method**: GET
- **Description**: Get customer balance and payment patterns
- **Input**: customer_id (URL parameter)
- **Output**: Pattern analysis for customer

### AR Breakdown
- **Endpoint**: `/api/customer/<int:customer_id>/balance/ar-breakdown`
- **Method**: GET
- **Description**: Get detailed AR breakdown with aging
- **Input**: customer_id (URL parameter)
- **Output**: Detailed AR aging breakdown

### Balance Summary
- **Endpoint**: `/api/customer/<int:customer_id>/balance/summary`
- **Method**: GET
- **Description**: Get balance summary statistics
- **Input**: customer_id (URL parameter)
- **Output**: Statistical summary of customer balance

### Multiple Customer Balances
```http
GET /api/customers/balances?customer_ids={ids}
```

**Query Parameters**:
- `customer_ids`: String, comma-separated integers, max 100 IDs

**Parameter Validation**:
- `customer_ids`: Required, format "123,456,789"
- Maximum 100 customer IDs per request
- All IDs must be positive integers
- Invalid IDs are skipped with error noted in response

**Example Request**:
```
GET /api/customers/balances?customer_ids=123,456,789
```

**Response**:
```json
{
  "success": true,
  "data": {
    "customers": [
      {
        "customer_id": 123,
        "balance": 150.75,
        "status": "success"
      },
      {
        "customer_id": 456,
        "balance": -25.00,
        "status": "success"
      },
      {
        "customer_id": 789,
        "balance": null,
        "status": "error",
        "error": "Customer not found"
      }
    ],
    "summary": {
      "total_requested": 3,
      "successful": 2,
      "failed": 1
    }
  }
}
```

**Field Specifications**:
- Each customer object includes `status` field
- Failed lookups still return object with error details
- `balance` is `null` for failed lookups

**Error Conditions**:
- `400`: Missing customer_ids parameter
- `400`: Invalid customer_ids format
- `400`: More than 100 customer IDs requested

### Balance Methodology
- **Endpoint**: `/api/balance-methodology`
- **Method**: GET
- **Description**: Get information about balance calculation methodology
- **Output**: Methodology documentation and information

### All Balances Summary
- **Endpoint**: `/api/customers/balances/summary`
- **Method**: GET
- **Description**: Get summary of all customer balances
- **Output**: Statistical summary of all customer balances

### Comprehensive Customer Overview
- **Endpoint**: `/api/customer/<int:customer_id>/overview`
- **Method**: GET
- **Description**: Get comprehensive customer overview with all details
- **Input**: customer_id (URL parameter)
- **Output**: Complete customer profile with all metrics

---

## 16. TRANSACTION DETAIL APIs

### Transaction Details
```http
GET /api/transaction/{transaction_number}/details
```

**URL Parameters**:
- `transaction_number`: Integer, must be valid transaction number

**Parameter Validation**:
- `transaction_number`: Required, positive integer, must exist in Transaction table

**Response**:
```json
{
  "success": true,
  "data": {
    "transaction_info": {
      "transaction_number": int,       // Original transaction number
      "date_time": "datetime|null",    // Transaction timestamp
      "batch_number": int|null,        // POS batch number
      "customer_id": int|null,         // Customer ID (null for walk-in)
      "customer_name": "string",       // Customer name or "Walk-in"
      "customer_phone": "string",      // Phone number or empty string
      "customer_address": "string",    // Address or empty string
      "customer_city": "string",       // City or empty string
      "customer_state": "string",      // State or empty string
      "customer_zip": "string",        // ZIP code or empty string
      "subtotal": float,               // Pre-tax amount
      "tax": float,                    // Sales tax amount
      "total": float,                  // Final total amount
      "comment": "string",             // Transaction comment or empty
      "cashier_id": int|null,          // Cashier ID
      "store_id": int|null             // Store ID
    },
    "line_items": [
      {
        "line_id": int,                // TransactionEntry.ID
        "item_id": int,                // Item.ID
        "lookup_code": "string",       // Item lookup code or empty
        "description": "string",       // Item description or empty
        "quantity": float,             // Quantity sold
        "price": float,                // Unit price
        "line_total": float,           // quantity * price
        "cost": float,                 // Unit cost (0.0 if not available)
        "line_profit": float,          // (quantity * price) - (quantity * cost)
        "department": "string",        // Department name or empty
        "category": "string"           // Category name or empty
      }
    ],
    "tender_details": [
      {
        "tender_id": int|null,         // Tender type ID
        "amount": float,               // Payment amount
        "description": "string"        // Payment method description
      }
    ],
    "summary": {
      "item_count": int,               // Number of line items
      "total_quantity": float,         // Sum of all quantities
      "total_profit": float           // Sum of all line profits
    }
  }
}
```

**Field Specifications**:
- All monetary values in USD with 2 decimal precision
- `null` values indicate missing/unavailable data
- Empty strings used instead of null for text fields
- `line_profit` may be 0.0 if cost data unavailable

**Error Conditions**:
- `400`: Invalid transaction_number format
- `404`: Transaction not found
- `500`: Database error

### AR Details
- **Endpoint**: `/api/ar/<int:ar_id>/details`
- **Method**: GET
- **Description**: Get detailed AR/invoice information
- **Input**: ar_id (URL parameter)
- **Output**:
```json
{
  "success": boolean,
  "data": {
    "ar_info": object,
    "history": array,
    "transaction_details": object
  }
}
```

---

## 17. PROFESSIONAL EXCEL EXPORT APIs

### Professional Excel Export
- **Endpoint**: `/api/customer/<int:customer_id>/export/professional`
- **Method**: GET
- **Description**: Export professional, business-ready Excel report
- **Input**: customer_id (URL parameter)
- **Output**: Professional Excel file download

### Detailed Excel Export
- **Endpoint**: `/api/customer/<int:customer_id>/export/detailed`
- **Method**: GET
- **Description**: Export detailed Excel report with everything
- **Input**: customer_id (URL parameter)
- **Output**: Detailed Excel file download with multiple sheets

---

## 18. SALES DASHBOARD V2 APIs

### Dashboard Summary
- **Endpoint**: `/api/v2/sales/dashboard-summary`
- **Method**: GET
- **Description**: Get comprehensive dashboard summary with all KPIs
- **Input Parameters**:
  - `period` (optional): "today", "yesterday", "week", "month"
- **Output**:
```json
{
  "period": "string",
  "date_range": object,
  "kpis": object,
  "trends": object,
  "comparisons": object
}
```

### Real-time Feed
- **Endpoint**: `/api/v2/sales/real-time-feed`
- **Method**: GET
- **Description**: Get real-time sales feed for live updates
- **Output**: Real-time sales data stream

---

## 19. CUSTOMER 360 VIEW API

### Customer 360 View
- **Endpoint**: `/api/customer/<int:customer_id>/360`
- **Method**: GET
- **Description**: Get complete 360-degree customer view
- **Input**: customer_id (URL parameter)
- **Output**: Comprehensive customer profile with all data points

---

## 20. RISK ANALYSIS APIs

### Customer Risk Analysis
- **Endpoint**: `/api/risk/customer/<int:customer_id>`
- **Method**: GET
- **Description**: Get risk analysis for specific customer
- **Input**: customer_id (URL parameter)
- **Output**: Risk assessment and scoring

### Portfolio Risk Analysis
- **Endpoint**: `/api/risk/portfolio`
- **Method**: GET
- **Description**: Get portfolio-wide risk analysis
- **Output**: Overall risk metrics and analysis

---

## 🔧 DEVELOPER INTEGRATION GUIDE

### Request Headers
All POST requests must include:
```
Content-Type: application/json
```

### Parameter Encoding
- URL parameters: URL-encoded
- Query parameters: URL-encoded
- JSON body: UTF-8 encoded JSON

### Date/Time Handling
**Input Formats Accepted**:
- ISO 8601: `2025-01-06T15:30:45.123Z`
- Date only: `2025-01-06`
- SQL format: `2025-01-06 15:30:45`

**Output Format** (Always):
- ISO 8601 with timezone: `2025-01-06T15:30:45.123Z`

### Monetary Values
- **Input**: Accept integers, floats, or strings
- **Output**: Always float with 2 decimal precision
- **Currency**: Always USD
- **Precision**: Rounded to nearest cent

### Boolean Values
- **Input**: `true`, `false`, `1`, `0`, `"true"`, `"false"`
- **Output**: Always `true` or `false`

### Null Handling
- **Database NULL**: Returned as `null` in JSON
- **Empty Strings**: Returned as `""` (not converted to null)
- **Zero Values**: Returned as `0` or `0.0` (not converted to null)

### Error Response Details
```json
{
  "success": false,
  "status": "error",
  "error": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE", // Optional
  "details": {                           // Optional
    "field": "parameter_name",
    "value": "invalid_value",
    "expected": "description_of_expected_format"
  },
  "timestamp": "2025-01-06T15:30:45.123Z"
}
```

### Pagination Pattern
For endpoints supporting pagination:
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total_records": int,      // Total records matching query
    "returned_records": int,   // Records in this response
    "offset": int,             // Current offset (0-based)
    "limit": int,              // Requested limit
    "has_more": boolean,       // More records available
    "next_offset": int|null    // Offset for next page (null if no more)
  }
}
```

### Rate Limiting
Currently no rate limiting implemented. For production deployment, consider:
- 1000 requests/hour per IP for GET endpoints
- 100 requests/hour per IP for POST endpoints
- 10 requests/minute for export endpoints

### Caching Headers
APIs may return caching headers:
```
Cache-Control: public, max-age=300  // 5 minutes for data endpoints
Cache-Control: no-cache             // For real-time endpoints
ETag: "abc123"                      // For conditional requests
```

### Content-Type Responses
- **JSON APIs**: `application/json; charset=utf-8`
- **CSV Exports**: `text/csv; charset=utf-8`
- **Excel Exports**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Streaming**: `text/event-stream`

---

## 🔒 SECURITY & AUTHENTICATION

### Current Security Status
**⚠️ WARNING**: Currently NO authentication implemented. All endpoints are publicly accessible.

### Input Validation
All endpoints implement:
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Prevention**: HTML encoding of output
- **Type Validation**: Strict type checking on all parameters
- **Range Validation**: Numeric bounds checking
- **Length Validation**: String length limits enforced

### Recommended Production Security
```javascript
// Example API key authentication (not currently implemented)
fetch('/api/customer/123/balance', {
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  }
})
```

**Recommended Implementation**:
1. **API Key Authentication** - Simple token-based auth
2. **JWT Tokens** - For session management
3. **Role-Based Access** - Different permissions per endpoint
4. **Rate Limiting** - Prevent abuse
5. **HTTPS Only** - Encrypt all traffic
6. **IP Whitelisting** - Restrict access by IP

---

## 🚨 ERROR HANDLING REFERENCE

### HTTP Status Code Meanings
- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameters or request format
- `404 Not Found`: Resource (customer, transaction, etc.) not found
- `500 Internal Server Error`: Database error or system failure

### Common Error Scenarios

#### Invalid Customer ID
```json
{
  "success": false,
  "status": "error",
  "error": "Customer ID 99999 not found",
  "error_code": "CUSTOMER_NOT_FOUND",
  "timestamp": "2025-01-06T15:30:45.123Z"
}
```

#### Invalid Parameter Format
```json
{
  "success": false,
  "status": "error", 
  "error": "Invalid date format. Expected YYYY-MM-DD, got '2025-13-45'",
  "error_code": "INVALID_DATE_FORMAT",
  "details": {
    "parameter": "start_date",
    "provided_value": "2025-13-45",
    "expected_format": "YYYY-MM-DD"
  }
}
```

#### Database Connection Error
```json
{
  "success": false,
  "status": "error",
  "error": "Database connection failed. Please try again.",
  "error_code": "DATABASE_CONNECTION_ERROR",
  "retry_after": 30
}
```

#### Missing Required Parameter
```json
{
  "success": false,
  "status": "error",
  "error": "Missing required parameter: customer_ids",
  "error_code": "MISSING_PARAMETER",
  "details": {
    "parameter": "customer_ids",
    "description": "Comma-separated list of customer IDs required"
  }
}
```

### Error Recovery Strategies
1. **Retry Logic**: For 500 errors, retry after delay
2. **Fallback Data**: Some endpoints provide cached data on DB failure
3. **Partial Success**: Bulk operations return partial results with error details
4. **Graceful Degradation**: Missing optional data doesn't cause failure

---

## ⚡ PERFORMANCE OPTIMIZATION

### Response Time Expectations
- **Simple Queries** (customer lookup): < 100ms
- **Complex Analytics** (sales performance): < 2 seconds  
- **Large Exports** (Excel generation): < 30 seconds
- **AI Queries**: 2-10 seconds depending on complexity

### Caching Strategy
```javascript
// Example: Check cache headers for client-side caching
const response = await fetch('/api/business-overview/executive-summary');
const cacheControl = response.headers.get('Cache-Control');
// Response: "public, max-age=300" (5 minutes)
```

**Cached Endpoints**:
- Business overview APIs: 5 minutes
- Customer lists: 2 minutes
- Static data (categories, items): 1 hour

### Pagination Best Practices
```javascript
// Efficient pagination pattern
let offset = 0;
const limit = 100;
let hasMore = true;

while (hasMore) {
  const response = await fetch(`/api/ar/customers?limit=${limit}&offset=${offset}`);
  const data = await response.json();
  
  // Process data.data array
  processCustomers(data.data);
  
  hasMore = data.pagination.has_more;
  offset = data.pagination.next_offset;
}
```

### Large Dataset Handling
- **Streaming**: Use `stream=true` for AI queries
- **Chunking**: Process large customer lists in batches of 100
- **Async Processing**: Long-running exports return immediately with job ID

### Database Query Optimization
- All queries use proper indexes
- Complex queries are pre-optimized
- Query execution time logged for monitoring
- Automatic query plan caching

---

## 🚀 DEPLOYMENT CONFIGURATION

### Environment Variables
```bash
# Required
DATABASE_SERVER=10.1.10.105
DATABASE_NAME=GAWDB
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password

# Optional
PORT=8080
DEBUG=false
OPENAI_API_KEY=your_openai_api_key_here...  # For AI Assistant functionality
LOG_LEVEL=INFO
```

### System Requirements
- **Python**: 3.8+
- **Database**: SQL Server 2008 R2+ 
- **Memory**: 2GB minimum, 4GB recommended
- **Storage**: 1GB for application, additional for logs/cache

### Dependencies Installation
```bash
pip install -r requirements.txt
```

**Key Dependencies**:
- `Flask==2.3.3`
- `pymssql==2.2.8` 
- `pandas==2.1.1`
- `openai==1.3.5` (optional, for AI features)

### Configuration Files
- `config/database.py`: Database connection settings
- `config/logging_config.py`: Logging configuration
- `requirements.txt`: Python dependencies

### Health Check Endpoint
```http
GET /api
```
Use this endpoint to verify deployment status.

### Startup Command
```bash
python run.py
# Or for production:
gunicorn --bind 0.0.0.0:8080 --workers 4 run:app
```

---

## CHANGELOG & VERSION HISTORY

- **v9.18**: Current version with comprehensive API coverage
- **Features Added**: AI Assistant, Customer Segmentation, Advanced Analytics
- **Performance Improvements**: Caching, Query optimization
- **Bug Fixes**: Balance calculation accuracy, Export functionality

---

This documentation covers all available APIs and functions in the Georgia Dashboard application. For specific implementation details, refer to the source code in the respective modules and files.
