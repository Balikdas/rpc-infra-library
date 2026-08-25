# Create Admin RBAC Configuration

This procedure is to create RBAC rules for Cloud Admins (not tenants!) that will be used to manage the Kubernetes cluster via their OSS-AD login.

**Prerequisite**: You must install Pinniped in the Tanzu Management cluster first to enable login and group mapping via OSS-AD

## Create Admin ClusterRoleBinding

- The Cluster Admin will use the default `cluster-admin` ClusterRole which provides full access to the entire cluster. For each Clustter Admin group, create the rolebinding using the YAML below, replacing `%AD-GROUP-ADMIN%` with the OSS-AD group name.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-admin:%AD-GROUP-ADMIN%
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: %AD-GROUP-ADMIN%
```

- Additional admin and read-only groups can be added by adding additional roleBindings using the same procedure above.

## Generate the Non-Admin Kubeconfig for Cluster Admin Access

**Prerequisite**: You must have a working Tanzu CLI implementation in the local machine you will run kubectl. For instructions on host to setup Tanzu CLI, read [here](https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/1.6/vmware-tanzu-kubernetes-grid-16/GUID-install-cli.html)

- Once you have installed the Tanzu CLI, run the below to set Rogers Tanzu environment specific settings:

```bash
tanzu config set env.TKG_CUSTOM_IMAGE_REPOSITORY harbor.cc.vf.rogers.com/registry  # LAB
tanzu config set env.TKG_CUSTOM_IMAGE_REPOSITORY harbor.cc.net.rogers.com/registry # PROD
tanzu init
tanzu plugin sync
tanzu login   # Follow steps to add the local kubeconfig of the Tanzu Management cluster
    ```

- Generate the non-admin kubeconfig for a management cluster using the Tanzu CLI.

```bash
tanzu management-cluster kubeconfig get --export-file=${management_cluster_name}-kubeconfig.yaml
```

- Generate the non-admin kubeconfig for a workload cluster using the Tanzu CLI.

```bash
tanzu cluster kubeconfig get -n ${workload_cluster_name} ${workload_cluster_name} --export-file=${workload_cluster_name}-kubeconfig.yaml
```

- Distribute the kubeconfig to the admin via secure means
