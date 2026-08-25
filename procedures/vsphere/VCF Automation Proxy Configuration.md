# How to add a proxy to VCF Automation

This procedure outlines how to create proxy configuration on VCF Automation

## Authenticate to the API

[TODO]

## Create the proxyConfiguration

- Create a proxy definition:

```bash
curl -k -X POST https://${vcf_automation_host}/cloudapi/1.0.0/proxyConfigurations \
  -H 'Content-type: application/json' -H 'Accept:application/json;version=41.0.0-alpha' \
  -H 'Authorization: Bearer ${auth_value}' \
  -d '{
  "name": "RNCC Proxy",
  "authType": "NO_AUTH",
  "password": "",
  "host": "http://rncc-proxy-min.mgslb.vf.rogers.com",
  "port": 80
}'
```

## Get the ProxyConfiguration ID

- Get the value of the `id` field from the below API call:

```bash
curl -k https://${vcf_automation_host}/cloudapi/1.0.0/proxyConfigurations \
  -H 'Content-type: application/json' -H 'Accept:application/json;version=41.0.0-alpha' \
  -H 'Authorization: Bearer ${auth_value}'
```

## Create the ProxyRule

- Rule must be created per destination URL:

```bash
curl -k -X POST https://${vcf_automation_host}/cloudapi/1.0.0/proxyRules \
  -H 'Content-type: application/json' -H 'Accept:application/json;version=41.0.0-alpha' \
  -H 'Authorization: Bearer ${auth_value}' \
  -d '{
    "name": "RNCC Proxy Rule", 
    "destination": "https://${destination_fqdn}$:443", 
    "proxy": { "id": "urn:vcloud:${proxy_configuration_id}$" }, 
    "priority": 0
  }'
```
