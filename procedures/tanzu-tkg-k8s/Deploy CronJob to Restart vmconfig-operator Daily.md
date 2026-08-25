# Deploy CronJob to Restart vmconfig-operator Daily

This procedure is to deploy the cronjob that will restart the vmconfig-operator daily at midnight. This is required due to the bug in vmconfig-operator where it will not reconcile NodePolicy CRs on newly created control-plane nodes.

## Prerequisite Steps

The below manifest depends on the alpine/kubectl image available from Docker Hub. It must be pulled, retagged and pushed to Harbor first. If not already done, apply the following procedure for production or lab as required.

- Production:

**Note:** The appropriate version depends on the TKG version in use. Use a version of Kubectl that is compatible with the management cluster Kubernetes version. The below version works with TKG 2.5.4.

```bash
docker pull alpine/kubectl:1.33.3
docker tag alpine/kubectl:1.33.3 harbor.cc.net.rogers.com/library/alpine:1.33.3
docker tag alpine/kubectl:1.33.3 harbor.cc.net.rogers.com/library/alpine:latest
docker push harbor.cc.net.rogers.com/library/alpine/kubectl:1.33.3
docker push harbor.cc.net.rogers.com/library/alpine/kubectl:latest
```

- Lab

```bash
docker pull alpine/kubectl:1.33.3
docker tag alpine/kubectl:1.33.3 harbor.cc.vf.rogers.com/library/alpine/kubectl:1.33.3
docker tag alpine/kubectl:1.33.3 harbor.cc.vf.rogers.com/library/alpine/kubectl:latest
docker push harbor.cc.vf.rogers.com/library/alpine/kubectl:1.33.3
docker push harbor.cc.vf.rogers.com/library/alpine/kubectl:latest
```

## Procedure

- Login to the Bastion VM in the same AZ as the management cluster you are working on
- Create a manifest file named 'vmconfig-operator-restarter.yaml' on the bastion VM based on either the production or lab versions below:

  - Production:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vmconfig-operator-restarter
  namespace: tca-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-restart-role
  namespace: tca-system
rules:
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - patch
  - update
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployment-restart-binding
  namespace: tca-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: deployment-restart-role
subjects:
- kind: ServiceAccount
  name: vmconfig-operator-restarter
  namespace: tca-system
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: restart-vmconfig-operator-cronjob
  namespace: tca-system
spec:
  concurrencyPolicy: Forbid
  failedJobsHistoryLimit: 3
  jobTemplate:
    metadata:
      creationTimestamp: null
    spec:
      template:
        metadata:
          creationTimestamp: null
        spec:
          containers:
          - command:
            - kubectl
            - rollout
            - restart
            - deployment/vmconfig-operator
            - -n
            - tca-system
            image: harbor.cc.net.rogers.com/library/alpine/kubectl:latest
            imagePullPolicy: Always
            name: kubectl-restart
            resources: {}
            terminationMessagePath: /dev/termination-log
            terminationMessagePolicy: File
          dnsPolicy: ClusterFirst
          restartPolicy: OnFailure
          schedulerName: default-scheduler
          securityContext: {}
          serviceAccount: vmconfig-operator-restarter
          serviceAccountName: vmconfig-operator-restarter
          terminationGracePeriodSeconds: 30
  schedule: 0 0 * * *
  successfulJobsHistoryLimit: 3
  suspend: false
```

  - Lab:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vmconfig-operator-restarter
  namespace: tca-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-restart-role
  namespace: tca-system
rules:
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - patch
  - update
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployment-restart-binding
  namespace: tca-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: deployment-restart-role
subjects:
- kind: ServiceAccount
  name: vmconfig-operator-restarter
  namespace: tca-system
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: restart-vmconfig-operator-cronjob
  namespace: tca-system
spec:
  concurrencyPolicy: Forbid
  failedJobsHistoryLimit: 3
  jobTemplate:
    metadata:
      creationTimestamp: null
    spec:
      template:
        metadata:
          creationTimestamp: null
        spec:
          containers:
          - command:
            - kubectl
            - rollout
            - restart
            - deployment/vmconfig-operator
            - -n
            - tca-system
            image: harbor.cc.vf.rogers.com/library/alpine/kubectl:latest
            imagePullPolicy: Always
            name: kubectl-restart
            resources: {}
            terminationMessagePath: /dev/termination-log
            terminationMessagePolicy: File
          dnsPolicy: ClusterFirst
          restartPolicy: OnFailure
          schedulerName: default-scheduler
          securityContext: {}
          serviceAccount: vmconfig-operator-restarter
          serviceAccountName: vmconfig-operator-restarter
          terminationGracePeriodSeconds: 30
  schedule: 0 0 * * *
  successfulJobsHistoryLimit: 3
  suspend: false
```

- Apply the configuration:

```bash
kubectl apply -f vmconfig-operator-restarter.yaml
```
