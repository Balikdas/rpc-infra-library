# How to Update Managed Addons Configuration in TKG

This procedure describes how to update the TKG managed addons configuration. The example below is given for the vsphere-csi-addon but the same procedure can be applied to any managed addon.

These changes are necessary when something the addon relies on is changed, such as vCenter credentials etc. The process is outlined in the VMware KB article below:

<https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/1.6/vmware-tanzu-kubernetes-grid-16/GUID-packages-update-addons.html>

- Save the values:

```bash
kubectl get secret/$cluster_name-vsphere-csi-addon -n tkg-system  -o jsonpath="{.data.values\.yaml}" | base64 -d > values.yaml
```

- Edit the values.yaml to replace the datacenter name with the new one

```bash
vi values.yaml
```

- Patch the addon values:

```bash
kubectl patch secret/$cluster_name-vsphere-csi-addon -n tkg-system -p "{\"data\":{\"values.yaml\":\"$(base64 -w 0 < values.yaml)\"}}" --type=merge
```

- Verify the packages have reconciled (this takes a few mins to complete):

```bash
watch kubectl get app -n tkg-system
```

- Verify the values are updated in the package (requires kctrl to be installed on the local machine):

```bash
kctrl package installed get --package-install vsphere-csi --values -n tkg-system
```

- Verify all pods in the kube-system namespace are running

```bash
kubectl get pod -n kube-system
```
