"""
FBA Profit Analyzer - Comprehensive Amazon FBA Analysis Tool
Combines your product catalog with Amazon SP-API and Jungle Scout data
to calculate projected FBA profits, sales volumes, and ROI.

Author: Generated for Georgia Dashboard
Date: October 2025
"""

import csv
import json
import os
import time
import hashlib
import hmac
import base64
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Tobacco/Vapor Product Detection
TOBACCO_CATEGORIES = {
    'CIGARETTE', 'LT-TAX PAID', 'CIGAR', 'VAPE', 'VAPOR', 'E-CIG', 'ECIG',
    'TOBACCO', 'NICOTINE', 'JUUL', 'VUSE'
}

TOBACCO_KEYWORDS = {
    'cigarette', 'cigar', 'tobacco', 'vape', 'vapor', 'e-cig', 'ecig',
    'juul', 'vuse', 'nicotine', 'dip', 'chew', 'snus', 'hookah', 'shisha',
    'mod', 'pod system', 'salt nic', 'freebase', 'nic salt'
}

# Allowed tobacco accessories (these ARE on Amazon)
TOBACCO_ACCESSORIES_ALLOWED = {
    'rolling paper', 'raw', 'zig zag', 'zigzag', 'blunt wrap', 'cone',
    'lighter', 'match', 'ashtray', 'grinder', 'rolling machine',
    'filter', 'tip', 'hemp wick'
}


def is_tobacco_or_vapor_product(product_data: Dict) -> bool:
    """
    Determine if a product is tobacco/vapor (not allowed on Amazon FBA)

    Returns True if product should be EXCLUDED (is tobacco/vapor)
    Returns False if product should be INCLUDED (accessories or non-tobacco)
    """
    category = str(product_data.get('CurrentCategory', '')).upper()
    main_category = str(product_data.get('MainCategory', '')).upper()
    description = str(product_data.get('Description', '')).lower()
    product_type = str(product_data.get('ProductType', '')).lower()

    # Check if category is explicitly tobacco/vapor
    if category in TOBACCO_CATEGORIES:
        # But allow accessories
        desc_lower = description.lower()
        if any(accessory in desc_lower for accessory in TOBACCO_ACCESSORIES_ALLOWED):
            return False  # It's an accessory, allow it
        return True  # It's actual tobacco/vapor, exclude it

    # Check main category
    if 'TOBACCO' in main_category or 'NICOTINE' in main_category:
        # Check if it's an accessory
        desc_lower = description.lower()
        if any(accessory in desc_lower for accessory in TOBACCO_ACCESSORIES_ALLOWED):
            return False
        return True

    # Check description for tobacco keywords
    desc_lower = description.lower()

    # If it mentions allowed accessories, it's OK
    if any(accessory in desc_lower for accessory in TOBACCO_ACCESSORIES_ALLOWED):
        return False

    # Otherwise check for tobacco keywords
    if any(keyword in desc_lower for keyword in TOBACCO_KEYWORDS):
        return True

    return False


def extract_pack_size(text: str) -> Optional[int]:
    """
    Extract pack size/count from product description or title

    Examples:
    - "5-HOUR ENERGY 12CT- BERRY" -> 12
    - "Red Bull 24 Pack" -> 24
    - "Snickers Single Bar" -> 1
    - "Monster Energy 4-Pack" -> 4
    """
    if not text:
        return None

    text = text.upper()

    # Pattern 1: "12CT", "24 CT", "12-CT"
    match = re.search(r'(\d+)\s*[-]?\s*CT\b', text)
    if match:
        return int(match.group(1))

    # Pattern 2: "12 COUNT", "24-COUNT"
    match = re.search(r'(\d+)\s*[-]?\s*COUNT\b', text)
    if match:
        return int(match.group(1))

    # Pattern 3: "12 PACK", "24-PACK", "4-PK"
    match = re.search(r'(\d+)\s*[-]?\s*(PACK|PK)\b', text)
    if match:
        return int(match.group(1))

    # Pattern 4: "SINGLE", "EACH", "1CT"
    if any(word in text for word in ['SINGLE', 'EACH', '1CT', '1 CT']):
        return 1

    # Pattern 5: "DISPLAY OF 12", "BOX OF 24"
    match = re.search(r'(?:DISPLAY|BOX|CASE)\s+OF\s+(\d+)', text)
    if match:
        return int(match.group(1))

    return None


def normalize_price_per_unit(price: float, pack_size: int) -> float:
    """Calculate price per single unit"""
    if pack_size and pack_size > 0:
        return price / pack_size
    return price


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date from CSV (handles multiple formats)

    Examples:
    - "10/9/25" -> datetime
    - "10/17/25" -> datetime
    - "" -> None
    """
    if not date_str or date_str.strip() == '':
        return None

    date_str = date_str.strip()

    # Try common formats
    formats = [
        '%m/%d/%y',    # 10/9/25
        '%m/%d/%Y',    # 10/09/2025
        '%Y-%m-%d',    # 2025-10-09
        '%m-%d-%Y',    # 10-09-2025
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # If year is < 100, it's likely 2-digit year
            if parsed.year < 100:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed
        except ValueError:
            continue

    return None


def is_active_product(product_data: Dict, months_back: int = 12) -> bool:
    """
    Check if product is active (sold recently AND purchased recently)

    Args:
        product_data: Product row from CSV
        months_back: How many months to look back (default 12)

    Returns:
        True if product sold AND purchased in last N months
    """
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)

    # Check LastSold
    last_sold_str = product_data.get('LastSold', '')
    last_sold = parse_date(last_sold_str)

    # Check LastReceived (when you last purchased inventory)
    last_received_str = product_data.get('LastReceived', '')
    last_received = parse_date(last_received_str)

    # Must have BOTH recent sale AND recent purchase
    has_recent_sale = last_sold and last_sold >= cutoff_date
    has_recent_purchase = last_received and last_received >= cutoff_date

    return has_recent_sale and has_recent_purchase


class AmazonSPAPI:
    """Amazon Seller Partner API client for product data and FBA fees"""

    def __init__(self, refresh_token: str, client_id: str, client_secret: str, region: str = "us-east-1"):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        self.access_token = None
        self.token_expiry = None

        # SP-API endpoints by region
        self.endpoints = {
            "us-east-1": "https://sellingpartnerapi-na.amazon.com",
            "eu-west-1": "https://sellingpartnerapi-eu.amazon.com",
            "us-west-2": "https://sellingpartnerapi-fe.amazon.com"
        }
        self.base_url = self.endpoints.get(region, self.endpoints["us-east-1"])

    def get_access_token(self) -> str:
        """Get or refresh access token"""
        if self.access_token and self.token_expiry and datetime.now(timezone.utc).timestamp() < self.token_expiry:
            return self.access_token

        # Request new token
        url = "https://api.amazon.com/auth/o2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            # Token expires in 3600 seconds, set expiry to 55 minutes from now
            self.token_expiry = datetime.now(timezone.utc).timestamp() + 3300

            return self.access_token
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None

    def lookup_product_by_upc(self, upc: str, marketplace_id: str = "ATVPDKIKX0DER", max_retries: int = 3) -> Optional[Dict]:
        """
        Look up product by UPC using Catalog Items API with retry logic

        Args:
            upc: Product UPC/barcode
            marketplace_id: Amazon marketplace ID (ATVPDKIKX0DER = US)
            max_retries: Maximum number of retries for rate limit errors

        Returns:
            Product data dictionary with ASIN and details
        """
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/catalog/2022-04-01/items"
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json"
        }
        params = {
            "identifiers": upc,
            "identifiersType": "UPC",
            "marketplaceIds": marketplace_id,
            "includedData": "attributes,dimensions,identifiers,images,productTypes,salesRanks,summaries"
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if data.get("items") and len(data["items"]) > 0:
                    return data["items"][0]
                return None

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    return None  # Product not found
                elif e.response.status_code == 429:
                    # Rate limit - exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                        time.sleep(wait_time)
                        continue
                    return None
                print(f"HTTP error looking up UPC {upc}: {e}")
                return None
            except Exception as e:
                print(f"Error looking up UPC {upc}: {e}")
                return None

        return None

    def get_competitive_price(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[Dict]:
        """
        Get competitive pricing for an ASIN

        Args:
            asin: Amazon ASIN
            marketplace_id: Amazon marketplace ID

        Returns:
            Pricing data including current price, buybox price
        """
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/products/pricing/v0/items/{asin}/offers"
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json"
        }
        params = {
            "MarketplaceId": marketplace_id,
            "ItemCondition": "New"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting price for ASIN {asin}: {e}")
            return None

    def get_fba_fees(self, asin: str, price: float, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[Dict]:
        """
        Get FBA fees estimate for a product

        Args:
            asin: Amazon ASIN
            price: Product price for fee calculation
            marketplace_id: Amazon marketplace ID

        Returns:
            FBA fees breakdown
        """
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/products/fees/v0/items/{asin}/feesEstimate"
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json"
        }
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": marketplace_id,
                "IsAmazonFulfilled": True,
                "PriceToEstimateFees": {
                    "ListingPrice": {
                        "CurrencyCode": "USD",
                        "Amount": price
                    }
                },
                "Identifier": asin
            }
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("payload"):
                return data["payload"].get("FeesEstimateResult")
            return None

        except Exception as e:
            print(f"Error getting FBA fees for ASIN {asin}: {e}")
            return None

    def get_product_variations(self, asin: str, marketplace_id: str = "ATVPDKIKX0DER") -> List[Dict]:
        """
        Get all variations of a product (different pack sizes, colors, etc.)

        Args:
            asin: Parent or child ASIN
            marketplace_id: Amazon marketplace ID

        Returns:
            List of variation data dictionaries
        """
        token = self.get_access_token()
        if not token:
            return []

        url = f"{self.base_url}/catalog/2022-04-01/items/{asin}"
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json"
        }
        params = {
            "marketplaceIds": marketplace_id,
            "includedData": "attributes,dimensions,identifiers,salesRanks,summaries,variations"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            variations = []

            # Check if this product has variations
            if data.get("variations"):
                for variation in data["variations"]:
                    variations.append(variation)

            # If no variations found, return the original ASIN as single variation
            if not variations and data.get("asin"):
                variations.append({
                    "asin": data["asin"],
                    "attributes": data.get("attributes", {}),
                    "summaries": data.get("summaries", [])
                })

            return variations

        except Exception as e:
            # Variations not available or error - return empty list
            return []

    def find_best_variation_match(
        self,
        variations: List[Dict],
        target_pack_size: Optional[int],
        js_api: 'JungleScoutAPI'
    ) -> Optional[Tuple[Dict, Dict]]:
        """
        Find the variation that best matches your product's pack size

        Args:
            variations: List of Amazon product variations
            target_pack_size: Pack size from your catalog
            js_api: Jungle Scout API instance for getting sales data

        Returns:
            Tuple of (variation_data, jungle_scout_data) or None
        """
        if not variations:
            return None

        best_match = None
        best_score = -1

        for variation in variations:
            asin = variation.get('asin')
            if not asin:
                continue

            # Get title/attributes to extract pack size
            summaries = variation.get('summaries', [{}])
            title = summaries[0].get('itemName', '') if summaries else ''

            # Extract pack size from Amazon listing
            amazon_pack_size = extract_pack_size(title)

            # Calculate match score
            score = 0

            if target_pack_size and amazon_pack_size:
                # Exact match is best
                if amazon_pack_size == target_pack_size:
                    score = 100
                # Close match (within 20%)
                elif abs(amazon_pack_size - target_pack_size) / target_pack_size < 0.2:
                    score = 80
                # Same order of magnitude
                elif 0.5 <= amazon_pack_size / target_pack_size <= 2.0:
                    score = 50
                else:
                    score = 10
            elif not target_pack_size and amazon_pack_size == 1:
                # If we don't know pack size, prefer single units
                score = 60
            else:
                # Default score
                score = 30

            if score > best_score:
                best_score = score
                best_match = variation

        # Get Jungle Scout data for best match
        if best_match:
            asin = best_match.get('asin')
            js_data = js_api.lookup_by_asin(asin) if asin else None
            return (best_match, js_data)

        return None


class JungleScoutAPI:
    """Jungle Scout Cobalt API client for sales estimates"""

    def __init__(self, api_name: str, api_key: str):
        self.api_name = api_name
        self.api_key = api_key
        self.base_url = "https://developer.junglescout.com/api"
        self.headers = {
            "Authorization": f"{api_name}:{api_key}",
            "Content-Type": "application/json"
        }

    def lookup_by_upc(self, upc: str, marketplace: str = "us") -> Optional[Dict]:
        """
        Look up product by UPC

        Args:
            upc: Product UPC
            marketplace: Amazon marketplace

        Returns:
            Product data with sales estimates
        """
        # First search for the product
        search_url = f"{self.base_url}/keywords/keywords_by_keyword_query"
        search_params = {
            "marketplace": marketplace,
            "keyword": upc,
            "categories": []
        }

        try:
            response = requests.get(search_url, headers=self.headers, params=search_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("data") and len(data["data"]) > 0:
                asin = data["data"][0].get("asin")
                if asin:
                    return self.get_product_details(asin, marketplace)
            return None

        except Exception as e:
            print(f"JS Error looking up UPC {upc}: {e}")
            return None

    def lookup_by_asin(self, asin: str, marketplace: str = "us") -> Optional[Dict]:
        """Look up product by ASIN"""
        return self.get_product_details(asin, marketplace)

    def get_product_details(self, asin: str, marketplace: str = "us") -> Optional[Dict]:
        """Get detailed product information and sales estimates"""
        url = f"{self.base_url}/product/single_product"
        params = {
            "asin": asin,
            "marketplace": marketplace
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except Exception as e:
            print(f"JS Error getting details for ASIN {asin}: {e}")
            return None


class FBAProfitAnalyzer:
    """Main analyzer combining all data sources"""

    def __init__(self, sp_api: AmazonSPAPI, js_api: JungleScoutAPI):
        self.sp_api = sp_api
        self.js_api = js_api
        self.marketplace_id = "ATVPDKIKX0DER"  # US marketplace

    def analyze_product(self, product_data: Dict) -> Dict:
        """
        Analyze a single product from your catalog

        Args:
            product_data: Row from your master catalog CSV

        Returns:
            Complete analysis including FBA fees and profit projections
        """
        upc_raw = str(product_data.get('ItemLookupCode', '')).strip()

        # Convert scientific notation to full number (Excel issue)
        # e.g., "7.19411E+11" → "719411000000"
        if 'E+' in upc_raw.upper() or 'E-' in upc_raw.upper():
            try:
                upc = str(int(float(upc_raw)))
            except:
                upc = upc_raw
        else:
            upc = upc_raw

        your_cost = float(product_data.get('Cost', 0) or 0)
        your_price = float(product_data.get('Price', 0) or 0)
        description = product_data.get('Description', '')

        # Extract pack size from your catalog
        your_pack_size = extract_pack_size(description)

        result = {
            # Your catalog data
            'item_id': product_data.get('ItemID'),
            'upc': upc,
            'description': description,
            'brand': product_data.get('Brand'),
            'category': product_data.get('CurrentCategory'),
            'main_category': product_data.get('MainCategory'),
            'subcategory': product_data.get('Subcategory'),
            'product_type': product_data.get('ProductType'),
            'your_cost': your_cost,
            'your_price': your_price,
            'your_margin': product_data.get('GrossMargin'),
            'on_hand': product_data.get('OnHand'),
            'monthly_qty': product_data.get('MonthlyAvgQty'),
            'monthly_revenue': product_data.get('MonthlyAvgRevenue'),
            'your_pack_size': your_pack_size or '',

            # Amazon data (to be filled)
            'asin': '',
            'amazon_title': '',
            'amazon_pack_size': '',
            'pack_size_match': '',
            'amazon_price': 0,
            'amazon_price_per_unit': 0,
            'your_price_per_unit': 0,
            'amazon_bsr': '',
            'amazon_rating': '',
            'amazon_reviews': '',
            'amazon_sellers_count': '',

            # FBA data
            'fba_available': 'Unknown',
            'fba_fee_total': 0,
            'fba_referral_fee': 0,
            'fba_fulfillment_fee': 0,
            'fba_storage_fee': 0,

            # Jungle Scout sales data
            'js_monthly_sales_units': '',
            'js_monthly_revenue': '',
            'js_price': '',

            # Profit calculations
            'projected_amazon_price': 0,
            'projected_fba_profit': 0,
            'projected_fba_profit_per_unit': 0,
            'projected_fba_roi': 0,
            'vs_your_retail_profit': 0,

            # Metadata
            'data_source': '',
            'timestamp': datetime.now().isoformat()
        }

        # CHECK 1: Filter out tobacco/vapor products
        if is_tobacco_or_vapor_product(product_data):
            result['data_source'] = 'TOBACCO_VAPOR_EXCLUDED'
            return result

        if not upc or upc == '0':
            result['data_source'] = 'NO_UPC'
            return result

        # STEP 1: Use Amazon SP-API to get ASIN from UPC
        amazon_product = self.sp_api.lookup_product_by_upc(upc, self.marketplace_id)

        # STEP 1B: If primary UPC failed, try alternate barcodes
        if not amazon_product:
            alternates_str = str(product_data.get('AlternateBarcodes', '')).strip()

            if alternates_str:
                # Parse pipe-separated alternates
                alternate_upcs = [alt.strip() for alt in alternates_str.split('|') if alt.strip()]

                # Try up to 5 alternate UPCs (with retry logic, this is safe)
                for idx, alt_upc in enumerate(alternate_upcs[:5], 1):
                    # Skip if alternate is same as primary
                    if alt_upc == upc:
                        continue

                    # Convert scientific notation if needed
                    if 'E+' in alt_upc.upper() or 'E-' in alt_upc.upper():
                        try:
                            alt_upc = str(int(float(alt_upc)))
                        except:
                            pass

                    # Small delay between alternate attempts to avoid rate limiting
                    time.sleep(0.25)

                    amazon_product = self.sp_api.lookup_product_by_upc(alt_upc, self.marketplace_id)

                    if amazon_product:
                        result['data_source'] = f'ALTERNATE_UPC_{idx}'
                        upc = alt_upc  # Update UPC to the one that worked
                        result['upc'] = upc
                        break

        if not amazon_product:
            result['data_source'] = 'NOT_FOUND'
            return result

        asin = amazon_product.get('asin')
        if not asin:
            result['data_source'] = 'NOT_FOUND'
            return result

        result['asin'] = asin
        result['data_source'] = 'AMAZON_SP_API'

        # CHECK FOR PRODUCT VARIATIONS (different pack sizes on Amazon)
        variations = self.sp_api.get_product_variations(asin, self.marketplace_id)

        if variations and len(variations) > 1:
            # Multiple variations found - find best match for our pack size
            match_result = self.sp_api.find_best_variation_match(
                variations,
                your_pack_size,
                self.js_api
            )

            if match_result:
                best_variation, variation_js_data = match_result

                # Update ASIN to the best matching variation
                asin = best_variation.get('asin', asin)
                result['asin'] = asin

                # Extract pack size from matched variation
                var_summaries = best_variation.get('summaries', [{}])
                var_title = var_summaries[0].get('itemName', '') if var_summaries else ''
                amazon_pack_size = extract_pack_size(var_title)

                result['amazon_pack_size'] = amazon_pack_size or ''
                result['amazon_title'] = var_title

                # Determine match quality
                if your_pack_size and amazon_pack_size:
                    if amazon_pack_size == your_pack_size:
                        result['pack_size_match'] = 'EXACT'
                    elif abs(amazon_pack_size - your_pack_size) / your_pack_size < 0.2:
                        result['pack_size_match'] = 'CLOSE'
                    else:
                        result['pack_size_match'] = 'DIFFERENT'
                else:
                    result['pack_size_match'] = 'UNKNOWN'

                # Use variation's Jungle Scout data if available
                if variation_js_data:
                    js_product = variation_js_data

                result['data_source'] = result.get('data_source', '') + ' + VARIATION_MATCHED'

        # Get Amazon data
        if amazon_product:
            summaries = amazon_product.get('summaries', [{}])[0] if amazon_product.get('summaries') else {}
            result['amazon_title'] = summaries.get('itemName', '')
            result['amazon_brand'] = summaries.get('brand', '')

            # Sales rank
            sales_ranks = amazon_product.get('salesRanks', [])
            if sales_ranks:
                result['amazon_bsr'] = sales_ranks[0].get('rank', '')

        # STEP 2: Get Jungle Scout data using the ASIN we got from Amazon
        js_product = None
        if asin:
            js_product = self.js_api.lookup_by_asin(asin)

        if js_product:
            result['js_monthly_sales_units'] = js_product.get('approximate_30_day_sales', '')
            result['js_monthly_revenue'] = js_product.get('approximate_30_day_revenue', '')
            result['js_price'] = js_product.get('price', '')
            result['amazon_bsr'] = result['amazon_bsr'] or js_product.get('ranks', [{}])[0].get('rank', '')
            result['amazon_rating'] = js_product.get('rating', '')
            result['amazon_reviews'] = js_product.get('reviews_count', '')
            result['amazon_sellers_count'] = js_product.get('sellers_count', '')
            result['fba_available'] = 'Yes' if js_product.get('has_fba_offers') else 'No'
            result['amazon_title'] = result['amazon_title'] or js_product.get('title', '')

            if result['data_source'] == 'AMAZON_SP_API':
                result['data_source'] = 'AMAZON_SP_API + JUNGLE_SCOUT'

        # Get competitive pricing from Amazon
        price_data = self.sp_api.get_competitive_price(asin, self.marketplace_id)
        amazon_price = 0

        if price_data and price_data.get('payload'):
            offers = price_data['payload'].get('Offers', [])
            if offers:
                listing_price = offers[0].get('ListingPrice', {})
                amazon_price = float(listing_price.get('Amount', 0))

        # Use best available price
        if amazon_price > 0:
            result['amazon_price'] = amazon_price
            result['projected_amazon_price'] = amazon_price
        elif result['js_price']:
            result['amazon_price'] = float(result['js_price'])
            result['projected_amazon_price'] = float(result['js_price'])
        elif your_price > 0:
            # Use your price as fallback
            result['projected_amazon_price'] = your_price * 1.1  # Assume 10% higher on Amazon

        # Get FBA fees
        if result['projected_amazon_price'] > 0:
            fba_fees = self.sp_api.get_fba_fees(asin, result['projected_amazon_price'], self.marketplace_id)

            if fba_fees and fba_fees.get('FeesEstimate'):
                fee_details = fba_fees['FeesEstimate'].get('FeeDetailList', [])

                total_fees = 0
                for fee in fee_details:
                    fee_type = fee.get('FeeType')
                    fee_amount = float(fee.get('FeeAmount', {}).get('Amount', 0))
                    total_fees += fee_amount

                    if 'Referral' in fee_type:
                        result['fba_referral_fee'] = fee_amount
                    elif 'FBA' in fee_type or 'Fulfillment' in fee_type:
                        result['fba_fulfillment_fee'] = fee_amount
                    elif 'Storage' in fee_type:
                        result['fba_storage_fee'] = fee_amount

                result['fba_fee_total'] = total_fees

        # Calculate profit projections
        if result['projected_amazon_price'] > 0 and your_cost > 0:
            # Get pack sizes for normalization
            amazon_pack = result.get('amazon_pack_size', 0)
            your_pack = result.get('your_pack_size', 0)

            # If we don't know pack sizes, assume they match
            if not amazon_pack:
                amazon_pack = your_pack if your_pack else 1
            if not your_pack:
                your_pack = amazon_pack if amazon_pack else 1

            # Calculate per-unit pricing for comparison
            result['amazon_price_per_unit'] = normalize_price_per_unit(
                result['projected_amazon_price'],
                amazon_pack
            )
            result['your_price_per_unit'] = normalize_price_per_unit(
                your_price,
                your_pack
            ) if your_price > 0 else 0

            # FBA Profit = Amazon Price - FBA Fees - Your Cost
            result['projected_fba_profit'] = (
                result['projected_amazon_price'] -
                result['fba_fee_total'] -
                your_cost
            )

            # Calculate profit per unit (normalized)
            # This accounts for pack size differences
            if amazon_pack > 0:
                result['projected_fba_profit_per_unit'] = (
                    result['amazon_price_per_unit'] -
                    (result['fba_fee_total'] / amazon_pack) -
                    (your_cost / (your_pack if your_pack > 0 else 1))
                )

            # ROI = (Profit / Cost) * 100
            if your_cost > 0:
                result['projected_fba_roi'] = (result['projected_fba_profit'] / your_cost) * 100

            # Compare to your retail margin
            if your_price > 0:
                your_retail_profit = your_price - your_cost
                result['vs_your_retail_profit'] = result['projected_fba_profit'] - your_retail_profit

        return result


def process_catalog(
    input_file: str,
    output_file: str,
    sp_api: AmazonSPAPI,
    js_api: JungleScoutAPI,
    rate_limit: float = 2.0,
    max_products: int = None,
    filter_active_only: bool = False,
    active_months: int = 12
):
    """
    Process entire product catalog

    Args:
        input_file: Path to master product catalog CSV
        output_file: Path to output analysis CSV
        sp_api: Amazon SP-API instance
        js_api: Jungle Scout API instance
        rate_limit: Seconds to wait between API calls
        max_products: Maximum number of products to process (for testing)
        filter_active_only: Only analyze products sold & purchased recently
        active_months: How many months to look back for activity (default 12)
    """
    analyzer = FBAProfitAnalyzer(sp_api, js_api)

    print("=" * 80)
    print("FBA PROFIT ANALYZER")
    print("=" * 80)
    print(f"\nReading catalog: {input_file}")

    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        return

    results = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)

        catalog_total = len(products)

        # Apply active product filter if requested
        if filter_active_only:
            print(f"Filtering for products sold & purchased in last {active_months} months...")
            products = [p for p in products if is_active_product(p, active_months)]
            print(f"  Catalog total: {catalog_total}")
            print(f"  Active products: {len(products)}")
            print(f"  Filtered out: {catalog_total - len(products)} (inactive)\n")

        total = len(products)
        if max_products:
            total = min(total, max_products)
            products = products[:max_products]

        print(f"Processing {total} products\n")

        for idx, product in enumerate(products, 1):
            upc = product.get('ItemLookupCode', '')
            description = product.get('Description', '')

            print(f"[{idx}/{total}] {description[:60]}")
            print(f"  UPC: {upc}")

            # Analyze product
            result = analyzer.analyze_product(product)
            results.append(result)

            # Print summary
            if result['data_source'] == 'TOBACCO_VAPOR_EXCLUDED':
                print(f"  ⊘ Tobacco/Vapor - Skipped (not allowed on Amazon)")
            elif result['asin']:
                print(f"  ✓ ASIN: {result['asin']}")

                # Show pack size matching if applicable
                if result.get('pack_size_match'):
                    your_pack = result.get('your_pack_size', '')
                    amz_pack = result.get('amazon_pack_size', '')
                    match_type = result['pack_size_match']

                    if match_type == 'EXACT':
                        print(f"  Pack: {your_pack}ct (Exact match ✓)")
                    elif match_type == 'CLOSE':
                        print(f"  Pack: Yours={your_pack}ct, Amazon={amz_pack}ct (Close match)")
                    elif match_type == 'DIFFERENT':
                        print(f"  Pack: Yours={your_pack}ct, Amazon={amz_pack}ct (Different sizes!)")

                print(f"  Amazon Price: ${result['projected_amazon_price']:.2f}")

                # Show per-unit pricing if pack sizes differ
                if result.get('pack_size_match') == 'DIFFERENT' and result.get('amazon_price_per_unit'):
                    print(f"  Per Unit: ${result['amazon_price_per_unit']:.2f}")

                print(f"  FBA Fees: ${result['fba_fee_total']:.2f}")
                print(f"  Projected Profit: ${result['projected_fba_profit']:.2f} ({result['projected_fba_roi']:.1f}% ROI)")

                if result['js_monthly_sales_units']:
                    print(f"  Est. Monthly Sales: {result['js_monthly_sales_units']} units")
            else:
                print(f"  ✗ Not found on Amazon ({result['data_source']})")

            print()

            # Rate limiting
            if idx < total:
                time.sleep(rate_limit)

    # Write results
    print("=" * 80)
    print(f"Writing results to: {output_file}")

    if results:
        fieldnames = list(results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        # Summary statistics
        tobacco_excluded = sum(1 for r in results if r['data_source'] == 'TOBACCO_VAPOR_EXCLUDED')
        found = sum(1 for r in results if r['asin'])
        variation_matched = sum(1 for r in results if 'VARIATION_MATCHED' in r.get('data_source', ''))
        profitable = sum(1 for r in results if r['projected_fba_profit'] > 0)
        total_potential_profit = sum(r['projected_fba_profit'] for r in results if r['projected_fba_profit'] > 0)

        print(f"\n✓ Analysis complete!")
        print(f"  Products in catalog: {len(results)}")
        print(f"  Tobacco/Vapor excluded: {tobacco_excluded} (saved API calls!)")
        print(f"  Found on Amazon: {found}")
        print(f"  Variation matched: {variation_matched} (pack size optimization)")
        print(f"  Potentially profitable: {profitable}")
        print(f"  Total potential monthly profit: ${total_potential_profit:.2f}")
        print(f"\nResults saved to: {output_file}")
    else:
        print("No results to write")


def main():
    """Main execution"""

    # Load configuration
    SP_REFRESH_TOKEN = os.getenv("SP_REFRESH_TOKEN")
    SP_CLIENT_ID = os.getenv("SP_CLIENT_ID")
    SP_CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
    SP_REGION = os.getenv("SP_REGION", "us-east-1")

    JS_API_NAME = os.getenv("JS_API_NAME")
    JS_API_KEY = os.getenv("JS_API_KEY")

    INPUT_CSV = os.getenv("INPUT_CSV", "master_product_catalog.csv")
    OUTPUT_CSV = os.getenv("OUTPUT_CSV", "fba_profit_analysis.csv")
    RATE_LIMIT = float(os.getenv("RATE_LIMIT", "2.0"))
    MAX_PRODUCTS = os.getenv("MAX_PRODUCTS")
    FILTER_ACTIVE_ONLY = os.getenv("FILTER_ACTIVE_ONLY", "false").lower() == "true"
    ACTIVE_MONTHS = int(os.getenv("ACTIVE_MONTHS", "12"))

    # Validate configuration
    if not all([SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET]):
        print("ERROR: Amazon SP-API credentials not configured!")
        print("\nRequired environment variables:")
        print("  SP_REFRESH_TOKEN")
        print("  SP_CLIENT_ID")
        print("  SP_CLIENT_SECRET")
        print("\nSee .env.example for setup instructions")
        return

    if not all([JS_API_NAME, JS_API_KEY]):
        print("ERROR: Jungle Scout API credentials not configured!")
        print("\nRequired environment variables:")
        print("  JS_API_NAME")
        print("  JS_API_KEY")
        return

    # Initialize APIs
    sp_api = AmazonSPAPI(SP_REFRESH_TOKEN, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_REGION)
    js_api = JungleScoutAPI(JS_API_NAME, JS_API_KEY)

    # Process catalog
    max_prod = int(MAX_PRODUCTS) if MAX_PRODUCTS else None
    process_catalog(
        INPUT_CSV,
        OUTPUT_CSV,
        sp_api,
        js_api,
        RATE_LIMIT,
        max_prod,
        FILTER_ACTIVE_ONLY,
        ACTIVE_MONTHS
    )


if __name__ == "__main__":
    main()
