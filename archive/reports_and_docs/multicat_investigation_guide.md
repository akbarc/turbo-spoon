# MultiCat Investigation Guide

## Specific Examples to Check in MultiCat

### 1. Winston Products
Check these exact products in MultiCat:

| Product Name | Your POS UPC | MSA Shows | What to Look For |
|-------------|--------------|-----------|-------------------|
| WINST WHITE BOX | 090500100133 | 123007031300 | Does MultiCat show BOTH codes? |
| WINST GOLD 100 BOX | 090500100126 | 123001591350 | Is 123... stored as "Manufacturer UPC"? |
| WINST RED BOX | 090500100096 | 123001121300 | Check if there's a "Master UPC" field |

**Key Questions:**
- Does MultiCat have multiple UPC fields (Retail UPC, Manufacturer UPC, Master UPC)?
- Is there a "UPC Cross Reference" section?
- Does it show ITG Brands as the manufacturer with their codes?

### 2. Check for UPC Transformation Patterns

Test if MSA UPCs are transformed versions of POS UPCs:

#### Pattern A: Check Digit Recalculation
```
POS: 090500100133
     09050010013 (remove last digit)
     + recalculate check digit for different standard
     = Could give different UPC?
```

#### Pattern B: Prefix Substitution
```
POS: 090500100133
Replace prefix: 090 → 123
Middle stays same? 500100133
Result: 123500100133 (not quite matching... but close?)
```

#### Pattern C: Segment Rearrangement
```
POS:  090-50010-0133
MSA:  123-00703-1300
Check if segments are rearranged or encoded
```

### 3. Specific Things to Check in MultiCat

#### A. Product Setup Screen
Look for fields like:
- Primary UPC
- Secondary UPC  
- Manufacturer UPC
- Vendor UPC
- MSA Reporting UPC
- State Reporting Code

#### B. Vendor/Supplier Section
Check if Winston products show:
- Vendor: Your distributor (uses 090... UPCs)
- Manufacturer: ITG Brands (uses 123... UPCs)

#### C. MSA Configuration
Look for:
- "MSA UPC Override"
- "Use Manufacturer UPC for MSA"
- "State Reporting Configuration"

### 4. Transaction Codes Investigation

These appear in PUR records but not BID:

| Transaction Code | Used Times | What to Check |
|-----------------|------------|---------------|
| 000282001 | 414 | Is this a MultiCat internal SKU? |
| 000317002 | 390 | Category code? |
| 000259003 | 373 | Department code? |

**In MultiCat, check:**
- Is there a "Transaction Code" separate from UPC?
- Are these category or department codes?
- Do products have both a UPC and a transaction code?

### 5. Test These Specific Patterns

#### Test 1: Zero Movement (like customers)
```python
# Your customer pattern:
POS: 4042922594 → Remove first → 042922594 → Move 0 → 429225940

# Try same with UPCs:
POS: 090500100133
     Remove first: 90500100133 (11 digits)
     Not matching...
```

#### Test 2: Barcode Format Conversion
```
UPC-A (12 digits): 090500100133
EAN-13 (13 digits): 0090500100133 or different?
MSA shows 13-digit: 123007031300

Is MultiCat converting between formats?
```

#### Test 3: Vendor to Manufacturer Mapping
```
Your POS: 090... (your vendor's prefix)
MSA File: 123... (ITG Brands prefix)

Check if MultiCat has a table like:
Vendor_UPC → Manufacturer_UPC
090500100133 → 123007031300
```

### 6. Database Tables to Look For in MultiCat

If MultiCat has a database, check for tables named:
- `UPC_CrossReference`
- `Manufacturer_Codes`  
- `MSA_Reporting_Codes`
- `Product_Aliases`
- `Vendor_Items`
- `Master_Products`

### 7. Quick Validation Test

Pick 5 products that ARE mapping correctly (the 83.4%):

| Product | POS UPC | MSA UPC2 (secondary) |
|---------|---------|---------------------|
| ZYN 6MG WINTERGREEN | 609249903426 | 0609249903426 |

**Question:** Do these products ALSO have different manufacturer UPCs in MultiCat that just aren't being used?

### 8. The Smoking Gun to Find

Look for a screen or report in MultiCat that shows:
```
Product: WINSTON WHITE BOX
Retail UPC: 090500100133 (what you use)
Manufacturer UPC: 123007031300 (what MSA uses)
MSA Reporting: Use Manufacturer UPC ✓
```

## What to Report Back

1. Does MultiCat have multiple UPC fields per product?
2. Is there a "Manufacturer UPC" or "Master UPC" field?
3. Can you find where 123007031300 is stored for Winston?
4. Is there a UPC cross-reference feature?
5. What does MultiCat show for the transaction codes (000282001)?

This will tell us exactly where the 16.6% unmapped UPCs are coming from!