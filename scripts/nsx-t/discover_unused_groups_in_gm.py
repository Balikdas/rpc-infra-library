import requests
import urllib3
import json
import time

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
NSX_GLOBAL_MANAGER = "https://nsx.cc.vf.rogers.com"
USERNAME = "admin"
PASSWORD = "xxxxxxxx"
DOMAIN = "default"  # Change if you use custom global domains
# ---------------------

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.verify = False

def get_valid_enforcement_points():
    """Dynamically finds all absolute multi-site enforcement point paths on GM."""
    sites_url = f"{NSX_GLOBAL_MANAGER}/global-manager/api/v1/global-infra/sites"
    response = session.get(sites_url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching Federation sites: {response.text}")
        return []
    
    sites = response.json().get("results", [])
    enforcement_paths = []
    
    for site in sites:
        site_id = site.get("id")
        if not site_id:
            continue
        
        # Query enforcement points belonging specifically to this registered Site ID
        ep_url = f"{NSX_GLOBAL_MANAGER}/global-manager/api/v1/global-infra/sites/{site_id}/enforcement-points"
        ep_response = session.get(ep_url, headers=headers)
        
        if ep_response.status_code == 200:
            ep_results = ep_response.json().get("results", [])
            for ep in ep_results:
                if ep.get("path"):
                    enforcement_paths.append(ep["path"])
                    
    # If no sites or enforcement points are discovered, fall back to structural guess
    if not enforcement_paths:
        print("Warning: Could not dynamically auto-discover paths. Staging standard default topology.")
        enforcement_paths.append("/global-infra/sites/default/enforcement-points/default")
        
    return enforcement_paths

def get_all_global_groups():
    """Fetches all inventory groups directly using a standard GET request."""
    url = f"{NSX_GLOBAL_MANAGER}/global-manager/api/v1/global-infra/domains/{DOMAIN}/groups"
    groups = []
    cursor = None
    
    while True:
        params = {"cursor": cursor} if cursor else {}
        response = session.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching groups from GM: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        groups.extend(data.get("results", []))
        
        cursor = data.get("cursor")
        if not cursor:
            break
            
    return groups

def is_global_group_used(group_path, enforcement_points):
    """Checks group bindings across all discovered site enforcement paths."""
    url = f"{NSX_GLOBAL_MANAGER}/global-manager/api/v1/global-infra/group-service-associations"
    
    # We must look through each site enforcement boundary; if used on ANY site, it's marked in-use
    for ep_path in enforcement_points:
        params = {
            "intent_path": group_path,
            "enforcement_point_path": ep_path
        }
        
        response = session.get(url, headers=headers, params=params)
        
        # Handle rate limiting dynamically
        if response.status_code == 429 or "exceeded request rate" in response.text:
            print("Rate limit warning triggered. Cooling down for 2 seconds...")
            time.sleep(2)
            return is_global_group_used(group_path, enforcement_points)
            
        if response.status_code != 200:
            print(f"Error checking associations for {group_path} on {ep_path}: {response.text}")
            continue # Skip to next site point if one fails
            
        data = response.json()
        results = data.get("results", [])
        
        if len(results) > 0:
            return True # Found usage on this site cluster
            
    return False

def main():
    print("Connecting to NSX Global Manager API...")
    
    # Dynamically extract real, valid path models from your Federation configuration mapping
    enforcement_points = get_valid_enforcement_points()
    print(f"Discovered active tracking points: {enforcement_points}")
    
    all_groups = get_all_global_groups()
    if not all_groups:
        print("No global groups retrieved or connection failed.")
        return
        
    print(f"Found {len(all_groups)} global groups. Analyzing configuration mappings safely...")
    unused_groups = []
    
    for group in all_groups:
        group_id = group["id"]
        group_name = group.get("display_name", group_id)
        group_path = group["path"]
        
        # Skip internal system groups
        if group.get("_system_owned", False):
            continue
            
        if not is_global_group_used(group_path, enforcement_points):
            unused_groups.append({
                "id": group_id,
                "name": group_name,
                "path": group_path
            })
            print(f"  [UNUSED] Name: {group_name} | ID: {group_id}")
            
        time.sleep(0.015) # Maintain safe API throughput thresholds

    print("\n" + "="*60)
    print(f"SCAN COMPLETE: Found {len(unused_groups)} unmapped global groups.")
    print("="*60)
    
    if unused_groups:
        filename = "unused_global_groups.json"
        with open(filename, "w") as f:
            json.dump(unused_groups, f, indent=4)
        print(f"Accurate results successfully saved to '{filename}'")

if __name__ == "__main__":
    main()
