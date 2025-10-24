# Complete Customer Balance Analysis Summary
## 5 Star Food Mart Somani (Customer ID: 4915, Account: 2058737683)

### Executive Summary
This comprehensive analysis demonstrates how to properly calculate a customer's current balance by tracking ALL account activity throughout the lifetime of the account. The analysis reveals significant patterns in payment behavior, NSF occurrences, and overall account management.

### Key Findings

#### Current Balance Status
- **Current AR Balance (from AR table)**: $43,424.87
- **Calculated Timeline Balance**: $49,326.97
- **Discrepancy**: $5,902.10 (needs investigation)

#### Account Activity Summary (All Time)
- **Total Transactions**: 270 activities
- **Total Invoiced**: $221,633.95 (62 invoices)
- **Total Payments**: $392,819.31 (91 payments)
- **NSF Events**: 89 occurrences totaling $230,985.56
- **Adjustments**: 10 transactions totaling -$10,473.23

#### Account Health Indicators
- **Balance Range**: $50,198.75 (from -$871.78 to $49,326.97)
- **NSF Rate**: Very high - 89 NSF events out of 270 total activities (33%)
- **Payment Frequency**: Regular payments but often returned as NSF
- **Recent Activity**: 5 transactions in last 90 days

### How Customer Balance Should Be Calculated

#### Proper Methodology
1. **Start with $0.00 balance**
2. **Add each invoice** (positive amount to AR)
3. **Subtract each payment** (reduces AR balance)
4. **Add NSFs and fees** (increases AR when checks bounce)
5. **Apply adjustments** (can be positive or negative)
6. **Result = Current AR Balance**

#### Why Simple Invoice-Payment Calculation Fails
The simple calculation (Total Invoiced - Total Payments = $221,633.95 - $392,819.31 = -$171,185.36) gives a negative balance, which is completely wrong. This fails because:

- **NSFs are not accounted for** - Returned checks add back to the balance
- **Fees and adjustments** are ignored
- **Timing of transactions** is not considered
- **Partial payments to specific invoices** are not tracked

### Account Activity Patterns

#### NSF Pattern Analysis
- **First NSF**: June 2022 ($2,053.44)
- **Largest NSF**: $11,667.85 (May 2025)
- **Most NSFs in one month**: April 2025 (multiple large NSFs)
- **NSF Fees**: $65 per occurrence, adding significant cost

#### Payment Behavior
- Regular attempts to pay $2,500-$7,500 amounts
- High frequency of NSFs suggests cash flow issues
- Often pays immediately after NSF notifications
- Uses both checks and electronic payments

#### Balance Trends
- **Highest Balance**: $49,326.97 (July 2025)
- **Lowest Balance**: -$871.78 (March 2025) - briefly negative
- **Recent Growth**: Balance increased $10,391.18 in last 90 days
- **Seasonal Patterns**: Higher activity in Q4/Q1

### Monthly Activity Summary

| Month | Ending Balance | Activities | Invoices | Payments | Adjustments |
|-------|----------------|------------|----------|----------|-------------|
| 2022-06 | $2,098.44 | 6 | 2 | 2 | 0 |
| 2022-07 | $4,361.03 | 8 | 3 | 3 | 0 |
| 2024-10 | $7,783.76 | 19 | 7 | 4 | 6 |
| 2024-11 | $15,489.95 | 29 | 6 | 11 | 0 |
| 2024-12 | $24,649.71 | 26 | 6 | 12 | 0 |
| 2025-01 | $18,771.79 | 31 | 7 | 12 | 6 |
| 2025-02 | $1,965.27 | 42 | 11 | 13 | 6 |
| 2025-03 | $12,234.95 | 42 | 11 | 13 | 7 |
| 2025-04 | $13,141.67 | 55 | 6 | 19 | 2 |
| 2025-05 | $41,820.69 | 9 | 3 | 1 | 1 |
| 2025-07 | $49,326.97 | 2 | 0 | 0 | 0 |

### Database Tables Used for Complete Analysis

#### 1. Transaction Table
- **Purpose**: All sales/invoices to the customer
- **Key Fields**: TransactionNumber, Time, Total, CustomerID
- **Usage**: Creates AR entries when sales are made

#### 2. Payment Table
- **Purpose**: All payments received from customer
- **Key Fields**: Time, Amount, CustomerID, Comment
- **Usage**: Reduces AR balance when payments clear

#### 3. AccountReceivable Table
- **Purpose**: Current outstanding balances
- **Key Fields**: OriginalAmount, Balance, TransactionNumber
- **Usage**: Shows what's currently owed

#### 4. AccountReceivableHistory Table
- **Purpose**: All AR movements and adjustments
- **Key Fields**: Date, Amount, HistoryType, Comment
- **Usage**: Complete audit trail of balance changes
- **History Types**:
  - 0: Invoice Created
  - 1: Adjustment
  - 2: Payment Applied
  - 3: Transfer/NSF
  - 4: Write-off
  - 5: Other (NSFs, fees, etc.)

### Critical Insights for Account Management

#### Risk Factors
1. **Extremely High NSF Rate**: 33% of all activities are NSFs
2. **Large Outstanding Balance**: $43,424.87 is significant
3. **Recent Balance Growth**: $10K increase in 90 days
4. **Cash Flow Issues**: Pattern suggests customer struggles with liquidity

#### Collection Strategies
1. **Require Cash or Certified Funds**: Given NSF history
2. **Smaller, More Frequent Deliveries**: Reduce exposure
3. **Payment Terms**: Consider COD or prepayment
4. **Credit Limit**: Current balance exceeds prudent limits

#### System Requirements
- **Real-time NSF Monitoring**: Alert on returned payments
- **Credit Limit Enforcement**: Prevent over-extension
- **Payment Method Restrictions**: Limit check acceptance
- **Collection Fees**: Ensure NSF fees cover costs

### Technical Implementation Notes

#### AR History Balance Reconciliation
- **AR History Total**: $43,424.87 (matches current AR)
- **Timeline Calculation**: $49,326.97 (includes some duplicates)
- **Reconciliation**: The AR History table is the authoritative source

#### Query Optimization
- Use AR History for balance calculation (authoritative)
- Transaction table for invoice details
- Payment table for payment timing and methods
- Join all three for complete customer view

### Conclusion

This analysis demonstrates that **proper customer balance calculation requires examining the complete AR History**, not just simple invoice-payment arithmetic. The customer shows a concerning pattern of NSFs and growing balance that requires immediate attention for credit management and collection strategy.

The methodology shown here can be applied to any customer to understand their complete financial relationship with the company, identify risk patterns, and make informed credit decisions.
