# K8s Cluster Upgrade via TCA Procedure

1. Disable all Load Balancer VIPs for the target cluster in AVI UI
2. Terminate all daemonsets in the target cluster (repeat 2nd command for all listed daemonsets from the first command):

    ```bash
    kubectl get ds -A | egrep -v 'kube-system|tca-system|tkg-system'
    kubectl patch ds -n $namespace $daemonset_name -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
    ```

3. Check status of all vCenter APIs, especially the /sdk api endpoint, and restart vCenter if necessary, then initiate the cluster upgrade from TCA UI
4. Monitor the upgrade progress from the Management cluster:

    ```bash
    watch kubectl get machine -n $workload_cluster_name
    ```

5. If any node rotation appears to stall, ie. node is not rotated after more than 10 minutes, investigate what pods are running on the node stuck in "Deleting" state and terminate the pods:

    ```bash
    kubectl config get-contexts
    kubectl use-context $workload_cluster_context
    kubectl get pods -A -o wide | egrep -v 'kube-system|tca-system|tkg-system' | grep $node
    kubectl delete pod -n $namespace $pod
    ```

6. When all nodes are rotated and the TCA UI indicates the cluster upgrade is successful perform the following steps:

    * Re-enable daemonsets that were disabled in step 2:

        ```bash
        kubectl get ds -A | egrep -v 'kube-system|tca-system|tkg-system'
        kubectl patch ds -n $namespace $daemonset_name --type json -p='[{"op": "remove", "path": "/spec/template/spec/nodeSelector/non-existing"}]'
        ```

    * Tag the new nodes in NSX-T with the `AppId: kubernetes` tag
    * Tag the new nodes in NSX-T with the application tag (`AppId: $appId`) and any other tags as required for DFW rules
    * Apply any node customizations as required by the application CIQ spec by ssh'ing to the nodes as capv user and applying the required configuration
    * Update NAT mapping for egress VIP in NSX-T for the new nodes (new node IPs as source in the existing SNAT rule for the cluster)

7. Validate that all pods are running and passing readiness checks in the workload cluster

    ```bash
    kubectl get pod -A
    ```

8. Re-enable the Load Balancer VIPs in AVI UI for the workload cluster
