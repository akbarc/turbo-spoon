# FBA Profit Analyzer

Comprehensive Amazon FBA profit analysis tool that combines your product catalog with Amazon SP-API and Jungle Scout data to calculate projected FBA profits, sales volumes, and ROI.

## What It Does

This tool analyzes every product in your master catalog and provides:

### Amazon Product Data (SP-API)
- ✅ ASIN lookup from your UPCs
- ✅ Current Amazon selling price
- ✅ Product details (title, brand, BSR, ratings)
- ✅ **FBA Fee Breakdown** (referral fees, fulfillment fees, storage fees)
- ✅ Competitive pricing data

### Sales Estimates (Jungle Scout)
- ✅ Monthly sales volume (units sold)
- ✅ Monthly revenue estimates
- ✅ Number of sellers
- ✅ FBA availability
- ✅ Product ratings and reviews

### Profit Calculations
- ✅ **Projected FBA Profit** = Amazon Price - FBA Fees - Your Cost
- ✅ **ROI Percentage** = (Profit / Cost) × 100
- ✅ Comparison to your retail margins
- ✅ Monthly profit potential based on sales volume

## Data Sources

The script intelligently combines data from multiple sources:

1. **Amazon SP-API** (Primary for product data & FBA fees)
   - Most accurate for FBA fee calculations
   - Direct access to Amazon catalog
   - Real-time pricing data

2. **Jungle Scout** (Primary for sales estimates)
   - Industry-leading sales estimates
   - Historical sales data
   - Competitive analysis

3. **Your Catalog** (Cost basis)
   - Your wholesale costs
   - Current inventory
   - Historical sales performance

The script uses **whichever source has better data** for each field, automatically merging the best information from all sources.

## Setup Instructions

### Step 1: Install Dependencies (1 minute)

```bash
pip install -r requirements_fba.txt
```

### Step 2: Get Amazon SP-API Credentials (10-15 minutes)

Amazon SP-API requires a Seller Central account and app registration:

1. **Register as Amazon Seller** (if not already)
   - Go to https://sellercentral.amazon.com/
   - Complete registration

2. **Register Your Application**
   - Go to https://developer-docs.amazon.com/sp-api/
   - Navigate to "Developer Console"
   - Click "Add new app client"
   - Note your **Client ID** and **Client Secret**

3. **Authorize Your Application**
   - In Seller Central, go to Settings → User Permissions
   - Under "Developer Applications", authorize your app
   - This generates a **Refresh Token**

4. **Get Refresh Token**
   - Follow the OAuth flow: https://developer-docs.amazon.com/sp-api/docs/self-authorization
   - Save the refresh token securely

**Detailed Guide:** https://developer-docs.amazon.com/sp-api/docs/registering-your-application

### Step 3: Get Jungle Scout API Credentials (2 minutes)

1. Log into your Jungle Scout account (you have the $70 tier)
2. Go to https://developer.junglescout.com/
3. Click "API" in the menu
4. Click "Create API Key"
5. Copy your **API Name** and **API Key**

### Step 4: Configure the Script (2 minutes)

```bash
# Copy the example environment file
cp .env.fba.example .env.fba

# Edit .env.fba with your credentials
nano .env.fba
```

Update these values:
```env
SP_REFRESH_TOKEN=your_actual_refresh_token
SP_CLIENT_ID=your_actual_client_id
SP_CLIENT_SECRET=your_actual_client_secret

JS_API_NAME=your_jungle_scout_api_name
JS_API_KEY=your_jungle_scout_api_key
```

### Step 5: Run the Analysis!

```bash
python fba_profit_analyzer.py
```

## Output Data

The script creates `fba_profit_analysis.csv` with these columns:

### Your Catalog Data
- `item_id` - Your internal item ID
- `upc` - Product UPC/barcode
- `description` - Product description
- `brand` - Product brand
- `category` - Your categorization
- `your_cost` - Your wholesale cost
- `your_price` - Your retail price
- `your_margin` - Your current gross margin %
- `on_hand` - Current inventory
- `monthly_qty` - Your monthly sales volume
- `monthly_revenue` - Your monthly revenue

### Amazon Data
- `asin` - Amazon ASIN
- `amazon_title` - Amazon product title
- `amazon_price` - Current Amazon selling price
- `amazon_bsr` - Best Seller Rank
- `amazon_rating` - Average star rating
- `amazon_reviews` - Number of reviews
- `amazon_sellers_count` - Number of competing sellers
- `fba_available` - Whether FBA is available

### FBA Fees Breakdown
- `fba_fee_total` - Total FBA fees
- `fba_referral_fee` - Amazon referral fee (commission)
- `fba_fulfillment_fee` - FBA pick, pack, ship fee
- `fba_storage_fee` - Monthly storage fee

### Jungle Scout Sales Data
- `js_monthly_sales_units` - Estimated monthly units sold
- `js_monthly_revenue` - Estimated monthly revenue
- `js_price` - Jungle Scout tracked price

### Profit Projections
- `projected_amazon_price` - Price used for calculations
- `projected_fba_profit` - **Net profit per unit after all FBA fees**
- `projected_fba_roi` - **Return on investment percentage**
- `vs_your_retail_profit` - Profit difference vs selling retail

### Metadata
- `data_source` - Which API(s) provided the data
- `timestamp` - When data was fetched

## Understanding the Profit Calculations

### FBA Profit Formula

```
Projected FBA Profit = Amazon Selling Price - FBA Fees - Your Cost

Where:
  Amazon Selling Price = Current competitive price on Amazon
  FBA Fees = Referral Fee + Fulfillment Fee + Storage Fee
  Your Cost = Your wholesale cost from the catalog
```

### ROI Calculation

```
ROI % = (Projected FBA Profit / Your Cost) × 100

Example:
  Amazon Price: $25.00
  FBA Fees: $8.50 (34% referral + fulfillment)
  Your Cost: $10.00
  Profit: $25.00 - $8.50 - $10.00 = $6.50
  ROI: ($6.50 / $10.00) × 100 = 65%
```

### Monthly Profit Potential

```
Monthly Profit = Projected FBA Profit × Jungle Scout Monthly Sales

Example:
  Profit per unit: $6.50
  Monthly sales: 500 units
  Monthly potential: $6.50 × 500 = $3,250
```

## Configuration Options

### Rate Limiting

Adjust API call frequency in `.env.fba`:

```env
# Conservative (recommended for first run)
RATE_LIMIT=3.0

# Standard
RATE_LIMIT=2.0

# Aggressive (if you have high API limits)
RATE_LIMIT=1.0
```

### Testing Mode

Process only a subset of products:

```env
# Process first 10 products
MAX_PRODUCTS=10

# Process all products (comment out or remove)
# MAX_PRODUCTS=
```

### Marketplace Region

Change Amazon marketplace:

```env
# US (default)
SP_REGION=us-east-1

# Europe
SP_REGION=eu-west-1

# Far East
SP_REGION=us-west-2
```

## API Rate Limits

### Amazon SP-API
- **Catalog Items:** 5 requests/second
- **Product Pricing:** 10 requests/second
- **FBA Fees:** 10 requests/second

Our script uses 2-second delays by default (well under limits).

### Jungle Scout
- **$70 Tier:** Typically 2,000-10,000 requests/day
- Check your dashboard: https://developer.junglescout.com/

## Troubleshooting

### "Authentication failed" (Amazon)

```
ERROR: Check these:
1. Refresh token is valid and not expired
2. App is authorized in Seller Central
3. Client ID and Secret are correct
4. You have an active seller account
```

**Fix:** Re-authorize your app in Seller Central and generate new refresh token.

### "Authentication failed" (Jungle Scout)

```
ERROR: Check these:
1. API credentials are copied correctly (no extra spaces)
2. Your Jungle Scout subscription is active
3. API access is enabled in your tier
```

**Fix:** Regenerate API key in Jungle Scout dashboard.

### "Rate limit exceeded"

```
ERROR: Too many API calls
```

**Fix:** Increase `RATE_LIMIT` in `.env.fba` from 2.0 to 3.0 or 5.0.

### "Product not found"

This is normal! Many products happen for these reasons:
- UPC not listed on Amazon
- Product discontinued
- UPC format issues (scientific notation in Excel)

The script will mark these as `NOT_FOUND` and continue.

### Scientific Notation UPCs

If your CSV shows UPCs like `6.85142E+11`, that's Excel converting them to scientific notation.

**Fix options:**

1. **In Excel:** Format UPC column as "Text" before importing
2. **In CSV:** Wrap UPCs in quotes: `"685142000000"`
3. **Script handles it:** The script converts UPCs to strings automatically

## Example Output

```
================================================================================
FBA PROFIT ANALYZER
================================================================================

Reading catalog: master_product_catalog.csv
Found 1247 products to analyze

[1/1247] 100 GRAND REGULAR 24CT
  UPC: 99900715329
  ✓ ASIN: B001234567
  Amazon Price: $52.99
  FBA Fees: $15.23
  Projected Profit: $-5.35 (-12.4% ROI)
  Est. Monthly Sales: 150 units

[2/1247] 2 CYCLE ITASCA 8OZ 12CT
  UPC: 73135008166
  ✓ ASIN: B009876543
  Amazon Price: $18.99
  FBA Fees: $6.45
  Projected Profit: $1.25 (11.1% ROI)
  Est. Monthly Sales: 85 units

...

================================================================================
Writing results to: fba_profit_analysis.csv

✓ Analysis complete!
  Products analyzed: 1247
  Found on Amazon: 892
  Potentially profitable: 437
  Total potential monthly profit: $12,543.67

Results saved to: fba_profit_analysis.csv
```

## Data Quality & Accuracy

### Sales Estimates
- **Jungle Scout** uses proprietary algorithms based on BSR
- Accuracy: ±20-30% typical variance
- Best for: Relative comparison, trend analysis
- Consider: Seasonal variations, new products

### FBA Fees
- **Amazon SP-API** provides official fee estimates
- Accuracy: Very high (direct from Amazon)
- Note: Storage fees vary by time of year
- Consider: Oversized items have higher fees

### Pricing Data
- Real-time competitive pricing from Amazon
- Updates frequently (current at time of query)
- Consider: Prices fluctuate, especially seasonal items

## Best Practices

1. **Start Small**
   - Test with `MAX_PRODUCTS=10` first
   - Verify data quality before full run

2. **Run Regularly**
   - Amazon prices change frequently
   - Sales estimates improve with more data
   - Monthly runs recommended

3. **Validate Results**
   - Spot-check high-profit items manually
   - Verify FBA fees for oversized items
   - Cross-reference with actual FBA calculator

4. **Consider Inventory**
   - High ROI + High sales volume = Priority
   - Low inventory items may not justify FBA setup
   - Factor in shipping to Amazon warehouse

5. **Factor in Additional Costs**
   - Shipping to Amazon FBA warehouse
   - Long-term storage fees (6+ months)
   - Return processing fees
   - Prep services (if using)

## Next Steps

After running the analysis:

1. **Sort by ROI** - Find highest return products
2. **Filter by sales volume** - Prioritize high-volume items
3. **Check inventory** - Ensure you have stock
4. **Calculate total potential** - Profit × Monthly Sales × On-Hand
5. **Create FBA shipment** - Start with top 20-50 items

## Support & Resources

### Amazon SP-API
- Docs: https://developer-docs.amazon.com/sp-api/
- Forum: https://sellercentral.amazon.com/forums
- Status: https://status.aws.amazon.com/

### Jungle Scout
- Support: https://support.junglescout.com/
- Docs: https://developer.junglescout.com/docs
- Dashboard: https://developer.junglescout.com/

### FBA Resources
- FBA Calculator: https://sellercentral.amazon.com/fba/profitabilitycalculator
- Fee Schedule: https://sell.amazon.com/pricing
- Fulfillment Fees: https://sellercentral.amazon.com/gp/help/201112670

## License

Free to use for your business needs.

---

**Questions?** Check the troubleshooting section or contact support for the respective APIs.
