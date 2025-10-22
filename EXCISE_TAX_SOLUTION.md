# Excise Tax Calculation Solution

## Problem

Initial attempts to calculate excise tax by querying Item.SubDescription3 and calculating `Cost * Quantity * Rate` in Python were **incorrect**.

The actual excise tax amount is more complex than a simple percentage of cost, and is already calculated and stored in the `PUExciseEntry` table.

## Solution

The correct approach is to:

1. **Query `PUExciseEntry` table directly**
2. **Use the `PriceC` field** - this contains the actual excise tax amount per unit
3. **Calculate total**: `SUM(PriceC * Quantity)`

## Key Fields in PUExciseEntry

| Field | Description |
|-------|-------------|
| `PriceC` | **Actual excise tax amount per unit** (already calculated) |
| `Quantity` | Number of units sold |
| `SubDescription3` | Tax category code (e.g., LC23PAID, VD07COLL) |
| `TransactionTime` | Date/time of transaction (use for filtering) |
| `Cost` | Product cost |
| `Price` | Sale price |

## Tax Category Codes

The SubDescription3 field contains tax category codes:

| Code | Description | Approx Rate |
|------|-------------|-------------|
| `LT10PAID` | Loose Tobacco - Paid to state | ~10% |
| `LT10COLL` | Loose Tobacco - Collected from customer | ~10% |
| `SL10PAID` | Smokeless - Paid to state | ~10% |
| `LC23PAID` | Large Cigars - Paid to state | ~23% |
| `LC23COLL` | Large Cigars - Collected from customer | ~23% |
| `LC25PAID` | Little Cigars - Paid to state | ~25% |
| `VD07PAID` | Vape Device - Paid to state | ~7% |
| `VD07COLL` | Vape Device - Collected from customer | ~7% |
| `VC05PAID` | Vapors Closed - Paid to state | ~5% |

**Note**: The actual tax calculation is more complex than just Cost * Rate. Always use the PriceC field!

## Implementation

### Module: `src/utils/excise_tax.py`

```python
def calculate_excise_tax(db_connection, start_date, end_date):
    """
    Calculate total excise tax paid to state.

    Queries PUExciseEntry directly using PriceC field (actual tax amount).
    """
    query = """
    SELECT SUM(PriceC * Quantity) as TotalExcisePaid
    FROM PUExciseEntry WITH (NOLOCK)
    WHERE TransactionTime >= ? AND TransactionTime <= ?
      AND SubDescription3 LIKE '%PAID'
    """
    # Returns the actual excise tax amount from database
```

### Usage in Dashboard

```python
from utils.excise_tax import calculate_excise_tax, calculate_excise_collected

# Calculate PAID (to state) - used in gross profit
excise_paid, error = calculate_excise_tax(
    db,
    start_date.strftime('%Y-%m-%d %H:%M:%S'),
    end_date.strftime('%Y-%m-%d %H:%M:%S')
)

# Calculate COLLECTED (from customers) - for reporting
excise_collected, error = calculate_excise_collected(
    db,
    start_date.strftime('%Y-%m-%d %H:%M:%S'),
    end_date.strftime('%Y-%m-%d %H:%M:%S')
)

if excise_paid is not None:
    gross_profit = revenue - cogs - excise_paid
```

## Query Details

### Correct Query:
```sql
-- Query PUExciseEntry using PriceC field (actual tax amount)
SELECT SUM(PriceC * Quantity) as TotalExcisePaid
FROM PUExciseEntry WITH (NOLOCK)
WHERE TransactionTime >= '2024-09-01 00:00:00'
  AND TransactionTime <= '2024-09-30 23:59:59'
  AND SubDescription3 LIKE '%PAID'
```

**Why this works:**
- `PriceC` contains the actual excise tax amount per unit (already calculated)
- `NOLOCK` hint prevents table locking
- Date filtering on `TransactionTime` is efficient
- `LIKE '%PAID'` gets all tax paid to state

## Verification

Run the test script against September 2024 (known values):

```bash
python3 test_excise_september.py
```

**Expected Results:**
- Excise Paid: $30,568.20
- Excise Collected: $66,828.73

## Performance

With NOLOCK hint and date filtering:
- Small ranges (7 days): < 1 second
- Medium ranges (30 days): 1-3 seconds
- Large ranges (90 days): 3-10 seconds

## Benefits

1. **Accurate** - Uses actual tax amounts from PriceC field
2. **Fast** - Direct query with NOLOCK and date filter
3. **Simple** - No complex joins or calculations needed
4. **Reliable** - Matches official excise tax reports

## Important Notes

- The `PAID` suffix = tax paid to government (subtract from gross profit)
- The `COLL` suffix = tax collected from customers (separate metric)
- `PriceC` is the actual excise tax amount - **do not recalculate it!**
- The relationship between PriceC and Cost/Price is complex and varies by product
