# Proceudre to Migrate T0/T1 to Active Active Stateful

## Split the existing Edge Cluster and Configure Temporary T1 Router

- Remove 2 nodes from the existing edge cluster
  - Choose 2 nodes which are on different hosts to remove and put them in NSX mtce mode
  - Disable the source interfaces of these nodes from their BGP neighbors
  - Delete the source interfaces from these nodes
  - Remove these nodes from the edge cluster
- Add the 2 nodes from the step above to a new edge cluster and take them out of NSX mtce mode
- Create a temp T0 router in A/A statefule mode connected to new edge cluster
- Configure interfaces on Edge VMs in new edge cluster (use same IPs as they had before)
- Configure interface groups on Edge VMs in new edge cluster (one per tor switch)
- Configure BGP on temp T0
- Disable gateway firewall on temp T0
- Configure route advertisement/redistribution rules on temp T0

## Migrate T1s and Segments to Temporary T1 Router

- Backup the existing NAT rules for the non-routable T1 using the curl command below:

```bash
curl -k -u 'admin:${password}' -H 'Accept: application/json' -X GET "https://${nsx_mgr_fqdn}/policy/api/v1/infra/tier-1s/${t1_router_name}/nat/USER/nat-rules" -o t1_nat_rules.json
```

- Backup the existing static routes for the non-routable T1 using the curl command below:

```bash
curl -k -u 'admin:${password}' -H 'Accept: application/json' -X GET "https://${nsx_mgr_fqdn}/policy/api/v1/infra/tier-1s/${t1_router_name}/static-routes" -o t1_static_routes.json
```

- Migrate existing routable T1 to temp T0 and verify by pinging VMs on the routable segments from RCMIN

**IMPORTANT:** The below steps must be executed as quickly as possible to minimize downtime

- Disconnect all segments from non-routable T1 (set T1 Gateway to None)
- Delete the non-routable T1
- Recreate the non-routable T1 as Active/Active and connect to the temp T0
- Set the route advertisements on the new non-routable T1 (Static Routes, NAT IP, LB VIPs)
- Reconnect the non-routable segments to the new non-routable T1 router
- Restore the NAT rules using the script below:

```python
import json
import requests
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
NSX_MGR = "https://${nsx_mgr_fqdn}"
AUTH = ("admin", "${password}")
TARGET_T1_ID = "${t1_router_name}"
JSON_FILE = "t1_nat_rules.json"

def recreate_nat_rules():
    # Load rules from the exported JSON file
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            rules = data.get("results", [])
    except FileNotFoundError:
        print(f"Error: {JSON_FILE} not found.")
        return

    print(f"Found {len(rules)} rules to recreate...")

    for rule in rules:
        rule_id = rule['id']
        # The Policy API path for T1 NAT rules
        url = f"{NSX_MGR}/policy/api/v1/infra/tier-1s/{TARGET_T1_ID}/nat/USER/nat-rules/{rule_id}"
        
        # Clean system-generated fields before pushing back to API
        # These fields can cause conflicts if re-uploaded directly
        clean_rule = {k: v for k, v in rule.items() if not k.startswith('_') and k not in ['parent_path', 'path', 'relative_path', 'unique_id', 'realization_id']}

        try:
            # Use PUT to create or update the rule
            response = requests.put(url, auth=AUTH, json=clean_rule, verify=False)
            if response.status_code in [200, 201]:
                print(f"Successfully recreated rule: {rule.get('display_name', rule_id)}")
            else:
                print(f"Failed to recreate rule {rule_id}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"An error occurred while processing rule {rule_id}: {e}")

if __name__ == "__main__":
    recreate_nat_rules()
```

- Restore the static routes using the script below:

```python
import json
import requests
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
NSX_MGR = "https://${nsx_mgr_fqdn}"
AUTH = ("admin", "${password}")
TARGET_T1_ID = "${t1_router_name}"
JSON_FILE = "t1_static_routes.json"

def recreate_static_routes():
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
            routes = data.get("results", [])
    except FileNotFoundError:
        print(f"Error: {JSON_FILE} not found.")
        return

    print(f"Found {len(routes)} static routes to recreate...")

    for route in routes:
        route_id = route['id']
        # Endpoint for Tier-1 Static Routes
        url = f"{NSX_MGR}/policy/api/v1/infra/tier-1s/{TARGET_T1_ID}/static-routes/{route_id}"
        
        # Strip system-generated read-only fields to avoid API errors
        clean_route = {
            k: v for k, v in route.items() 
            if not k.startswith('_') and k not in [
                'parent_path', 'path', 'relative_path', 
                'unique_id', 'realization_id'
            ]
        }

        try:
            # PUT creates the route if it doesn't exist or updates it if it does
            response = requests.put(url, auth=AUTH, json=clean_route, verify=False)
            if response.status_code in [200, 201]:
                print(f"Successfully recreated route: {route.get('display_name', route_id)} ({route.get('network')})")
            else:
                print(f"Failed to recreate route {route_id}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"An error occurred while processing route {route_id}: {e}")

if __name__ == "__main__":
    recreate_static_routes()
```

## Migrate to new T0

- Delete BGP neighbors and interfaces from old T0 stateless router
- Delete old T0 stateless router
- Move the existing edge routers to the new edge cluster
- Delete existing edge cluster
- Create a new T0 router in A/A stateful mode connected to new edge cluster
- Configure interfaces on new T0 router (use same IPs as they had before)
- Configure interface groups on new T0 router (one per tor switch)
- Configure BGP on new T0
- Disable gateway firewall on new T0
- Configure route advertisement/redistribution rules on new T0
- Migrate T1 routers to new T0
- Delete temp T0
- Configure remaining interfaces on new T0 router (use same IPs as they had before)
- Add remaining interfaces to interface groups on new T0 router
- Configure remaining BGP neighbors on new T0
- Rename new edge cluster to same name as before
