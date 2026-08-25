# RabbitMQ Installation

This will install Rabbit MQ on your cluster.

## Prerequisites

- tanzu CLI installed on your bastion host
- cert-manager installed on your cluster

First run the appropriate installer for either prod or lab:

### Production

```bash
./rabbitmq_install_prod.sh
```

### Lab

```bash
./rabbitmq_install_lab.sh
```

Then create the Rabbit MQ cluster (adjust the config as needed):

```bash
kubectl apply -f rabbitmq-cluster.yaml
```

To get the username and password for the cluster, run the following commands:

```bash
kubectl get secret spdr-rabbit-default-user -o jsonpath='{.data.username}' | base64 -d
kubectl get secret spdr-rabbit-default-user -o jsonpath='{.data.password}' | base64 -d
```
