import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from folium import plugins
import time
import re
import os

def clean_and_combine_address(row):
    """Combine address fields into a single geocodable address"""
    address_parts = []
    
    # Add main address
    if pd.notna(row.get('Address')) and str(row.get('Address')).strip():
        address_parts.append(str(row.get('Address')).strip())
    
    # Add address2 if it exists and looks like additional address info
    if pd.notna(row.get('Address2')) and str(row.get('Address2')).strip():
        addr2 = str(row.get('Address2')).strip()
        # Only add if it's not already in the main address and looks like address info
        if addr2 not in str(row.get('Address', '')) and any(x in addr2.upper() for x in ['STE', 'SUITE', 'UNIT', 'APT', 'BLDG', 'FLOOR', '#']):
            address_parts.append(addr2)
    
    # Add city
    if pd.notna(row.get('City')) and str(row.get('City')).strip():
        address_parts.append(str(row.get('City')).strip())
    
    # Add state
    if pd.notna(row.get('State')) and str(row.get('State')).strip():
        address_parts.append(str(row.get('State')).strip())
    
    # Add zip
    if pd.notna(row.get('Zip')) and str(row.get('Zip')).strip():
        zip_code = str(row.get('Zip')).strip()
        # Clean zip code (remove .0 if present)
        if zip_code.endswith('.0'):
            zip_code = zip_code[:-2]
        address_parts.append(zip_code)
    
    if address_parts:
        return ', '.join(address_parts)
    return None

def geocode_addresses_batch(addresses, customer_info, batch_size=50, delay=0.5):
    """Geocode addresses in batches with progress tracking"""
    geolocator = Nominatim(user_agent="georgia_customer_mapper")
    results = []
    
    total = len(addresses)
    print(f"Geocoding {total} addresses in batches of {batch_size}...")
    
    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        batch_addresses = addresses[i:batch_end]
        batch_info = customer_info[i:batch_end]
        
        print(f"\nProcessing batch {i//batch_size + 1}/{(total-1)//batch_size + 1} (addresses {i+1}-{batch_end})")
        
        for j, (address, info) in enumerate(zip(batch_addresses, batch_info)):
            overall_idx = i + j
            
            if pd.isna(address) or address == '':
                results.append({
                    'address': address, 
                    'latitude': None, 
                    'longitude': None, 
                    'status': 'empty',
                    'customer_info': info
                })
                continue
                
            try:
                print(f"  {overall_idx+1}/{total}: {address}")
                location = geolocator.geocode(address, timeout=10)
                
                if location:
                    results.append({
                        'address': address,
                        'latitude': location.latitude,
                        'longitude': location.longitude,
                        'full_address': location.address,
                        'status': 'success',
                        'customer_info': info
                    })
                    print(f"    ✓ Found: {location.latitude:.6f}, {location.longitude:.6f}")
                else:
                    results.append({
                        'address': address,
                        'latitude': None,
                        'longitude': None,
                        'status': 'not_found',
                        'customer_info': info
                    })
                    print(f"    ✗ Not found")
                    
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                print(f"    ⚠ Geocoding error: {e}")
                results.append({
                    'address': address,
                    'latitude': None,
                    'longitude': None,
                    'status': 'error',
                    'customer_info': info
                })
            
            # Add delay between requests
            if overall_idx < total - 1:
                time.sleep(delay)
        
        # Progress update
        successful = len([r for r in results if r['status'] == 'success'])
        print(f"  Batch complete. Total successful so far: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    
    return results

def create_comprehensive_map(geocoded_data, output_file='comprehensive_customer_map.html'):
    """Create an interactive map with all geocoded customer addresses"""
    # Filter out addresses without coordinates
    valid_locations = [loc for loc in geocoded_data if loc['latitude'] is not None and loc['longitude'] is not None]
    
    if not valid_locations:
        print("No valid coordinates found. Cannot create map.")
        return None
    
    print(f"Creating comprehensive map with {len(valid_locations)} valid locations...")
    
    # Calculate center point (focus on Georgia)
    lats = [loc['latitude'] for loc in valid_locations]
    lons = [loc['longitude'] for loc in valid_locations]
    
    center_lat = np.mean(lats)
    center_lon = np.mean(lons)
    
    # Create map centered on Georgia
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add additional tile layers
    folium.TileLayer('cartodb positron').add_to(m)
    
    # Use marker clustering for better performance
    marker_cluster = plugins.MarkerCluster(
        name="Customer Locations",
        overlay=True,
        control=True,
        options={
            'maxClusterRadius': 50,
            'disableClusteringAtZoom': 12
        }
    ).add_to(m)
    
    # Add markers for each customer
    for i, loc in enumerate(valid_locations):
        customer_info = loc.get('customer_info', {})
        
        # Create detailed popup text
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 350px;">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
                Customer #{i+1}
            </h4>
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Name:</b></td><td>{customer_info.get('FirstName', '')} {customer_info.get('LastName', '')}</td></tr>
                <tr><td><b>Account #:</b></td><td>{customer_info.get('Account #', 'Unknown')}</td></tr>
                <tr><td><b>Company:</b></td><td>{customer_info.get('Company', 'N/A')}</td></tr>
                <tr><td><b>Address:</b></td><td>{loc['address']}</td></tr>
                <tr><td><b>Full Address:</b></td><td>{loc.get('full_address', 'N/A')}</td></tr>
                <tr><td><b>Phone:</b></td><td>{customer_info.get('Phone #', 'N/A')}</td></tr>
                <tr><td><b>Total Sales:</b></td><td>${customer_info.get('Total Sales', 0):,.2f}</td></tr>
                <tr><td><b>Balance:</b></td><td>${customer_info.get('Balance', 0):,.2f}</td></tr>
                <tr><td><b>Coordinates:</b></td><td>{loc['latitude']:.6f}, {loc['longitude']:.6f}</td></tr>
            </table>
        </div>
        """
        
        # Create tooltip text
        customer_name = f"{customer_info.get('FirstName', '')} {customer_info.get('LastName', '')}".strip()
        if not customer_name:
            customer_name = customer_info.get('Company', f'Customer {i+1}')
        
        # Color code by sales volume
        total_sales = customer_info.get('Total Sales', 0)
        if total_sales > 100000:
            icon_color = 'red'  # High value customers
        elif total_sales > 50000:
            icon_color = 'orange'  # Medium value customers
        elif total_sales > 10000:
            icon_color = 'blue'  # Regular customers
        else:
            icon_color = 'green'  # Low value customers
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_html, max_width=400),
            tooltip=customer_name,
            icon=folium.Icon(color=icon_color, icon='user')
        ).add_to(marker_cluster)
    
    # Add a legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <p><b>Customer Sales Volume</b></p>
    <p><i class="fa fa-map-marker" style="color:red"></i> > $100,000</p>
    <p><i class="fa fa-map-marker" style="color:orange"></i> $50,000 - $100,000</p>
    <p><i class="fa fa-map-marker" style="color:blue"></i> $10,000 - $50,000</p>
    <p><i class="fa fa-map-marker" style="color:green"></i> < $10,000</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(output_file)
    print(f"Comprehensive map saved as {output_file}")
    
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx"
    
    print("Reading full customer list...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total customer records")
    
    # Clean and combine addresses
    print("Processing addresses...")
    addresses = []
    customer_info = []
    
    for idx, row in df.iterrows():
        combined_address = clean_and_combine_address(row)
        
        if combined_address:
            addresses.append(combined_address)
            customer_info.append({
                'Account #': row.get('Account #', 'Unknown'),
                'FirstName': row.get('FirstName', ''),
                'LastName': row.get('LastName', ''),
                'Company': row.get('Company', ''),
                'Phone #': row.get('Phone #', ''),
                'Total Sales': row.get('Total Sales', 0),
                'Balance': row.get('Balance', 0),
                'City': row.get('City', ''),
                'State': row.get('State', ''),
                'Zip': row.get('Zip', '')
            })
    
    print(f"Prepared {len(addresses)} addresses for geocoding")
    
    # Show sample addresses
    print(f"\nSample addresses to be geocoded:")
    for i, addr in enumerate(addresses[:10]):
        print(f"  {i+1}. {addr}")
    
    # Ask about processing approach
    print(f"\nFound {len(addresses)} addresses to geocode.")
    print("Options:")
    print("1. Process all addresses (will take ~2-3 hours)")
    print("2. Process first 100 addresses (for testing)")
    print("3. Process first 500 addresses (reasonable sample)")
    
    # For automation, let's process first 500 as a reasonable sample
    sample_size = min(500, len(addresses))
    print(f"\nProcessing first {sample_size} addresses as a sample...")
    
    sample_addresses = addresses[:sample_size]
    sample_info = customer_info[:sample_size]
    
    # Geocode addresses
    print(f"\nGeocoding {len(sample_addresses)} addresses...")
    geocoded_results = geocode_addresses_batch(sample_addresses, sample_info, batch_size=25, delay=0.3)
    
    # Create comprehensive map
    print("\nCreating comprehensive customer map...")
    map_file = "/Users/akbarchranya/georgiadashboard/comprehensive_customer_map.html"
    create_comprehensive_map(geocoded_results, map_file)
    
    # Save detailed results
    print("\nSaving detailed results...")
    
    # Prepare results for CSV
    csv_data = []
    for result in geocoded_results:
        info = result.get('customer_info', {})
        csv_data.append({
            'account_number': info.get('Account #', ''),
            'first_name': info.get('FirstName', ''),
            'last_name': info.get('LastName', ''),
            'company': info.get('Company', ''),
            'phone': info.get('Phone #', ''),
            'original_address': result['address'],
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'geocoded_address': result.get('full_address', ''),
            'geocoding_status': result['status'],
            'total_sales': info.get('Total Sales', 0),
            'balance': info.get('Balance', 0),
            'city': info.get('City', ''),
            'state': info.get('State', ''),
            'zip': info.get('Zip', '')
        })
    
    results_df = pd.DataFrame(csv_data)
    results_file = "/Users/akbarchranya/georgiadashboard/comprehensive_customer_geocoded.csv"
    results_df.to_csv(results_file, index=False)
    print(f"Detailed results saved as {results_file}")
    
    # Summary
    successful = len([r for r in geocoded_results if r['status'] == 'success'])
    failed = len([r for r in geocoded_results if r['status'] in ['not_found', 'error']])
    empty = len([r for r in geocoded_results if r['status'] == 'empty'])
    
    print(f"\n{'='*50}")
    print(f"COMPREHENSIVE CUSTOMER MAPPING COMPLETE")
    print(f"{'='*50}")
    print(f"Total customers processed: {len(sample_addresses)}")
    print(f"Successfully geocoded: {successful}")
    print(f"Failed to geocode: {failed}")
    print(f"Empty addresses: {empty}")
    print(f"Success rate: {successful/(len(sample_addresses)-empty)*100:.1f}%")
    print(f"\nFiles created:")
    print(f"📍 Interactive Map: {map_file}")
    print(f"📊 Detailed CSV: {results_file}")
    print(f"\n🎉 Open the HTML file in your browser to explore {successful} customer locations!")
    
    if successful > 0:
        # Calculate some stats
        valid_results = [r for r in geocoded_results if r['status'] == 'success']
        total_sales_mapped = sum([r['customer_info'].get('Total Sales', 0) for r in valid_results])
        print(f"\n📈 Mapped customers represent ${total_sales_mapped:,.2f} in total sales")

if __name__ == "__main__":
    main()
