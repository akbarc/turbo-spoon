# Georgia Dashboard - Vercel Deployment

**Simplest deployment: Vercel Serverless → Tailscale → SQL Server**

## 🚀 Quick Deploy

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Navigate to this directory
cd /Users/akbarchranya/georgiadashboard/gadash108/vercel-deploy

# 3. Login to Vercel
vercel login

# 4. Deploy
vercel

# 5. Set environment variables in Vercel dashboard
# - DB_SERVER=10.1.10.105
# - DB_PORT=1433
# - DB_USERNAME=amchranya
# - DB_PASSWORD=your_password
# - DB_DATABASE=GAWDB

# 6. Deploy to production
vercel --prod
```

## 📁 Project Structure

```
vercel-deploy/
├── public/              # Static HTML files
│   └── index.html      # Executive dashboard
├── api/                # Serverless Python functions
│   ├── _lib/          # Shared code
│   │   ├── database.py
│   │   └── utils.py
│   ├── health.py      # GET /api/health
│   └── executive-summary.py
├── requirements.txt
├── vercel.json        # Vercel configuration
└── README.md
```

## 🔧 How It Works

1. **Static Files**: HTML files in `public/` are served directly
2. **API Functions**: Python files in `api/` become serverless endpoints
3. **Database**: Each function connects to SQL Server via environment variables
4. **Tailscale**: Connection works if Vercel can reach 10.1.10.105

## 🌐 API Endpoints

- `GET /api/health` - Health check and database connectivity test
- `GET /api/executive-summary` - Executive dashboard metrics

## ⚙️ Environment Variables

Set these in Vercel dashboard (Settings → Environment Variables):

```
DB_SERVER=10.1.10.105
DB_PORT=1433
DB_USERNAME=amchranya
DB_PASSWORD=your_password_here
DB_DATABASE=GAWDB
TDS_VERSION=7.0
```

## 🔒 Database Connectivity Options

### Option 1: Tailscale Funnel (Recommended)
Expose SQL Server via Tailscale Funnel:
```bash
# On Windows desktop
tailscale funnel --bg 10.1.10.105:1433
```

### Option 2: Direct Connection
If Vercel can reach your office network IP directly:
- Use public IP with port forwarding (not recommended)
- Use VPN tunnel

### Option 3: Proxy Service
Deploy a small proxy on Railway with Tailscale:
- Railway has native Tailscale support
- Proxy forwards requests to SQL Server
- Vercel → Railway Proxy → SQL Server

## 🧪 Local Testing

```bash
# Install Vercel CLI
npm install -g vercel

# Set environment variables locally
export DB_SERVER=10.1.10.105
export DB_PORT=1433
export DB_USERNAME=amchranya
export DB_PASSWORD=your_password
export DB_DATABASE=GAWDB

# Run local dev server
vercel dev

# Open browser
open http://localhost:3000
```

## 📊 Limitations

| Aspect | Limit | Impact |
|--------|-------|--------|
| Function timeout | 10s (hobby), 60s (pro) | Must optimize queries |
| Cold start | 1-3s | First request slower |
| Concurrent functions | 100 (hobby) | Should be fine |
| Package size | 250MB | Need slim dependencies |

## ✅ What's Built

- ✅ Health check endpoint
- ✅ Executive summary API
- ✅ Basic dashboard frontend
- ✅ Database connection handler
- ✅ CORS configuration
- ✅ Error handling

## 🔜 Next Steps

1. **Add More Endpoints**:
   - AR Dashboard API
   - Customer Ledger API
   - POS Reports API

2. **Add More Pages**:
   - Copy templates from `../templates/`
   - Update to use `/api/` endpoints

3. **Optimize**:
   - Add caching
   - Optimize queries
   - Add loading states

## 🚨 Troubleshooting

### Database Connection Fails

```bash
# Check if SQL Server is reachable
curl https://your-app.vercel.app/api/health

# Check Vercel function logs
vercel logs
```

### Slow Performance

- Enable Vercel Pro for 60s timeout
- Optimize database queries
- Add Redis caching (via Vercel KV)

### Package Too Large

- Remove unused dependencies
- Use `pymssql` only (slim)
- Consider switching to Node.js for some endpoints

## 📚 Resources

- Vercel Python Docs: https://vercel.com/docs/functions/runtimes/python
- Tailscale Funnel: https://tailscale.com/kb/1223/funnel
- pymssql Docs: https://pymssql.readthedocs.io

## 🎯 Success Criteria

✅ Health endpoint returns 200
✅ Executive summary loads data
✅ Dashboard displays metrics
✅ Can access from any browser globally
✅ Response time < 3 seconds

---

**Ready to deploy! Follow the Quick Deploy steps above.** 🚀
