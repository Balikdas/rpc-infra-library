# How to query Tanzu Kubernetes etcd

## Exec into one of the etcd pods with example command below

```bash
etcdctl \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get --keys-only --prefix=true
```
