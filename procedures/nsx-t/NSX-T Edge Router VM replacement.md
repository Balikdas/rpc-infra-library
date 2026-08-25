# NSX-T Edge Router VM replacement

## Error message

```bash
If the Edge VM is present in vCenter with a different moref id, please follow the below action. Use NSX add or update placement API with JSON request payload properties vm_id and vm_deployment_config to update the new vm moref id and vSphere deployment parameters. POST https://<manager-ip>/api/v1/transport-nodes/<tn-id>?action=addOrUpdatePlacementReferences.
```

* Get the current VM properties (the UUID comes from node properties in NSX-T)

```bash
curl --insecure -u '<username>:<password>' https://$NSX_manager_VIP/api/v1/transport-nodes/$edge_router_UUID
```

* Apply the new properties (vm_id comes from the URL in vCenter, vm_deployment_config comes from the above curl request output)

```bash
curl --insecure -k -v -u "$username:$password" -X POST -H 'Content-Type: application/json' -d '
{
  "vm_id":"<vm_id>",
  "vm_deployment_config" : {
    "vc_id" : "9c02ef6a-060a-4f0b-9d15-051d02fd57e0",
    "compute_id" : "domain-c8",
    "storage_id" : "datastore-23",
    "management_network_id" : "dvportgroup-42",
    "management_port_subnets" : [ {
        "ip_addresses" : [ "192.168.65.19" ],
        "prefix_length" : 25
    } ],
    "default_gateway_addresses" : [ "192.168.65.1" ],
    "data_network_ids" : [ "dvportgroup-7225", "dvportgroup-7223", "dvportgroup-7224" ],
    "reservation_info" : {
        "memory_reservation" : {
        "reservation_percentage" : 100
        },
        "cpu_reservation" : {
        "reservation_in_shares" : "HIGH_PRIORITY"
        }
    },
    "resource_allocation" : {
        "cpu_count" : 8,
        "memory_allocation_in_mb" : 32768
    },
    "placement_type" : "VsphereDeploymentConfig"
    },
    "node_user_settings" : {
    "cli_username" : "admin"
    }
}' https://$NSX_manager_VIP/api/v1/transport-nodes/$edge_router_UUID?action=addOrUpdatePlacementReferences
```
