# How to scale daemonset to zero replicas

## Scale to zero

```bash
kubectl patch ds -n $namespace $daemonset_name -p '{"spec": {"template": {"spec": {"nodeSelector": {"non-existing": "true"}}}}}'
```

### Scale back to original

```bash
kubectl patch ds -n $namespace $daemonset_name --type json -p='[{"op": "remove", "path": "/spec/template/spec/nodeSelector/non-existing"}]'
```
