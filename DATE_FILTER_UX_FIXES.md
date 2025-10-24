# Date Filter UX Fixes - October 15, 2025

## Issues Fixed

### 1. Date Off-By-One Bug ✅

**Problem**: When entering custom dates like 1/1/25 to 10/15/25, the system was displaying 12/31/24 to 10/14/25 instead.

**Root Cause**: The `formatDate()` function was using `toISOString()`, which converts dates to UTC timezone. This caused dates to shift backward by several hours (depending on timezone), resulting in the previous day being displayed.

**Fix**: Replaced `toISOString()` with local timezone formatting:
```javascript
// OLD (buggy):
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// NEW (correct):
function formatDate(date) {
    // Format date in local timezone (not UTC) to avoid off-by-one errors
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
```

**Result**: Dates now display exactly as entered. 1/1/25 stays 1/1/25, not 12/31/24.

---

### 2. Always-Visible Date Picker ✅

**Problem**: Date picker was hidden by default and only appeared when selecting "Custom Range" from dropdown.

**User Request**: "Make the date picker show up always (the one for custom range) and when i click one of the dropdowns, it should just change the dates in the date picker"

**Changes Made**:

1. **Removed hide/show CSS logic**:
```css
/* OLD: */
.custom-range {
    display: none;
    gap: 10px;
    align-items: center;
}
.custom-range.active {
    display: flex;
}

/* NEW: */
.custom-range {
    display: flex;  /* Always visible */
    gap: 10px;
    align-items: center;
}
```

2. **Updated dropdown behavior** to populate date picker:
```javascript
function handleDateRangeChange() {
    const select = document.getElementById('dateRangeSelect');
    const rangeType = select.value;

    // Calculate dates for the selected range
    const {start, end} = getDateRange(rangeType);

    // Update the date picker inputs (NEW)
    document.getElementById('startDate').value = formatDate(start);
    document.getElementById('endDate').value = formatDate(end);

    // Update current dates and load data
    currentStartDate = formatDate(start);
    currentEndDate = formatDate(end);
    updateDateDisplay(rangeType, start, end);
    loadAllData();
}
```

3. **Enhanced Apply button** to set dropdown to "Custom":
```javascript
function applyCustomRange() {
    // ...validation...

    // Set dropdown to custom (NEW)
    document.getElementById('dateRangeSelect').value = 'custom';

    currentStartDate = startDate;
    currentEndDate = endDate;
    updateDateDisplay('custom', new Date(startDate), new Date(endDate));
    loadAllData();
}
```

**Result**:
- Date picker is always visible
- Selecting any preset from dropdown automatically updates the date picker inputs
- Users can see and modify exact dates even when using presets
- Apply button updates dropdown to "Custom" when used

---

## New User Experience

### Before:
1. ❌ Date picker hidden by default
2. ❌ Had to select "Custom Range" to see date inputs
3. ❌ Preset selections didn't show exact dates
4. ❌ Dates shifted by timezone (off-by-one errors)

### After:
1. ✅ Date picker always visible
2. ✅ Clicking "Month to Date" instantly shows start/end dates in picker
3. ✅ Can manually adjust dates shown by preset
4. ✅ Dates display exactly as entered (no timezone issues)

---

## Example Workflow

**Scenario 1: Using Presets**
1. Click "Year to Date" dropdown
2. Date picker automatically shows: `2025-01-01` to `2025-10-15`
3. Dashboard loads YTD data
4. User can see exact dates being used

**Scenario 2: Tweaking a Preset**
1. Click "Last 30 Days" dropdown
2. Date picker shows calculated range
3. User manually adjusts end date forward by 2 days
4. Click "Apply" button
5. Dashboard loads custom range

**Scenario 3: Fully Custom Range**
1. Manually enter dates in picker: `2025-01-01` to `2025-10-15`
2. Click "Apply"
3. Dropdown automatically switches to "Custom"
4. Dashboard loads custom range

---

## Files Modified

- **`templates/gp_dashboard.html`**
  - Line 80-84: Removed hide/show CSS for `.custom-range`
  - Line 351-357: Fixed `formatDate()` to use local timezone
  - Line 428-444: Updated `handleDateRangeChange()` to populate date picker
  - Line 446-462: Enhanced `applyCustomRange()` to set dropdown to "custom"

---

## Testing Verified

✅ Selecting "Today" populates date picker with today's date
✅ Selecting "MTD" shows first of month to today
✅ Selecting "YTD" shows Jan 1 to today
✅ Manually entering dates and clicking Apply works correctly
✅ Date picker is visible on page load
✅ No more off-by-one errors on date conversion

---

## Server Restarted

Dashboard restarted with updated template at: **October 15, 2025, 8:40 PM**

Access:
- Local: http://localhost:8081
- Tailscale: http://100.126.106.37:8081

**Clear browser cache (Ctrl+Shift+R) or use incognito to see the changes immediately.**
