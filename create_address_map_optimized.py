import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from folium import plugins
import time
import re
import os

def extract_address_from_company(company_name):
    """Extract potential address from company name"""
    if pd.isna(company_name) or company_name == '':
        return None
    
    company_str = str(company_name).strip()
    
    # Look for patterns that might indicate addresses
    # Pattern 1: Numbers followed by street names (more comprehensive)
    street_pattern = r'\b\d+\s+[A-Z][a-z]*\s*(ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|BLVD|BOULEVARD|HWY|HIGHWAY|WAY|LANE|LN|PKWY|PARKWAY|PL|PLACE|CT|COURT|CIR|CIRCLE|PKWY)\b'
    
    match = re.search(street_pattern, company_str, re.IGNORECASE)
    if match:
        # Extract the address part
        address_part = match.group(0)
        return address_part
    
    # Pattern 2: Look for highway numbers (more specific)
    highway_pattern = r'\b\d+\s+(COVINGTON|MEMORIAL|INDUSTRIAL|MAIN|OLD|NEW|PEACHTREE|BUFORD|LAWRENCEVILLE|JONESBORO|STOCKBRIDGE|MCDONOUGH|CONYERS|ATLANTA)\s+(HWY|HIGHWAY|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE)\b'
    
    match = re.search(highway_pattern, company_str, re.IGNORECASE)
    if match:
        return match.group(0)
    
    # Pattern 3: Look for just street numbers with common Georgia road names
    georgia_pattern = r'\b\d+\s+(COVINGTON|MEMORIAL|INDUSTRIAL|MAIN|OLD|PEACHTREE|BUFORD|LAWRENCEVILLE|JONESBORO|STOCKBRIDGE|MCDONOUGH|CONYERS|ATLANTA|GLENWOOD|PANOLA|FLAT SHOALS|BROADWAY|ROCKBRIDGE)\b'
    
    match = re.search(georgia_pattern, company_str, re.IGNORECASE)
    if match:
        return match.group(0) + " RD"  # Assume it's a road
    
    return None

def clean_address(address):
    """Clean and standardize address format"""
    if pd.isna(address) or address == '':
        return None
    
    address = str(address).strip()
    
    # Remove extra whitespace
    address = re.sub(r'\s+', ' ', address)
    
    # Add Georgia, USA if not present
    if 'georgia' not in address.lower() and 'ga' not in address.lower():
        address += ', Georgia, USA'
    elif 'usa' not in address.lower() and 'united states' not in address.lower():
        address += ', USA'
    
    return address

def geocode_addresses(addresses, delay=1):
    """Geocode a list of addresses to get coordinates"""
    geolocator = Nominatim(user_agent="georgia_dashboard_mapper")
    results = []
    
    print(f"Geocoding {len(addresses)} addresses...")
    
    for i, address in enumerate(addresses):
        if pd.isna(address) or address == '':
            results.append({'address': address, 'latitude': None, 'longitude': None, 'status': 'empty'})
            continue
            
        try:
            print(f"Geocoding {i+1}/{len(addresses)}: {address}")
            location = geolocator.geocode(address, timeout=10)
            
            if location:
                results.append({
                    'address': address,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'full_address': location.address,
                    'status': 'success'
                })
                print(f"  ✓ Found: {location.latitude}, {location.longitude}")
            else:
                results.append({
                    'address': address,
                    'latitude': None,
                    'longitude': None,
                    'status': 'not_found'
                })
                print(f"  ✗ Not found")
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  ⚠ Geocoding error: {e}")
            results.append({
                'address': address,
                'latitude': None,
                'longitude': None,
                'status': 'error'
            })
        
        # Add delay to avoid rate limiting
        if i < len(addresses) - 1:
            time.sleep(delay)
    
    return results

def create_address_map(geocoded_data, address_info, output_file='address_map.html'):
    """Create an interactive map with all geocoded addresses"""
    # Filter out addresses without coordinates
    valid_locations = [loc for loc in geocoded_data if loc['latitude'] is not None and loc['longitude'] is not None]
    
    if not valid_locations:
        print("No valid coordinates found. Cannot create map.")
        return None
    
    print(f"Creating map with {len(valid_locations)} valid locations...")
    
    # Calculate center point (focus on Georgia)
    center_lat = np.mean([loc['latitude'] for loc in valid_locations])
    center_lon = np.mean([loc['longitude'] for loc in valid_locations])
    
    # If we don't have many points, center on Atlanta
    if len(valid_locations) < 10:
        center_lat = 33.7490  # Atlanta
        center_lon = -84.3880
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles='OpenStreetMap'
    )
    
    # Add additional tile layers
    folium.TileLayer('cartodb positron').add_to(m)
    
    # Create a mapping of addresses to customer info
    address_to_info = {}
    for info in address_info:
        address_to_info[info['cleaned_address']] = info
    
    # Add marker clustering for better performance with many markers
    if len(valid_locations) > 10:
        marker_cluster = plugins.MarkerCluster().add_to(m)
        target_map = marker_cluster
    else:
        target_map = m
    
    # Add markers for each address
    for i, loc in enumerate(valid_locations):
        # Get customer info if available
        customer_info = address_to_info.get(loc['address'], {})
        
        # Create popup text
        popup_text = f"""
        <div style="font-family: Arial, sans-serif; width: 300px;">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Location {i+1}</h4>
            <p style="margin: 5px 0;"><b>Customer:</b> {customer_info.get('customer_name', 'Unknown')}</p>
            <p style="margin: 5px 0;"><b>Account #:</b> {customer_info.get('account_number', 'Unknown')}</p>
            <p style="margin: 5px 0;"><b>Original Company:</b> {customer_info.get('original_address', 'N/A')}</p>
            <p style="margin: 5px 0;"><b>Extracted Address:</b> {loc['address']}</p>
            <p style="margin: 5px 0;"><b>Full Geocoded Address:</b> {loc.get('full_address', 'N/A')}</p>
            <p style="margin: 5px 0;"><b>Coordinates:</b> {loc['latitude']:.6f}, {loc['longitude']:.6f}</p>
        </div>
        """
        
        # Create tooltip text
        tooltip_text = f"{customer_info.get('customer_name', f'Location {i+1}')}"
        
        # Use different colors for different types of matches
        if 'HWY' in loc['address'] or 'HIGHWAY' in loc['address']:
            icon_color = 'red'  # Highways
        elif any(road_type in loc['address'] for road_type in ['ST', 'STREET', 'AVE', 'AVENUE']):
            icon_color = 'blue'  # Streets and avenues
        else:
            icon_color = 'green'  # Other roads
        
        folium.Marker(
            location=[loc['latitude'], loc['longitude']],
            popup=folium.Popup(popup_text, max_width=350),
            tooltip=tooltip_text,
            icon=folium.Icon(color=icon_color, icon='info-sign')
        ).add_to(target_map)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(output_file)
    print(f"Map saved as {output_file}")
    
    return m

def main():
    file_path = "/Users/akbarchranya/georgiadashboard/5.20 akbar (3).xlsx"
    
    # Read the Excel file
    print("Reading Excel file...")
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print(f"Found {len(df)} total records")
    
    # Extract addresses from company names
    print("Extracting addresses from company names...")
    extracted_addresses = []
    address_info = []
    
    for idx, row in df.iterrows():
        company = row.get('Company', '')
        if pd.notna(company) and str(company).strip():
            extracted_address = extract_address_from_company(str(company))
            
            if extracted_address:
                cleaned_address = clean_address(extracted_address)
                if cleaned_address:
                    extracted_addresses.append(cleaned_address)
                    address_info.append({
                        'sheet': 'Sheet1',
                        'row': idx,
                        'original_address': str(company),
                        'cleaned_address': cleaned_address,
                        'customer_name': row.get('Name', 'Unknown'),
                        'account_number': row.get('Account #', 'Unknown'),
                        'total_sales': row.get('Total Sales', 0),
                        'balance': row.get('Balance', 0)
                    })
    
    print(f"Extracted {len(extracted_addresses)} addresses with recognizable patterns")
    
    if not extracted_addresses:
        print("No addresses with street patterns found!")
        return
    
    # Show sample of extracted addresses
    print("\nSample of extracted addresses:")
    for i, addr in enumerate(extracted_addresses[:10]):
        print(f"  {i+1}. {addr}")
    
    # Process all addresses since we have a reasonable number
    print(f"\nProcessing all {len(extracted_addresses)} addresses...")
    
    # Geocode addresses
    print("\nGeocoding addresses...")
    geocoded_results = geocode_addresses(extracted_addresses, delay=0.5)  # Faster delay
    
    # Create map
    print("\nCreating interactive map...")
    map_file = "/Users/akbarchranya/georgiadashboard/georgia_addresses_map.html"
    create_address_map(geocoded_results, address_info, map_file)
    
    # Save results
    print("\nSaving results...")
    results_df = pd.DataFrame(geocoded_results)
    
    # Add customer info to results
    for i, info in enumerate(address_info):
        if i < len(results_df):
            results_df.loc[i, 'customer_name'] = info['customer_name']
            results_df.loc[i, 'account_number'] = info['account_number']
            results_df.loc[i, 'original_company'] = info['original_address']
            results_df.loc[i, 'total_sales'] = info.get('total_sales', 0)
            results_df.loc[i, 'balance'] = info.get('balance', 0)
    
    results_file = "/Users/akbarchranya/georgiadashboard/geocoded_addresses_optimized.csv"
    results_df.to_csv(results_file, index=False)
    print(f"Results saved as {results_file}")
    
    # Summary
    successful = len([r for r in geocoded_results if r['status'] == 'success'])
    failed = len([r for r in geocoded_results if r['status'] in ['not_found', 'error']])
    
    print(f"\n=== SUMMARY ===")
    print(f"Total addresses processed: {len(extracted_addresses)}")
    print(f"Successfully geocoded: {successful}")
    print(f"Failed to geocode: {failed}")
    if len(extracted_addresses) > 0:
        print(f"Success rate: {successful/len(extracted_addresses)*100:.1f}%")
    print(f"\nMap created: {map_file}")
    print(f"Results saved: {results_file}")
    
    if successful > 0:
        print(f"\n🎉 Successfully created map with {successful} locations!")
        print("Open the HTML file in your browser to view the interactive map.")
    else:
        print("\n⚠️  No addresses could be geocoded. You may need to manually review the address patterns.")

if __name__ == "__main__":
    main()
