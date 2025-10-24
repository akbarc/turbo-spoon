# Fast Startup Configuration

## Problem Solved

The dashboard was taking 60+ seconds to start because the AI Assistant was trying to load the database schema and timing out due to the pandas/pymssql conflict.

## Solution

**Disabled AI Assistant** during startup for immediate dashboard availability.

### Startup Time:
- **Before**: 60+ seconds (waiting for AI assistant timeout)
- **After**: ~5 seconds (instant startup)

## What Was Disabled

The AI SQL Assistant feature has been temporarily disabled by commenting out:

1. Import in `app/main.py` line 28:
   ```python
   # from app.ai_sql_assistant import AISQLAssistant
   ```

2. Initialization in `app/main.py` line 117-129:
   ```python
   def init_ai_assistant():
       """Initialize AI assistant - DISABLED for faster startup"""
       AI_AVAILABLE = False
       ai_assistant = None
   ```

3. Startup call in `app/main.py` line 5703:
   ```python
   # init_ai_assistant()
   ```

## Impact

- ✅ Dashboard starts in ~5 seconds
- ✅ All main features work (sales, inventory, AR, etc.)
- ❌ AI SQL query assistant not available (was already broken due to pandas conflict)

## To Re-enable AI Assistant

1. Fix the pandas/pymssql import order in `ai_sql_assistant.py`
2. Uncomment the lines above
3. Test that schema loading doesn't timeout

## Current Status

**Dashboard is FAST and WORKING!**

- Starts in ~5 seconds
- Accessible at http://100.126.106.37:8080 (Tailscale)
- All business dashboards functional
- Database connections working via Tailscale subnet routing

---

**Date**: October 15, 2025
**Startup Time**: ~5 seconds ✅
