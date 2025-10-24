# POS Dashboard Error Handling Guide

Quick reference for all error messages and their meanings.

---

## Receipt Generation Errors

### ⚠️ "Please enter a valid transaction number"
**Cause:** No transaction number entered, or number is 0 or negative
**Fix:** Enter a positive transaction number

### ⚠️ "Transaction #X not found. Please verify the transaction number."
**Cause:** Transaction doesn't exist in database
**Fix:** Check the transaction number is correct

### ❌ "Unable to connect to server. Please check your connection."
**Cause:** Server is down or network issue
**Fix:** Check server is running, verify network connection

### ⚠️ "Pop-up blocked. Please allow pop-ups for this site to view receipts."
**Cause:** Browser is blocking the receipt popup window
**Fix:** Click "Allow pop-ups" in browser address bar

---

## Report Generation Errors

### ⚠️ "Please select a report type"
**Cause:** No report type selected
**Fix:** Choose a report from the dropdown

### ⚠️ "Please select a report type before exporting"
**Cause:** Trying to export without selecting report
**Fix:** Select a report type first

### ❌ "Server error. The report may have encountered a database issue."
**Cause:** Database query failed (500 error)
**Fix:** Try a smaller date range, or contact admin

### ❌ "Unable to connect to server. Please check your connection."
**Cause:** Cannot reach server
**Fix:** Verify server is running and network is connected

### "No data found for the selected date range. Try expanding your date range or selecting a different report."
**Cause:** Query returned no results
**Fix:** Expand date range or verify data exists for selected period

---

## Search Errors

### ⚠️ "Please enter at least one search criterion"
**Cause:** No search filters entered
**Fix:** Enter at least one: search term, date, amount, or customer ID

### ❌ "Unable to connect to server. Please check your connection."
**Cause:** Network/server issue
**Fix:** Check connection and server status

### "No transactions match your search criteria. Try expanding your date range or adjusting your filters."
**Cause:** No results found
**Fix:** Broaden search criteria

---

## Loading Messages

### "Running report..."
**Status:** Report is executing (< 3 seconds)
**Action:** Wait

### "Running report... This may take a moment for large date ranges."
**Status:** Report is taking longer than 3 seconds
**Action:** Wait, or cancel and try smaller date range

### "Searching... This may take a moment for large date ranges."
**Status:** Search is taking longer than 3 seconds
**Action:** Wait, or cancel and narrow search

### "Generating receipt..."
**Status:** Fetching transaction data
**Action:** Wait

---

## Best Practices

### For Fastest Performance:
1. **Use date ranges of 30 days or less**
2. **Try "Daily Sales Summary" or "Register Analysis" first** - these are fastest
3. **Avoid very large date ranges** (>90 days) without additional filters

### When Reports Fail:
1. Check the date range - try last 7 days
2. Verify server is running
3. Try a different report type
4. Clear browser cache if issues persist

### When Exports Fail:
1. Run the report first to verify it works
2. Check pop-up blocker settings
3. Try CSV instead of Excel (faster)
4. Ensure you have disk space for download

---

## Common Error Codes

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 404 | Not Found | Transaction/resource doesn't exist |
| 500 | Server Error | Database query failed |
| Failed to fetch | Network Error | Server down or connection issue |

---

## Troubleshooting Checklist

### Receipt Won't Generate:
- [ ] Transaction number is valid positive integer
- [ ] Transaction exists in database
- [ ] Server is running
- [ ] Network connection active

### Report Won't Run:
- [ ] Report type selected
- [ ] Date range not too large (try <30 days)
- [ ] Server is running
- [ ] Database connection active

### Search Returns Nothing:
- [ ] At least one criterion entered
- [ ] Date range includes actual transactions
- [ ] Search term spelled correctly
- [ ] Amount range is reasonable

### Export/Print Won't Work:
- [ ] Pop-ups allowed in browser
- [ ] Disk space available
- [ ] Report has data to export
- [ ] Network connection stable

---

## Support Contact

If errors persist after troubleshooting:
1. Note the exact error message
2. Note what you were trying to do
3. Note the date/time of the error
4. Contact system administrator with this information
