# 🧪 Testing Your Vercel Deployment

## Quick Test (No Deployment Required)

Just created **test.html** - a comprehensive test page that checks:

✅ Static file serving (HTML/CSS/JS)
✅ JavaScript execution
✅ API endpoint routing
✅ Database connection (optional)

## How to Test Locally

### Option 1: Simple HTTP Server (No dependencies)

```bash
cd /Users/akbarchranya/georgiadashboard/gadash108/vercel-deploy/public
python3 -m http.server 8000
```

Then open: http://localhost:8000/test.html

**Note:** API tests will fail because Python server can't run the API functions.

### Option 2: Vercel Dev (Recommended - Full testing)

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to project
cd /Users/akbarchranya/georgiadashboard/gadash108/vercel-deploy

# Set environment variables (optional for test endpoint)
export DB_SERVER=10.1.10.105
export DB_USERNAME=amchranya
export DB_PASSWORD=your_password
export DB_DATABASE=GAWDB

# Run Vercel dev server
vercel dev
```

Then open: http://localhost:3000/test.html

**This will test everything including API endpoints!**

## What Each Test Does

### Test 1: Static Files ✅
- Confirms HTML/CSS/JS loads
- Tests Vercel CDN

### Test 2: JavaScript Execution ✅
- Confirms browser compatibility
- Tests client-side code

### Test 3: API Endpoint 🔧
- Tests `/api/test` serverless function
- Confirms API routing works
- Shows server information

### Test 4: Database Connection 🔌
- Tests `/api/health` endpoint
- Confirms SQL Server connectivity
- Only works if database is accessible

## Expected Results

### Before Deployment (Local)
- ✅ Test 1: Pass
- ✅ Test 2: Pass
- ❌ Test 3: Fail (expected)
- ❌ Test 4: Fail (expected)

### After Deployment to Vercel (No DB setup)
- ✅ Test 1: Pass
- ✅ Test 2: Pass
- ✅ Test 3: Pass
- ❌ Test 4: Fail (expected - need Tailscale/proxy)

### After Full Setup (DB accessible)
- ✅ Test 1: Pass
- ✅ Test 2: Pass
- ✅ Test 3: Pass
- ✅ Test 4: Pass

## Files Created

```
vercel-deploy/
├── public/
│   ├── landing.html         # Simple landing page
│   ├── test.html           # 🆕 Comprehensive test page
│   └── index.html          # Executive dashboard
└── api/
    ├── test.py             # 🆕 Simple test endpoint (no DB)
    ├── health.py           # Health check (requires DB)
    └── executive-summary.py # Dashboard data (requires DB)
```

## Quick Test Flow

1. **Open test.html locally** (with simple HTTP server)
   - Tests 1 & 2 should pass
   - Tests 3 & 4 will fail (expected)

2. **Deploy to Vercel**
   ```bash
   vercel --prod
   ```

3. **Open test.html on Vercel**
   - Tests 1, 2, 3 should pass
   - Test 4 will fail until DB is accessible

4. **Setup Database Access** (Tailscale Funnel or Railway Proxy)

5. **Set Environment Variables in Vercel**

6. **Retest** - All 4 tests should pass!

## Troubleshooting

### Test 3 Fails (API endpoint)
- Make sure you're accessing via Vercel (not local HTTP server)
- Check `/api/test` is accessible
- Look at Vercel function logs

### Test 4 Fails (Database)
- Expected if database not accessible yet
- Need to set up Tailscale Funnel or Railway Proxy
- Check environment variables in Vercel

## Next Steps

1. ✅ Test locally (optional)
2. 🚀 Deploy to Vercel
3. 🧪 Run test.html on deployed site
4. 🔌 Setup database access if Test 4 needed
5. 🎉 All tests passing = Ready for production!

---

**Start here:** Open `test.html` in browser after deploying to Vercel
