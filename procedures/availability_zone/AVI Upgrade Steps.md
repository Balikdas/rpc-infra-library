# AVI 21.1.4 to 30.2.1-2p3 Upgrade Procedure

## Prerequisites

- Make sure AKO chart and images for 1.12.1 are uploaded to Harbor
- Make sure the AKO chart values.yaml file is uploaded to Bastion VM and edit the `controllerHost` field to match the AZ being upgraded

## Controller Upgrade Steps

- In UI Administration > Configuration Backup download the last backup file to your local machine
- In UI Administration > Controller > Software, upload controller version 30.2.1 to the UI
- In UI Administration > Controller > Software, upload patch version 2p3 to the UI
- In UI Administrator > Controller > System Update, run the upgrade to 30.2.1 + 2p3 (select both when performing upgrade) and include all Service Engines
- Login to AVI Controller CLI as admin user run the below commands:

```bash
$ shell
> configure controller properties
> edit_system_limits
> save
> configure systemlimits
> controller_limits
> controller_cloud_limits index 13
> t1_lrs_per_cloud 300
> save
> save
> save
```

- Login to AVI Controller CLI as admin user and set anycast VIPs to auto withdraw route when down (replace `${virtualServiceName}` with actual VS Name)

```bash
# shell
> configure virtualservice ${virtualServiceName}
> revoke_vip_route
> save
```

- In UI Infrastructure > Clouds, change name of cloud "NSX-T WL" to "NSX" and change "vCenter WL" to "vCenter"

- Remove scripts for anycast VIP route withdrawal (old method)
  - Remove from UI: Operations > Alert Config > VS-VIP-Status-harbor (and any other anycast VIP)
  - Remove from UI: Operations > Alert Actions > Enable-Disable-VS-VIP
  - Remove from UI: Templates > Scripts > ControlScripts > enable_disable_vs_vip

## AKO Upgrade Steps

- Update AKO on all clusters to 1.12.1 (replace `${context}` with kubeconfig cluster context and `${clusterName}` with the actual cluster name)

```bash
kubectl config use ${context}
kubectl delete ns avi-system && kubectl delete crd $(kubectl get crd | awk '{print $1}' | egrep 'avi|ako')
sed "s/CLUSTER_NAME/${clusterName}/g" values-1.12.1.yaml > values-${clusterName}.yaml
helm install ako library/ako --version 1.12.1 --create-namespace --namespace avi-system --values values-${clusterName}.yaml
kubectl logs -n avi-system ako-0 -f
```
