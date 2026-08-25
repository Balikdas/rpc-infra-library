# Fix Cluster API `machine` and `vspherevm` Objects Reporting Failed State

This proecdure is used to patch the state of the `machine` and `vspherevm` ClusterAPI objects showing as Failed state due to a temporary failure of the vCenter API.

The issue and this workaround are documented here: <https://kb.vmware.com/s/article/93689>

```bash
ns=${namespace}
for i in `./kubectl-v1.29.2 get machine -n $ns --no-headers | grep Failed | awk '{print $1}'`; do
  ./kubectl-v1.29.2 -n $ns patch --subresource=status --type merge vspherevm $i --patch '{"status": {"failureMessage": null, "failureReason": null}}'
  ./kubectl-v1.29.2 -n $ns patch --subresource=status --type merge machine $i --patch '{"status": {"failureMessage": null, "failureReason": null}}'
done
```
