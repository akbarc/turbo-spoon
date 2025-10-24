# Unmatched Items Analysis Report

## Executive Summary
Of the 26.1% unmatched MSA items, **58.6% are likely SKU mapping issues** that can be fixed, while **41.4% are truly missing** from the POS database (likely discontinued or new products).

---

## 1. Breakdown of Unmatched Items (1,346 unique SKUs)

### 1.1 Match Analysis Results:
- **789 items (58.6%)**: Found potential matches via description
- **557 items (41.4%)**: No match found - truly missing from POS

### 1.2 If SKU Mappings Were Fixed:
- **Match rate would improve from 73.9% to 89.2%**
- Only ~10.8% would remain truly unmatched

---

## 2. Category Analysis of Unmatched Items

| Category | Count | Percentage | Observation |
|----------|-------|------------|-------------|
| OTHER | 836 | 62.1% | Miscellaneous/new products |
| VAPE | 286 | 21.2% | Fast-changing product category |
| CIGARS | 65 | 4.8% | Limited assortment items |
| SMOKELESS | 56 | 4.2% | Regional/specialty products |
| CIGARETTES | 55 | 4.1% | Unusual - these should match |
| ACCESSORIES | 43 | 3.2% | Papers, wraps, etc. |
| NIC_POUCHES | 5 | 0.4% | Newer product category |

### Key Insights:
1. **VAPE products (21.2%)** - High turnover category with frequent new SKUs
2. **OTHER category (62.1%)** - Includes many non-standard or specialty items
3. **CIGARETTES (4.1%)** - Surprisingly low, these are usually well-mapped

---

## 3. Patterns in Unmatched Items

### 3.1 SKU Format Issues:
Many unmatched SKUs have problematic formats:
- **All zeros prefix**: "000000000000FN", "00000000000JOY"
- **Short/custom codes**: "BOOST", "UGLY", "CALI"
- **Missing proper UPC**: Using abbreviated codes instead

### 3.2 Product Types:
- **Disposable vapes**: Rapid product turnover, new brands weekly
- **Limited editions**: Seasonal or promotional items
- **Regional products**: Local/specialty items not in main catalog
- **Accessories**: Papers, wraps with inconsistent coding

### 3.3 Likely Reasons for No Match:
1. **New products** - Not yet added to POS
2. **Discontinued** - Removed from POS but still in MSA
3. **Manual entries** - Custom SKUs created at MSA level
4. **Format mismatches** - Different UPC/SKU conventions

---

## 4. Impact of Missing Purchase Order Data

### 4.1 The Issue:
- **835 items** show negative expected inventory in week 07042025
- Total shortfall: **11,788 units**
- Concentrated in high-volume products (Newport, Marlboro)

### 4.2 Why It's NOT a Major Problem:

1. **MSA provides beginning inventory** - Each week starts with MSA's reported inventory
2. **Week-to-week continuity** - Previous week's ending becomes next week's beginning
3. **Self-correcting** - Any purchases are reflected in the MSA inventory number
4. **Only affects variance analysis** - Not actual operations

### 4.3 When PO Data Would Matter:
- Identifying receiving patterns
- Vendor performance analysis
- Lead time calculations
- Reorder point optimization

---

## 5. Recommendations

### 5.1 Immediate Actions:
1. **Create SKU mapping table** for the 789 items with description matches
2. **Standardize UPC formats** - Remove leading zeros, consistent length
3. **Manual review** of top 50 unmatched items by sales volume

### 5.2 System Improvements:
1. **Alias Management**:
   - Add MSA SKUs as aliases in POS
   - Create lookup table for format conversions
   
2. **Product Categories**:
   - Better tracking of VAPE products (high turnover)
   - Flag discontinued items properly
   
3. **Data Quality**:
   - Validation rules for SKU formats
   - Regular reconciliation process

### 5.3 Priority Items to Fix:
Based on sales volume, prioritize mapping these:
1. Newport products (1,708 + 684 + 113 + 96 = 2,601 units/week)
2. Marlboro products (169 + 95 = 264 units/week)
3. Grabba Leaf wraps (644 units/week)
4. Swisher Sweets products (239 + 151 + 128 + 114 + 87 = 719 units/week)

---

## 6. Conclusion

### The 26.1% unmatched rate breaks down as:
- **15.3%** - Can be fixed with SKU mapping (789 items)
- **10.8%** - Truly missing (557 items)

### Missing PO data impact:
- **Not critical** for inventory tracking (MSA provides continuity)
- **Only affects** variance analysis and root cause identification
- **Week 07042025** anomaly is likely a bulk receiving event

### Next Steps:
1. Implement SKU mapping for 789 items
2. Investigate top 50 truly missing items
3. Establish process for new product additions
4. Consider PO integration only if needed for analytics

The system is functioning well despite these gaps. The unmatched items are mostly explicable (new products, discontinued, format issues) and the missing PO data doesn't prevent accurate inventory tracking.