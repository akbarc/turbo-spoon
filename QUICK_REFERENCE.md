# Quick Reference - Data Foundation

**Last Updated**: October 15, 2025

---

## Status

✅ **Excise Tax Fix**: COMPLETE - CIGAR GA now positive, GP corrected by +$1,350
✅ **Department Hierarchy**: COMPLETE - 6 departments, 82 categories mapped
✅ **Dashboard**: RUNNING at http://100.126.106.37:8081
⏳ **Customer Grouping**: Phase 1B - Not started

---

## Daily Commands

### Update Today's GP Data:
```bash
cd /Users/akbarchranya/georgiadashboard
python3 populate_gp_summary.py
```

### View Department Performance:
```bash
python3 test_department_gp.py
```

### Verify Excise Tax is Correct:
```bash
python3 verify_corrected_gp.py
```

---

## Key Insights (Oct 15, 2025)

**Department Performance**:
- **Tobacco**: $199K revenue, 2.8% margin (94.5% of total)
- **Food & Beverage**: $1.9K revenue, **19.4% margin** ⭐
- **Household**: $1.6K revenue, **19.8% margin** ⭐
- **Vaping**: $6.1K revenue, 1.4% margin ⚠️ (needs review)

**Total**: $211K revenue, $6.7K GP, 3.2% margin

---

## Database Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `GP_Daily_Summary` | Pre-calculated daily GP by category | Updated daily |
| `ExciseTaxTypes` | Lookup for PAID vs COLL excise | 14 tax types |
| `Departments` | 6 main product departments | 6 departments |
| `CategoryMapping` | Links categories to departments | 82 mappings |

---

## Departments

1. **Tobacco & Smoking** (16 categories) - Cigarettes, Cigars, Smokeless, Papers
2. **Vaping & Alternatives** (7 categories) - E-cigs, Nicotine Pouches, CBD
3. **Food & Beverage** (8 categories) - Candy, Snacks, Drinks
4. **Health & Wellness** (6 categories) - Medicine, Vitamins, Beauty
5. **Household & General** (24 categories) - Cleaning, Electronics, Novelty
6. **Other** (21 categories) - Misc, Temp, Inactive

---

## Critical Files

**Main Scripts**:
- `populate_gp_summary.py` - Update GP data (run daily)
- `gp_dashboard.py` - Web dashboard
- `test_department_gp.py` - Department analysis

**Setup (one-time)**:
- `create_excise_tax_lookup.py` - Creates excise lookup table
- `create_department_structure.py` - Creates department hierarchy

**Documentation**:
- `SESSION_SUMMARY.md` - Full session details
- `EXCISE_TAX_FIX_COMPLETE.md` - Excise tax fix details
- `PRODUCT_CATEGORIZATION_PLAN.md` - Department design

---

## Useful SQL Queries

### Department GP Today:
```sql
SELECT
    d.DepartmentName,
    SUM(gp.Revenue) as Revenue,
    SUM(gp.GrossProfit) as GP
FROM GP_Daily_Summary gp
INNER JOIN CategoryMapping cm ON gp.CategoryID = cm.CategoryID
INNER JOIN Departments d ON cm.DepartmentID = d.DepartmentID
WHERE gp.BusinessDate = CAST(GETDATE() AS DATE)
GROUP BY d.DepartmentName
ORDER BY GP DESC
```

### Category GP Today:
```sql
SELECT
    CategoryName,
    Revenue,
    GrossProfit,
    GrossProfit / Revenue * 100 as Margin
FROM GP_Daily_Summary
WHERE BusinessDate = CAST(GETDATE() AS DATE)
ORDER BY GrossProfit DESC
```

### Pre-Paid vs Collected Excise:
```sql
SELECT
    TaxType,
    IsPrePaid,
    CASE WHEN IsPrePaid = 1 THEN 'PRE-PAID (in COGS)' ELSE 'COLLECTED (at POS)' END as Type
FROM ExciseTaxTypes
ORDER BY IsPrePaid DESC, TaxType
```

---

## Dashboard Access

**URL**: http://100.126.106.37:8081

**API Endpoints**:
- `/api/gp/today` - Today's summary
- `/api/gp/categories` - Category breakdown

---

## Known Issues

⚠️ **NICOTINE POUCHES showing negative GP** (-21.9%)
**Cause**: FRE products priced below cost ($9.99 price vs $18.50 cost)
**Solution**: Update POS pricing for FRE items (not our scope)

---

## Database Credentials

**Read-Only** (for queries):
- Server: 10.1.10.105
- User: amchranya
- Password: 2000Akbar!
- Database: GAWDB

**Admin** (for table creation):
- Server: 10.1.10.105
- User: sa
- Password: Tech7World
- Database: GAWDB

---

## Technical Notes

- TDS Version: 7.0 (SQL Server 2008 R2)
- NO PANDAS (pure pymssql)
- All POS table operations are READ-ONLY
- GP calculations use ExciseTaxTypes lookup for speed
- Pre-calculated summaries for instant queries

---

## What's Next

**Phase 1B - Customer Grouping**:
- Fuzzy customer name matching
- Consolidate duplicate customers
- Create CustomerGroup tables
- Link to GP analysis

---

## Quick Wins

1. **Tobacco drives 94.5% of revenue** - but only 2.8% margin
2. **Food & Household have 19%+ margins** - opportunity to grow these
3. **Vaping margin only 1.4%** - review pricing strategy
4. **CIGAR GA is profitable** - was showing negative due to excise bug (now fixed!)

---

**For detailed information, see SESSION_SUMMARY.md**
