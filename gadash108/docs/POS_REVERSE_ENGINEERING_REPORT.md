# POS System Reverse Engineering Report
## Based on MSA Data Analysis

### Executive Summary
Through analysis of 8 weeks of MSA (Management Science Associates) data and comparison with the POS database, we have reverse-engineered the structure and data flow of the point-of-sale system.

---

## 1. Data Architecture

### 1.1 Database Schema (Reconstructed)

#### Core Tables Identified:
- **Item** - Product catalog with 12,520+ items
- **Transaction** - Sales transactions
- **TransactionEntry** - Line items for each sale
- **Customer** - Customer records
- **Alias** - UPC/barcode aliases for items
- **PurchaseOrder** - Incoming inventory
- **PurchaseOrderEntry** - Purchase order line items

### 1.2 Key Data Relationships
```
Item (1) ←→ (N) Alias          [Multiple UPCs per item]
Item (1) ←→ (N) TransactionEntry [Sales records]
Transaction (1) ←→ (N) TransactionEntry [Order details]
Customer (1) ←→ (N) Transaction [Customer purchases]
```

---

## 2. Inventory Management Logic

### 2.1 Inventory Formula
```
Ending Inventory = Beginning Inventory + Purchases - Sales - Adjustments
```

### 2.2 Key Findings:
- **73.9% Match Rate**: Successfully matched 30,588 of 41,364 MSA records to POS items
- **Inventory Variance**: Only 2% of records show variance, concentrated in week 07042025
- **Average POS vs MSA Difference**: 30.40 units

### 2.3 Variance Patterns Identified:

#### Week 07042025 Anomaly:
- 836 items showed variance (all other weeks had 0)
- Top variances were all positive (MSA > Expected)
- Suggests a bulk inventory adjustment or receiving event

#### Top Variance Items:
1. Newport Menthol 100 Box: +1,708 units
2. Newport Menthol Box K/S: +684 units
3. Grabba Leaf Cigar Wraps: +644 units

---

## 3. Product Catalog Structure

### 3.1 SKU/UPC Mapping
- **Primary Key**: ItemLookupCode (in POS)
- **MSA SKU**: distributor_sku (14 digits, often padded with zeros)
- **UPC Formats**: Multiple formats supported (12, 13, 14 digits)

### 3.2 Product Categories (MSA Codes):
- **003231**: Cigarettes (most common)
- **003211**: Moist Snuff
- **003251**: Large Cigars
- **003261**: Papers/Tubes/Wraps

### 3.3 Inventory Units:
- Items tracked by "selling unit" (cartons, sleeves, packs)
- Conversion factor in "items_per_selling_unit" field

---

## 4. Transaction Processing

### 4.1 Sales Flow:
1. **POS Transaction** → Creates Transaction record
2. **Line Items** → Creates TransactionEntry records
3. **Inventory Update** → Decrements Item.Quantity
4. **MSA Export** → Weekly aggregation as PUR records

### 4.2 Weekly Processing Cycle:
- **Period**: Saturday to Friday (week ending Friday)
- **Records Generated**:
  - HID: Header (1 per file)
  - BID: Brand/SKU records (~5,200 per week)
  - SID: Customer records (~185 per week)
  - PUR: Purchase/sales records (~4,800 per week)
  - TOT: Totals (1 per file)

---

## 5. Customer/Store Management

### 5.1 Customer Structure:
- **Average**: 185-196 unique ship-to locations per week
- **Customer Types**: Retail stores, wholesalers, cash & carry
- **Geographic**: Primarily Georgia-based

### 5.2 Customer Identification:
- Ship-to customer number (8 digits)
- Shipping number (8 digits)
- Optional extension field

---

## 6. Data Quality Issues

### 6.1 Unmatched Items (26.1%):
Common reasons for failed matches:
- New products not yet in POS
- Discontinued items
- UPC format mismatches
- Alias records missing

### 6.2 Inventory Discrepancies:
Primary causes identified:
- **Missing purchase data**: No purchase orders in analysis period
- **Timing differences**: Week-end cutoff misalignments
- **Returns**: Not properly tracked
- **Adjustments**: Manual inventory corrections

---

## 7. POS to MSA Transformation Logic

### 7.1 Data Extraction:
```python
# Weekly extraction process
1. Query transactions for date range
2. Aggregate by SKU and customer
3. Calculate inventory positions
4. Format as fixed-width records
5. Generate MSA file
```

### 7.2 Field Mappings:
| POS Field | MSA Field | Transformation |
|-----------|-----------|----------------|
| ItemLookupCode | distributor_sku | Pad to 14 digits |
| Item.Quantity | measure_value_1 (BID) | Direct copy |
| TransactionEntry.Quantity | measure_value_1 (PUR) | Sum by SKU |
| Item.Description | product_description | Truncate to 50 chars |

---

## 8. Recommendations

### 8.1 Immediate Actions:
1. **Investigate Week 07042025**: Large variance suggests data issue
2. **Complete UPC Mapping**: 26.1% items need mapping
3. **Add Purchase Tracking**: Include PO data in analysis

### 8.2 System Improvements:
1. **Real-time Sync**: Implement daily inventory reconciliation
2. **Audit Trail**: Track all inventory adjustments
3. **UPC Standardization**: Consistent format across systems
4. **Return Processing**: Proper return transaction tracking

---

## 9. Technical Specifications

### 9.1 MSA File Format:
- **Type**: Fixed-width ASCII
- **Encoding**: UTF-8
- **Line Length**: Variable by record type
- **Numeric Fields**: Real numbers with floating decimal

### 9.2 Database:
- **Server**: MS SQL Server
- **Database**: GAWDB
- **Key Tables**: 104 identified
- **Active Items**: 12,520+

---

## Conclusion

The POS system follows a standard retail architecture with:
- Comprehensive product catalog with alias support
- Transaction-based sales tracking
- Weekly batch processing for MSA reporting
- 74% successful data matching rate

Key improvement areas:
- Purchase order integration
- UPC/SKU mapping completion
- Inventory adjustment tracking
- Return processing enhancement

The system is fundamentally sound but requires better integration between POS and MSA reporting to achieve higher accuracy.