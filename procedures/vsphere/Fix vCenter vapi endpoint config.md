# Fix vCenter vapi Endpoint Config

The vCenter API that is used by Tanzu and other components can experience memory exhaustion with the default settings and needs to have the default response size changed to accommodate large responses. Changing the memory allocation to 1GB and allowing up to 100MB responses is usually sufficient but the numbers can be adjusted as required.

## Procedure

* SSH to the vCenter and edit the vapi endpoint.properties file:

```bash
vi /etc/vmware-vapi/endpoint.properties
```

* Add the following line at the end of the file:

```bash
http.response.maxSize=300000000
```

* Set the vapi heap memory to 32GB

```bash
cloudvm-ram-size -C 32768 vmware-vapi-endpoint
```

* Restart the vapi service:

```bash
service-control --stop vmware-vapi-endpoint && service-control --start vmware-vapi-endpoint
```
