"""
Debug Amazon SP-API to see actual responses
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Get token first
token_url = "https://api.amazon.com/auth/o2/token"
token_data = {
    "grant_type": "refresh_token",
    "refresh_token": os.getenv("SP_REFRESH_TOKEN"),
    "client_id": os.getenv("SP_CLIENT_ID"),
    "client_secret": os.getenv("SP_CLIENT_SECRET")
}

print("Step 1: Getting access token...")
try:
    token_response = requests.post(token_url, data=token_data, timeout=30)
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]
    print(f"✓ Got access token: {access_token[:20]}...")
except Exception as e:
    print(f"✗ Error getting token: {e}")
    exit(1)

# Now try to look up a UPC
upc = "719411102121"  # 5-Hour Energy
marketplace_id = "ATVPDKIKX0DER"  # US

catalog_url = "https://sellingpartnerapi-na.amazon.com/catalog/2022-04-01/items"
headers = {
    "x-amz-access-token": access_token,
    "Content-Type": "application/json"
}
params = {
    "identifiers": upc,
    "identifiersType": "UPC",
    "marketplaceIds": marketplace_id,
    "includedData": "attributes,dimensions,identifiers,images,productTypes,salesRanks,summaries"
}

print(f"\nStep 2: Looking up UPC {upc}...")
print(f"URL: {catalog_url}")
print(f"Params: {params}")

try:
    response = requests.get(catalog_url, headers=headers, params=params, timeout=30)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body:")
    print(response.text[:1000])  # First 1000 chars

    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            print(f"\n✓ Found {len(data['items'])} item(s)!")
            for item in data["items"]:
                print(f"  ASIN: {item.get('asin')}")
        else:
            print(f"\n✗ No items found in response")
    else:
        response.raise_for_status()

except Exception as e:
    print(f"\n✗ Error: {e}")
