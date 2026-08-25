# Velero Cluster Migration Procedure

## Deploy New Cluster

- Take note of the source cluster spec in TCA
- Deploy a new cluster with identical spec but new name and K8s API IP

## Create MinIO Bucket

- On a server with MinIO installed, create a new bucket for saving the backups

## Install Velero to New and Old Clusters

- Create secret file:

```bash
echo '[default]
aws_access_key_id = minioadmin
aws_secret_access_key = minioadmin' > minio.secret
```

- Install Velero:

```bash
velero install --image harbor.cc.vf.rogers.com/library/velero:v1.11.1_vmware.1 \
--plugins harbor.cc.vf.rogers.com/library/velero-plugin-for-aws:v1.7.1_vmware.1 \
--provider aws \
--bucket ${minio_bucket_name}$ \
--use-volume-snapshots=false \
--default-volumes-to-fs-backup \
--use-node-agent \
--secret-file minio.secret \
--backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://${minio_server_fqdn}$:9000
```

- Configure velero-restore-helper

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: velero-restore-helper-config
  namespace: velero
  labels:
    velero.io/plugin-config: ""
    velero.io/pod-volume-restore: RestoreItemAction
data:
  image: harbor.cc.vf.rogers.com/library/velero-restore-helper:v1.11.1_vmware.1
```

## Backup Existing Cluster

```bash
velero backup create ${backup_name}
```

## Restore to New Cluster

```bash
velero restore create --from-backup ${backup_name} \
--exclude-namespaces avi-system,kube-node-lease,kube-public,kube-system,pinniped-concierge,secretgen-controller,tanzu-package-repo-global,tanzu-system,tca-system,tkg-system,tkg-system-public,twistlock,velero,vmware-system-antrea,vmware-system-csi \
--existing-resource-policy none
```

## Issues

- Destination cluster needs a temporary egress IP until the source cluster is shut down
- AKO needs to be reinstalled but this should not be done until after the AKO statefulset on the source cluster has been scaled to 0 replicas
- Some cluster scoped objects such as `ClusterRole` and `ClusterRoleBindings` won't get created on the destination cluster. Manually create them from the source.

## Uninstalling Velero

If you would like to completely uninstall Velero from your cluster, the following commands will remove all resources created by velero install:

```bash
kubectl delete namespace/velero clusterrolebinding/velero
kubectl delete crds -l component=velero
```
