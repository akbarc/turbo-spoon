# Category Insights Session Summary

## Date: October 16, 2025

## Main Question Answered

**Why does the GP Dashboard overview load quickly but category/department breakdowns only work for one day?**

### Root Cause
- **Overview queries** use simple `SUM()` aggregations on PUVIEWEXCISETRANSACTION (no `GROUP BY`) - FAST
- **Category/department queries** use `GROUP BY` on PUVIEWEXCISETRANSACTION over large date ranges - TIMEOUT after 30 seconds
- **GP_Daily_Summary table** only had 1 day of data (Oct 15, 2025) - designed to solve this but not populated

### Solution: FAST Approach

Instead of querying PUVIEWEXCISETRANSACTION with GROUP BY (which times out), we:

1. **Skip the PUExciseEntry join** - Query Transaction + TransactionEntry + Item + Category directly
2. **Calculate excise tax** using derived category rates:
   - CIGARS: 8.23%
   - CIGAR GA: 10.59%
   - LT-TAX-COLLECTED: 4.84%
   - LT-TAX-PAID: 4.84%
   - LC23PAID: 4.84%
   - LC23COLL: 4.84%
3. **Results**: 22.57 seconds for full YTD vs 30+ second timeout

## Category Insights YTD (Jan 1 - Oct 15, 2025)

### File Created
**Location**: `/Users/akbarchranya/Downloads/category_insights_ytd_2025.csv`

### Columns Included
- CategoryName
- Revenue
- COGS (Cost of Goods Sold)
- ExciseTax
- GrossProfit
- GPMarginPercent
- UniqueCustomers
- TotalTransactions
- CategoryOnlyTransactions (single-category purchases)
- CategoryOnlyPercent

### Top 5 Categories by Gross Profit

1. **CIGARS**
   - Revenue: $3,496,517.76
   - Gross Profit: $564,509.07 (16.14% margin)
   - Excise Tax: $287,763.41
   - Unique Customers: 482
   - Total Transactions: 7,440
   - Category-Only: 199 (2.7%)

2. **CIGARETTE**
   - Revenue: $15,884,555.17 (HIGHEST REVENUE!)
   - Gross Profit: $420,923.29 (2.65% margin)
   - Excise Tax: $0.00
   - Unique Customers: 476
   - Total Transactions: 7,287
   - Category-Only: 1,196 (16.4%)

3. **LT-TAX PAID**
   - Revenue: $951,649.04
   - Gross Profit: $119,782.87 (12.59% margin)
   - Excise Tax: $0.00
   - Unique Customers: 432
   - Total Transactions: 4,903
   - Category-Only: 108 (2.2%)

4. **ELECTRONIC CIG**
   - Revenue: $1,168,837.90
   - Gross Profit: $111,910.75 (9.57% margin)
   - Excise Tax: $0.00
   - Unique Customers: 378
   - Total Transactions: 2,914
   - Category-Only: 299 (10.3%)

5. **LT-TAX-COLLECTED**
   - Revenue: $445,337.63
   - Gross Profit: $75,617.36 (16.98% margin)
   - Excise Tax: $21,554.34
   - Unique Customers: 377
   - Total Transactions: 3,338
   - Category-Only: 37 (1.1%)

### Key Business Insights

1. **Cross-Selling Success**
   - CIGARS: Only 2.7% category-only purchases - customers buying other products too!
   - LT-TAX-COLLECTED: Only 1.1% category-only - strong basket mix

2. **Quick Stop Categories**
   - CIGARETTE: 16.4% category-only - customers coming just for cigarettes
   - KRATOM: 16.8% category-only - destination purchases
   - MISC: 15.0% category-only

3. **Margin Leaders**
   - SHOPPING BAGS: 41.31% (highest margin)
   - MISC: 29.20%
   - MEDICINE: 22.25%
   - CANDYS: 19.21%

4. **Margin Challenges**
   - CIGARETTE: 2.65% (lowest margin but highest revenue)
   - ECIG - PODS: 5.07%
   - VITAMINS: 5.92%

## Total Categories Found

**50 categories** with YTD sales

## Background Processes Attempted (All Killed)

1. **GP_Daily_Summary Population** - Stuck on day 1
2. **September PUVIEWEXCISETRANSACTION Report (Full Month)** - Timed out after 3 retries
3. **September PUVIEWEXCISETRANSACTION Report (Weekly Chunks)** - Stuck on week 1
4. **September PUVIEWEXCISETRANSACTION Report (Daily Chunks)** - Stuck on day 1

**Conclusion**: PUVIEWEXCISETRANSACTION view with GROUP BY is too slow. FAST approach is the way forward.

## Technical Details

### Query Performance
- **FAST approach**: 5.76 - 22.57 seconds for full YTD
- **PUVIEWEXCISETRANSACTION**: 30+ second timeout, unusable for grouped queries
- **Accuracy**: 99% (calculated excise tax vs actual from PUExciseEntry)

### Files Reference
- **Category Insights CSV**: `/Users/akbarchranya/Downloads/category_insights_ytd_2025.csv`
- **GP Dashboard**: `/Users/akbarchranya/georgiadashboard/gp_dashboard.py` (port 8081)
- **GP Calculation Module**: `/Users/akbarchranya/georgiadashboard/data_foundation/gross_profit.py`
- **PUVIEWEXCISETRANSACTION Definition**: `/Users/akbarchranya/georgiadashboard/PUVIEWEXCISETRANSACTION_definition.sql`

### SQL View Definition
The PUVIEWEXCISETRANSACTION view joins:
- Transaction (main table)
- TransactionEntry (line items)
- PUExciseEntry (excise tax details) - THIS IS THE SLOW PART
- Customer, Item, Category, Department
- Cashier, Register, Batch

**66 total columns** - very comprehensive but slow with GROUP BY.

## Recommendations

1. **Use FAST approach** for all category/department analysis going forward
2. **Consider populating GP_Daily_Summary** for even faster queries (pre-aggregated)
3. **Monitor category-only percentages** to identify cross-sell opportunities
4. **Focus on low-margin, high-revenue categories** (CIGARETTE) for pricing strategy
5. **Leverage high-margin categories** (SHOPPING BAGS, MISC) for upselling

## Session Completed
- Query ran successfully in 22.57 seconds
- Data exported to Downloads folder
- All background processes cleaned up
- 50 categories analyzed with full YTD metrics
