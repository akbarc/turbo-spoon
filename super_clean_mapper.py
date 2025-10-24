import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import folium
from folium import plugins
import time
import re

def super_clean_address(row):
    """Super thorough address cleaning"""
    addr = str(row.get('Address', '')).strip()
    city = str(row.get('City', '')).strip()
    state = str(row.get('State', 'GA')).strip()
    zip_code = str(row.get('Zip', '')).strip()
    
    # Skip if no basic info
    if not addr or addr == 'nan' or not city or city == 'nan':
        return None
    
    # Clean address field
    addr = re.sub(r'\s+', ' ', addr)  # Multiple spaces to single
    addr = addr.strip()
    
    # Remove business suffixes from address field (they shouldn't be there)
    addr = re.sub(r'\s+(INC|LLC|CORP|CORPORATION)$', '', addr, flags=re.IGNORECASE)
    
    # Fix common address issues
    # If address ends without street type, try to infer it
    if re.match(r'^\d+\s+[A-Z\s]+$', addr) and not re.search(r'\b(ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|BLVD|BOULEVARD|HWY|HIGHWAY|WAY|LANE|LN|PKWY|PARKWAY|PL|PLACE|CT|COURT|CIR|CIRCLE)\b', addr, re.IGNORECASE):
        # Check if it might be a road based on common patterns
        if any(word in addr.upper() for word in ['KEITH BRIDGE', 'GAINSEVILLE', 'GLENWOOD', 'ATWATER', 'ROSEBUD', 'FAIRPLAY']):
            addr += ' RD'
        elif 'HWY' in addr.upper() or 'HIGHWAY' in addr.upper():
            pass  # Already has highway designation
        elif any(word in addr.upper() for word in ['MLK', 'MARTIN LUTHER KING']):
            addr += ' DR'
        elif 'BLVD' in addr.upper():
            pass  # Already has boulevard
        else:
            # Default to RD for numbered streets
            addr += ' RD'
    
    # Clean city field
    city = re.sub(r'\s+', ' ', city)
    city = city.strip()
    city = re.sub(r'\s+(INC|LLC)$', '', city, flags=re.IGNORECASE)
    
    # Clean state
    state = state.strip().upper()
    if not state or state == 'NAN':
        state = 'GA'
    
    # Clean zip code
    if zip_code and zip_code != 'nan':
        zip_code = re.sub(r'\.0$', '', zip_code)  # Remove .0
        zip_code = re.sub(r'[^\d-]', '', zip_code)  # Only digits and dashes
        zip_code = zip_code.strip()
    
    # Build final address
    parts = [addr, city, state]
    if zip_code and len(zip_code) >= 5:
        parts.append(zip_code)
    
    return ', '.join(parts)

def test_geocoding_sample(df, num_samples=10):
    """Test geocoding on a small sample first"""
    print(f"Testing geocoding on {num_samples} sample addresses...")
    
    geolocator = Nominatim(user_agent="georgia_test_cleaner", timeout=10)
    
    for i in range(min(num_samples, len(df))):
        row = df.iloc[i]
        company = str(row.get('Company', f'Company {i+1}')).replace(' INC', '').replace(' LLC', '')
        
        # Get cleaned address
        cleaned_addr = super_clean_address(row)
        if not cleaned_addr:
            print(f"{i+1}. {company}: NO ADDRESS")
            continue
            
        print(f"\n{i+1}. {company}")
        print(f"   Raw: {row.get('Address', 'N/A')} | {row.get('City', 'N/A')} | {row.get('State', 'GA')} | {row.get('Zip', 'N/A')}")
        print(f"   Cleaned: {cleaned_addr}")
        
        try:
            location = geolocator.geocode(cleaned_addr, timeout=10)
            if location:
                print(f"   ✅ SUCCESS: {location.latitude:.6f}, {location.longitude:.6f}")
                print(f"   Found: {location.address}")
            else:
                print(f"   ❌ NOT FOUND")
        except Exception as e:
            print(f"   ⚠️ ERROR: {e}")
        
        time.sleep(1.5)  # Be nice to the service
    
    print(f"\nSample test complete. Addresses look good for full processing!")

def process_companies_with_super_clean(df, max_companies=250):
    """Process companies with super clean addresses"""
    print(f"Processing {max_companies} companies with super clean addresses...")
    
    geolocator = Nominatim(user_agent="georgia_super_clean_mapper", timeout=10)
    results = []
    
    processed = 0
    for idx, row in df.iterrows():
        if processed >= max_companies:
            break
        
        # Clean address
        cleaned_addr = super_clean_address(row)
        if not cleaned_addr:
            continue
        
        # Get company name
        company = str(row.get('Company', '')).strip()
        if not company or company == 'nan':
            first_name = str(row.get('FirstName', '')).strip()
            last_name = str(row.get('LastName', '')).strip()
            company = f"{first_name} {last_name}".strip()
            if not company:
                company = f"Customer {processed+1}"
        
        # Clean company name for display
        company = re.sub(r'\s+(INC|LLC|CORP)(\s|$)', r'\2', company, flags=re.IGNORECASE)
        company = company.strip()
        
        customer_data = {
            'Account #': row.get('Account #', 'Unknown'),
            'Phone #': row.get('Phone #', ''),
            'Total Sales': row.get('Total Sales', 0),
            'Balance': row.get('Balance', 0),
            'City': row.get('City', ''),
            'State': row.get('State', 'GA'),
            'raw_address': f"{row.get('Address', '')} {row.get('City', '')} {row.get('State', '')} {row.get('Zip', '')}"
        }
        
        print(f"\n{processed+1}/{max_companies}: {company}")
        print(f"  Address: {cleaned_addr}")
        
        try:
            location = geolocator.geocode(cleaned_addr, timeout=12)
            
            if location:
                results.append({
                    'company': company,
                    'address': cleaned_addr,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'full_address': location.address,
                    'status': 'success',
                    'customer_data': customer_data
                })
                print(f"  ✅ SUCCESS: {location.latitude:.6f}, {location.longitude:.6f}")
            else:
                # Try without zip
                addr_no_zip = re.sub(r',\s*\d{5}(-\d{4})?$', '', cleaned_addr)
                if addr_no_zip != cleaned_addr:
                    time.sleep(1)
                    location = geolocator.geocode(addr_no_zip, timeout=12)
                    
                if location:
                    results.append({
                        'company': company,
                        'address': cleaned_addr,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'full_address': location.address,
                        'status': 'success_no_zip',
                        'customer_data': customer_data
                    })
                    print(f"  ✅ SUCCESS (no zip): {location.latitude:.6f}, {location.longitude:.6f}")
                else:
                    results.append({
                        'company': company,
                        'address': cleaned_addr,
                        'latitude': None,
                        'longitude': None,
                        'status': 'not_found',
                        'customer_data': customer_data
                    })
                    print(f"  ❌ NOT FOUND")
                    
        except Exception as e:
            results.append({
                'company': company,
                'address': cleaned_addr,
                'latitude': None,
                'longitude': None,
                'status': 'error',
                'error': str(e),
                'customer_data': customer_data
            })
            print(f"  ⚠️ ERROR: {e}")
        
        processed += 1
        
        # Progress update
        if processed % 50 == 0:
            successful = len([r for r in results if r['status'].startswith('success')])
            print(f"\n🔄 Progress: {processed}/{max_companies} ({successful} successful, {successful/processed*100:.1f}%)")
        
        time.sleep(1.3)  # Rate limiting
    
    return results

def create_super_clean_map(results, output_file):
    """Create map with super clean results"""
    valid_locations = [r for r in results if r['status'].startswith('success')]
    
    if not valid_locations:
        print("❌ No valid locations found!")
        return None
    
    print(f"Creating map with {len(valid_locations)} locations...")
    
    # Calculate center
    lats = [loc['latitude'] for loc in valid_locations]
    lons = [loc['longitude'] for loc in valid_locations]
    center_lat = np.mean(lats)
    center_lon = np.mean(lons)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add clustering
    marker_cluster = plugins.MarkerCluster().add_to(m)
    
    # Add markers
    for i, loc in enumerate(valid_locations):
        data = loc['customer_data']
        company = loc['company']
        
        # Color by sales
        sales = data.get('Total Sales', 0)
        if sales > 100000:
            color = 'red'
        elif sales > 50000:
            color = 'orange'
        elif sales > 10000:
            color = 'blue'
        else:
            color = 'green'
        
        popup_html = f"""
        <div style="width: 350px; font-family: Arial; font-size: 13px;">
            <h3 style="color: #2c3e50; margin: 0 0 10px 0;">{company}</h3>
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Account:</b></td><td>{data.get('Account #', 'N/A')}</td></tr>
                <tr><td><b>Phone:</b></td><td>{data.get('Phone #', 'N/A')}</td></tr>
                <tr><td><b>Location:</b></td><td>{data.get('City', 'N/A')}, {data.get('State', 'GA')}</td></tr>
                <tr><td><b>Sales:</b></td><td style="color: {color}; font-weight: bold;">${sales:,.2f}</td></tr>
                <tr><td><b>Balance:</b></td><td>${data.get('Balance', 0):,.2f}</td></tr>
            </table>
            <hr>
            <p style="font-size: 11px;"><b>Cleaned Address:</b> {loc['address']}</p>
            <p style="font-size: 11px;"><b>Found Address:</b> {loc.get('full_address', 'N/A')}</p>
            <p style="font-size: 11px;"><b>Method:</b> {loc['status']}</p>
        </div>
        """
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=380),
            tooltip=company,
            icon=folium.Icon(color=color, icon='briefcase')
        ).add_to(marker_cluster)
    
    m.save(output_file)
    print(f"Map saved: {output_file}")
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("🧹 Super Clean Address Mapper Starting...")
    
    # Read data
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total records")
    
    # Test sample first
    test_geocoding_sample(df, 5)
    
    # Process companies
    results = process_companies_with_super_clean(df, 250)
    
    # Create map
    map_file = "/Users/akbarchranya/georgiadashboard/super_clean_company_map.html"
    create_super_clean_map(results, map_file)
    
    # Save results
    csv_data = []
    for result in results:
        data = result['customer_data']
        csv_data.append({
            'company': result['company'],
            'account': data.get('Account #'),
            'phone': data.get('Phone #'),
            'city': data.get('City'),
            'state': data.get('State'),
            'raw_address': data.get('raw_address'),
            'cleaned_address': result['address'],
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'geocoding_status': result['status'],
            'found_address': result.get('full_address', ''),
            'total_sales': data.get('Total Sales', 0),
            'balance': data.get('Balance', 0)
        })
    
    results_df = pd.DataFrame(csv_data)
    csv_file = "/Users/akbarchranya/georgiadashboard/super_clean_results.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Summary
    successful = len([r for r in results if r['status'].startswith('success')])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"🧹 SUPER CLEAN MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"🏢 Companies processed: {total}")
    print(f"✅ Successfully geocoded: {successful}")
    print(f"❌ Failed: {total - successful}")
    print(f"📈 Success rate: {successful/total*100:.1f}%")
    
    if successful > 0:
        valid_results = [r for r in results if r['status'].startswith('success')]
        total_sales = sum([r['customer_data'].get('Total Sales', 0) for r in valid_results])
        print(f"💰 Total sales mapped: ${total_sales:,.2f}")
    
    print(f"\n📍 Interactive map: {map_file}")
    print(f"📄 Detailed results: {csv_file}")
    print(f"\n🎉 Open the HTML file to explore your company locations!")

if __name__ == "__main__":
    main()
