# Backend API Documentation

## Overview
This document details the backend API endpoints for the Georgia Dashboard system. The backend provides comprehensive analytics data through Flask endpoints connected to a live SQL Server database.

## Database Connection
- **Server**: 10.1.10.105 (SQL Server 2008 R2)
- **Connection Library**: pymssql with TDS 7.0 compatibility
- **Database**: GAWDB
- **Connection Management**: Pooled connections with semaphore control to prevent TDS assertion failures

## Profit Analysis APIs

### 1. Profit Analysis by Item
- **Endpoint**: `/api/profit/analysis/items`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "30d") - Time period for analysis
  - `limit` (default: 50) - Number of items to return
- **Description**: Returns profit analysis for individual items
- **Data Fields**: 
  - `item_description`: Product description
  - `total_revenue`: Total revenue for the period
  - `total_profit`: Total profit for the period
  - `total_cost`: Total cost for the period
- **Status**: ✅ Working (50 records returned)

### 2. Profit Analysis by Category  
- **Endpoint**: `/api/profit/analysis/categories`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "30d") - Time period for analysis
- **Description**: Returns profit analysis grouped by product categories
- **Data Fields**:
  - `category`: Product category name
  - `total_revenue`: Category total revenue
  - `total_profit`: Category total profit
  - `item_count`: Number of items in category
- **Status**: ✅ Working (49 records returned)

### 3. Profit Analysis by Customer
- **Endpoint**: `/api/profit/analysis/customers`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "30d") - Time period for analysis
  - `limit` (default: 30) - Number of customers to return
- **Description**: Returns profit analysis for top customers
- **Data Fields**:
  - `customer_name`: Customer name
  - `total_revenue`: Customer total revenue
  - `total_profit`: Customer total profit
  - `transaction_count`: Number of transactions
- **Status**: ✅ Working (30 records returned)

## Customer Segmentation APIs

### 1. Business Segments
- **Endpoint**: `/api/sales-analytics/customer-segments`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "365d") - Analysis period
- **Description**: Returns optimal customer segments based on 5-year active data
- **Data Fields**:
  - `segment_name`: Business segment name
  - `customer_count`: Number of customers in segment
  - `segment_revenue`: Total segment revenue
  - `avg_lifetime_value`: Average customer lifetime value
  - `avg_days_since_last_purchase`: Recency metric
- **Status**: ✅ Working (4 segments returned)

### 2. RFM Analysis
- **Endpoint**: `/api/customer-segmentation/rfm`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "365d") - Analysis period
- **Description**: RFM (Recency, Frequency, Monetary) customer segmentation
- **Status**: ✅ Working (500 customers returned)

### 3. Lifecycle Analysis
- **Endpoint**: `/api/customer-segmentation/lifecycle`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "365d") - Analysis period
- **Description**: Customer lifecycle stage analysis
- **Status**: ✅ Working (1000 customers returned)

### 4. Behavioral Segmentation
- **Endpoint**: `/api/customer-segmentation/behavioral`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "365d") - Analysis period
- **Description**: Behavioral patterns and purchasing habits
- **Status**: ✅ Working (500 customers returned)

### 5. Geographic Segmentation
- **Endpoint**: `/api/customer-segmentation/geographic`
- **Method**: GET
- **Description**: Geographic distribution of customers
- **Status**: ✅ Working (515 locations returned)

### 6. Segmentation Summary
- **Endpoint**: `/api/customer-segmentation/summary`
- **Method**: GET
- **Parameters**: 
  - `period` (default: "365d") - Analysis period
- **Description**: Aggregated summary of all segmentation data
- **Status**: ✅ Working

## Historical Analysis APIs

### 1. Historical Trends
- **Endpoint**: `/api/historical/trends`
- **Method**: GET
- **Parameters**: 
  - `start_year` (default: 2013) - Starting year for analysis
  - `end_year` (default: 2025) - Ending year for analysis
- **Description**: Historical business trends and analytics
- **Data Structure**:
  ```json
  {
    "date_range": {
      "start_year": 2013,
      "end_year": 2025
    },
    "trends": [],
    "accounts_receivable": [],
    "inventory": [],
    "analytics": {
      "status": "no_data" | "success",
      "total_revenue": number,
      "total_profit": number,
      "total_transactions": number
    },
    "cache_info": {
      "source": "comprehensive_cache",
      "last_updated": "timestamp"
    }
  }
  ```
- **Status**: ⚠️ Partial (Backend error: 'revenue' in comprehensive calculator)

## Historical Cache System

### Comprehensive Historical Calculator
- **File**: `comprehensive_historical_calculator.py`
- **Cache File**: `comprehensive_historical_cache.json`
- **Purpose**: Pre-calculated historical analytics for performance
- **Current Issue**: Error with 'revenue' field causing fallback to basic analysis
- **Cache Status**: ✅ Loaded but incomplete data structure

### Cache Features
- **Backup System**: Multiple backup formats (CSV, JSON, SQLite)
- **Automatic Fallback**: Falls back to real-time calculation if cache fails
- **61 Tables**: Complete backup of GAWDB database
- **17M+ Records**: Comprehensive data coverage

## Database Queries

### Query Types
1. **Sales Summary**: Daily/period sales totals
2. **Profit Analysis**: Margin calculations by item/category/customer
3. **Customer Analytics**: RFM, lifecycle, behavioral patterns
4. **AR Analytics**: Accounts receivable aging and trends
5. **Inventory Analysis**: Stock levels and movement

### Performance Optimizations
- **Connection Pooling**: Limited concurrent connections to prevent TDS failures
- **Query Caching**: Historical data cached for performance
- **Semaphore Control**: Maximum concurrent requests managed
- **Timeout Management**: 30-second query timeouts

## API Response Format

### Success Response
```json
{
  "status": "success",
  "data": [...],
  "message": "Query executed successfully",
  "count": number
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description",
  "error_code": "DB_ERROR" | "QUERY_FAILED" | "CONNECTION_ERROR"
}
```

## Current System Status

### Working APIs ✅
- All Profit Analysis endpoints (items, categories, customers)
- All Customer Segmentation endpoints (business segments, RFM, lifecycle, behavioral, geographic)
- Basic Historical Trends (with fallback)
- Database health checks
- Sales and AR analytics

### Known Issues ⚠️
- Historical comprehensive calculator has 'revenue' field error
- TDS assertion failures under high concurrent load (mitigated with connection pooling)
- Pandas SQLAlchemy warnings (functional but should be addressed)

### Database Connection Health
- **Status**: ✅ Connected and operational
- **Connection Test**: Passing
- **Query Success Rate**: >95% with retry logic

## Future Improvements

1. **Fix Historical Calculator**: Resolve 'revenue' field error in comprehensive cache
2. **SQLAlchemy Migration**: Replace pymssql with SQLAlchemy for better connection handling
3. **Enhanced Caching**: Implement Redis or similar for real-time cache management
4. **API Versioning**: Add version control to API endpoints
5. **Error Handling**: Enhanced error reporting and logging

---

**Last Updated**: August 4, 2025  
**Database Version**: SQL Server 2008 R2  
**API Version**: 1.0  
**Cache Version**: 2025.08.04 