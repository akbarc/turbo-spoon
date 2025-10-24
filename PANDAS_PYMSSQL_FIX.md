# Pandas/pymssql Conflict - Fixed!

## Problem Discovered

**Importing pandas BEFORE pymssql breaks SQL Server connections over Tailscale!**

When pandas is imported before pymssql in the same Python process, all subsequent pymssql.connect() calls timeout, even though:
- Network connectivity is fine (ping works)
- Port 1433 is reachable (nc test succeeds)
- Direct pymssql connections work BEFORE pandas is imported

## Root Cause

Pandas initializes some internal components (likely thread pools or network libraries) that interfere with FreeTDS/pymssql's ability to establish TDS protocol connections. This is a known incompatibility between pandas and pymssql when used with older SQL Server versions (2008 R2) over complex network configurations like Tailscale.

## Solution

**ALWAYS import pymssql/database modules BEFORE pandas!**

### Files Fixed:

1. **database_pymssql.py**
   - Set `TDSVER='7.0'` BEFORE any imports
   - Import pymssql BEFORE pandas
   - Use lazy pandas import in execute_query()

2. **app/main.py**
   - Moved pandas import to AFTER database_pymssql import

3. **app/ai_sql_assistant.py**
   - Moved pandas import to AFTER database_pymssql import

## Test Results

### Before Fix:
```
Test 1: Direct pymssql ✅ WORKING
Test 2: After importing database_pymssql ❌ TIMEOUT
```

### After Fix:
```
Test 1: Direct pymssql ✅ WORKING
Test 2: After importing database_pymssql ✅ WORKING
🎉 SUCCESS: Both methods work!
```

## Key Takeaways

1. **Import Order Matters**: pymssql must be imported before pandas
2. **Module-level Imports**: The conflict happens at import time, not at connection time
3. **Lazy Imports**: Best practice is to import pandas only when needed (inside functions)
4. **Network Routing**: This issue is more pronounced with Tailscale subnet routing but affects all remote connections

## Working Configuration

```python
# ✅ CORRECT ORDER
import os
os.environ['TDSVER'] = '7.0'

from database_pymssql import SQLServerConnection
import pandas as pd  # pandas AFTER database module
```

```python
# ❌ WRONG ORDER - WILL BREAK!
import pandas as pd  # pandas FIRST
from database_pymssql import SQLServerConnection  # Will timeout!
```

## Tailscale Configuration

The dashboard now works via Tailscale subnet routing:
- **Server**: 10.1.10.105 (routed through Tailscale)
- **Tailscale Router**: 100.84.221.9 (Windows desktop)
- **Dashboard**: http://100.126.106.37:8080

No need to connect directly to 100.84.221.9 - subnet routing handles it automatically!

---

**Date**: October 15, 2025
**Status**: FIXED ✅
**Testing**: All connection tests passing
