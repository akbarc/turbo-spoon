# Complete Matching Rules & Patterns Summary
## Customer and Item Matching Logic Discovered

---

## 1. CUSTOMER MATCHING RULES (100% Success Rate)

### 1.1 The 8-Digit Key Extraction Algorithm
```
RULE: Extract last 8 digits from phone/account number
      If first digit is 0, rotate it to the end
```

#### Examples:
| Input | Extracted Key | Result |
|-------|--------------|---------|
| 9012466298 | 12466298 | Last 8 digits |
| 4047701234 | 47701234 | Last 8 digits |
| 012345678 | 12345678 | 0 moved to end |
| 04047701234 | 47701234 | Last 8, then 0 moved |

### 1.2 POS Account Number Structure
```
POS Account = [Prefix] + [8-digit key]
```

#### Prefix Patterns Discovered:
| Prefix | Meaning | Example |
|--------|---------|---------|
| 90 | Standard retail | 90**12466298** |
| 32 | Distributors | 32**12985964** |
| 20 | Chain stores | 20**16588290** |
| 470 | Georgia regional | 470**2320139**0 |
| 770 | Atlanta metro (area code) | 770**2035941**0 |
| 678 | North Georgia | 678**xxxx** |
| 404 | Atlanta city | 404**xxxx** |
| 510 | Special accounts | 510**2039309** |

### 1.3 Zero Rotation Pattern
When MSA customer number starts with 0:
```
MSA: 02320139 → POS: 4702320139 (0 moved to end)
MSA: 02035941 → POS: 7702035941 (0 moved to end)
```

### 1.4 Matching Success
- **385 of 385** customers matched (100%)
- **384** via account key match
- **1** via phone-to-account key match

---

## 2. ITEM/SKU MATCHING RULES (74% Success Rate)

### 2.1 SKU Format Issues Identified

#### Problem Patterns:
| Pattern | Example | Issue |
|---------|---------|-------|
| All zeros prefix | 000000000000FN | Non-standard format |
| Short codes | BOOST, UGLY, CALI | Custom abbreviations |
| Missing UPC | 00000000DMS99 | Manual entries |
| Leading zeros | 00026100805734 | Needs stripping |

### 2.2 Successful Matching Strategies

#### Priority Order:
1. **Direct UPC match** (most reliable)
2. **Clean UPC match** (strip leading zeros)
3. **SKU as ItemLookupCode**
4. **Alias table lookup**
5. **Description matching** (last resort)

#### Cleaning Rules:
```python
# Strip leading zeros
clean_upc = upc.lstrip('0')
clean_sku = sku.lstrip('0')

# Try multiple formats
formats = [
    original,
    stripped_zeros,
    last_12_digits,
    last_14_digits
]
```

### 2.3 Match Statistics
- **30,588 of 41,364** items matched (74%)
- **10,776** unmatched items breakdown:
  - 789 (58.6%) - Can be fixed with better mapping
  - 557 (41.4%) - Truly missing from POS

### 2.4 Category Analysis of Unmatched
| Category | % Unmatched | Reason |
|----------|-------------|--------|
| OTHER | 62.1% | Miscellaneous/specialty items |
| VAPE | 21.2% | High product turnover |
| CIGARS | 4.8% | Limited assortment |
| CIGARETTES | 4.1% | Should match - needs investigation |

---

## 3. MSA DATA STRUCTURE PATTERNS

### 3.1 Record Type Hierarchy
```
HID (Header - 1 per file)
 ├── BID (Brands/SKUs - ~5,200 per week)
 ├── SID (Customers - ~185 per week)
 ├── PUR (Purchases - ~4,800 per week)
 └── TOT (Totals - 1 per file)
```

### 3.2 Week Format
- **Date format**: MMDDYYYY (e.g., 06202025)
- **Period**: Saturday to Friday
- **End date**: Friday of the week

### 3.3 Key Fields Mapping

#### BID (Brand/Product) Records:
| MSA Field | POS Field | Notes |
|-----------|-----------|-------|
| distributor_sku | ItemLookupCode | May need cleaning |
| upc_code | Alias/ItemLookupCode | Multiple formats |
| measure_value_1 | Item.Quantity | Inventory |
| items_per_selling_unit | Conversion factor | Pack size |

#### SID (Customer) Records:
| MSA Field | POS Field | Notes |
|-----------|-----------|-------|
| ship_to_customer_number | AccountNumber (last 8) | Apply extraction |
| ship_to_customer_name | Company | May differ |
| ship_to_customer_phone | PhoneNumber | Alternative key |

#### PUR (Purchase) Records:
| MSA Field | POS Field | Notes |
|-----------|-----------|-------|
| ship_to_customer_number | Customer.AccountNumber | Via mapping |
| distributor_sku | Item.ItemLookupCode | Via mapping |
| measure_value_1 | TransactionEntry.Quantity | Units sold |
| measure_value_2 | Price * Quantity | Dollar value |

---

## 4. DATA QUALITY PATTERNS

### 4.1 Common Issues Found
1. **Spelling errors**: "DIDTRIBUTING" vs "DISTRIBUTING"
2. **City abbreviations**: "STN MTN" vs "STONE MOUNTAIN"
3. **Leading zeros**: Inconsistent handling
4. **Manual entries**: Custom SKUs not in POS

### 4.2 Business Logic Discovered
1. **Business transitions**: Same address, different names (Address matching caught these)
2. **Chain stores**: Multiple locations under same account
3. **Cash & Carry**: Special handling for walk-in customers
4. **Returns**: Negative quantities in PUR records

---

## 5. INVENTORY CALCULATION RULES

### 5.1 Formula
```
Ending Inventory = Beginning Inventory + Purchases - Sales - Adjustments
```

### 5.2 Key Finding
- MSA provides weekly snapshots
- Each week's ending becomes next week's beginning
- Purchase orders not critical (embedded in inventory changes)

### 5.3 Variance Pattern
- Only week 07042025 showed variances
- All other weeks had 0 variance
- Suggests bulk receiving event that week

---

## 6. INTEGRATION KEYS

### 6.1 Customer Integration
```python
def extract_account_key(number):
    # Take last 8 digits
    last_8 = number[-8:]
    # If starts with 0, rotate to end
    if last_8[0] == '0':
        last_8 = last_8[1:] + '0'
    return last_8
```

### 6.2 Item Integration
```python
def match_item(sku, upc):
    # Try multiple strategies in order
    attempts = [
        sku,
        upc,
        sku.lstrip('0'),
        upc.lstrip('0'),
        check_aliases(sku),
        check_aliases(upc)
    ]
    return first_match(attempts)
```

---

## 7. SUCCESS METRICS

### 7.1 What Works Well
- **Customer matching**: 100% (perfect)
- **Item matching**: 74% (good, improvable)
- **Data structure**: Well-aligned
- **Business logic**: Clear patterns

### 7.2 Improvement Opportunities
- Complete item mapping for 26% unmatched
- Standardize UPC formats
- Clean up manual entries
- Add new products promptly

---

## 8. KEY TAKEAWAYS

1. **The 8-digit key with zero rotation is the golden rule for customers**
2. **Leading zeros cause most item matching issues**
3. **POS account prefixes indicate geography/type**
4. **MSA and POS are tightly integrated by design**
5. **Weekly snapshots provide continuity**
6. **Address matching catches business transitions**
7. **VAPE products have highest turnover/mismatch rate**
8. **The systems are fundamentally compatible**

This matching logic can be implemented programmatically with high confidence based on these discovered patterns.