import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import folium
from folium import plugins
import time
import re

def clean_company_name(company_str):
    """Clean company name for display"""
    if not company_str or company_str == 'nan':
        return ""
    
    company = str(company_str).strip()
    # Remove common business suffixes for cleaner display
    company = re.sub(r'\s+(INC|LLC|CORP|CORPORATION)$', '', company, flags=re.IGNORECASE)
    return company

def prepare_address_simple(row):
    """Simple, reliable address preparation"""
    # Get address components
    addr = str(row.get('Address', '')).strip()
    city = str(row.get('City', '')).strip()
    state = str(row.get('State', 'GA')).strip()
    zip_code = str(row.get('Zip', '')).strip()
    
    # Skip if no basic address info
    if not addr or addr == 'nan' or not city or city == 'nan':
        return None
    
    # Clean components
    addr = re.sub(r'\s+', ' ', addr)
    city = re.sub(r'\s+(INC|LLC)$', '', city, flags=re.IGNORECASE)
    
    # Clean zip code
    if zip_code and zip_code != 'nan':
        zip_code = re.sub(r'\.0$', '', zip_code)  # Remove .0
        zip_code = re.sub(r'[^\d-]', '', zip_code)  # Only digits and dashes
    
    # Build address - try with and without zip
    if zip_code and len(zip_code) >= 5:
        return f"{addr}, {city}, {state} {zip_code}"
    else:
        return f"{addr}, {city}, {state}"

def geocode_reliable(addresses_with_info, sample_size=200):
    """Reliable geocoding with proper error handling"""
    print(f"Geocoding {min(sample_size, len(addresses_with_info))} addresses reliably...")
    
    geolocator = Nominatim(user_agent="georgia_reliable_mapper", timeout=10)
    results = []
    
    # Process only a sample for reliability
    to_process = addresses_with_info[:sample_size]
    
    for i, (address, company, customer_data) in enumerate(to_process):
        print(f"\n{i+1}/{len(to_process)}: {company}")
        print(f"  Address: {address}")
        
        try:
            # First attempt with full address
            location = geolocator.geocode(address, timeout=10)
            
            if location:
                results.append({
                    'company': company,
                    'address': address,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'full_address': location.address,
                    'status': 'success',
                    'customer_data': customer_data
                })
                print(f"  ✓ SUCCESS: {location.latitude:.6f}, {location.longitude:.6f}")
            else:
                # Try without zip code
                addr_no_zip = re.sub(r',?\s*\d{5}(-\d{4})?$', '', address)
                if addr_no_zip != address:
                    print(f"  Trying without zip: {addr_no_zip}")
                    time.sleep(1)
                    location = geolocator.geocode(addr_no_zip, timeout=10)
                
                if location:
                    results.append({
                        'company': company,
                        'address': address,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'full_address': location.address,
                        'status': 'success_no_zip',
                        'customer_data': customer_data
                    })
                    print(f"  ✓ SUCCESS (no zip): {location.latitude:.6f}, {location.longitude:.6f}")
                else:
                    results.append({
                        'company': company,
                        'address': address,
                        'latitude': None,
                        'longitude': None,
                        'status': 'not_found',
                        'customer_data': customer_data
                    })
                    print(f"  ✗ NOT FOUND")
        
        except Exception as e:
            results.append({
                'company': company,
                'address': address,
                'latitude': None,
                'longitude': None,
                'status': 'error',
                'error': str(e),
                'customer_data': customer_data
            })
            print(f"  ⚠ ERROR: {e}")
        
        # Progress update every 25 addresses
        if (i + 1) % 25 == 0:
            successful = len([r for r in results if r['status'].startswith('success')])
            print(f"\n--- Progress: {i+1}/{len(to_process)} ({successful} successful, {successful/(i+1)*100:.1f}%) ---")
        
        # Rate limiting - be nice to the service
        time.sleep(1.2)
    
    return results

def create_reliable_map(results, output_file):
    """Create a reliable map with good error handling"""
    valid_locations = [r for r in results if r['status'].startswith('success')]
    
    if not valid_locations:
        print("❌ No valid locations found!")
        return None
    
    print(f"Creating map with {len(valid_locations)} company locations...")
    
    # Calculate center point
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
    
    # Add marker clustering
    marker_cluster = plugins.MarkerCluster(
        name="Company Locations"
    ).add_to(m)
    
    # Add markers
    for i, loc in enumerate(valid_locations):
        data = loc['customer_data']
        company = loc['company']
        
        # Color by sales volume
        sales = data.get('Total Sales', 0)
        if sales > 100000:
            color = 'red'
            size_class = 'high'
        elif sales > 50000:
            color = 'orange'
            size_class = 'medium'
        elif sales > 10000:
            color = 'blue'
            size_class = 'regular'
        else:
            color = 'green'
            size_class = 'low'
        
        # Create popup
        popup_html = f"""
        <div style="width: 320px; font-family: Arial; font-size: 13px;">
            <h3 style="color: #2c3e50; margin: 0 0 10px 0; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
                {company}
            </h3>
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Account #:</b></td><td>{data.get('Account #', 'N/A')}</td></tr>
                <tr><td><b>Phone:</b></td><td>{data.get('Phone #', 'N/A')}</td></tr>
                <tr><td><b>Location:</b></td><td>{data.get('City', 'N/A')}, {data.get('State', 'GA')}</td></tr>
                <tr><td><b>Total Sales:</b></td><td style="color: {color}; font-weight: bold;">${sales:,.2f}</td></tr>
                <tr><td><b>Balance:</b></td><td>${data.get('Balance', 0):,.2f}</td></tr>
                <tr><td><b>Sales Category:</b></td><td>{size_class.title()}</td></tr>
            </table>
            <hr style="margin: 8px 0;">
            <p style="font-size: 11px; margin: 5px 0;"><b>Address:</b> {loc['address']}</p>
            <p style="font-size: 11px; margin: 5px 0;"><b>Geocoded:</b> {loc.get('full_address', 'N/A')}</p>
        </div>
        """
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=company,
            icon=folium.Icon(color=color, icon='briefcase')
        ).add_to(marker_cluster)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 140px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:13px; padding: 10px; box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">Company Sales Volume</h4>
    <p style="margin: 3px 0;"><span style="color:red; font-size: 16px;">●</span> High (> $100K)</p>
    <p style="margin: 3px 0;"><span style="color:orange; font-size: 16px;">●</span> Medium ($50K - $100K)</p>
    <p style="margin: 3px 0;"><span style="color:blue; font-size: 16px;">●</span> Regular ($10K - $50K)</p>
    <p style="margin: 3px 0;"><span style="color:green; font-size: 16px;">●</span> Low (< $10K)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    m.save(output_file)
    print(f"Map saved: {output_file}")
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("🎯 Reliable Company Mapper Starting...")
    start_time = time.time()
    
    # Read data
    print("Reading customer data...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total records")
    
    # Prepare addresses
    print("Preparing company addresses...")
    addresses_with_info = []
    
    for idx, row in df.iterrows():
        address = prepare_address_simple(row)
        if not address:
            continue
        
        # Get company name
        company = clean_company_name(row.get('Company', ''))
        if not company:
            first_name = str(row.get('FirstName', '')).strip()
            last_name = str(row.get('LastName', '')).strip()
            company = f"{first_name} {last_name}".strip()
            if not company:
                company = f"Customer {idx+1}"
        
        # Customer data
        customer_data = {
            'Account #': row.get('Account #', 'Unknown'),
            'Phone #': row.get('Phone #', ''),
            'Total Sales': row.get('Total Sales', 0),
            'Balance': row.get('Balance', 0),
            'City': row.get('City', ''),
            'State': row.get('State', 'GA')
        }
        
        addresses_with_info.append((address, company, customer_data))
    
    print(f"Prepared {len(addresses_with_info)} valid addresses")
    
    # Show sample
    print(f"\nSample addresses:")
    for i, (addr, company, _) in enumerate(addresses_with_info[:5]):
        print(f"  {i+1}. {company}: {addr}")
    
    # Geocode reliably
    sample_size = 300  # Process a good sample size
    results = geocode_reliable(addresses_with_info, sample_size)
    
    # Create map
    map_file = "/Users/akbarchranya/georgiadashboard/reliable_company_map.html"
    create_reliable_map(results, map_file)
    
    # Save results
    print("Saving results...")
    csv_data = []
    for result in results:
        data = result['customer_data']
        csv_data.append({
            'company': result['company'],
            'account': data.get('Account #'),
            'phone': data.get('Phone #'),
            'city': data.get('City'),
            'state': data.get('State'),
            'address': result['address'],
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'geocoding_status': result['status'],
            'total_sales': data.get('Total Sales', 0),
            'balance': data.get('Balance', 0),
            'full_geocoded_address': result.get('full_address', '')
        })
    
    results_df = pd.DataFrame(csv_data)
    csv_file = "/Users/akbarchranya/georgiadashboard/reliable_company_results.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    
    successful = len([r for r in results if r['status'].startswith('success')])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"🎯 RELIABLE COMPANY MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"⏱️  Total time: {duration/60:.1f} minutes")
    print(f"🏢 Companies processed: {total}")
    print(f"✅ Successfully geocoded: {successful}")
    print(f"❌ Failed: {total - successful}")
    print(f"📈 Success rate: {successful/total*100:.1f}%")
    
    if successful > 0:
        valid_results = [r for r in results if r['status'].startswith('success')]
        total_sales = sum([r['customer_data'].get('Total Sales', 0) for r in valid_results])
        print(f"💰 Total sales mapped: ${total_sales:,.2f}")
        print(f"📊 Average sales per company: ${total_sales/successful:,.2f}")
    
    print(f"\n📍 Interactive map: {map_file}")
    print(f"📄 Detailed results: {csv_file}")
    print(f"\n🎉 Open the HTML file to explore {successful} company locations!")

if __name__ == "__main__":
    main()
