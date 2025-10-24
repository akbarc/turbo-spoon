import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import folium
from folium import plugins
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class FastGeocoder:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="georgia_fast_company_mapper", timeout=5)
        self.lock = threading.Lock()
        
    def geocode_single(self, address_info):
        """Geocode a single address with company info"""
        idx, address, company, customer_data = address_info
        
        try:
            location = self.geolocator.geocode(address, timeout=5)
            if location:
                return {
                    'idx': idx,
                    'company': company,
                    'address': address,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'full_address': location.address,
                    'status': 'success',
                    'customer_data': customer_data
                }
            else:
                return {
                    'idx': idx,
                    'company': company,
                    'address': address,
                    'latitude': None,
                    'longitude': None,
                    'status': 'not_found',
                    'customer_data': customer_data
                }
        except Exception as e:
            return {
                'idx': idx,
                'company': company,
                'address': address,
                'latitude': None,
                'longitude': None,
                'status': 'error',
                'error': str(e),
                'customer_data': customer_data
            }

def prepare_addresses_fast(df, max_records=500):
    """Prepare addresses quickly with company names"""
    print(f"Preparing addresses for {max_records} companies...")
    
    address_data = []
    
    for idx, row in df.head(max_records).iterrows():
        # Get company name (prioritize this over person name)
        company = str(row.get('Company', '')).strip()
        if not company or company == 'nan':
            # Fallback to person name if no company
            first_name = str(row.get('FirstName', '')).strip()
            last_name = str(row.get('LastName', '')).strip()
            company = f"{first_name} {last_name}".strip()
            if not company:
                company = f"Customer {idx+1}"
        
        # Clean company name
        company = company.replace(' INC', '').replace(' LLC', '').replace(' CORP', '')
        
        # Build address
        addr = str(row.get('Address', '')).strip()
        city = str(row.get('City', '')).strip()
        state = str(row.get('State', 'GA')).strip()
        zip_code = str(row.get('Zip', '')).strip()
        
        # Skip if no address
        if not addr or addr == 'nan' or not city or city == 'nan':
            continue
        
        # Clean address components
        addr = re.sub(r'\s+', ' ', addr)
        city = city.replace(' INC', '').replace(' LLC', '')
        
        # Clean zip
        if zip_code and zip_code != 'nan':
            zip_code = re.sub(r'\.0$', '', zip_code)
            zip_code = re.sub(r'[^\d-]', '', zip_code)
            if len(zip_code) >= 5:
                full_address = f"{addr}, {city}, {state}, {zip_code}"
            else:
                full_address = f"{addr}, {city}, {state}"
        else:
            full_address = f"{addr}, {city}, {state}"
        
        # Customer data for popup
        customer_data = {
            'Account #': row.get('Account #', 'Unknown'),
            'Phone #': row.get('Phone #', ''),
            'Total Sales': row.get('Total Sales', 0),
            'Balance': row.get('Balance', 0),
            'City': city,
            'State': state
        }
        
        address_data.append((idx, full_address, company, customer_data))
    
    print(f"Prepared {len(address_data)} addresses for geocoding")
    return address_data

def geocode_parallel(address_data, max_workers=5):
    """Geocode addresses in parallel for speed"""
    print(f"Geocoding {len(address_data)} addresses with {max_workers} parallel workers...")
    
    geocoder = FastGeocoder()
    results = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_address = {executor.submit(geocoder.geocode_single, addr_info): addr_info for addr_info in address_data}
        
        # Process completed jobs
        for future in as_completed(future_to_address):
            result = future.result()
            results.append(result)
            completed += 1
            
            # Progress update
            if completed % 25 == 0 or completed == len(address_data):
                successful = len([r for r in results if r['status'] == 'success'])
                print(f"Progress: {completed}/{len(address_data)} ({successful} successful, {successful/completed*100:.1f}%)")
            
            # Small delay to avoid overwhelming the service
            time.sleep(0.1)
    
    # Sort results by original index
    results.sort(key=lambda x: x['idx'])
    return results

def create_fast_map(results, output_file):
    """Create map quickly with company focus"""
    valid_locations = [r for r in results if r['status'] == 'success']
    
    if not valid_locations:
        print("❌ No valid locations found!")
        return None
    
    print(f"Creating map with {len(valid_locations)} company locations...")
    
    # Calculate Georgia-centered view
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
    
    # Add fast clustering
    marker_cluster = plugins.MarkerCluster(
        name="Company Locations",
        options={
            'maxClusterRadius': 40,
            'disableClusteringAtZoom': 11
        }
    ).add_to(m)
    
    # Add markers efficiently
    for i, loc in enumerate(valid_locations):
        data = loc['customer_data']
        company = loc['company']
        
        # Color by sales volume
        sales = data.get('Total Sales', 0)
        if sales > 100000:
            color = 'red'
        elif sales > 50000:
            color = 'orange'  
        elif sales > 10000:
            color = 'blue'
        else:
            color = 'green'
        
        # Efficient popup
        popup_html = f"""
        <div style="width: 300px; font-family: Arial; font-size: 12px;">
            <h4 style="color: #2c3e50; margin: 0 0 8px 0;">{company}</h4>
            <p><b>Account:</b> {data.get('Account #', 'N/A')}</p>
            <p><b>Location:</b> {data.get('City', 'N/A')}, {data.get('State', 'GA')}</p>
            <p><b>Phone:</b> {data.get('Phone #', 'N/A')}</p>
            <p><b>Total Sales:</b> ${sales:,.2f}</p>
            <p><b>Balance:</b> ${data.get('Balance', 0):,.2f}</p>
            <p><b>Address:</b> {loc['address']}</p>
        </div>
        """
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=company,
            icon=folium.Icon(color=color, icon='briefcase')
        ).add_to(marker_cluster)
    
    # Add simple legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 110px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 8px;">
    <h4 style="margin: 0 0 8px 0;">Sales Volume</h4>
    <p style="margin: 2px 0;"><span style="color:red;">●</span> > $100K</p>
    <p style="margin: 2px 0;"><span style="color:orange;">●</span> $50K - $100K</p>
    <p style="margin: 2px 0;"><span style="color:blue;">●</span> $10K - $50K</p>
    <p style="margin: 2px 0;"><span style="color:green;">●</span> < $10K</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    m.save(output_file)
    print(f"Map saved: {output_file}")
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("🚀 Fast Company Mapper Starting...")
    start_time = time.time()
    
    # Read data
    print("Reading customer data...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total companies")
    
    # Prepare addresses (fast)
    max_companies = 1000  # Process more since we're faster
    address_data = prepare_addresses_fast(df, max_companies)
    
    if not address_data:
        print("❌ No valid addresses found!")
        return
    
    # Geocode in parallel (much faster)
    results = geocode_parallel(address_data, max_workers=8)  # More workers for speed
    
    # Create map
    map_file = "/Users/akbarchranya/georgiadashboard/fast_company_map.html"
    create_fast_map(results, map_file)
    
    # Save CSV quickly
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
            'status': result['status'],
            'total_sales': data.get('Total Sales', 0),
            'balance': data.get('Balance', 0)
        })
    
    results_df = pd.DataFrame(csv_data)
    csv_file = "/Users/akbarchranya/georgiadashboard/fast_company_results.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Final summary
    end_time = time.time()
    duration = end_time - start_time
    
    successful = len([r for r in results if r['status'] == 'success'])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"⚡ FAST COMPANY MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"⏱️  Total time: {duration:.1f} seconds")
    print(f"🏢 Companies processed: {total}")
    print(f"✅ Successfully geocoded: {successful}")
    print(f"❌ Not found: {total - successful}")
    print(f"📈 Success rate: {successful/total*100:.1f}%")
    print(f"⚡ Speed: {total/duration:.1f} addresses/second")
    
    if successful > 0:
        valid_results = [r for r in results if r['status'] == 'success']
        total_sales = sum([r['customer_data'].get('Total Sales', 0) for r in valid_results])
        avg_sales = total_sales / successful
        print(f"💰 Total sales mapped: ${total_sales:,.2f}")
        print(f"📊 Average sales per company: ${avg_sales:,.2f}")
    
    print(f"\n📍 Company map: {map_file}")
    print(f"📄 Results: {csv_file}")
    print(f"\n🎉 Open the HTML file to explore {successful} company locations!")

if __name__ == "__main__":
    main()
