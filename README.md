# Georgia Dashboard - Local Deployment

## Overview

A Flask-based business analytics dashboard that runs **locally on your Mac** with remote access via Tailscale.

**Deployment Type**: Local (not cloud/Vercel)

## Quick Start

```bash
cd /Users/akbarchranya/georgiadashboard
./start_dashboard.sh
```

Access at: **http://100.126.106.37:8080** (via Tailscale)

## Architecture

- **Backend**: Flask + pymssql
- **Database**: SQL Server 2008 R2 at 10.1.10.105
- **Network**: Tailscale subnet routing via desktop-srvmc6b (100.84.221.9)
- **Hosting**: Runs locally on Mac, accessible via Tailscale network

## Requirements

- Python 3.8+
- Tailscale installed and running
- Virtual environment with dependencies
- SQL Server accessible via Tailscale subnet routing

## Key Files

- `start_dashboard.sh` - Start the dashboard
- `START_HERE.md` - Quick reference
- `PANDAS_PYMSSQL_FIX.md` - Critical fix documentation
- `.env` - Database configuration

## Access Methods

1. **Local**: http://localhost:8080
2. **Tailscale**: http://100.126.106.37:8080
3. **Office Network**: http://10.1.10.68:8080

## Important Notes

- **Not deployed to Vercel** - runs locally only
- **Pandas/pymssql conflict** - import order matters (see PANDAS_PYMSSQL_FIX.md)
- **Tailscale required** - for remote access to SQL Server
- **Subnet routing** - Windows desktop routes office network traffic

## Troubleshooting

### Dashboard won't start?
```bash
lsof -ti:8080 | xargs kill -9
./start_dashboard.sh
```

### Can't connect to database?
1. Check Tailscale is running: `tailscale status`
2. Test connectivity: `ping 10.1.10.105`
3. Check subnet routing is enabled on desktop-srvmc6b

### Import errors?
Make sure pymssql is imported BEFORE pandas in all modules.

## Documentation

- [START_HERE.md](START_HERE.md) - Quick start guide
- [PANDAS_PYMSSQL_FIX.md](PANDAS_PYMSSQL_FIX.md) - Critical pandas conflict fix
- [LOCAL_DEPLOYMENT_COMPLETE.md](LOCAL_DEPLOYMENT_COMPLETE.md) - Full setup
- [LOCAL_ACCESS.md](LOCAL_ACCESS.md) - Access instructions

---

**Status**: Running locally via Tailscale ✅
**Last Updated**: October 15, 2025
