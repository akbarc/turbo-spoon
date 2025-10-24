# Data Foundation Plan for New Dashboard

## Date: October 15, 2025

## Overview

Before building the executive dashboard UI, we need to establish a clean data layer that provides:
1. **Accurate Gross Profit** calculations with proper excise tax handling
2. **Customer Grouping** for consolidated AR and sales views
3. **Enhanced Product Categorization** for better insights
4. **Customer Segmentation** that persists across transactions

---

## 1. EXCISE TAX & GROSS PROFIT CALCULATION

### Current Understanding

From `CORRECT_EXCISE_TAX_STRUCTURE.md`:
- **Excise tax is stored in `PUExciseEntry` table**
- **Column `PriceC`** contains the actual excise tax amount
- **Column `SubDescription3`** contains the excise tax type (LC23COLL, LC23PAID, etc.)
- **Join on**: `TransactionEntry.ID = PUExciseEntry.TransactionEntryID`

### Excise Tax Types:
| Type | Count | Description |
|------|-------|-------------|
| LC23COLL | 1,299,799 | Large Cigar 23% Collected (wholesale) |
| LC23PAID | 298,741 | Large Cigar 23% Pre-Paid (retail) |
| SL10PAID | 112,517 | Smokeless Tobacco 10% Paid |
| LT10PAID | 72,704 | Little Tobacco 10% Paid |
| VD07PAID | 52,196 | Vaping Device 7% Paid |
| LT10COLL | 36,995 | Little Tobacco 10% Collected |
| Other | ~47k | Various other types |

### Correct Gross Profit Formula:

```sql
Gross Profit =
    (SalePrice * Quantity) -                    -- Revenue
    (Cost * Quantity) -                          -- Cost of Goods
    COALESCE(ExciseTax, 0)                       -- Excise Tax (from PUExciseEntry.PriceC)
```

### Implementation Plan:

**Create a view or function: `vw_TransactionGrossProfit`**

```sql
CREATE VIEW vw_TransactionGrossProfit AS
SELECT
    te.TransactionNumber,
    te.ID as TransactionEntryID,
    te.TransactionTime,
    t.CustomerID,
    te.ItemID,
    i.Description as ItemName,
    c.Name as CategoryName,
    te.Quantity,
    te.Price as SalePrice,
    te.Cost,

    -- Revenue
    (te.Price * te.Quantity) as Revenue,

    -- Cost of Goods
    (te.Cost * te.Quantity) as COGS,

    -- Excise Tax from PUExciseEntry
    COALESCE(pe.PriceC, 0) as ExciseTax,
    pe.SubDescription3 as ExciseTaxType,

    -- CORRECT Gross Profit
    (te.Price * te.Quantity) -
    (te.Cost * te.Quantity) -
    COALESCE(pe.PriceC, 0) as GrossProfit,

    -- GP Percentage
    CASE
        WHEN (te.Price * te.Quantity) > 0
        THEN ((te.Price * te.Quantity) - (te.Cost * te.Quantity) - COALESCE(pe.PriceC, 0)) / (te.Price * te.Quantity) * 100
        ELSE 0
    END as GPPercent

FROM [dbo].[TransactionEntry] te
JOIN [dbo].[Transaction] t ON te.TransactionNumber = t.TransactionNumber
LEFT JOIN [dbo].[PUExciseEntry] pe ON te.ID = pe.TransactionEntryID
LEFT JOIN [dbo].[Item] i ON te.ItemID = i.ID
LEFT JOIN [dbo].[Category] c ON i.CategoryID = c.ID
WHERE te.Quantity > 0  -- Exclude returns/voids
```

---

## 2. CUSTOMER GROUPING

### Current Logic (from `customer_grouping.py`):

The existing logic uses:
- **Name similarity matching** (fuzzy matching with 85% threshold)
- **Phone number matching** (perfect match = group)
- **Address matching** (supplementary)
- **Smart name handling**:
  - Prioritizes person names over company names
  - Handles name variations (Bob/Robert, etc.)
  - Detects swapped first/last names
  - Identifies family groups by last name

### Issues with Current Approach:
- ❌ Uses pandas (can't use in new dashboard)
- ❌ Groups are not saved/persisted in database
- ❌ Re-calculated every time
- ❌ No way to manually override or confirm groups

### New Implementation Plan:

**Create a customer groups table in database:**

```sql
CREATE TABLE CustomerGroup (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    GroupName NVARCHAR(200) NOT NULL,
    CreatedDate DATETIME DEFAULT GETDATE(),
    ModifiedDate DATETIME DEFAULT GETDATE(),
    Notes NVARCHAR(500)
)

CREATE TABLE CustomerGroupMember (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    GroupID INT NOT NULL,
    CustomerID INT NOT NULL,
    IsPrimary BIT DEFAULT 0,  -- Mark primary contact
    AddedDate DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (GroupID) REFERENCES CustomerGroup(ID),
    FOREIGN KEY (CustomerID) REFERENCES Customer(ID)
)

-- Index for fast lookups
CREATE INDEX IX_CustomerGroupMember_CustomerID ON CustomerGroupMember(CustomerID)
CREATE INDEX IX_CustomerGroupMember_GroupID ON CustomerGroupMember(GroupID)
```

**Python functions (without pandas):**

```python
def find_customer_groups_no_pandas(min_similarity=0.85):
    """
    Find potential customer groups using pure pymssql (no pandas)
    Returns list of suggested groups
    """
    # Implementation using pure pymssql cursor
    # Returns list of dicts with suggested groups

def save_customer_group(group_name, customer_ids, primary_customer_id=None):
    """
    Save a customer group to database
    """
    # Insert into CustomerGroup
    # Insert members into CustomerGroupMember

def get_customer_group_ar_balance(group_id):
    """
    Get combined AR balance for entire group
    """
    # SUM(c.AccountBalance) WHERE CustomerID IN (group members)

def get_group_transaction_history(group_id, days=30):
    """
    Get all transactions for all members of a group
    """
    # Query across all group members
```

---

## 3. ENHANCED PRODUCT CATEGORIZATION

### Current Structure:
- `Category` table exists with basic categories
- Need deeper sub-categorization

### Investigation Needed:
1. What categories exist currently?
2. Do we need sub-categories?
3. Are there product attributes we can use? (Size, Brand, Type)

### Proposed Structure:

```sql
CREATE TABLE ProductSubCategory (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT NOT NULL,
    SubCategoryName NVARCHAR(100),
    DisplayOrder INT DEFAULT 0,
    FOREIGN KEY (CategoryID) REFERENCES Category(ID)
)

CREATE TABLE ItemCategorization (
    ItemID INT PRIMARY KEY,
    CategoryID INT,
    SubCategoryID INT NULL,
    Brand NVARCHAR(100) NULL,
    ProductType NVARCHAR(50) NULL,  -- e.g., 'Cigarette', 'Cigar', 'Vape', 'Snack'
    Size NVARCHAR(50) NULL,
    IsExcisable BIT DEFAULT 0,
    FOREIGN KEY (ItemID) REFERENCES Item(ID),
    FOREIGN KEY (CategoryID) REFERENCES Category(ID),
    FOREIGN KEY (SubCategoryID) REFERENCES ProductSubCategory(ID)
)
```

### Categorization Logic:

Based on item description patterns:
- **Cigarettes**: Pattern matching for pack sizes (20pk, 25pk)
- **Cigars**: Based on PUExciseEntry presence (LC23COLL/LC23PAID)
- **Vaping**: Based on excise type (VD07PAID, VC05PAID)
- **Smokeless**: Based on excise type (SL10PAID)
- **Food/Beverage**: Non-excise items in specific categories

---

## 4. CUSTOMER SEGMENTATION

### Segmentation Criteria:

**Tier 1: Transaction-based Segments**
- **VIP**: $500K+ annual sales OR $50K+ AR balance
- **Major Account**: $100K-$500K annual sales OR $10K-$50K AR
- **Regular**: $10K-$100K annual sales OR $1K-$10K AR
- **Small**: <$10K annual sales OR <$1K AR
- **Inactive**: No purchases in 90 days

**Tier 2: Payment Behavior**
- **Excellent**: Always pays within 30 days, no NSF
- **Good**: Pays within 45 days, minimal NSF
- **Slow Pay**: Regularly pays 60-90 days
- **At Risk**: Balance over 90 days, multiple NSF

**Tier 3: Product Preference**
- **Tobacco-Heavy**: >70% sales from tobacco products
- **Mixed**: Balanced product mix
- **Convenience**: >70% from food/beverage

### Implementation:

```sql
CREATE TABLE CustomerSegment (
    CustomerID INT PRIMARY KEY,

    -- Sales Tier
    SalesTier VARCHAR(20),  -- VIP, Major, Regular, Small, Inactive
    AnnualSales DECIMAL(18,2),
    LastPurchaseDate DATETIME,

    -- Payment Tier
    PaymentTier VARCHAR(20),  -- Excellent, Good, Slow, AtRisk
    AvgDaysToPay INT,
    NSFCount INT,
    OverdueBalance DECIMAL(18,2),

    -- Product Preference
    ProductProfile VARCHAR(20),  -- Tobacco-Heavy, Mixed, Convenience
    TobaccoSalesPct DECIMAL(5,2),

    -- Timestamps
    LastCalculated DATETIME DEFAULT GETDATE(),

    FOREIGN KEY (CustomerID) REFERENCES Customer(ID)
)

-- Update this table nightly or weekly
```

**Calculation function:**

```python
def calculate_customer_segments():
    """
    Calculate and update customer segments
    Run nightly via scheduled job
    """
    # Calculate sales tier
    # Calculate payment tier
    # Calculate product profile
    # Update CustomerSegment table
```

---

## 5. NEXT STEPS - IMPLEMENTATION PLAN

### Phase 1: Excise Tax & GP (Priority 1)
1. ✅ Read excise tax documentation (DONE)
2. Create `vw_TransactionGrossProfit` view
3. Test GP calculations against known good data
4. Verify against PU Excise report
5. Create Python helper functions

### Phase 2: Customer Groups (Priority 2)
1. Create `CustomerGroup` and `CustomerGroupMember` tables
2. Port grouping logic from pandas to pure pymssql
3. Create group management API endpoints
4. Test with known customer groups

### Phase 3: Product Categorization (Priority 3)
1. Query existing categories
2. Analyze item descriptions for patterns
3. Create sub-category structure
4. Implement categorization logic
5. Create helper functions

### Phase 4: Customer Segmentation (Priority 4)
1. Create `CustomerSegment` table
2. Implement segment calculation logic
3. Create nightly update job
4. Add API endpoints

### Phase 5: Dashboard Integration
1. Create data layer API module
2. Build dashboard endpoints using foundation
3. Test all calculations
4. Document for future use

---

## Questions to Answer:

1. **Excise Tax**: Should we create the view in database or calculate in Python?
   - **Recommendation**: Create SQL view for performance

2. **Customer Groups**: Do you want to review/approve suggested groups before saving?
   - **Recommendation**: Build approval workflow

3. **Categorization**: What level of detail do you need? Brand-level? Size-level?
   - **Recommendation**: Start with Category + Brand

4. **Segmentation**: Are the tier thresholds correct? ($500K for VIP, etc.)
   - **Recommendation**: Review with actual data

5. **Update Frequency**: How often should segments recalculate?
   - **Recommendation**: Nightly for segments, real-time for GP

---

## Files to Create:

1. `data_foundation/excise_gross_profit.py` - GP calculations
2. `data_foundation/customer_groups.py` - Group management (no pandas)
3. `data_foundation/product_categorization.py` - Product categories
4. `data_foundation/customer_segmentation.py` - Segment calculations
5. `data_foundation/data_layer_api.py` - Unified API for dashboard

## SQL Scripts to Create:

1. `sql/create_view_transaction_gross_profit.sql`
2. `sql/create_customer_group_tables.sql`
3. `sql/create_product_categorization_tables.sql`
4. `sql/create_customer_segment_table.sql`

---

**Next Action**: Let's discuss priorities and start with Phase 1 (Excise Tax & GP)?
