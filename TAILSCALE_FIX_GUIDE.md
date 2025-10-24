# Tailscale SQL Server Connection - Fix Guide

## Current Status
✅ Tailscale network is working
✅ Mac can reach Windows desktop (100.84.221.9)
✅ Port 1433 is open and reachable
❌ SQL Server authentication failing: "Login failed for user 'amchranya'"

## The Problem
SQL Server on your Windows desktop is currently configured to only accept connections from the local network (10.1.10.x). When you connect via Tailscale (100.84.221.9), SQL Server sees it as a remote connection and rejects it.

## The Solution
Configure SQL Server to accept connections from any IP address (including Tailscale IPs).

---

## Steps to Fix (On Windows Desktop - 100.84.221.9)

### Step 1: Enable TCP/IP in SQL Server

1. **Open SQL Server Configuration Manager**
   - Search for "SQL Server Configuration Manager" in Windows Start menu
   - Or run: `SQLServerManager15.msc` (adjust version number)

2. **Enable TCP/IP**
   - Navigate to: **SQL Server Network Configuration** → **Protocols for MSSQLSERVER** (or your instance name)
   - Right-click **TCP/IP** → **Enable** (if not already enabled)

3. **Configure IP Addresses**
   - Right-click **TCP/IP** → **Properties**
   - Click **IP Addresses** tab
   - Scroll to bottom to find **IPALL** section
   - Set:
     - **TCP Dynamic Ports**: *leave blank*
     - **TCP Port**: **1433**
   - Click **OK**

4. **Restart SQL Server**
   - Go to **SQL Server Services** in Configuration Manager
   - Right-click **SQL Server (MSSQLSERVER)** → **Restart**

### Step 2: Configure Windows Firewall

1. **Open Windows Defender Firewall**
   - Search for "Windows Defender Firewall with Advanced Security"

2. **Add Inbound Rule**
   - Click **Inbound Rules** → **New Rule**
   - Select **Port** → Next
   - Select **TCP** and enter **1433** → Next
   - Select **Allow the connection** → Next
   - Check all profiles (Domain, Private, Public) → Next
   - Name it "SQL Server" → Finish

### Step 3: Configure SQL Server Authentication

1. **Open SQL Server Management Studio (SSMS)**
   - Connect to your local SQL Server

2. **Enable Mixed Authentication**
   - Right-click server name → **Properties**
   - Go to **Security** page
   - Under "Server authentication", select **SQL Server and Windows Authentication mode**
   - Click **OK**

3. **Verify User Permissions**
   - Expand **Security** → **Logins**
   - Find **amchranya**
   - Right-click → **Properties**
   - Go to **User Mapping**
   - Check the box next to **GAWDB**
   - Make sure user has appropriate role (db_owner or db_datareader/db_datawriter)
   - Click **OK**

4. **Restart SQL Server** (required for authentication changes)
   - Right-click server name in SSMS
   - Select **Restart**

### Step 4: Test Connection

1. **From your Windows desktop, open PowerShell and run:**
   ```powershell
   Test-NetConnection -ComputerName 100.84.221.9 -Port 1433
   ```
   Should show: **TcpTestSucceeded : True**

2. **Test SQL connection:**
   ```powershell
   sqlcmd -S 100.84.221.9 -U amchranya -P "2000Akbar!" -d GAWDB -Q "SELECT @@VERSION"
   ```
   Should return SQL Server version info

---

## Alternative: Quick Test from Mac

Once you've made the changes above, test from your Mac:

```bash
cd /Users/akbarchranya/georgiadashboard
python3 test_tailscale_sql.py
```

If it shows "✅ Connection successful!", restart your dashboard:

```bash
./start_dashboard.sh
```

---

## Your Dashboard URLs

Once working, access your dashboard from anywhere via:
- **Tailscale**: http://100.126.106.37:8080
- **Local**: http://localhost:8080

---

## Troubleshooting

### If you still get "Login failed":
1. Check if SQL Server is in Windows Authentication mode only
2. Make sure user 'amchranya' exists and has a password set
3. Try connecting locally first to verify credentials

### If connection times out:
1. Check Windows Firewall is allowing port 1433
2. Make sure SQL Server service is running
3. Verify SQL Server is listening on all IP addresses (0.0.0.0)

### To check SQL Server is listening:
```powershell
netstat -an | findstr :1433
```
Should show: `0.0.0.0:1433` or `[::]:1433`

---

## Summary

The issue is SQL Server security settings - it needs to:
1. ✅ Listen on all IP addresses (not just 10.1.10.105)
2. ✅ Accept SQL authentication (not just Windows auth)
3. ✅ Allow user 'amchranya' to connect from any IP
4. ✅ Windows Firewall must allow port 1433

Once these are configured, your dashboard will work from anywhere via Tailscale!
