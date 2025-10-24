# FBA Profit Analyzer - Quick Start

Get your FBA profit analysis running in 10 minutes!

## 🆕 New Features (Oct 21, 2025)
- ⊘ **Tobacco/Vapor Filtering** - Automatically skips tobacco products (not on Amazon)
- 📦 **Pack Size Matching** - Finds the right Amazon variation (12-pack vs 24-pack)
- 💰 **Per-Unit Pricing** - Normalized pricing for accurate comparisons

**See `FBA_NEW_FEATURES.md` for full details!**

## Prerequisites
- ✅ You have Jungle Scout $70/month tier (API access included)
- ✅ You have (or can create) an Amazon Seller Central account
- ✅ Python 3.7+ installed
- ✅ Your master_product_catalog.csv ready

## 3-Step Setup

### 1. Install Dependencies (30 seconds)

```bash
cd /Users/akbarchranya/georgiadashboard/gadash108
pip install -r requirements_fba.txt
```

### 2. Get API Credentials

#### Jungle Scout (2 minutes) ⚡
1. Go to https://developer.junglescout.com/
2. Click "API" → "Create API Key"
3. Copy **API Name** and **API Key**

#### Amazon SP-API (10 minutes) 📦
**Quick path if you already have Seller Central:**
1. Go to https://sellercentral.amazon.com/apps/manage
2. Click "Add new app client"
3. Get your **Client ID**, **Client Secret**, and **Refresh Token**

**New to SP-API?**
- Follow guide: https://developer-docs.amazon.com/sp-api/docs/registering-your-application
- OR skip for now and use Jungle Scout only (reduced features)

### 3. Configure & Run

```bash
# Copy example config
cp .env.fba.example .env.fba

# Edit with your credentials
nano .env.fba
# (Add your API keys)

# Test with first 10 products
# Uncomment MAX_PRODUCTS=10 in .env.fba for testing

# Run it!
python fba_profit_analyzer.py
```

## What You'll Get

Output file: `fba_profit_analysis.csv`

Key columns:
- **your_cost** - What you pay
- **amazon_price** - What Amazon price is
- **fba_fee_total** - All Amazon fees
- **projected_fba_profit** - Your net profit per unit
- **projected_fba_roi** - Your ROI percentage
- **js_monthly_sales_units** - How many units sell per month

## Quick Win Strategy

1. **Run the analysis**
2. **Sort by ROI** (highest first)
3. **Filter for:**
   - ROI > 30%
   - Monthly sales > 50 units
   - You have inventory on hand
4. **Start with top 20-50 products**

## Example Results

```
[16/1247] 5-HOUR ENERGY 12CT- BERRY
  ✓ ASIN: B00L91KAJ8
  Pack: 12ct (Exact match ✓)
  Amazon Price: $26.99
  FBA Fees: $6.45
  Projected Profit: $1.54 (8.1% ROI)
  Est. Monthly Sales: 150 units

[245/1247] 24/7 GOLD 100 BOX 10CT
  ⊘ Tobacco/Vapor - Skipped (not allowed on Amazon)
```

## Troubleshooting

### "Can't get Amazon credentials yet"
No problem! The script works with Jungle Scout alone:
- You'll still get sales estimates
- You'll still get Amazon prices
- You WON'T get exact FBA fee breakdowns
- Start with this, add SP-API later

### "Script is slow"
Normal! Each product needs 2-3 API calls.
- 100 products ≈ 6-10 minutes
- 1000 products ≈ 60-100 minutes
- Use `MAX_PRODUCTS=50` for testing

### "Some products not found"
Expected! Happens when:
- Product not on Amazon
- UPC format issue
- Product discontinued

The script continues automatically.

## Next Steps

1. **Analyze results** - Open CSV in Excel/Google Sheets
2. **Prioritize** - Sort by profit × monthly sales
3. **Verify** - Spot-check top items on Amazon manually
4. **Ship to FBA** - Create shipment with top performers

## Full Documentation

See: `FBA_PROFIT_ANALYZER_README.md` for complete details.

## Support

- Jungle Scout: https://support.junglescout.com/
- Amazon SP-API: https://developer-docs.amazon.com/sp-api/

---

**Ready to find your most profitable FBA products?** Run the script!
