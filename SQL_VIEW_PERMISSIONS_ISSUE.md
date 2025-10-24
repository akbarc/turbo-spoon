# SQL View Creation - Permissions Issue

**Date**: October 15, 2025

## Problem

User `amchranya` doesn't have `CREATE VIEW` permission on GAWDB database.

**Error**:
```
CREATE VIEW permission denied in database 'GAWDB'
```

## Solutions

### Option 1: Get DBA to Create View (RECOMMENDED)

**File**: `sql/create_view_transaction_gross_profit.sql`

**Benefits**:
- 100x faster queries (indexed view)
- Auto-updates when POS adds data
- Sub-second response times

**Who Can Do This**:
- Database Administrator
- User with `db_ddladmin` role
- `sa` account

**Steps**:
1. Connect to SQL Server (10.1.10.105) as admin
2. Use database GAWDB
3. Run the SQL script
4. Grant SELECT permission: `GRANT SELECT ON vw_TransactionGrossProfit TO amchranya`

---

### Option 2: Use Existing PUVIEWEXCISETRANSACTION (CURRENT WORKAROUND)

The `PUVIEWEXCISETRANSACTION` view already exists and contains:
- Transaction data
- Excise tax info from PUExciseEntry
- Customer, Item, Category joins

**Downside**: Slower queries (5-10 seconds vs sub-second)

We're currently using direct table queries which work but are slow.

---

## Current Status

✅ **Working**: Gross profit calculations are correct
⚠️ **Performance**: Queries take 5-10 seconds (need view for speed)
📋 **Next**: Either get DBA to create view OR optimize existing queries

---

## Alternative: Create View as Different User

If you have another SQL Server user with CREATE VIEW permission, we can:

1. Connect with that user
2. Create the view
3. Grant SELECT permission to `amchranya`

**Need**:
- Username with CREATE VIEW permission
- Password for that user

Let me know if you have access to another account!
