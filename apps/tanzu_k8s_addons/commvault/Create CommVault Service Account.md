# Create CommVault Service Account

```bash
kubectl create ns cv-config
kubectl create serviceaccount cv-config -n cv-config
kubectl create clusterrolebinding cluster-admin-cv-config --clusterrole=cluster-admin --serviceaccount=cv-config:cv-config
kubectl get secret -n cv-config $(k get secret -n cv-config | grep cv-config-token | awk '{print $1}') -o jsonpath='{.data.token}' | base64 -d
```
