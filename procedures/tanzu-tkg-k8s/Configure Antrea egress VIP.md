# How to Configure Egress VIP in Antrea CNI

This procedure describes how to configure an Egress VIP for a TKG K8s cluster

1. Create a YAML file named `egress.yaml` with the following content, replacing `${egressIP}` with the actual Egress IP:

   ```yaml
   apiVersion: crd.antrea.io/v1beta1
   kind: ExternalIPPool
   metadata:
     name: egress-pool
   spec:
     ipRanges:
       - start: ${egressIP}
         end: ${egressIP}
     nodeSelector:
       matchExpressions:
         - key: node-role.kubernetes.io/control-plane
           operator: DoesNotExist
   ---
   apiVersion: crd.antrea.io/v1beta1
   kind: Egress
   metadata:
     name: egress-default
   spec:
     appliedTo:
       podSelector: {}
     egressIP: ${egressIP}
     externalIPPool: egress-pool
   ```

2. Apply the manifest:

   ```bash
   kubectl apply -f egress.yaml
   ```

3. In NSX-T T1 Router configuration, add a static route for the Egress VIP to the T1 router named `t1-rcsinSrv-nrt`:
   - Name: `${k8s-cluster-name}`-egress
   - Network: `${egressIP}`/32
   - Add Next Hop
     - IP Address: NULL
     - Admin Distance: 1
     - Scope: oSeg-rcsinSrv-prv-nrt-k8s-01

4. In NSX-T NAT configuration, under `t1-rcsinSrv-nrt`, ensure there is a No SNAT rule defined with a source IP range that covers the Egress VIP.
   - Name: default-egress-nonat
   - Action: No SNAT
   - Source IP: `${egress-ip-subnet}`
   - Destination IP: Any
   - Translated IP: Any
   - Priority: 9998
