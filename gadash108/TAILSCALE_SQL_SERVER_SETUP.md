# Tailscale SQL Server Remote Access Setup

## 🎯 **GOAL**
Connect to your live SQL Server (`10.1.10.105`) from anywhere using Tailscale.

## 🔍 **CURRENT STATUS**
- ✅ **Tailscale working** - Mac and Windows desktop connected
- ✅ **Dashboard accessible** via `100.126.106.37:8080`
- ✅ **Windows desktop reachable** via `100.84.221.9`
- ✅ **SQL Server port accessible** through Windows desktop
- ❌ **Direct SQL connection** not working yet

## 🚀 **SOLUTION: Tailscale Subnet Router**

### **Step 1: Enable Subnet Routing (On Windows Desktop)**

**On your Windows desktop (`desktop-srvmc6b`):**

```cmd
# Open Command Prompt as Administrator
tailscale up --advertise-routes=10.1.10.0/24

# This tells Tailscale: "Route all 10.1.10.x traffic through me"
```

### **Step 2: Approve Routes (Tailscale Admin Console)**

1. **Go to:** https://login.tailscale.com/admin/machines
2. **Find your Windows desktop** (`desktop-srvmc6b`)
3. **Click the "..." menu** → **Edit route settings**
4. **Approve the subnet route** `10.1.10.0/24`

### **Step 3: Test Connection**

**From your Mac (on hotspot):**
```bash
# Test if SQL Server is now reachable
/Applications/Tailscale.app/Contents/MacOS/Tailscale ping 10.1.10.105

# Should now work!
```

### **Step 4: Restart Dashboard**

**Your dashboard will now work from anywhere:**
- **Office network:** Direct connection to `10.1.10.105`
- **Hotspot/Remote:** Via Tailscale routing through Windows desktop
- **No code changes** needed - uses same `10.1.10.105` IP

---

## 🎯 **ALTERNATIVE: Direct SQL Server Tailscale**

**If you can access the SQL Server machine directly:**

1. **Install Tailscale** on the SQL Server machine (`10.1.10.105`)
2. **Join same tailnet**
3. **Get Tailscale IP** (e.g., `100.x.x.x`)
4. **Update .env file:**
   ```
   DB_SERVER=100.x.x.x
   ```

---

## 🔧 **IMMEDIATE WORKAROUND**

**If you can't set up subnet routing right now:**

**Option A: SSH Tunnel**
```bash
# Create SSH tunnel through Windows desktop (if SSH enabled)
ssh -L 1433:10.1.10.105:1433 user@100.84.221.9
# Then connect to localhost:1433
```

**Option B: Temporary ngrok**
```bash
# On a machine that can reach SQL Server, create tunnel
ngrok tcp 10.1.10.105:1433
# Get public endpoint, update DB_SERVER temporarily
```

---

## 🎉 **EXPECTED RESULT**

Once subnet routing is set up:

**From anywhere with internet:**
1. **Connect to Tailscale** (your tailnet)
2. **Access dashboard:** `http://100.126.106.37:8080`
3. **Dashboard connects** to SQL Server via `10.1.10.105` (routed through Tailscale)
4. **Full functionality** - all reports, real-time data, everything works!

**The key is getting your Windows desktop to route the office network through Tailscale.**

---

Would you like me to help you set up the subnet routing, or do you have access to install Tailscale directly on the SQL Server machine?
