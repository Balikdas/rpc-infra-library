# Palo Alto Prisma Defender Installation

* Modify the `twistlock-${environment}.yaml` file (either lab or prod depending on your use case) to add the cluster name:

```bash
- name: DEFENDER_CLUSTER
value: "CLUSTER_NAME"
```

Example:

```bash
- name: DEFENDER_CLUSTER
value: "rtrm-prod-wlfdle"
```

* Apply the yaml:

```bash
kuebctl apply -f twistlock-${environment}.yaml
```

* Verify the pods are running:

```bash
watch kubectl get all -n twistlock
```

* Verify the logs

```bash
kubectl logs -n twistlock daemonset.apps/twistlock-defender-ds
```

* Additionally, the below commands can automate the process on all contexts in your kubeconfig (excluding the management cluster of course):

```bash
k config get-contexts --no-headers | grep -v rncc | tr -d '*' | while read line; do cls=`echo $line | awk '{print $2}'`; cp -p twistlock-${environment}.yaml twistlock-$cls.yaml; sed -i "s/CLUSTER_NAME/$cls/g" twistlock-$cls.yaml; done
k config get-contexts --no-headers | grep -v rncc | tr -d '*' | while read line; do ctx=`echo $line | awk '{print $1}'`; cls=`echo $line | awk '{print $2}'`; k config use $ctx; k apply -f twistlock-$cls.yaml; done
```
