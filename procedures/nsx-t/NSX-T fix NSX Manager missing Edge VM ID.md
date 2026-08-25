# How to fix NSX Manager missing Edge node VM ID

- Go to MOB and get instance UUID and VM ID:

(<https://${vc_fqdn}/mob/?moid=vm-98&doPath=config>)

- Note down the UUID, name, VMID and Instance UUID:

```text
NSX Edge UUID Edge Name VMID MoREF instanceUuid
c9fa4f4d-a9d8-4c9a-a6a2-9fb947de63ce rncc-vedge1-north vm-96 503c6e39-3122-af89-31dd-f6060839389a
fd1bef85-c913-4551-a7c4-b22d51f3ef3b rncc-vedge2-north vm-98 503cae55-9e79-57e0-98c0-c1c8b8533060
```

- Run the commands on the NSX Manager to get the DBs

```bash
corfu_tool_runner.py -o showTable -n nsx -t EdgeNodeExternalConfig > /image/EdgeNodeExternalConfig.txt
corfu_tool_runner.py -o showTable -n nsx -t EdgeNodeInstallInfo > /image/EdgeNodeInstallInfo.txt
corfu_tool_runner.py -o showTable -n nsx -t DeploymentUnitInstance > /image/DeploymentUnitInstance.txt
```

- Should get some output like this

```json
Key:
{"stringId": "/infra/sites/default/enforcement-points/default/edge-transport-node/c9fa4f4d-a9d8-4c9a-a6a2-9fb947de63ce"}

Payload:
{
"managementIp": [{
"ipAddress": [{
"ipv4": 3232241368
}],
"prefixLength": 26
}],
"deploymentType": "VIRTUAL_MACHINE",
"cpu": 8,
"memory": 32734684,
"hypervisor": "VMware",
"managementInterface": "eth0",
"maintenanceMode": "MAINTENANCE_MODE_DISABLED",
"searchString": "biosUuid:423cd231-0232-80f0-7c57-5119ee357bdb;macAddress:00:50:56:bc:5f:61",
"pnic": [{
"name": "fp-eth2",
"mac": "00:50:56:bc:a7:19"
}, {
"name": "fp-eth1",
"mac": "00:50:56:bc:9c:3e"
}, {
"name": "fp-eth0",
"mac": "00:50:56:bc:64:6c"
}],
"prevPnic": [{
"name": "fp-eth2",
"mac": "00:50:56:bc:a7:19"
}, {
"name": "fp-eth1",
"mac": "00:50:56:bc:9c:3e"
}, {
"name": "fp-eth0",
"mac": "00:50:56:bc:64:6c"
}],
"hostname": "rncc-vedge1-north.cc.vf.rogers.com",
"searchDomain": ["cc.vf.rogers.com"],
"ntpServer": ["172.30.232.20"],
"dnsServer": ["172.30.5.112"],
"qatConfig": {
"isVm": true,
"fipsCompliant": true
}
}
```

- Minify the JSON and add the "vmId" parameter as per below:

```bash
corfu_tool_runner.py -t EdgeNodeExternalConfig -n nsx -o editTable --keyToEdit '{"stringId": "/infra/sites/default/enforcement-points/default/edge-transport-node/c9fa4f4d-a9d8-4c9a-a6a2-9fb947de63ce"}' --newRecord '{"managementIp":[{"ipAddress":[{"ipv4":3232241368}],"prefixLength":26}],"vmId":{"stringId":"503c6e39-3122-af89-31dd-f6060839389a"},"deploymentType":"VIRTUAL_MACHINE","cpu":8,"memory":32734684,"hypervisor":"VMware","managementInterface":"eth0","maintenanceMode":"MAINTENANCE_MODE_DISABLED","searchString":"biosUuid:423cd231-0232-80f0-7c57-5119ee357bdb;macAddress:00:50:56:bc:5f:61","pnic":[{"name":"fp-eth2","mac":"00:50:56:bc:a7:19"},{"name":"fp-eth1","mac":"00:50:56:bc:9c:3e"},{"name":"fp-eth0","mac":"00:50:56:bc:64:6c"}],"prevPnic":[{"name":"fp-eth2","mac":"00:50:56:bc:a7:19"},{"name":"fp-eth1","mac":"00:50:56:bc:9c:3e"},{"name":"fp-eth0","mac":"00:50:56:bc:64:6c"}],"hostname":"rncc-vedge1-north.cc.vf.rogers.com","searchDomain":["cc.vf.rogers.com"],"ntpServer":["172.30.232.20"],"dnsServer":["172.30.5.112"],"qatConfig":{"isVm":true,"fipsCompliant":true}}'
```

- Repeat for all problematic Edge VMs
