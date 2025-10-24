# 🚀 Georgia Dashboard - Local Setup (Tailscale)

## Quick Start (~5 second startup!)

From `/Users/akbarchranya/georgiadashboard`, run:

```bash
./start_dashboard.sh
```

Dashboard starts in ~5 seconds and is ready to use!

## Access URLs

When on Tailscale network:
- **On this computer**: http://localhost:8080
- **Via Tailscale (from anywhere)**: http://100.126.106.37:8080

When on office network:
- **Local network**: http://10.1.10.68:8080

## How It Works

The dashboard runs **locally on your Mac** and connects to SQL Server via Tailscale subnet routing. No cloud hosting needed!

- SQL Server: 10.1.10.105 (routed through Tailscale)
- Dashboard: Runs on your Mac
- Access: Via Tailscale from any device on your tailnet

## Stop the Server

Press `Ctrl+C` in the terminal

## Full Documentation

- `PANDAS_PYMSSQL_FIX.md` - Critical pandas/pymssql conflict fix
- `LOCAL_DEPLOYMENT_COMPLETE.md` - Complete setup details
- `LOCAL_ACCESS.md` - Detailed access instructions

---

**Note**: This is a LOCAL deployment, not Vercel/cloud. The dashboard runs on your computer and is accessible via Tailscale.
