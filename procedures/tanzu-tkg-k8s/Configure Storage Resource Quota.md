# Configure Kubernetes Storage Resource Quota

This YAML will add a resource quota and limit the amount of storage that can be reserved by a given namespace. Modify the parameters to suit your needs.

Replace `${namespace}` with the tenants namesapce name. Replace the value of `requests.storage` to set a limit on PVCs and replace the value of `requests.ephemeral-storage` to limit the amount of ephemeral storage the namesapce can consume.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ${namespace}-storage-quota
  namespace: ${namespace}
spec:
  hard:
    requests.storage: 1024Gi
    requests.ephemeral-storage: 80Gi
```
