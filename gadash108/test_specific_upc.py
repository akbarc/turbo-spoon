"""
Test specific UPC lookup to verify API is working
"""
import os
from dotenv import load_dotenv

load_dotenv()

from fba_profit_analyzer import AmazonSPAPI, JungleScoutAPI

# Initialize APIs
sp_api = AmazonSPAPI(
    os.getenv("SP_REFRESH_TOKEN"),
    os.getenv("SP_CLIENT_ID"),
    os.getenv("SP_CLIENT_SECRET"),
    "us-east-1"
)

js_api = JungleScoutAPI(
    os.getenv("JS_API_NAME"),
    os.getenv("JS_API_KEY")
)

# Test with a known 5-Hour Energy UPC (from the catalog)
test_upcs = [
    "719411102121",  # 5-HOUR ENERGY 12CT- BERRY
    "40000246039",   # 3 MUSKETEERS KS 24CT
    "73135008166",   # 2 CYCLE ITASCA 8OZ 12CT
]

print("Testing UPC lookups:")
print("=" * 60)

for upc in test_upcs:
    print(f"\nTesting UPC: {upc}")

    # Try Amazon SP-API
    result = sp_api.lookup_product_by_upc(upc)

    if result:
        asin = result.get('asin')
        print(f"  ✓ Amazon SP-API: Found ASIN: {asin}")

        # Try to get title
        summaries = result.get('summaries', [{}])
        if summaries:
            title = summaries[0].get('itemName', '')
            print(f"  Title: {title[:60]}...")

        # Now try Jungle Scout with the ASIN
        if asin:
            js_result = js_api.lookup_by_asin(asin)
            if js_result:
                sales = js_result.get('approximate_30_day_sales', 'N/A')
                revenue = js_result.get('approximate_30_day_revenue', 'N/A')
                print(f"  ✓ Jungle Scout: Sales={sales}/mo, Revenue=${revenue}/mo")
            else:
                print(f"  ✗ Jungle Scout: No data for ASIN {asin}")
    else:
        print(f"  ✗ Amazon SP-API: Not found")

    print()

print("=" * 60)
