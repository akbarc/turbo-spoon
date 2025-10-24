# Product Category Analysis Dashboard

## Overview
Interactive dashboard for analyzing product category performance with filtering, sorting, and detailed product-level drill-down capabilities.

## Location
**URL:** http://localhost:8080/category-analysis
**Navigation:** Analytics → Category Analysis

## Features

### 1. **Interactive Filters**
- **Time Period**: 30 days, 90 days, 6 months, 12 months, 24 months
- **Margin Filters**: Filter by minimum/maximum margin percentage
- **Revenue Filter**: Filter by minimum revenue threshold
- **Sorting**: Sort by revenue, margin, growth, transactions, units, or category name
- **Sort Order**: Ascending or descending

### 2. **Summary Metrics Dashboard**
Real-time calculation of:
- Total Revenue
- Total Gross Profit
- Overall Margin %
- Active Categories Count
- Total Transactions
- Total Units Sold

### 3. **Classification System**
Categories are automatically classified into:

#### 💰 **Money Makers**
- High margin (>20%) OR significant revenue (>5%) with decent margin (>15%)
- **Action:** Keep and expand inventory/marketing

#### 🎯 **Strategic**
- Lower margin (>5%) but high volume (>5% revenue share)
- **Action:** Important for traffic - optimize margins

#### 🔍 **Investigate**
- Mixed performance signals
- **Action:** Analyze individual SKU performance

#### ⚠️ **Underperformers**
- Low revenue share (<1%) and declining (>-10% growth)
- **Action:** Review SKUs, consider reducing

#### ❌ **Money Losers**
- Very low margins (<5%) and minimal profit contribution (<1%)
- **Action:** Discontinue or drastically reduce inventory

### 4. **Interactive Category Table**
- Click any row to see top products in that category
- Real-time search/filter
- Visual progress bars for revenue share
- Growth indicators with up/down arrows
- Color-coded classification badges

### 5. **Product Drill-Down Modal**
Click any category to see:
- Top 20 products by revenue
- Product SKU
- Revenue and profit per product
- Margin % per product
- Units sold

### 6. **Export Capabilities**
- Export filtered results to CSV
- Includes all metrics for external analysis

## Key Insights from Current Data

### Business Snapshot (Last 12 Months)
- **Total Revenue:** $33.5M
- **Gross Profit:** $3.1M
- **Overall Margin:** 9.1%
- **Categories Analyzed:** 52

### Top Findings

#### Money Makers (2 categories - 15% of revenue)
1. **CIGARS** - $4.3M revenue, 24.2% margin (declining -18%)
2. **LT-TAX-COLLECTED** - $711K revenue, 22.1% margin (growing +177%!)

#### Biggest Opportunity
**CIGARETTE** - Your largest category at $16.7M (50% of revenue) but only 2.8% margin
- **Potential:** Just +2% margin improvement = $334K extra profit annually

#### Categories to Eliminate (2)
- **JBR** - $46K revenue, 2.2% margin
- **PHONE CARDS** - $18K revenue, 3.4% margin

#### High Growth Opportunities (6 categories)
Categories with >10% growth AND >15% margins:
- **LT-TAX-COLLECTED**: +177% growth
- **MISC**: +105% growth
- **APPAREL & CLOTHING**: +500% growth (small base)
- **CIG ROLLING PAPER**: +17% growth
- **INCENSE**: +17% growth

### Strategic Recommendations

1. **Immediate Eliminations (12 categories)**
   - Combined revenue impact: <1% of total
   - Profit improvement: +$XX,XXX

2. **Margin Optimization (Top 7 categories)**
   - **CIGARETTE**: 2.8% → 4.8% = $334K gain
   - **ELECTRONIC CIG**: 8.4% → 10.4% = $34K gain
   - **LT-TAX PAID**: 9.3% → 11.3% = $22K gain
   - **Total Potential**: $543K+ with just 2% improvement

3. **Growth Focus**
   - Double down on **LT-TAX-COLLECTED** (177% growth)
   - Expand **CIG ROLLING PAPER** inventory (17% growth, 19% margin)

4. **Investigation Required**
   - **CIGARS**: High margin but declining -18% (find cause)
   - **ELECTRONIC CIG**: 5% revenue share but declining -32%

## API Endpoints

### Get Category Data
```
GET /api/category-analysis/data
```

**Query Parameters:**
- `days` - Time period (default: 365)
- `min_margin` - Minimum margin %
- `max_margin` - Maximum margin %
- `min_revenue` - Minimum revenue $
- `classification` - Filter by classification (MONEY_MAKER, STRATEGIC, etc.)
- `sort_by` - Sort field (revenue, margin, growth, etc.)
- `sort_order` - asc or desc

**Response:**
```json
{
  "status": "success",
  "data": [...],
  "summary": {
    "total_revenue": 33457326.28,
    "total_profit": 3053730.99,
    "overall_margin": 9.1,
    "category_count": 52
  },
  "period": "2024-10-03 to 2025-10-03"
}
```

### Get Top Products by Category
```
GET /api/category-analysis/top-products/<category_name>
```

**Query Parameters:**
- `days` - Time period (default: 365)
- `limit` - Number of products (default: 20)

## Files Created

### Backend
- `/app/category_analysis.py` - Flask blueprint with API endpoints
- Integration in `/app/main.py` - Routes registered

### Frontend
- `/templates/category_analysis.html` - Interactive dashboard UI

### Analysis Scripts
- `/comprehensive_category_analysis.py` - Standalone analysis script
- `/category_visual_dashboard.py` - Text-based dashboard generator

### Data Exports
- `category_analysis_comprehensive_YYYYMMDD_HHMMSS.csv`
- `category_classification_summary_YYYYMMDD_HHMMSS.csv`
- `category_top_products_YYYYMMDD_HHMMSS.csv`

## Usage Tips

1. **Quick Win Analysis**
   - Filter by classification: "Money Losers"
   - Review candidates for elimination

2. **Growth Opportunities**
   - Sort by "Growth %"
   - Filter min margin > 15%
   - Find high-growth, high-margin categories to expand

3. **Margin Improvement**
   - Sort by "Revenue"
   - Focus on top 10 revenue categories with <10% margin
   - Calculate 2% margin improvement potential

4. **Product-Level Decisions**
   - Click any category
   - Review top products
   - Identify specific SKUs to keep/kill

## Next Steps

1. Run monthly to track classification changes
2. Set margin improvement targets by category
3. Review eliminated category impact quarterly
4. Expand high-growth categories systematically
5. Create alerts for categories changing classification
