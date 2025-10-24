# Georgia Dashboard - Current Structure Documentation

## Overview
This document provides a comprehensive overview of the Georgia Dashboard application's current structure, including pages, APIs, navigation, and functionality status.

---

## 1. PAGES & ROUTES

### Main Pages (Currently Implemented)

| Page | Route | Template | Description | Status |
|------|-------|----------|-------------|--------|
| **Executive Dashboard** | `/` | `executive_dashboard.html` | Main dashboard with business overview | ✅ Active |
| **Customer Ledger** | `/customer-ledger` | `customer_ledger.html` | Customer account details and ledger | ✅ Active |
| **AR Dashboard** | `/ar-dashboard` | `ar_dashboard.html` | Accounts receivable management | ✅ Active |
| **Sales Operations** | `/sales-ops` | `sales_ops.html` | Sales and payment operations | ✅ Active |
| **Suppliers** | `/suppliers` | `suppliers.html` | Supplier and purchase order management | ✅ Active |
| **Wholesale/Retail** | `/wholesale-retail` | `wholesale_retail_improved.html` | Wholesale vs retail analysis | ✅ Active |
| **GP Analysis** | `/gp-analysis` | `gp_analysis.html` | Gross profit analysis dashboard | ✅ Active |
| **Inventory** | `/inventory` | `inventory.html` | Inventory management dashboard | ✅ Active |
| **AI Assistant** | `/ai-assistant` | `ai_assistant.html` | Natural language SQL query interface | ✅ Active |
| **Customer Segmentation** | `/customer-segmentation` | `customer_segmentation.html` | Customer segmentation analysis | ✅ Active |

### Duplicate/Legacy Templates Found
- `ai_assistant_new.html` - Newer version exists
- `ar_dashboard_new.html` - Newer version exists
- `customer_ledger_new.html` - Newer version exists
- `executive_dashboard_new.html` - Newer version exists
- `gp_analysis_new.html` - Newer version exists
- `sales_ops_new.html` - Newer version exists
- `suppliers_new.html` - Newer version exists
- `wholesale_retail_improved_new.html` - Newer version exists

---

## 2. API ENDPOINTS

### AI Assistant APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/ai/query` | POST | Execute natural language SQL queries | ✅ Working |
| `/api/ai/refine` | POST | Refine existing SQL with natural language | ✅ Working |
| `/api/ai/export/<query_id>` | GET | Export query results as CSV | ✅ Working |
| `/api/ai/sql/<query_id>` | GET | Get cached SQL for a query | ✅ Working |

### Business Overview APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/business-overview/executive-summary` | GET | Key business metrics summary | ✅ Working |
| `/api/business-overview/sales-performance` | GET | Sales performance metrics | ✅ Working |
| `/api/business-overview/inventory-health` | GET | Inventory health overview | ✅ Working |
| `/api/business-overview/customer-intelligence` | GET | Customer insights and metrics | ✅ Working |
| `/api/business-overview/performance-trends` | GET | Performance trend analysis | ✅ Working |
| `/api/business-overview/sales-trends` | GET | Sales trend data | ✅ Working |

### Inventory APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/inventory-health/low-stock` | GET | Low stock items alert | ✅ Working |
| `/api/inventory-health/deadstock` | GET | Dead stock analysis | ✅ Working |
| `/api/inventory-health/overstock` | GET | Overstock items | ✅ Working |
| `/api/inventory-health/negative-quantity` | GET | Items with negative quantities | ✅ Working |
| `/api/inventory-health/velocity` | GET | Inventory velocity metrics | ✅ Working |
| `/api/inventory-health/category-values` | GET | Category-wise inventory values | ✅ Working |
| `/api/item/<item_id>/details` | GET | Individual item details | ✅ Working |

### Financial APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/financial/ar-aging` | GET | AR aging analysis | ✅ Working |
| `/api/financial/ar-aging-optimized` | GET | Optimized AR aging analysis | ✅ Working |
| `/api/financial/nsf-details` | GET | NSF (Non-Sufficient Funds) details | ✅ Working |

### Sales Operations APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/sales-ops/overview` | GET | Sales operations overview | ✅ Working |
| `/api/sales-ops/sales-detail` | GET | Detailed sales data | ✅ Working |
| `/api/sales-ops/payments-detail` | GET | Payment details | ✅ Working |

### Supplier APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/suppliers/overview` | GET | Suppliers overview | ✅ Working |
| `/api/suppliers/list` | GET | List of all suppliers | ✅ Working |
| `/api/suppliers/purchase-orders` | GET | Purchase orders list | ✅ Working |
| `/api/suppliers/inventory-alerts` | GET | Inventory reorder alerts | ✅ Working |
| `/api/suppliers/top-products` | GET | Top ordered products | ✅ Working |

### Wholesale/Retail APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/wholesale-retail/analysis` | GET | Wholesale vs retail analysis | ✅ Working |
| `/api/wholesale-retail/ytd-comparison` | GET | Year-to-date comparison | ✅ Working |
| `/api/wholesale-retail/wholesale-customers` | GET | Wholesale customer details | ✅ Working |
| `/api/wholesale-retail/monthly/<year>` | GET | Monthly breakdown by year | ✅ Working |

### GP Analysis APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/gp/executive-summary` | GET | GP executive summary | ✅ Working |
| `/api/gp/trending` | GET | GP trending analysis | ✅ Working |
| `/api/gp/categories` | GET | GP by categories | ✅ Working |
| `/api/gp/customers` | GET | GP by customers | ✅ Working |
| `/api/gp/products` | GET | GP by products | ✅ Working |
| `/api/gp/opportunities` | GET | GP improvement opportunities | ✅ Working |

### Customer Segmentation APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/customer-segmentation` | GET | Customer segmentation data | ⚠️ Placeholder in api_routes.py |

### System APIs
| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api` | GET | API status and available endpoints | ✅ Working |

---

## 3. NAVIGATION STRUCTURE

### Primary Navigation (navbar)
Current navigation bar includes:
1. **Dashboard** (/) - Executive Dashboard
2. **Customer Ledger** (/customer-ledger)
3. **AR Management** (/ar-dashboard)
4. **GP Analysis** (/gp-analysis)
5. **Segmentation** (/customer-segmentation)
6. **AI Assistant** (/ai-assistant)

### Missing from Navigation
Pages that exist but are not in main navigation:
- Sales Operations (/sales-ops)
- Suppliers (/suppliers)
- Wholesale/Retail (/wholesale-retail)
- Inventory (/inventory)

---

## 4. FILE STRUCTURE

### Main Application Files
- `app/main.py` - Main Flask application with all routes and API endpoints
- `app/routes/api_routes.py` - Separate API blueprint (appears to be placeholder/duplicate)
- `app/customer_segmentation.py` - Customer segmentation module

### Template Organization
```
templates/
├── Primary Pages (Active)
│   ├── executive_dashboard.html
│   ├── customer_ledger.html
│   ├── ar_dashboard.html
│   ├── sales_ops.html
│   ├── suppliers.html
│   ├── wholesale_retail_improved.html
│   ├── gp_analysis.html
│   ├── inventory.html
│   ├── ai_assistant.html
│   └── customer_segmentation.html
├── Navigation
│   ├── navigation.html (current)
│   ├── base_navigation.html
│   ├── shared_navigation.html
│   └── unified_navigation.html
└── Legacy/Duplicate Templates
    └── *_new.html versions
```

### Supporting Modules
```
modules/
├── segmentation/ - Customer segmentation logic
core/ - Core business logic
app/services/ - Service layer
static/ - Static assets (CSS, JS, images)
config/ - Configuration files
```

---

## 5. DATABASE & DATA FILES

### Excel Data Files
- `5.20 akbar (3).xlsx` - Sales/inventory data
- `FULL CUSTOMER LIST 2.18 (4).xlsx` - Customer database

### CSV Files
- `Items- 06202025.csv` & `Items- 06202025 MODIFIED.csv` - Item data
- `Sales - 06202025.csv` & `Sales - 06202025 MODIFIED.csv` - Sales data
- `Sales_with_Categories_06202025.csv` - Categorized sales
- `Items_MSA_Category_Mapping.csv` - MSA category mappings
- Various customer matching and mapping CSVs

### Database
- `georgia_dashboard.db` - SQLite database (appears empty/unused)

---

## 6. ISSUES & RECOMMENDATIONS

### Technical Issues
1. **Duplicate Templates**: Multiple "_new.html" versions exist alongside originals
2. **Duplicate API Routes**: `api_routes.py` contains placeholder duplicates of main.py routes
3. **Navigation Incomplete**: Several pages missing from main navigation
4. **Database**: SQLite DB exists but appears unused (0 bytes)

### Organizational Issues
1. **File Clutter**: Root directory contains many analysis scripts that should be organized
2. **Mixed Concerns**: Business logic mixed with route handlers in main.py
3. **Legacy Code**: Multiple versions of similar functionality (mappers, analyzers)

### Recommended Actions
1. **Clean up duplicate templates** - Remove or archive "_new" versions
2. **Complete navigation** - Add missing pages to navigation menu
3. **Consolidate API routes** - Remove duplicate api_routes.py or properly integrate
4. **Organize scripts** - Move analysis scripts to appropriate directories
5. **Implement proper service layer** - Separate business logic from routes
6. **Database migration** - Decide on database strategy (SQLite vs external)
7. **Remove legacy code** - Archive or delete unused mapper/analyzer scripts

---

## 7. FUNCTIONALITY STATUS SUMMARY

### ✅ **Fully Functional**
- Executive Dashboard with all metrics
- AI Assistant for natural language queries
- Customer Ledger with detailed views
- AR Management and aging analysis
- GP Analysis with multiple dimensions
- Inventory health monitoring
- Supplier management
- Sales operations tracking
- Wholesale vs Retail analysis

### ⚠️ **Partially Functional**
- Customer Segmentation (placeholder API in api_routes.py)

### ❌ **Non-Functional/Issues**
- SQLite database (0 bytes, unused)
- Duplicate route definitions in api_routes.py

---

## 8. API RESPONSE PATTERNS

Most APIs follow this pattern:
```json
{
    "status": "success/error",
    "data": {...},
    "message": "...",
    "timestamp": "..."
}
```

Error responses:
```json
{
    "error": "Error message",
    "status": "error"
}
```

---

## Next Steps for Reorganization

1. **Phase 1: Cleanup**
   - Remove duplicate templates
   - Archive legacy scripts
   - Consolidate navigation files

2. **Phase 2: Restructure**
   - Implement proper MVC pattern
   - Create service layer
   - Organize routes into blueprints

3. **Phase 3: Enhancement**
   - Complete customer segmentation
   - Implement missing features
   - Add comprehensive error handling

4. **Phase 4: Documentation**
   - API documentation
   - Code documentation
   - User guide