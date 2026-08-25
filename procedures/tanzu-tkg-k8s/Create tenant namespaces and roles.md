# Create Tenant Namespaces and RBAC Roles

This procedure is to create namespaces for tenant apps that will run inside the Kubernetes cluster, and to provide access via OSS-AD logins to these apps.

**Prerequisite**: You must install Pinniped in the Tanzu Management cluster first to enable login and group mapping via OSS-AD

## Create Tenant Namespaces

- Using the Admin kubeconfig for the tenant Kubernetes cluster, create the namespaces as required from the CIQ:

    ```bash
    kubectl create ns ${namespace}
    ```

- Repeat the above step for all namespaces required by the tenant app.

## Create Roles for Each Namespace

- For each namespace created above, create an admin and read-only role using the YAML below, replacing `%NAMESPACE%` with the namespace name.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: %NAMESPACE%-admin
  namespace: %NAMESPACE%
rules:
- apiGroups:
  - "*"
  resources:
  - roles
  - rolebindings
  verbs:
  - list
  - get
  - watch
- apiGroups:
  - "*"
  resources:
  - configmaps
  - controllerrevisions
  - cronjobs
  - cronjobs/status
  - daemonsets
  - daemonsets/status
  - deployments
  - deployments/scale
  - deployments/status
  - endpoints
  - events
  - horizontalpodautoscalers
  - horizontalpodautoscalers/status
  - ingresses
  - ingresses/status
  - jobs
  - jobs/status
  - leases
  - limitranges
  - persistentvolumeclaims
  - persistentvolumeclaims/status
  - poddisruptionbudgets
  - poddisruptionbudgets/status
  - pods
  - pods/attach
  - pods/binding
  - pods/ephemeralcontainers
  - pods/eviction
  - pods/exec
  - pods/log
  - pods/portforward
  - pods/proxy
  - pods/status
  - podtemplates
  - replicasets
  - replicasets/scale
  - replicasets/status
  - replicationcontrollers
  - replicationcontrollers/scale
  - replicationcontrollers/status
  - secrets
  - serviceaccounts
  - serviceaccounts/token
  - services
  - services/proxy
  - services/status
  - statefulsets
  - statefulsets/scale
  - statefulsets/status
  verbs:
  - create
  - delete
  - deletecollection
  - get
  - list
  - patch
  - update
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: %NAMESPACE%-read-only
  namespace: %NAMESPACE%
rules:
- apiGroups:
  - "*"
  resources:
  - roles
  - rolebindings
  verbs:
  - list
  - get
  - watch
- apiGroups:
  - "*"
  resources:
  - configmaps
  - controllerrevisions
  - cronjobs
  - cronjobs/status
  - daemonsets
  - daemonsets/status
  - deployments
  - deployments/scale
  - deployments/status
  - endpoints
  - events
  - horizontalpodautoscalers
  - horizontalpodautoscalers/status
  - ingresses
  - ingresses/status
  - jobs
  - jobs/status
  - leases
  - limitranges
  - persistentvolumeclaims
  - persistentvolumeclaims/status
  - poddisruptionbudgets
  - poddisruptionbudgets/status
  - pods
  - pods/attach
  - pods/binding
  - pods/ephemeralcontainers
  - pods/eviction
  - pods/exec
  - pods/log
  - pods/portforward
  - pods/proxy
  - pods/status
  - podtemplates
  - replicasets
  - replicasets/scale
  - replicasets/status
  - replicationcontrollers
  - replicationcontrollers/scale
  - replicationcontrollers/status
  - secrets
  - serviceaccounts
  - serviceaccounts/token
  - services
  - services/proxy
  - services/status
  - statefulsets
  - statefulsets/scale
  - statefulsets/status
  verbs:
  - get
  - list
  - watch
```

## Create RoleBindings for Each OSS-AD Group

- For each namespace created above, create the roleBinding with the appropriate OSS-AD group. Be sure to associate the admin group with the admin role, and the read-only group with the read-only role. Replacing `%NAMESPACE%` with the namespace name, `%AD-GROUP-ADMIN%` with the admin OSS-AD group name and `%AD-GROUP-READ-ONLY%` with the read-only OSS-AD group name.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: %NAMESPACE%-admin:%AD-GROUP-ADMIN%
  namespace: %NAMESPACE%
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: %NAMESPACE%-admin
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: %AD-GROUP-ADMIN%
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: %NAMESPACE%-read-only:%AD-GROUP-READ-ONLY%
  namespace: %NAMESPACE%
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: %NAMESPACE%-read-only
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: %AD-GROUP-READ-ONLY%
```

- Additional admin and read-only groups can be added by adding additional roleBindings using the same procedure above.

## Create ClusterRole and ClusterRoleBindings for Cluster Level Object Access

- Create ClusterRole for the tenant OSS-AD groups ussing the YAML below:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tenant-cluster-role
rules:
- apiGroups:
  - "*"
  resources:
  - ingressclasses
  - namespaces
  - nodes
  - storageclasses
  verbs:
  - get
  - list
  - watch
```

- Create the ClusterRoleBinding for the tenant OSS-AD groups, replacing %OSS-AD-GROUP% with the OSS-AD group name. Repeat for each OSS-AD group that needs to access the cluster (both admin and read-only groups):

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tenant-cluster-role:%OSS-AD-GROUP%
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tenant-cluster-role
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: %OSS-AD-GROUP%
```

## Generate the Non-Admin Kubeconfig for Tenant Access

**Prerequisite**: Both you and the tenant must have a working Tanzu CLI implementation in the local machine you will run kubectl. For instructions on host to setup Tanzu CLI, read [here](https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/1.6/vmware-tanzu-kubernetes-grid-16/GUID-install-cli.html)

- Once you have installed the Tanzu CLI, run the below to set Rogers Tanzu environment specific settings:

```bash
tanzu init
tanzu config set env.TKG_CUSTOM_IMAGE_REPOSITORY harbor.cc.vf.rogers.com/registry  # LAB
tanzu config set env.TKG_CUSTOM_IMAGE_REPOSITORY harbor.cc.net.rogers.com/registry # PROD
tanzu plugin sync
tanzu login   # Follow steps to add the local kubeconfig of the Tanzu Management cluster
```

- Generate the non-admin kubeconfig for the workload cluster using the Tanzu CLI.

```bash
tanzu cluster kubeconfig get -n ${workload_cluster_name} ${workload_cluster_name} --export-file=${workload_cluster_name}-kubeconfig.yaml
```

- Distribute the kubeconfig to the tenant as part of the CIQ as-build response.
