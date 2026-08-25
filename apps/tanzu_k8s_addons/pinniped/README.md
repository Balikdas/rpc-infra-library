# Pinniped Installation in Tanzu Clusters (OSS-AD Integration)

This application will enable OSS-AD auth in the management and workload K8s clusters.

## Deploy Pinniped and Dex

1. Replace the `%MGMT_CLUSTER_TLS_CERT_WITH_INTERMEDIATE_CA_PEM%`, `%MGMT_CLUSTER_TLS_KEY_PEM%`, `%RNCC_VF_LAB_ROOT_CA_PEM%`, `%RNCC_ROOT_CA_BASE64%`,`%MGMT_CLUSTER_FQDN%`, `%CLUSTER_NAME%` and `%LDAP_PASSWORD%` fields in the yaml with the appropriate values:

   ```bash
   vi pinniped-prod.yaml
   ```

   or

   ```bash
   vi pinniped-lab.yaml
   ```

   - The `%CLUSTER_NAME%` field should be updated to the name of the Tanzu Management Cluster.
   - The `%LDAP_PASSWORD%` field should be updated to the OSS-AD service account password for the rnccadmin account.

2. Switch to the kubeconfig admin context for the Tanzu Management cluster:

   ```bash
   kubectl config get-contexts
   kubectl config use-context ${mgmt_cluster_admin_context}
   ```

3. Apply the yaml:

   ```bash
   kubectl apply -f pinniped-lab.yaml
   ```

   or

   ```bash
   kubectl apply -f pinniped-prod.yaml
   ```

4. Monitor the progress of the install:

   ```bash
   watch kubectl get app -A
   ```

5. Create the `clusterRole` and `clusterRoleBinding` for the user/group access to the cluster.
   - This is covered at length in the Kubernetes documentation [Kubernetes RBAC documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac)
   - For the below example, we'll provide cluster-admin (root level) privilege using the `cluster-admin` role

   ```bash
   kubectl create clusterrolebinding ${oss_ad_group_name}-cluster-admin --clusterrole cluster-admin --group ${oss_ad_group_name}
   ```

6. Test the integration
   - Note that if you do not have Tanzu CLI setup yet, you'll need to follow these steps first (assuming Tanzu CLI has been installed on your system / bastion host):

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

   - Attempt to login to the cluster from an OSS-AD user in the aforementioned group that was added to the clusterRoleBinding:

   ```bash
   kubectl get pod -A --kubeconfig ${workload_cluster_name}-kubeconfig.yaml
   ```

After running the kubectl command, you will get a prompt to visit a web link where you need to login with your OSS-AD credentials. One you've logged in, you'll get a token which you need to copy/paste into the shell window where you ran the kubectl command. If everything worked properly you will be able to see the pods running in the cluster.
