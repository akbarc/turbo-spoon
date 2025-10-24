import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from folium import plugins
import time
import re

def clean_address_smart(row):
    """Smart address cleaning and validation"""
    address_parts = []
    
    # Get and clean main address
    addr = str(row.get('Address', '')).strip()
    if addr and addr != 'nan':
        # Clean common issues
        addr = re.sub(r'\s+', ' ', addr)  # Multiple spaces
        addr = re.sub(r'^[^\w\d]+', '', addr)  # Leading non-alphanumeric
        addr = addr.replace(' INC', '').replace(' LLC', '').replace(' CORP', '')
        
        # Skip if it looks like a company name rather than address
        if not re.search(r'\d+\s+[A-Za-z]', addr):  # No number + street pattern
            return None, "No street number found"
            
        address_parts.append(addr)
    else:
        return None, "No main address"
    
    # Add city (required)
    city = str(row.get('City', '')).strip()
    if city and city != 'nan':
        city = city.replace(' INC', '').replace(' LLC', '')
        address_parts.append(city)
    else:
        return None, "No city"
    
    # Add state (default to GA if missing)
    state = str(row.get('State', 'GA')).strip()
    if state and state != 'nan':
        address_parts.append(state)
    else:
        address_parts.append('GA')
    
    # Add zip if available and valid
    zip_code = str(row.get('Zip', '')).strip()
    if zip_code and zip_code != 'nan':
        # Clean zip
        zip_code = re.sub(r'\.0$', '', zip_code)  # Remove .0
        zip_code = re.sub(r'[^\d-]', '', zip_code)  # Only digits and dashes
        if len(zip_code) >= 5:
            address_parts.append(zip_code)
    
    full_address = ', '.join(address_parts)
    return full_address, "OK"

def test_sample_addresses(df, sample_size=10):
    """Test a small sample first to check success rate"""
    print(f"Testing {sample_size} sample addresses...")
    
    sample_df = df.head(sample_size)
    test_addresses = []
    test_info = []
    
    for idx, row in sample_df.iterrows():
        addr, status = clean_address_smart(row)
        if addr:
            test_addresses.append(addr)
            test_info.append({
                'row': idx,
                'name': f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip(),
                'company': row.get('Company', ''),
                'status': status
            })
    
    print(f"Sample addresses to test:")
    for i, (addr, info) in enumerate(zip(test_addresses, test_info)):
        print(f"  {i+1}. {addr}")
    
    # Test geocoding
    geolocator = Nominatim(user_agent="georgia_test_mapper")
    success_count = 0
    
    for i, addr in enumerate(test_addresses):
        try:
            print(f"Testing {i+1}/{len(test_addresses)}: {addr}")
            location = geolocator.geocode(addr, timeout=10)
            if location:
                print(f"  ✓ SUCCESS: {location.latitude:.6f}, {location.longitude:.6f}")
                success_count += 1
            else:
                print(f"  ✗ NOT FOUND")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠ ERROR: {e}")
    
    success_rate = success_count / len(test_addresses) * 100
    print(f"\nSample test results: {success_count}/{len(test_addresses)} successful ({success_rate:.1f}%)")
    
    return success_rate > 70  # Continue if >70% success rate

def geocode_with_fallbacks(address, geolocator):
    """Try multiple variations of an address"""
    variations = [
        address,  # Original
        address.replace(' STE ', ' SUITE '),  # Suite variation
        address.replace(' SUITE ', ' STE '),  # Suite variation reverse
        re.sub(r',\s*\d{5}.*$', '', address),  # Without zip
        re.sub(r'\s+STE\s+\w+', '', address),  # Without suite
    ]
    
    for i, addr_variant in enumerate(variations):
        try:
            location = geolocator.geocode(addr_variant, timeout=10)
            if location:
                return location, addr_variant, f"variant_{i}"
        except Exception:
            continue
    
    return None, address, "all_failed"

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("Reading customer data...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} customer records")
    
    # Test sample first
    if not test_sample_addresses(df, 10):
        print("❌ Sample test failed. Address format issues detected.")
        print("Let me analyze the address patterns...")
        
        # Analyze address patterns
        print("\nAddress pattern analysis:")
        for i in range(min(20, len(df))):
            row = df.iloc[i]
            addr, status = clean_address_smart(row)
            print(f"Row {i}: {status} -> {addr}")
        
        return
    
    print("✅ Sample test passed! Proceeding with full geocoding...")
    
    # Process all addresses
    print("Processing all addresses...")
    addresses = []
    customer_info = []
    skipped = 0
    
    for idx, row in df.iterrows():
        addr, status = clean_address_smart(row)
        if addr:
            addresses.append(addr)
            customer_info.append({
                'Account #': row.get('Account #', 'Unknown'),
                'FirstName': row.get('FirstName', ''),
                'LastName': row.get('LastName', ''),
                'Company': row.get('Company', ''),
                'Phone #': row.get('Phone #', ''),
                'Total Sales': row.get('Total Sales', 0),
                'Balance': row.get('Balance', 0),
                'original_address': f"{row.get('Address', '')} {row.get('City', '')} {row.get('State', '')} {row.get('Zip', '')}".strip()
            })
        else:
            skipped += 1
    
    print(f"Prepared {len(addresses)} valid addresses (skipped {skipped} invalid)")
    
    # Geocode with smart batching
    print(f"\nGeocoding {len(addresses)} addresses with fallback strategies...")
    geolocator = Nominatim(user_agent="georgia_smart_mapper")
    results = []
    
    batch_size = 50
    for i in range(0, len(addresses), batch_size):
        batch_end = min(i + batch_size, len(addresses))
        print(f"\nBatch {i//batch_size + 1}: Processing addresses {i+1}-{batch_end}")
        
        for j in range(i, batch_end):
            addr = addresses[j]
            info = customer_info[j]
            
            print(f"  {j+1}/{len(addresses)}: {addr}")
            
            location, used_addr, method = geocode_with_fallbacks(addr, geolocator)
            
            if location:
                results.append({
                    'address': addr,
                    'used_address': used_addr,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'full_address': location.address,
                    'status': 'success',
                    'method': method,
                    'customer_info': info
                })
                print(f"    ✓ SUCCESS ({method}): {location.latitude:.6f}, {location.longitude:.6f}")
            else:
                results.append({
                    'address': addr,
                    'used_address': addr,
                    'latitude': None,
                    'longitude': None,
                    'status': 'not_found',
                    'method': 'failed',
                    'customer_info': info
                })
                print(f"    ✗ NOT FOUND")
            
            time.sleep(0.5)  # Rate limiting
        
        # Progress update
        successful = len([r for r in results if r['status'] == 'success'])
        print(f"  Progress: {successful}/{len(results)} successful ({successful/len(results)*100:.1f}%)")
    
    # Create map
    print(f"\nCreating map...")
    valid_locations = [r for r in results if r['status'] == 'success']
    
    if not valid_locations:
        print("❌ No valid locations found!")
        return
    
    # Create map
    center_lat = np.mean([loc['latitude'] for loc in valid_locations])
    center_lon = np.mean([loc['longitude'] for loc in valid_locations])
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
    
    marker_cluster = plugins.MarkerCluster().add_to(m)
    
    for i, loc in enumerate(valid_locations):
        info = loc['customer_info']
        name = f"{info.get('FirstName', '')} {info.get('LastName', '')}".strip()
        if not name:
            name = info.get('Company', f'Customer {i+1}')
        
        popup_html = f"""
        <div style="width: 300px;">
            <h4>{name}</h4>
            <p><b>Account:</b> {info.get('Account #', 'N/A')}</p>
            <p><b>Company:</b> {info.get('Company', 'N/A')}</p>
            <p><b>Address:</b> {loc['address']}</p>
            <p><b>Sales:</b> ${info.get('Total Sales', 0):,.2f}</p>
            <p><b>Method:</b> {loc['method']}</p>
        </div>
        """
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=name
        ).add_to(marker_cluster)
    
    # Save files
    map_file = "/Users/akbarchranya/georgiadashboard/smart_customer_map.html"
    m.save(map_file)
    
    # Save CSV
    csv_data = []
    for result in results:
        info = result['customer_info']
        csv_data.append({
            'account': info.get('Account #'),
            'name': f"{info.get('FirstName', '')} {info.get('LastName', '')}".strip(),
            'company': info.get('Company'),
            'original_address': info.get('original_address'),
            'cleaned_address': result['address'],
            'used_address': result.get('used_address'),
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'status': result['status'],
            'method': result.get('method'),
            'total_sales': info.get('Total Sales', 0)
        })
    
    results_df = pd.DataFrame(csv_data)
    csv_file = "/Users/akbarchranya/georgiadashboard/smart_geocoded_results.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Final summary
    successful = len([r for r in results if r['status'] == 'success'])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"SMART CUSTOMER MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Total addresses processed: {total}")
    print(f"✅ Successfully geocoded: {successful}")
    print(f"❌ Failed: {total - successful}")
    print(f"📈 Success rate: {successful/total*100:.1f}%")
    print(f"\n📍 Map created: {map_file}")
    print(f"📄 Results saved: {csv_file}")
    print(f"\n🎉 Open the HTML file to explore {successful} customer locations!")

if __name__ == "__main__":
    main()
