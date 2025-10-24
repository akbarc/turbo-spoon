# CORRECT EXCISE TAX STRUCTURE - FROM POS SYSTEM

## Date: October 6, 2025

## CRITICAL FINDING
The POS system stores excise tax in the `PUExciseEntry` table, NOT in custom calculated fields. All previous custom calculations were WRONG.

## Database Structure

### PUExciseEntry Table
**Purpose**: Stores excise tax information for tobacco/vaping products as recorded by the POS system at point of sale.

**Key Columns**:
- `ID` - Primary key
- `TransactionNumber` - Links to transaction
- `TransactionEntryID` - Links to TransactionEntry.ID (FK)
- `ItemID` - The item sold
- `Quantity` - Quantity sold
- `Price` - Sale price
- `PriceC` - **EXCISE TAX AMOUNT** (this is the actual excise tax paid/collected)
- `SubDescription3` - **EXCISE TAX TYPE** (e.g., LC23COLL, LC23PAID, LT10PAID)
- `TransactionTime` - When the transaction occurred

## Excise Tax Types (SubDescription3)

Based on analysis of 1.9M+ excise transactions:

| Type | Count | Description |
|------|-------|-------------|
| LC23COLL | 1,299,799 | Large Cigar 23% Collected (warehouse/wholesale) |
| LC23PAID | 298,741 | Large Cigar 23% Pre-Paid (retail purchase) |
| SL10PAID | 112,517 | Smokeless Tobacco 10% Paid |
| LT10PAID | 72,704 | Little Tobacco 10% Paid |
| VD07PAID | 52,196 | Vaping Device 7% Paid |
| LT10COLL | 36,995 | Little Tobacco 10% Collected |
| LC25COLL | 18,315 | Large Cigar 25% Collected (old rate) |
| VD07COLL | 11,798 | Vaping Device 7% Collected |
| VC05COLL | 10,115 | Vaping Consumable 5% Collected |
| VC05PAID | 5,662 | Vaping Consumable 5% Paid |

## How to Join

```sql
SELECT
    te.ID as TransEntryID,
    te.TransactionNumber,
    te.ItemID,
    i.Description,
    te.Quantity,
    te.Price as SalePrice,
    pe.PriceC as ExciseTax,           -- This is the excise tax amount
    pe.SubDescription3 as ExciseType,  -- This is the excise tax type
    te.TransactionTime
FROM TransactionEntry te
LEFT JOIN PUExciseEntry pe ON te.ID = pe.TransactionEntryID
LEFT JOIN Item i ON te.ItemID = i.ID
WHERE pe.SubDescription3 IS NOT NULL
    AND pe.SubDescription3 != ''
```

## Calculation Examples (from real data)

### Example 1: GT WOODS NP 15/2CT DK ED BOLD
- Quantity: 1
- Sale Price: $21.49
- Excise Tax (PriceC): $3.67
- Excise Type: LC23PAID (23% pre-paid)
- Per Unit: $3.67

### Example 2: SS BLK 2/1.49 30/2CT SMOOTH
- Quantity: 4
- Sale Price: $32.59
- Excise Tax (PriceC): $5.34
- Excise Type: LC23COLL (23% collected)
- Per Unit: $1.335

## Important Notes

1. **Do NOT calculate excise tax** - Use the `PriceC` column from `PUExciseEntry`
2. **Excise tax is per transaction line item**, not per pack
3. **Not all items have excise tax** - LEFT JOIN is required
4. **PAID vs COLL matters**:
   - PAID = Pre-paid at wholesale/distributor level (retail purchases)
   - COLL = Collected at point of sale (warehouse/wholesale)
5. **Excise tax is already recorded** - No need for weight-based calculations
6. **Transaction dates**: Use TransactionEntry.TransactionTime, not PUExciseEntry.TransactionTime

## What Was Wrong Before

❌ WRONG: Calculating excise tax using category weights and rates
❌ WRONG: Using Item.SubDescription3 for excise type
❌ WRONG: Creating custom tax calculations based on department
❌ WRONG: Assuming all cigarettes have the same tax rate

✅ CORRECT: Using PUExciseEntry.PriceC directly
✅ CORRECT: Using PUExciseEntry.SubDescription3 for excise type
✅ CORRECT: Joining TransactionEntry to PUExciseEntry by TransactionEntryID

## How This Affects Reporting

All revenue/sales queries must:
1. LEFT JOIN to PUExciseEntry on TransactionEntry.ID = PUExciseEntry.TransactionEntryID
2. Use pe.PriceC for excise tax amounts
3. NOT calculate or derive excise tax from any other source
4. Handle NULL excise tax (items without excise tax)

## Date Range

- Data available from: 2013-01-07
- Latest transaction: 2025-10-06
- Total excise transactions: 1,920,109
