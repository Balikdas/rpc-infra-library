# Dynatrace Dynakube Configuration for TKG

The following needs to be configure for the Dynatrace Dynakube manifest to work with TKG. Use one of the prod or lab verisons as appropriate and replace `${cluster_name}` with the name of the Kubernetes cluster.

## Dynakube Configuration (Prod)

```yaml
apiVersion: dynatrace.com/v1beta5
kind: DynaKube
metadata:
  annotations:
  name: ${cluster_name}
  namespace: dynatrace
spec:
  activeGate:
    capabilities:
    - routing
    - kubernetes-monitoring
    - dynatrace-api
    resources:
      requests:
        cpu: 500m
        memory: 6Gi
      limits:
        cpu: 1000m
        memory: 6Gi
  apiUrl: https://skc41390.live.dynatrace.com/api
  logMonitoring: {}
  metadataEnrichment:
    enabled: true
    namespaceSelector:
      matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: NotIn
        values:
        - avi-system
        - kube-node-lease
        - kube-public
        - kube-system
        - pinniped-concierge
        - tanzu-package-repo-global
        - tanzu-system
        - tanzu-system-monitoring
        - tca-system
        - tkg-system
        - tkg-system-public
        - twistlock
        - vmware-system-antrea
        - vmware-system-csi
  oneAgent:
    cloudNativeFullStack:
      namespaceSelector:
        matchExpressions:
        - key: kubernetes.io/metadata.name
          operator: NotIn
          values:
          - avi-system
          - kube-node-lease
          - kube-public
          - kube-system
          - pinniped-concierge
          - tanzu-package-repo-global
          - tanzu-system
          - tanzu-system-monitoring
          - tca-system
          - tkg-system
          - tkg-system-public
          - twistlock
          - vmware-system-antrea
          - vmware-system-csi
      tolerations:
      - effect: NoSchedule
        key: node-role.kubernetes.io/master
        operator: Exists
      - effect: NoSchedule
        key: node-role.kubernetes.io/control-plane
        operator: Exists
  skipCertCheck: false
```

## Dynakube Configuration (Lab)

```yaml
apiVersion: dynatrace.com/v1beta5
kind: DynaKube
metadata:
  annotations:
  name: ${cluster_name}
  namespace: dynatrace
spec:
  activeGate:
    capabilities:
    - routing
    - kubernetes-monitoring
    - dynatrace-api
    resources:
      requests:
        cpu: 500m
        memory: 6Gi
      limits:
        cpu: 1000m
        memory: 6Gi
  apiUrl: https://lnd40843.live.dynatrace.com/api
  logMonitoring: {}
  metadataEnrichment:
    enabled: true
    namespaceSelector:
      matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: NotIn
        values:
        - avi-system
        - kube-node-lease
        - kube-public
        - kube-system
        - pinniped-concierge
        - tanzu-package-repo-global
        - tanzu-system
        - tanzu-system-monitoring
        - tca-system
        - tkg-system
        - tkg-system-public
        - twistlock
        - vmware-system-antrea
        - vmware-system-csi
  oneAgent:
    cloudNativeFullStack:
      namespaceSelector:
        matchExpressions:
        - key: kubernetes.io/metadata.name
          operator: NotIn
          values:
          - avi-system
          - kube-node-lease
          - kube-public
          - kube-system
          - pinniped-concierge
          - tanzu-package-repo-global
          - tanzu-system
          - tanzu-system-monitoring
          - tca-system
          - tkg-system
          - tkg-system-public
          - twistlock
          - vmware-system-antrea
          - vmware-system-csi
      tolerations:
      - effect: NoSchedule
        key: node-role.kubernetes.io/master
        operator: Exists
      - effect: NoSchedule
        key: node-role.kubernetes.io/control-plane
        operator: Exists
  skipCertCheck: false
```
