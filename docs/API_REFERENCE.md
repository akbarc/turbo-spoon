# GEORGIA DASHBOARD - COMPLETE API REFERENCE GUIDE

> **Every API Endpoint: What It Does, How It Works, Problems & Solutions**

**Database:** GAWDB (SQL Server 2008 R2)
**Data Coverage:** 13+ years, 4.6M+ transaction records, 12K+ products, 2.8K+ customers
**Server:** 10.1.10.105
**Document Date:** October 23, 2025

---

## 📋 TABLE OF CONTENTS

1. [System & Health APIs](#1-system--health-apis)
2. [AI Assistant APIs](#2-ai-assistant-apis)
3. [Business Overview APIs](#3-business-overview-apis)
4. [Inventory Management APIs](#4-inventory-management-apis)
5. [Financial/AR APIs](#5-financialar-apis)
6. [Sales Operations APIs](#6-sales-operations-apis)
7. [Supplier Management APIs](#7-supplier-management-apis)
8. [Wholesale/Retail APIs](#8-wholesaleretail-apis)
9. [Gross Profit APIs](#9-gross-profit-apis)
10. [Sales Analytics APIs](#10-sales-analytics-apis)
11. [POS System APIs](#11-pos-system-apis)
12. [Table Builder API](#12-table-builder-api)
13. [Known Issues & Solutions](#13-known-issues--solutions)

---

## IMPLEMENTATION STATUS

This document describes the **target API architecture** for the Georgia Dashboard system.

### Current State
- ✅ **Streamlit Dashboard**: Fully functional (3 pages: Executive, Profitability, Excise Tax)
- ✅ **Database Layer**: Complete SQL Server 2008 R2 connection and query utilities
- ✅ **Business Logic**: Excise tax calculations, profit analysis, sales metrics
- ❌ **REST API Layer**: Not yet implemented (this document serves as specification)

### Implementation Plan
1. Build Flask/FastAPI REST API layer matching this specification
2. Reuse existing database utilities and business logic from Streamlit dashboard
3. Create API testing suite
4. Deploy API alongside Streamlit dashboard

---

## 1. SYSTEM & HEALTH APIs

### `GET /api/health` - API Health Check

**Status:** 🟡 To Be Implemented

**What it does:** Confirms the API is running, checks database connectivity, and returns system status.

**Purpose:** Used for monitoring, health checks, load balancer probes, and initial connectivity testing.

**Implementation Plan:**
```python
from src.database.sql_server import db

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check API and database health."""
    # Test SQL Server connection
    sql_connected, sql_message = db.test_connection()

    return {
        "status": "running" if sql_connected else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "sql_server": {
                "status": "connected" if sql_connected else "disconnected",
                "message": sql_message
            }
        },
        "version": "1.0.0"
    }
```

**Expected Response:**
```json
{
  "status": "running",
  "timestamp": "2025-10-23T15:30:00Z",
  "database": {
    "sql_server": {
      "status": "connected",
      "message": "Connection successful"
    }
  },
  "version": "1.0.0"
}
```

---

## 2. AI ASSISTANT APIs

### `POST /api/ai/query` - Natural Language SQL Query

**Status:** 🟡 To Be Implemented (Requires OpenAI API Key)

**What it does:** Converts plain English questions into SQL queries, executes them, and returns results with AI-generated explanations.

**Purpose:** Allows non-technical users to query the database using natural language. Powers AI assistant features for ad-hoc analysis.

**Request:**
```json
{
  "question": "What were the top 10 products by revenue last month?",
  "stream": false
}
```

**How it works:**
1. Receives question in JSON body
2. Sends question + complete database schema to OpenAI GPT-4
3. AI generates SQL query compatible with SQL Server 2008 R2
4. Validates and executes query against GAWDB database
5. Caches results with UUID query_id for 1 hour
6. Returns results + human-readable explanation

**Technical Considerations:**
- Must explicitly specify SQL Server 2008 R2 limitations in prompt (no window functions)
- `Transaction` is a reserved keyword → must use `[dbo].[Transaction]`
- Implement query timeout (30s default)
- Cache results for 1 hour with UUID key
- Support streaming mode for real-time feedback

**Expected Response:**
```json
{
  "success": true,
  "query_id": "abc-123-def-456",
  "sql": "SELECT TOP 10 i.Description, SUM(te.Price * te.Quantity) as revenue...",
  "results": [
    {"Description": "Marlboro Red", "revenue": 15420.50},
    {"Description": "Red Bull 8.4oz", "revenue": 8950.00}
  ],
  "explanation": "This shows your top 10 products by revenue for October 2025...",
  "row_count": 10,
  "execution_time_ms": 1250
}
```

**Status:** 🟡 Requires OpenAI API key configuration

---

### `POST /api/ai/refine` - Query Refinement

**Status:** 🟡 To Be Implemented

**What it does:** Modifies an existing SQL query based on additional natural language instructions.

**Request:**
```json
{
  "instruction": "Add a column showing profit margin percentage",
  "query_id": "abc-123-def-456"
}
```

**Purpose:** Iterative data exploration without rewriting entire questions. Enables conversational analytics workflow.

---

### `GET /api/ai/export/<query_id>` - Export Query Results

**Status:** 🟡 To Be Implemented

**What it does:** Downloads cached query results as CSV file.

**Response Headers:**
```
Content-Type: text/csv
Content-Disposition: attachment; filename=query_results_{query_id}.csv
```

---

## 3. BUSINESS OVERVIEW APIs

### `GET /api/business-overview/executive-summary` - Executive KPIs

**Status:** 🟢 Logic Exists (in Streamlit) - API Wrapper Needed

**What it does:** THE primary dashboard API returning all key business metrics with automatic period-over-period comparisons. **This is the most important API in the system.**

**Existing Implementation:**
- Logic exists in `/pages/0_📊_Executive_Dashboard.py` lines 104-236
- Uses `src/database/sql_server.py` for queries
- Uses `src/utils/excise_tax.py` for tax calculations

**Parameters:**
- `period`: today|7d|30d|MTD|YTD (default: today)
- `start_date`: YYYY-MM-DD (custom start)
- `end_date`: YYYY-MM-DD (custom end)

**How it works:**

1. **Accepts flexible time periods** via query parameters
2. **Queries Transaction table for core metrics:**
   - Total revenue (SUM of Total)
   - Transaction count (COUNT of TransactionNumber)
   - Unique customers (COUNT DISTINCT CustomerID)
   - Average ticket size (AVG of Total)

3. **Joins to TransactionEntry → Item → Category for GP:**
   - Calculates gross profit with tobacco cost uplifts
   - Integrates excise tax calculations (PAID vs COLLECTED)

4. **Automatically calculates comparison period:**
   - Same duration as current period, shifted back
   - Calculates percentage changes

**Technical SQL (Already Working):**
```sql
-- Current period revenue/transactions (from Executive_Dashboard.py:104-113)
SELECT
    COUNT(DISTINCT TransactionNumber) as TotalTransactions,
    COUNT(DISTINCT CustomerID) as UniqueCustomers,
    SUM(Total) as TotalSales,
    AVG(Total) as AvgTransactionValue
FROM [Transaction]
WHERE Time >= '2025-10-01 00:00:00'
  AND Time <= '2025-10-23 23:59:59'

-- Line item metrics (from Executive_Dashboard.py:116-124)
SELECT
    SUM(te.Quantity) as TotalItemsSold,
    SUM((te.Price - te.Cost) * te.Quantity) as GrossProfitBeforeExcise
FROM TransactionEntry te
INNER JOIN [Transaction] t ON te.TransactionNumber = t.TransactionNumber AND te.StoreID = t.StoreID
WHERE t.Time >= '2025-10-01 00:00:00'
  AND t.Time <= '2025-10-23 23:59:59'
```

**Excise Tax Integration:**
```python
# Uses existing utility functions (from Executive_Dashboard.py:141-159)
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected

excise_paid, _ = calculate_excise_tax(db, start_date, end_date)
excise_collected, _ = calculate_excise_collected(db, start_date, end_date)

# Calculate net profit
gross_profit = metrics['GrossProfitBeforeExcise'] - metrics['TotalExciseCollected']
```

**Expected Response:**
```json
{
  "current_period": {
    "revenue": 125430.50,
    "transactions": 2450,
    "unique_customers": 180,
    "avg_ticket": 51.20,
    "gross_profit": 31357.63,
    "gross_profit_margin": 25.0,
    "excise_paid": 12500.00,
    "excise_collected": 15000.00
  },
  "comparison_period": {
    "revenue": 119200.00,
    "transactions": 2380,
    "unique_customers": 175,
    "avg_ticket": 50.08,
    "gross_profit": 29800.00,
    "gross_profit_margin": 25.0
  },
  "changes": {
    "revenue_change": 5.23,
    "transactions_change": 2.94,
    "customers_change": 2.86,
    "avg_ticket_change": 2.24,
    "gross_profit_change": 5.23
  },
  "period_info": {
    "start_date": "2025-10-01",
    "end_date": "2025-10-23",
    "days_in_period": 23
  }
}
```

**Implementation Task:**
- Create Flask route wrapping existing Streamlit logic
- Extract functions from `pages/0_📊_Executive_Dashboard.py`
- Add response caching (5 minutes)
- Add error handling for missing/invalid dates

**Known Issues (Solved in Streamlit):**
1. ✅ `Transaction` table requires brackets: `[dbo].[Transaction]`
2. ✅ Excise tax calculations use `PUExciseEntry.PriceC` field
3. ✅ Separate PAID (to state) vs COLLECTED (from customers) metrics
4. ✅ Net profit = Gross Profit - Excise Collected

**Performance:**
- Current: 2-3s for YTD queries in Streamlit
- Target: < 1s with caching for REST API

---

### `GET /api/business-overview/sales-performance` - Sales Performance Details

**Status:** 🟢 Logic Exists (in Streamlit) - API Wrapper Needed

**What it does:** Detailed sales breakdown by ALL products and categories with gross profit analysis.

**Existing Implementation:**
- Top categories logic in `/pages/0_📊_Executive_Dashboard.py` lines 303-327
- Top products logic in `/pages/0_📊_Executive_Dashboard.py` lines 353-375

**Parameters:**
- `period`: today|7d|30d|MTD|YTD (default: today)
- `start_date`: YYYY-MM-DD (custom start)
- `end_date`: YYYY-MM-DD (custom end)

**How it works:**

1. **Queries all products sold in period** (from Executive_Dashboard.py:353-375)
2. **Groups by category** for category performance (from Executive_Dashboard.py:303-327)
3. **Calculates gross profit with tobacco uplifts** (excise tax integrated)
4. **Returns complete dataset** (not paginated - frontend can filter)

**Technical SQL (Already Working):**
```sql
-- Top Categories (Executive_Dashboard.py:303-327)
SELECT TOP 10
    c.Name as Category,
    COUNT(DISTINCT t.TransactionNumber) as Transactions,
    SUM(te.Quantity) as QuantitySold,
    SUM(te.Price * te.Quantity) as Sales,
    SUM((te.Price - te.Cost) * te.Quantity) as GrossProfit,
    ISNULL(SUM(CASE WHEN pue.SubDescription3 LIKE '%COLL'
        THEN pue.PriceC * pue.Quantity
        ELSE 0 END), 0) as ExciseTax
FROM [Transaction] t WITH (NOLOCK)
JOIN TransactionEntry te WITH (NOLOCK)
    ON t.TransactionNumber = te.TransactionNumber AND t.StoreID = te.StoreID
JOIN Item i WITH (NOLOCK)
    ON te.ItemID = i.ID
JOIN Category c WITH (NOLOCK)
    ON i.CategoryID = c.ID
LEFT JOIN PUExciseEntry pue WITH (NOLOCK)
    ON t.TransactionNumber = pue.TransactionNumber
    AND te.ItemID = pue.ItemID
WHERE t.Time >= '2025-10-01 00:00:00'
  AND t.Time <= '2025-10-23 23:59:59'
GROUP BY c.Name
ORDER BY Sales DESC
```

**Expected Response:**
```json
{
  "top_products": [
    {
      "product": "Marlboro Red Box",
      "sku": "MAR-RED-BOX",
      "revenue": 15420.00,
      "units_sold": 1285,
      "gross_profit": 3855.00,
      "excise_tax": 1200.00,
      "net_profit": 2655.00,
      "net_margin": 17.2
    }
  ],
  "categories": [
    {
      "category_name": "CIGARETTE",
      "revenue": 125000.00,
      "gross_profit": 31250.00,
      "excise_tax": 15000.00,
      "net_profit": 16250.00,
      "net_margin": 13.0,
      "units_sold": 5420,
      "transaction_count": 1250,
      "item_count": 234
    }
  ]
}
```

**Implementation Task:**
- Extract query logic from Streamlit pages
- Add response caching (5 minutes)
- Remove TOP 10 limit (return all, let frontend filter)
- Add pagination support (optional)

---

### `GET /api/business-overview/sales-trends` - Daily Sales Trends

**Status:** 🟢 Logic Exists (in Streamlit) - API Wrapper Needed

**What it does:** Returns daily sales data for creating trend line charts.

**Existing Implementation:**
- Logic in `/pages/0_📊_Executive_Dashboard.py` lines 260-294

**Technical SQL (Already Working):**
```sql
-- Daily sales trend (Executive_Dashboard.py:260-270)
SELECT
    CAST(t.Time as DATE) as SalesDate,
    COUNT(DISTINCT t.TransactionNumber) as Transactions,
    SUM(t.Total) as DailySales
FROM [Transaction] t WITH (NOLOCK)
WHERE t.Time >= '2025-10-01 00:00:00'
  AND t.Time <= '2025-10-23 23:59:59'
GROUP BY CAST(t.Time as DATE)
ORDER BY SalesDate
```

**Expected Response:**
```json
{
  "trends": [
    {
      "date": "2025-10-01",
      "revenue": 4250.00,
      "transactions": 85,
      "customers": 62
    },
    {
      "date": "2025-10-02",
      "revenue": 5120.00,
      "transactions": 102,
      "customers": 75
    }
  ],
  "summary": {
    "total_days": 23,
    "avg_daily_revenue": 4987.50,
    "avg_daily_transactions": 98,
    "best_day": {"date": "2025-10-15", "revenue": 6420.00},
    "worst_day": {"date": "2025-10-08", "revenue": 3150.00}
  }
}
```

**Performance:** < 500ms even for 365-day ranges

---

## 4. INVENTORY MANAGEMENT APIs

**Status:** 🔴 Not Implemented (No Streamlit Pages for Inventory)

These endpoints would provide inventory health monitoring and alerts. Currently no inventory management pages exist in the Streamlit dashboard.

### `GET /api/inventory-health/low-stock` - Low Stock Alert

**What it does:** Lists items currently below their reorder point, requiring immediate attention for restocking.

**Proposed SQL:**
```sql
SELECT
    i.ID as item_id,
    i.Description,
    i.Quantity as current_stock,
    i.ReorderPoint,
    (i.ReorderPoint - i.Quantity) as deficit,
    c.Name as category
FROM Item i
LEFT JOIN Category c ON i.CategoryID = c.ID
WHERE i.Quantity < i.ReorderPoint
  AND i.Inactive = 0
ORDER BY deficit DESC
```

**Purpose:** Prevents stockouts, purchase order generation, automated reorder alerts.

---

### `GET /api/inventory-health/deadstock` - Dead Stock Analysis

**What it does:** Identifies items with no sales activity in X days (default 90), representing tied-up capital.

**Proposed SQL:**
```sql
SELECT
    i.ID as item_id,
    i.Description,
    i.Quantity as on_hand,
    i.Cost,
    (i.Quantity * i.Cost) as value_tied_up,
    i.LastSold,
    DATEDIFF(day, i.LastSold, GETDATE()) as days_since_sale
FROM Item i
WHERE (
    i.LastSold IS NULL
    OR i.LastSold < DATEADD(day, -90, GETDATE())
)
AND i.Quantity > 0
AND i.Inactive = 0
ORDER BY value_tied_up DESC
```

**Purpose:** Identify slow-moving inventory to discount or return, free up cash.

---

### `GET /api/inventory-health/overstock` - Overstock Items

**What it does:** Identifies items with quantity exceeding reasonable stock levels based on sales velocity.

**Algorithm:**
1. Calculate average daily sales per item from last 90 days
2. Determine "days of supply": Current Quantity / Avg Daily Sales
3. Flag items with > 90 days of supply
4. Calculate excess capital tied up

---

## 5. FINANCIAL/AR APIs

**Status:** 🔴 Not Implemented

### `GET /api/financial/ar-summary` - Accounts Receivable Summary

**What it does:** Customer AR balances, aging analysis, credit limits.

**Proposed Tables:** Customer (AccountBalance, CreditLimit), AccountReceivable

---

### `GET /api/financial/ar-aging` - AR Aging Report

**What it does:** AR breakdown by 30/60/90/120+ day buckets.

---

## 6. SALES OPERATIONS APIs

**Status:** 🔴 Not Implemented

### `GET /api/sales/transactions` - Transaction History

**What it does:** Paginated transaction list with filters.

---

## 7. SUPPLIER MANAGEMENT APIs

**Status:** 🔴 Not Implemented

### `GET /api/suppliers` - Supplier List

**What it does:** Supplier directory with contact info.

---

## 8. WHOLESALE/RETAIL APIs

**Status:** 🔴 Not Implemented

### `GET /api/channel-analysis/wholesale-vs-retail` - Channel Comparison

**What it does:** Compare wholesale vs retail performance.

---

## 9. GROSS PROFIT APIs

### `GET /api/gross-profit/analysis` - Gross Profit Analysis

**Status:** 🟢 Logic Exists (in Streamlit) - API Wrapper Needed

**Existing Implementation:**
- Complete implementation in `/pages/1_💰_Profitability_Analysis.py`
- Overall profitability (lines 105-135)
- Category profitability (lines 246-271)
- Product profitability (lines 320-348)
- Loss leaders analysis (lines 381-409)
- Profit trends (lines 445-458)

**What it does:** Deep dive into profit margins by category and product, identify loss leaders and profit drivers.

**Purpose:**
- Understand profitability drivers
- Identify high/low margin products
- Make pricing decisions
- Optimize product mix

---

## 10. SALES ANALYTICS APIs

**Status:** 🟡 Partial Implementation

### `GET /api/analytics/customer-segmentation` - Customer Analysis

**What it does:** RFM analysis (Recency, Frequency, Monetary), customer lifetime value, churn risk.

**Proposed Tables:** Customer (TotalSales, TotalVisits, LastVisit)

---

## 11. POS SYSTEM APIs

**Status:** 🔴 Not Implemented

### `POST /api/pos/transaction` - Create Transaction

**What it does:** Create new sales transaction (if building POS integration).

---

## 12. EXCISE TAX REPORTING API

### `GET /api/excise-tax/report` - Excise Tax Report

**Status:** 🟢 Logic Exists (in Streamlit) - API Wrapper Needed

**Existing Implementation:**
- Complete implementation in `/pages/2_🚬_Excise_Tax_Reporting.py`
- Uses `src/utils/excise_tax.py` for all calculations
- PAID calculation (lines 105-109)
- COLLECTED calculation (lines 111-115)
- Category breakdown (lines 212-217 PAID, 247-252 COLLECTED)
- Product-level details (lines 284-302)
- Monthly trends (lines 329-340)

**What it does:** Comprehensive excise tax reporting with PAID/COLLECTED breakdown by category and product.

**How it works:**

```python
# Uses existing utility functions (excise_tax.py:141-159)
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected, get_excise_breakdown

# Calculate totals
excise_paid, _ = calculate_excise_tax(db, start_date, end_date)
excise_collected, _ = calculate_excise_collected(db, start_date, end_date)

# Get category breakdown
paid_breakdown, _ = get_excise_breakdown(db, start_date, end_date, 'PAID')
coll_breakdown, _ = get_excise_breakdown(db, start_date, end_date, 'COLL')
```

**Key SQL Queries (Already Working):**

```sql
-- Total Excise PAID (excise_tax.py function)
SELECT
    ISNULL(SUM(PriceC * Quantity), 0) as total_excise
FROM PUExciseEntry
WHERE TransactionTime >= '2025-09-01 00:00:00'
  AND TransactionTime <= '2025-09-30 23:59:59'
  AND SubDescription3 LIKE '%PAID'

-- Category Breakdown (excise_tax.py:get_excise_breakdown)
SELECT
    SubDescription3 as Category,
    COUNT(*) as EntryCount,
    SUM(PriceC * Quantity) as TotalExcise
FROM PUExciseEntry
WHERE TransactionTime >= '2025-09-01 00:00:00'
  AND TransactionTime <= '2025-09-30 23:59:59'
  AND SubDescription3 LIKE '%PAID'
GROUP BY SubDescription3
ORDER BY TotalExcise DESC
```

**Expected Response:**
```json
{
  "summary": {
    "excise_paid": 30568.20,
    "excise_collected": 66828.73,
    "difference": 36260.53,
    "recovery_rate": 45.7
  },
  "paid_breakdown": [
    {
      "category": "LC23PAID",
      "description": "Large Cigars (23%)",
      "total_excise": 15234.50,
      "entry_count": 1250,
      "percentage": 49.8
    }
  ],
  "collected_breakdown": [
    {
      "category": "LC23COLL",
      "description": "Large Cigars (23%)",
      "total_excise": 28500.00,
      "entry_count": 1250,
      "percentage": 42.6
    }
  ],
  "monthly_trend": [
    {
      "month": "2025-09",
      "paid": 30568.20,
      "collected": 66828.73
    }
  ],
  "compliance_status": "OK",
  "notes": [
    "Excise PAID = Tax paid to state (reduce gross profit)",
    "Excise COLLECTED = Tax from customers (remit to state)"
  ]
}
```

**Tax Categories Reference:**
```
LC23PAID/COLL - Large Cigars (~23%)
LC25PAID/COLL - Little Cigars (~25%)
LT10PAID/COLL - Loose Tobacco (~10%)
SL10PAID/COLL - Smokeless Tobacco (~10%)
VD07PAID/COLL - Vape Device (~7%)
VO07PAID/COLL - Vapors Open (~7%)
VC05PAID/COLL - Vapors Closed (~5%)
```

**Implementation Task:**
- Create Flask route wrapping existing excise_tax.py functions
- Add CSV export endpoint for state filing
- Add response caching (15 minutes - tax data doesn't change frequently)

**Known Issues (Solved):**
1. ✅ Uses `PUExciseEntry.PriceC` field (actual tax amount per unit)
2. ✅ Formula: `SUM(PriceC * Quantity)`
3. ✅ PAID suffix = tax to government (subtract from profit)
4. ✅ COLL suffix = tax from customers (must remit to state)
5. ✅ Validated against September 2025: $30,568.20 PAID, $66,828.73 COLLECTED

**Performance:** < 2s for monthly queries

---

## 13. KNOWN ISSUES & SOLUTIONS

### Database-Specific Issues

#### 1. SQL Server 2008 R2 Limitations
**Issue:** Old database version doesn't support modern SQL features
**Impact:** Can't use window functions (ROW_NUMBER() OVER()), CTEs in some contexts
**Solution:** Use subqueries and temp tables instead

#### 2. Reserved Keyword: Transaction
**Issue:** `Transaction` is a T-SQL reserved word
**Impact:** Syntax errors if not properly escaped
**Solution:** Always use `[dbo].[Transaction]` with brackets

---

### Excise Tax Calculation Issues

#### 3. Excise Tax Integration
**Issue:** Excise tax not included in Item.Cost field
**Impact:** Gross profit calculations were 10-23% lower than actual
**Root Cause:** Cost field doesn't include excise taxes paid on tobacco products
**Solution:** Use `PUExciseEntry.PriceC` field for accurate excise tax amounts

**Tax Categories:**
- Large Cigars (LC23): ~23% excise
- Little Cigars (LC25): ~25% excise
- Loose Tobacco (LT10): ~10% excise
- Smokeless (SL10): ~10% excise
- Vape Device (VD07): ~7% excise
- Vapors Open (VO07): ~7% excise
- Vapors Closed (VC05): ~5% excise

**Formula:**
```python
# Use actual tax from PUExciseEntry
excise_paid = SUM(PriceC * Quantity) WHERE SubDescription3 LIKE '%PAID'
excise_collected = SUM(PriceC * Quantity) WHERE SubDescription3 LIKE '%COLL'

# Calculate net profit
gross_profit = revenue - cogs
net_profit = gross_profit - excise_collected  # What we owe to state
```

**Validation:**
- September 2025: $30,568.20 PAID, $66,828.73 COLLECTED ✅
- See `test_excise_september.py` for validation script

---

### Performance Issues

#### 4. Slow Queries on Large Date Ranges
**Issue:** YTD queries (9+ months) caused 30+ second timeouts
**Root Cause:** Full table scan on 4.6M TransactionEntry records
**Solution:**
- Use `WITH (NOLOCK)` hint for read queries
- Add composite indexes (if database allows modifications)
- Implement response caching (5-15 minutes TTL)

#### 5. Duplicate Data from JOINs
**Issue:** Sales numbers multiplied when joining Transaction → TransactionEntry → PUExciseEntry
**Root Cause:** Multiple excise entries per transaction entry (PAID + COLL)
**Solution:** Separate queries for transaction-level and line-item metrics (see Executive Dashboard implementation)

**Example:**
```sql
-- DON'T DO THIS (multiplies sales):
SELECT SUM(t.Total), SUM(pue.PriceC)
FROM [Transaction] t
JOIN PUExciseEntry pue ON t.TransactionNumber = pue.TransactionNumber

-- DO THIS (separate queries):
-- Query 1: Transaction metrics
SELECT SUM(Total) FROM [Transaction]

-- Query 2: Excise metrics
SELECT SUM(PriceC * Quantity) FROM PUExciseEntry
```

---

### Data Quality Issues

#### 6. Negative Inventory Quantities
**Issue:** 23 items have negative on-hand quantities
**Root Cause:** Returns not processed correctly or double-sells
**Impact:** Inventory reports unreliable
**Status:** Operational workaround (separate tracking API), data cleanup needed

#### 7. Missing Reorder Points
**Issue:** ReorderPoint field is NULL for many items
**Impact:** Low stock alerts incomplete
**Solution:** Default to 10 if NULL, flag for manual review
**Status:** 892 items still need reorder points set

#### 8. Uncategorized Items
**Issue:** 156 items have NULL CategoryID
**Impact:** Category reports incomplete
**Solution:** `COALESCE(c.Name, 'Uncategorized')` in all queries
**Status:** Resolved in queries, data cleanup pending

---

## IMPLEMENTATION PRIORITY

### Phase 1: Core Business APIs (Week 1)
1. ✅ Create Flask/FastAPI project structure
2. ✅ Implement health check endpoint
3. ✅ Extract and wrap executive summary logic
4. ✅ Extract and wrap sales performance logic
5. ✅ Extract and wrap excise tax reporting logic
6. ✅ Add response caching layer

### Phase 2: Analytics & Trends (Week 2)
1. Implement sales trends API
2. Implement profitability analysis API
3. Add comparison period calculations
4. Build testing suite for core endpoints

### Phase 3: Inventory & Operations (Week 3)
1. Implement inventory health APIs
2. Add low stock/deadstock/overstock endpoints
3. Build alerts system

### Phase 4: Advanced Features (Week 4)
1. Implement AI query endpoints (if OpenAI key available)
2. Add customer segmentation API
3. Add AR/financial APIs
4. Complete documentation

### Phase 5: Production Readiness (Week 5)
1. Add authentication/authorization
2. Add rate limiting
3. Set up logging and monitoring
4. Deploy to production
5. Create Postman collection

---

## TESTING STRATEGY

### Unit Tests
- Test each endpoint with valid/invalid inputs
- Test date range parsing
- Test SQL query generation
- Test excise tax calculations

### Integration Tests
- Test database connectivity
- Test query performance
- Test caching behavior
- Test error handling

### Load Tests
- Test concurrent request handling
- Test database connection pooling
- Test cache hit rates

### Validation Tests
- Compare API results to Streamlit dashboard results
- Validate excise tax calculations against known values (September 2025)
- Cross-check profit calculations with accounting records

---

## API AUTHENTICATION & SECURITY

### Recommended Approach
1. **API Keys** for machine-to-machine
2. **JWT Tokens** for user sessions
3. **Rate Limiting** (100 req/min per key)
4. **HTTPS Only** in production
5. **CORS** configuration for web frontends
6. **SQL Injection Prevention** (parameterized queries only)

---

## DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────┐
│         NGINX Reverse Proxy              │
│    (Load Balancer + SSL Termination)     │
└─────────────┬───────────────────────────┘
              │
      ┌───────┴───────┐
      │               │
┌─────▼─────┐   ┌────▼────┐
│ Streamlit │   │  Flask  │
│ Dashboard │   │   API   │
│  (Port    │   │  (Port  │
│   8501)   │   │   5000) │
└─────┬─────┘   └────┬────┘
      │              │
      └──────┬───────┘
             │
      ┌──────▼──────┐
      │ SQL Server  │
      │   GAWDB     │
      │ 10.1.10.105 │
      └─────────────┘
```

---

## APPENDIX A: Database Schema

### Key Tables

**Transaction** (238K records)
- TransactionNumber (PK)
- CustomerID (FK)
- Time (datetime)
- Total (money)
- StoreID

**TransactionEntry** (4.7M records)
- TransactionNumber (FK)
- ItemID (FK)
- Quantity (decimal)
- Price (money)
- Cost (money)
- StoreID

**PUExciseEntry** (4.7M records)
- TransactionNumber (FK)
- ItemID (FK)
- Quantity (decimal)
- PriceC (money) ← **Actual excise tax per unit**
- SubDescription3 (varchar) ← **Tax category (LC23PAID, LC23COLL, etc.)**
- TransactionTime (datetime)

**Item** (12.7K records)
- ID (PK)
- Description (varchar)
- ItemLookupCode (varchar) ← SKU
- CategoryID (FK)
- Quantity (decimal)
- Cost (money)
- Price (money)
- ReorderPoint (int)
- LastSold (datetime)
- Inactive (bit)

**Category** (83 records)
- ID (PK)
- Name (varchar)

**Customer** (2.8K records)
- ID (PK)
- Company (varchar)
- AccountBalance (money)
- CreditLimit (money)
- TotalSales (money)
- TotalVisits (int)
- LastVisit (datetime)

---

## APPENDIX B: Environment Variables

```bash
# SQL Server Connection
MSSQL_SERVER=10.1.10.105
MSSQL_USER=your_username
MSSQL_PASSWORD=your_password
MSSQL_DATABASE=GAWDB
MSSQL_TDS_VERSION=7.0
MSSQL_TIMEOUT=30

# API Configuration
API_PORT=5000
API_HOST=0.0.0.0
API_SECRET_KEY=your-secret-key-here

# OpenAI (optional - for AI query features)
OPENAI_API_KEY=sk-...

# Caching
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/georgia-api/api.log
```

---

## APPENDIX C: References

- **Database Analysis:** `GAWDB_SYSTEM_ANALYSIS.md`
- **Excise Tax Solution:** `EXCISE_TAX_SOLUTION.md`
- **Test Scripts:** `test_excise_september.py`, `test_connection.py`
- **Streamlit Dashboard:** `/pages/*.py`
- **Database Utilities:** `/src/database/sql_server.py`
- **Business Logic:** `/src/utils/excise_tax.py`

---

**Document Version:** 1.0
**Last Updated:** October 23, 2025
**Maintained By:** Development Team
**Status:** 🟡 In Progress - API Implementation Underway
