# Contour Ingress Controller Config

This document describes the procedure to install Contour Ingress into a TKG Kubernetes cluster.

- In the `contour.prod.yaml` (for production) or the `contour.lab.yaml` (for lab) file, in the below section, replace `${ingress_IP}` with the assigned external Ingress IP:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: envoy
  namespace: projectcontour
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
    ako.vmware.com/load-balancer-ip: "${ingressIP}"
spec:
  externalTrafficPolicy: Local
  ports:
  - port: 80
    name: http
    protocol: TCP
    targetPort: 8080
  - port: 443
    name: https
    protocol: TCP
    targetPort: 8443
  selector:
    app: envoy
  type: LoadBalancer
```

- Then load the YAML file. For production deployment:

  ```bash
  kubectl apply -f contour.prod.yaml
  ```

- for Lab deployment:

  ```bash
  kubectl apply -f contour.lab.yaml
  ```

- Verify that all pods are up and running in the projectcontour namespace:

```bash
kubectl get pods -n projectcontour
```

- Once this is done and the pods are up, you can create the HTTPProxy. In the ```httpProxy.yaml``` file, replace the variables in the section below. You may also need to update the port number and so on, depending on your app's configuration.

```yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: ${endpoint_name}
  namespace: ${namespace}
spec:
  virtualhost:
    fqdn: ${endpoint_fqdn}
    tls:
      secretName: ${endpoint_tls_secret}
  routes:
    - conditions:
      - prefix: ${endpoint_url_path}
      services:
        - name: 
          port: ${backend_service_port}
```

- Then load the YAML file.

```bash
kubectl apply -f httpProxy.yaml
```

It will create a resource of type 'httpproxy' in the default namespace. You can check the status by running:

```bash
kubectl get httpproxy -n ${namespace}
```

If the HTTPProxy shows as 'Invalid' check the reason by running this command:

```bash
kubectl describe httpproxy -n ${namespace} ${endpoint_name}
```

Fix the reason for the error and you may also need to restart Contour and Envoy:

```bash
kubectl rollout restart -n projectcontour deployment.apps/contour
kubectl rollout restart -n projectcontour daemonset.apps/envoy
```
