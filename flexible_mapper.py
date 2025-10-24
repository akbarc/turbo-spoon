import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from folium import plugins
import time
import re

def clean_address_flexible(row):
    """Clean address with multiple fallback strategies"""
    # Strategy 1: Full address
    addr = str(row.get('Address', '')).strip()
    city = str(row.get('City', '')).strip()
    state = str(row.get('State', 'GA')).strip()
    zip_code = str(row.get('Zip', '')).strip()
    
    if not addr or addr == 'nan':
        return []
    
    # Clean the address
    addr = re.sub(r'\s+', ' ', addr)
    addr = addr.replace(' INC', '').replace(' LLC', '').replace(' CORP', '')
    city = city.replace(' INC', '').replace(' LLC', '')
    
    # Clean zip
    if zip_code and zip_code != 'nan':
        zip_code = re.sub(r'\.0$', '', zip_code)
        zip_code = re.sub(r'[^\d-]', '', zip_code)
    
    # Create multiple address variations to try
    variations = []
    
    # Full address with zip
    if zip_code and len(zip_code) >= 5:
        variations.append(f"{addr}, {city}, {state}, {zip_code}")
    
    # Address without zip
    variations.append(f"{addr}, {city}, {state}")
    
    # Address with just city and state
    variations.append(f"{addr}, {city}, {state}")
    
    # Just street and city
    variations.append(f"{addr}, {city}")
    
    # Try with "Georgia" instead of "GA"
    if state == 'GA':
        variations.append(f"{addr}, {city}, Georgia")
    
    return [v for v in variations if v]

def geocode_with_multiple_attempts(address_variations, geolocator):
    """Try multiple address variations"""
    for i, addr in enumerate(address_variations):
        try:
            location = geolocator.geocode(addr, timeout=15)
            if location:
                return location, addr, f"variation_{i+1}"
            time.sleep(0.2)  # Small delay between attempts
        except Exception:
            continue
    return None, address_variations[0] if address_variations else "", "all_failed"

def process_customers_flexible(df, max_customers=1000):
    """Process customers with flexible geocoding"""
    print(f"Processing up to {max_customers} customers with flexible geocoding...")
    
    geolocator = Nominatim(user_agent="georgia_flexible_mapper", timeout=15)
    results = []
    processed = 0
    
    for idx, row in df.iterrows():
        if processed >= max_customers:
            break
            
        address_variations = clean_address_flexible(row)
        
        if not address_variations:
            continue
            
        customer_name = f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip()
        if not customer_name:
            customer_name = row.get('Company', f'Customer {processed+1}')
        
        print(f"\n{processed+1}/{max_customers}: {customer_name}")
        print(f"  Trying: {address_variations[0]}")
        
        location, used_addr, method = geocode_with_multiple_attempts(address_variations, geolocator)
        
        customer_info = {
            'Account #': row.get('Account #', 'Unknown'),
            'FirstName': row.get('FirstName', ''),
            'LastName': row.get('LastName', ''),
            'Company': row.get('Company', ''),
            'Phone #': row.get('Phone #', ''),
            'Total Sales': row.get('Total Sales', 0),
            'Balance': row.get('Balance', 0),
            'City': row.get('City', ''),
            'State': row.get('State', ''),
            'original_address': f"{row.get('Address', '')} {row.get('City', '')} {row.get('State', '')}".strip()
        }
        
        if location:
            results.append({
                'address': address_variations[0],
                'used_address': used_addr,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'full_address': location.address,
                'status': 'success',
                'method': method,
                'customer_info': customer_info
            })
            print(f"  ✓ SUCCESS ({method}): {location.latitude:.6f}, {location.longitude:.6f}")
        else:
            results.append({
                'address': address_variations[0],
                'used_address': address_variations[0],
                'latitude': None,
                'longitude': None,
                'status': 'not_found',
                'method': 'failed',
                'customer_info': customer_info
            })
            print(f"  ✗ NOT FOUND after {len(address_variations)} attempts")
        
        processed += 1
        
        # Progress update every 50 customers
        if processed % 50 == 0:
            successful = len([r for r in results if r['status'] == 'success'])
            print(f"\n--- Progress Update ---")
            print(f"Processed: {processed}")
            print(f"Successful: {successful} ({successful/processed*100:.1f}%)")
            print(f"Remaining: {max_customers - processed}")
        
        time.sleep(0.8)  # Rate limiting
    
    return results

def create_flexible_map(results, output_file):
    """Create map with results"""
    valid_locations = [r for r in results if r['status'] == 'success']
    
    if not valid_locations:
        print("❌ No valid locations found!")
        return None
    
    print(f"Creating map with {len(valid_locations)} locations...")
    
    # Calculate center (Georgia focus)
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
    marker_cluster = plugins.MarkerCluster(
        name="Customer Locations",
        options={'maxClusterRadius': 50}
    ).add_to(m)
    
    # Add markers
    for i, loc in enumerate(valid_locations):
        info = loc['customer_info']
        
        name = f"{info.get('FirstName', '')} {info.get('LastName', '')}".strip()
        if not name:
            name = info.get('Company', f'Customer {i+1}')
        
        # Color by sales volume
        sales = info.get('Total Sales', 0)
        if sales > 100000:
            color = 'red'
        elif sales > 50000:
            color = 'orange'  
        elif sales > 10000:
            color = 'blue'
        else:
            color = 'green'
        
        popup_html = f"""
        <div style="width: 320px; font-family: Arial;">
            <h4 style="color: #2c3e50; margin: 0 0 10px 0;">{name}</h4>
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Account:</b></td><td>{info.get('Account #', 'N/A')}</td></tr>
                <tr><td><b>Company:</b></td><td>{info.get('Company', 'N/A')}</td></tr>
                <tr><td><b>Phone:</b></td><td>{info.get('Phone #', 'N/A')}</td></tr>
                <tr><td><b>City:</b></td><td>{info.get('City', 'N/A')}</td></tr>
                <tr><td><b>Sales:</b></td><td>${sales:,.2f}</td></tr>
                <tr><td><b>Balance:</b></td><td>${info.get('Balance', 0):,.2f}</td></tr>
                <tr><td><b>Method:</b></td><td>{loc['method']}</td></tr>
                <tr><td><b>Address Used:</b></td><td>{loc['used_address']}</td></tr>
            </table>
        </div>
        """
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=name,
            icon=folium.Icon(color=color, icon='user')
        ).add_to(marker_cluster)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 10px;">
    <h4>Sales Volume</h4>
    <p><span style="color:red;">●</span> > $100,000</p>
    <p><span style="color:orange;">●</span> $50,000 - $100,000</p>
    <p><span style="color:blue;">●</span> $10,000 - $50,000</p>
    <p><span style="color:green;">●</span> < $10,000</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    m.save(output_file)
    print(f"Map saved: {output_file}")
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("Reading customer data...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total customers")
    
    # Process a reasonable number of customers
    max_customers = 500  # Adjust this number as needed
    print(f"Processing first {max_customers} customers...")
    
    results = process_customers_flexible(df, max_customers)
    
    # Create map
    map_file = "/Users/akbarchranya/georgiadashboard/flexible_customer_map.html"
    create_flexible_map(results, map_file)
    
    # Save CSV results
    csv_data = []
    for result in results:
        info = result['customer_info']
        csv_data.append({
            'account': info.get('Account #'),
            'name': f"{info.get('FirstName', '')} {info.get('LastName', '')}".strip(),
            'company': info.get('Company'),
            'phone': info.get('Phone #'),
            'city': info.get('City'),
            'original_address': info.get('original_address'),
            'geocoded_address': result['address'],
            'used_address': result.get('used_address'),
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'geocoding_status': result['status'],
            'method': result.get('method'),
            'total_sales': info.get('Total Sales', 0),
            'balance': info.get('Balance', 0)
        })
    
    results_df = pd.DataFrame(csv_data)
    csv_file = "/Users/akbarchranya/georgiadashboard/flexible_geocoded_customers.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Final summary
    successful = len([r for r in results if r['status'] == 'success'])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"🗺️  FLEXIBLE CUSTOMER MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Customers processed: {total}")
    print(f"✅ Successfully geocoded: {successful}")
    print(f"❌ Not found: {total - successful}")
    print(f"📈 Success rate: {successful/total*100:.1f}%")
    
    if successful > 0:
        valid_results = [r for r in results if r['status'] == 'success']
        total_sales = sum([r['customer_info'].get('Total Sales', 0) for r in valid_results])
        print(f"💰 Mapped customers represent: ${total_sales:,.2f} in sales")
    
    print(f"\n📍 Interactive map: {map_file}")
    print(f"📄 Detailed results: {csv_file}")
    print(f"\n🎉 Open the HTML file to explore your customer locations!")

if __name__ == "__main__":
    main()
