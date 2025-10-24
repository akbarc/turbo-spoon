# Vercel Serverless Deployment Plan
**Simplest Path: Direct Vercel → Tailscale → SQL Server**

## 🎯 Architecture

```
USER (Browser)
    ↓ HTTPS
VERCEL PLATFORM
├── Static Files (public/)
│   └── HTML/CSS/JS
└── Serverless Functions (api/)
    └── Python functions
        ↓ Tailscale connection
    SQL SERVER (10.1.10.105:1433)
```

## 📁 Project Structure

```
gadash108/
├── public/                          # Static files served by Vercel
│   ├── index.html                  # Executive Dashboard
│   ├── ar-dashboard.html
│   ├── customer-ledger.html
│   ├── ai-assistant.html
│   └── assets/
│       ├── css/
│       └── js/
├── api/                            # Vercel serverless functions
│   ├── __init__.py
│   ├── health.py                   # GET /api/health
│   ├── executive-summary.py        # GET /api/executive-summary
│   ├── ar/
│   │   ├── dashboard.py           # GET /api/ar/dashboard
│   │   └── aging.py               # GET /api/ar/aging
│   ├── pos/
│   │   └── reports.py             # GET /api/pos/reports
│   └── _lib/                       # Shared code
│       ├── database.py
│       └── utils.py
├── requirements.txt
├── vercel.json                     # Vercel configuration
├── .env.example
└── README.md
```

## 🔧 Key Challenges & Solutions

### Challenge 1: Tailscale in Vercel Functions
**Problem:** Vercel serverless functions are stateless and don't have Tailscale installed.

**Solutions:**
1. **Use Tailscale Funnel (Recommended)** - Expose SQL Server via Tailscale Funnel
2. **Use connection via Tailscale subnet router** - Connect to 10.1.10.105 from Vercel
3. **Use a proxy service** - Small proxy server on Railway with Tailscale

**Decision: Option 1 - Tailscale Funnel is simplest**

### Challenge 2: Database Connections in Serverless
**Problem:** Serverless functions don't maintain persistent connections.

**Solution:**
- Create new connection per request (acceptable for low traffic)
- Use connection pooling service (PgBouncer equivalent for SQL Server)
- Keep timeouts short

### Challenge 3: Python Dependencies
**Problem:** Vercel has size limits for Python functions.

**Solution:**
- Use slim dependencies only
- Pre-compile pymssql if needed
- Consider switching critical endpoints to Node.js

## ⚡ Implementation Steps

### Step 1: Restructure Project (Today)
- Move templates to public/
- Convert Flask routes to individual Python files in api/
- Create vercel.json configuration

### Step 2: Setup Tailscale Access (Today)
- Enable Tailscale Funnel OR
- Ensure subnet routing works from external IPs

### Step 3: Deploy to Vercel (Today)
- Push to GitHub
- Connect to Vercel
- Test deployment

## 📊 Limitations to Consider

| Aspect | Limitation | Workaround |
|--------|------------|------------|
| Function timeout | 10s (hobby), 60s (pro) | Optimize queries |
| Cold starts | 1-3s | Accept or upgrade |
| Concurrent executions | 100 (hobby), 1000 (pro) | Should be fine |
| Package size | 250MB uncompressed | Use slim packages |
| Memory | 1GB (hobby), 3GB (pro) | Should be fine |

## 🚀 Quick Start

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login
vercel login

# 3. Navigate to project
cd /Users/akbarchranya/georgiadashboard/gadash108

# 4. Initialize
vercel init

# 5. Deploy
vercel --prod
```

## 📝 Next Actions

1. Create clean folder structure
2. Move templates to public/
3. Convert main Flask routes to api/ functions
4. Create vercel.json
5. Test locally with `vercel dev`
6. Deploy to Vercel
