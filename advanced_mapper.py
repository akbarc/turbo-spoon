import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
import folium
from folium import plugins
import time
import re

def advanced_address_cleaning(row):
    """Advanced address cleaning based on failure analysis"""
    addr = str(row.get('Address', '')).strip()
    city = str(row.get('City', '')).strip()
    state = str(row.get('State', 'GA')).strip()
    zip_code = str(row.get('Zip', '')).strip()
    
    if not addr or addr == 'nan' or not city or city == 'nan':
        return []
    
    # Clean basic formatting
    addr = re.sub(r'\s+', ' ', addr).strip()
    city = re.sub(r'\s+', ' ', city).strip()
    
    # Remove business suffixes
    addr = re.sub(r'\s+(INC|LLC|CORP|CORPORATION)$', '', addr, flags=re.IGNORECASE)
    city = re.sub(r'\s+(INC|LLC)$', '', city, flags=re.IGNORECASE)
    
    # Fix common misspellings
    misspelling_fixes = {
        'GAINSEVILLE': 'GAINESVILLE',
        'GAINSVILLE': 'GAINESVILLE', 
        'LAWRENCEVILL': 'LAWRENCEVILLE',
        'ANNISTOWN': 'ANNISTOWN',  # This might be correct
        'STONEMOUNTIAN': 'STONE MOUNTAIN',
        'STN MOUNTAIN': 'STONE MOUNTAIN',
        'STN MTN': 'STONE MOUNTAIN',
        'DEACTUR': 'DECATUR',
        'MARIATTA': 'MARIETTA',
        'ROSEWELL': 'ROSWELL',
        'CONVINGTON': 'COVINGTON',
        'HAWASSEE': 'HIAWASSEE',
        'NORCORSS': 'NORCROSS'
    }
    
    for wrong, correct in misspelling_fixes.items():
        city = city.replace(wrong, correct)
        addr = addr.replace(wrong, correct)
    
    # Fix MLK variations
    mlk_variations = [
        ('MLK JR DR', 'MARTIN LUTHER KING JR DR'),
        ('MLK DR', 'MARTIN LUTHER KING JR DR'),
        ('MARTIN LUTHER KING DR', 'MARTIN LUTHER KING JR DR')
    ]
    
    for old, new in mlk_variations:
        addr = addr.replace(old, new)
    
    # Clean zip code
    if zip_code and zip_code != 'nan':
        zip_code = re.sub(r'\.0$', '', zip_code)
        zip_code = re.sub(r'[^\d-]', '', zip_code)
    
    # Create multiple address variations to try
    variations = []
    
    # Variation 1: Full address with zip
    if zip_code and len(zip_code) >= 5:
        variations.append(f"{addr}, {city}, {state} {zip_code}")
    
    # Variation 2: Address without zip
    variations.append(f"{addr}, {city}, {state}")
    
    # Variation 3: Remove suite information for suite addresses
    if 'STE ' in addr or 'SUITE ' in addr:
        addr_no_suite = re.sub(r'\s+(STE|SUITE)\s+[A-Z0-9]+', '', addr, flags=re.IGNORECASE)
        variations.append(f"{addr_no_suite}, {city}, {state}")
        if zip_code and len(zip_code) >= 5:
            variations.append(f"{addr_no_suite}, {city}, {state} {zip_code}")
    
    # Variation 4: Expand highway abbreviations
    if 'HWY' in addr:
        addr_highway = addr.replace(' HWY', ' HIGHWAY')
        variations.append(f"{addr_highway}, {city}, {state}")
    
    # Variation 5: Try with "Georgia" instead of "GA"
    variations.append(f"{addr}, {city}, Georgia")
    
    # Variation 6: For numbered highways, try different formats
    if re.search(r'HIGHWAY\s+\d+', addr):
        # Try "US Highway X" format
        addr_us = re.sub(r'HIGHWAY\s+(\d+)', r'US HIGHWAY \1', addr)
        variations.append(f"{addr_us}, {city}, {state}")
        
        # Try "State Route X" format  
        addr_sr = re.sub(r'HIGHWAY\s+(\d+)', r'STATE ROUTE \1', addr)
        variations.append(f"{addr_sr}, {city}, {state}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    return unique_variations

def geocode_with_multiple_strategies(address_variations, geolocator):
    """Try multiple geocoding strategies"""
    for i, addr in enumerate(address_variations):
        try:
            location = geolocator.geocode(addr, timeout=12)
            if location:
                return location, addr, f"strategy_{i+1}"
            time.sleep(0.3)  # Small delay between attempts
        except Exception:
            continue
    return None, address_variations[0] if address_variations else "", "all_failed"

def process_failed_addresses():
    """Reprocess the previously failed addresses with advanced cleaning"""
    print("🔍 Advanced Mapper - Processing Previously Failed Addresses...")
    
    # Read the full customer list
    df = pd.read_excel("/Users/akbarchranya/georgiadashboard/FULL CUSTOMER LIST 2.18 (4).xlsx", sheet_name='Sheet1')
    
    # Read previous results to identify failures
    prev_results = pd.read_csv("/Users/akbarchranya/georgiadashboard/super_clean_results.csv")
    failed_accounts = set(prev_results[prev_results['geocoding_status'] == 'not_found']['account'].astype(str))
    
    print(f"Found {len(failed_accounts)} previously failed accounts to retry")
    
    # Filter to previously failed addresses
    failed_df = df[df['Account #'].astype(str).isin(failed_accounts)].copy()
    
    print(f"Processing {len(failed_df)} failed addresses with advanced cleaning...")
    
    geolocator = Nominatim(user_agent="georgia_advanced_mapper", timeout=12)
    new_results = []
    
    for idx, row in failed_df.iterrows():
        # Get company name
        company = str(row.get('Company', '')).strip()
        if not company or company == 'nan':
            first_name = str(row.get('FirstName', '')).strip()
            last_name = str(row.get('LastName', '')).strip()
            company = f"{first_name} {last_name}".strip()
            if not company:
                company = f"Customer {idx}"
        
        company = re.sub(r'\s+(INC|LLC|CORP)(\s|$)', r'\2', company, flags=re.IGNORECASE).strip()
        
        # Get address variations
        address_variations = advanced_address_cleaning(row)
        
        if not address_variations:
            continue
            
        customer_data = {
            'Account #': row.get('Account #', 'Unknown'),
            'Phone #': row.get('Phone #', ''),
            'Total Sales': row.get('Total Sales', 0),
            'Balance': row.get('Balance', 0),
            'City': row.get('City', ''),
            'State': row.get('State', 'GA')
        }
        
        print(f"\n{len(new_results)+1}: {company}")
        print(f"  Original: {row.get('Address', '')} | {row.get('City', '')} | {row.get('State', 'GA')}")
        print(f"  Trying {len(address_variations)} variations...")
        
        location, used_addr, method = geocode_with_multiple_strategies(address_variations, geolocator)
        
        if location:
            new_results.append({
                'company': company,
                'address': address_variations[0],
                'used_address': used_addr,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'full_address': location.address,
                'status': 'success_advanced',
                'method': method,
                'customer_data': customer_data
            })
            print(f"  ✅ SUCCESS ({method}): {location.latitude:.6f}, {location.longitude:.6f}")
            print(f"     Used: {used_addr}")
        else:
            new_results.append({
                'company': company,
                'address': address_variations[0],
                'used_address': address_variations[0],
                'latitude': None,
                'longitude': None,
                'status': 'still_failed',
                'method': 'all_failed',
                'customer_data': customer_data
            })
            print(f"  ❌ STILL FAILED after {len(address_variations)} attempts")
        
        # Progress update
        if len(new_results) % 25 == 0:
            recovered = len([r for r in new_results if r['status'] == 'success_advanced'])
            print(f"\n🔄 Progress: {len(new_results)} processed, {recovered} recovered ({recovered/len(new_results)*100:.1f}%)")
        
        time.sleep(1.5)  # Rate limiting
    
    return new_results

def combine_results_and_create_final_map():
    """Combine old successful results with newly recovered ones"""
    print("\n📊 Combining results and creating final comprehensive map...")
    
    # Read previous successful results
    prev_results = pd.read_csv("/Users/akbarchranya/georgiadashboard/super_clean_results.csv")
    successful_prev = prev_results[prev_results['geocoding_status'].str.contains('success', na=False)]
    
    # Process new results
    new_results = process_failed_addresses()
    successful_new = [r for r in new_results if r['status'] == 'success_advanced']
    
    print(f"\n📈 RECOVERY RESULTS:")
    print(f"Previous successful: {len(successful_prev)}")
    print(f"Newly recovered: {len(successful_new)}")
    print(f"Total locations: {len(successful_prev) + len(successful_new)}")
    
    if not successful_new:
        print("❌ No new locations recovered")
        return
    
    # Create comprehensive map with all locations
    print(f"🗺️ Creating comprehensive map with {len(successful_prev) + len(successful_new)} locations...")
    
    # Calculate center point
    all_lats = list(successful_prev['latitude'].dropna()) + [r['latitude'] for r in successful_new]
    all_lons = list(successful_prev['longitude'].dropna()) + [r['longitude'] for r in successful_new]
    
    center_lat = np.mean(all_lats)
    center_lon = np.mean(all_lons)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add clustering
    marker_cluster = plugins.MarkerCluster(
        name="All Company Locations"
    ).add_to(m)
    
    # Add previous successful locations (blue markers)
    for idx, row in successful_prev.iterrows():
        sales = row.get('total_sales', 0)
        
        popup_html = f"""
        <div style="width: 320px; font-family: Arial; font-size: 12px;">
            <h4 style="color: #2c3e50;">{row['company']}</h4>
            <p><b>Status:</b> <span style="color: blue;">Previously Found</span></p>
            <p><b>Sales:</b> ${sales:,.2f}</p>
            <p><b>Address:</b> {row['cleaned_address']}</p>
        </div>
        """
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=row['company'],
            icon=folium.Icon(color='blue', icon='briefcase')
        ).add_to(marker_cluster)
    
    # Add newly recovered locations (green markers)
    for result in successful_new:
        data = result['customer_data']
        sales = data.get('Total Sales', 0)
        
        popup_html = f"""
        <div style="width: 320px; font-family: Arial; font-size: 12px;">
            <h4 style="color: #2c3e50;">{result['company']}</h4>
            <p><b>Status:</b> <span style="color: green;">Newly Recovered!</span></p>
            <p><b>Method:</b> {result['method']}</p>
            <p><b>Sales:</b> ${sales:,.2f}</p>
            <p><b>Used Address:</b> {result['used_address']}</p>
        </div>
        """
        
        folium.Marker(
            location=[result['latitude'], result['longitude']],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=result['company'],
            icon=folium.Icon(color='green', icon='star')
        ).add_to(marker_cluster)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 100px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:13px; padding: 10px; box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 10px 0;">Location Status</h4>
    <p style="margin: 3px 0;"><span style="color:blue; font-size: 16px;">●</span> Previously Found</p>
    <p style="margin: 3px 0;"><span style="color:green; font-size: 16px;">★</span> Newly Recovered</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save final map
    final_map_file = "/Users/akbarchranya/georgiadashboard/comprehensive_final_map.html"
    m.save(final_map_file)
    
    # Save combined results
    combined_results = []
    
    # Add previous results
    for idx, row in successful_prev.iterrows():
        combined_results.append({
            'company': row['company'],
            'account': row['account'],
            'phone': row['phone'],
            'city': row['city'],
            'state': row['state'],
            'address': row['cleaned_address'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'status': 'previously_found',
            'total_sales': row['total_sales'],
            'balance': row['balance']
        })
    
    # Add new results
    for result in successful_new:
        data = result['customer_data']
        combined_results.append({
            'company': result['company'],
            'account': data.get('Account #'),
            'phone': data.get('Phone #'),
            'city': data.get('City'),
            'state': data.get('State'),
            'address': result['used_address'],
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'status': 'newly_recovered',
            'total_sales': data.get('Total Sales', 0),
            'balance': data.get('Balance', 0)
        })
    
    combined_df = pd.DataFrame(combined_results)
    combined_csv = "/Users/akbarchranya/georgiadashboard/comprehensive_final_results.csv"
    combined_df.to_csv(combined_csv, index=False)
    
    # Final summary
    total_sales = combined_df['total_sales'].sum()
    
    print(f"\n{'='*60}")
    print(f"🎯 COMPREHENSIVE MAPPING COMPLETE!")
    print(f"{'='*60}")
    print(f"🏢 Total companies mapped: {len(combined_results)}")
    print(f"📍 Previously found: {len(successful_prev)}")
    print(f"🆕 Newly recovered: {len(successful_new)}")
    print(f"💰 Total sales represented: ${total_sales:,.2f}")
    print(f"\n📍 Final map: {final_map_file}")
    print(f"📄 Final results: {combined_csv}")
    print(f"\n🎉 Open the HTML file to explore ALL your company locations!")

if __name__ == "__main__":
    combine_results_and_create_final_map()


