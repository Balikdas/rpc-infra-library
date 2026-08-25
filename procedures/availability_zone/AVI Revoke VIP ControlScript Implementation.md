# AVI Revoke VIP ControlScript Implementation Procedure

This document outlines how to configure the AVI ControlScript and associate Alert Definition and Alert Action to trigger the script when the VirtualService comes up.

## 1. Add ControlScript to AVI Controller

- Login to the AVI controller UI and navigate to Templates > Scripts > ControlScripts
- Click "Create" and add a new ControlScript with the following values and click Save:
  - Name: set_revoke_vip_route_true
  - Content: (paste the belo into the blank box):

```python
#!/usr/bin/python3

import os
import json
import sys
from avi.sdk.avi_api import ApiSession
import urllib3
import requests

if hasattr(requests.packages.urllib3, 'disable_warnings'):
    requests.packages.urllib3.disable_warnings()

if hasattr(urllib3, 'disable_warnings'):
    urllib3.disable_warnings()

def ParseAviParams(argv):
    if len(argv) != 2:
        return {}
    
    try:
        alert_params = json.loads(argv[1])
        return alert_params
    except json.JSONDecodeError:
        return {}

def get_api_token():
    return os.environ.get('API_TOKEN')

def get_api_user():
    return os.environ.get('USER')

def get_api_endpoint():
    return os.environ.get('DOCKER_GATEWAY') or 'localhost'

if __name__ == '__main__':
    # Grab top level information from the alert argument 
    alert_params = ParseAviParams(sys.argv)
    events = alert_params.get('events', [])
    
    if not events:
        print("No events found in payload.")
        sys.exit()

    objuuid = events[0].get('obj_uuid')

    api_endpoint = get_api_endpoint()
    user = get_api_user()
    token = get_api_token()

    with ApiSession(api_endpoint, user, token=token, tenant='*',api_version='30.2.1') as session:
        
        # Query the Virtual Service
        resp = session.get(f'virtualservice/{objuuid}?fields=name,revoke_vip_route,cloud_type')
        
        # Check if the API call was successful
        if resp.status_code >= 300:
            print(f'Unable to locate Virtual Service {objuuid}. API returned {resp.status_code}')
            sys.exit()    
            
        vs = resp.json()

        # Safely check the cloud type
        if vs.get('cloud_type') != 'CLOUD_NSXT':
            print("VS is not in an NSX Cloud. Exiting.")
            sys.exit()  
        
        # Safely check the boolean value (no quotes)
        if vs.get('revoke_vip_route') is True:
            print("revoke_vip_route is already True. Exiting.")
            sys.exit()

        # Build the patch payload using native booleans
        patch_data = {
            'json_patch': [
                {
                    'op': 'replace',
                    'path': '/revoke_vip_route',
                    'value': True
                }
            ]
        }

        # Apply the patch
        upd = session.patch(f'virtualservice/{objuuid}', data=json.dumps(patch_data),api_version='30.2.1')
        
        if upd.status_code != 200:
            # Write to stderr so the Avi Controller flags it as an error in the logs
            print(f'Failed to update Virtual Service {vs.get("name")} with error code {upd.status_code} and message {upd.text}', file=sys.stderr)
        else:
            print(f'Successfully updated {vs.get("name")}')
```

## 2. Add Alert Action in AVI Controller

- In AVI Controller UI navigate to Operations > Alerts > Alert Config
- Click Create and populate the following values and click Save:
  - Name: Set-Revoke-VIP-Route-On-VS-Up
  - Alert Level: Low
  - Control Script: set_revoke_vip_route_true

## 3. Add Alert Definition in AVI Controller

- In AVI Controller UI navigate to Operations > Alerts > Alert Actions
- Click Create and populate the following values and click Save:
  - Name: VirtualService-State-Up
  - Enable Alert Trigger: Checked
  - Source: Event Logs
  - Throttle Alert: 0
  - Object: Virtual Service
  - Instance: All Instances
  - Number of Occurrences: 1
  - Category: Real Time
  - Under "Events" click "Add":
    - Event Occurs: VS UP
  - Under "Events" click "Add" again:
    - Event Occurs: VIP UP
  - Multiple Events Operator: OR
  - Alert Action: Set-Revoke-VIP-Route-On-VS-Up
  - Alert Expiry Time: 30

## 4. Apply to all existing Virtual Services

- In AVI Controller UI, navigate to Applications > Virtual Services
- Set "Items per Page" to the maximum value
- Check the "Select All" box at the top of the list (beside the "Name" column)
- Click "Disable" and then once all are disbled, reselect all and click "Enable" (note there is traffic impact as part of this action so do it quickly)
- Repeat the above steps for the remaining pages of Virtual Services in the UI
