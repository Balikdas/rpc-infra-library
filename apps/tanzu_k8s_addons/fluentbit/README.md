# FluentBit Logging

This will install the FluentBit daemonset in your cluster. Note that you still need to configure the ConfigMap to tell FluentBit how to collect your logs and where to ship them.

## Retrieve Latest Fluent-Bit Image and Helm Chart

The below steps will setup the Fluent-Bit Helm chart and container images in Harbor for later installation.

* Login to the bastion server and add the helm repo:

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update
```

* Pull the latest version of the helm chart

```bash
helm pull fluent/fluent-bit
```

* Extract the chart tgz file

```bash
tar zxvf ./$(ls -1tr fluent-bit*.tgz)
```

* Edit the values file:

```bash
vi ./fluent-bit/values.yaml
```

* Replace the image repository URL with one of the following:

  * Lab:

  ```yaml
  image:
    repository: harbor.cc.vf.rogers.com/library/fluent-bit
  ```

  * Prod:

  ```yaml
  image:
    repository: harbor.cc.net.rogers.com/library/fluent-bit
  ```

* Repackage the helm chart:

```bash
tar czvf ./$(ls -1tr fluent-bit*.tgz) fluent-bit
```

* Download the helm chart tgz file to your desktop and upload it to Harbor using the UI

  * Login to the Harbor UI as admin user
  * Click on the `library` repo
  * Click on `Helm Charts`
  * Click `Upload` and select the tgz file from your desktop and upload it

* Pull the latest fluent-bit container image:

```bash
tag=$(helm search repo fluent/fluent-bit --versions | grep -v NAME | head -1 | awk '{print $3}')
docker pull cr.fluentbit.io/fluent/fluent-bit:${tag}
```

* Re-tag and push the image to Harbor

  * Lab:

  ```bash
  docker tag cr.fluentbit.io/fluent/fluent-bit:${tag} harbor.cc.vf.rogers.com/library/fluent-bit:${tag}
  docker push harbor.cc.vf.rogers.com/library/fluent-bit:${tag}
  ```

  * Prod:

  ```bash
  docker tag cr.fluentbit.io/fluent/fluent-bit:${tag} harbor.cc.net.rogers.com/library/fluent-bit:${tag}
  docker push harbor.cc.vf.rogers.com/library/fluent-bit:${tag}
  ```

## Install Fluent-Bit into the cluster

The below steps will install the Fluent-Bit daemonset into the cluster. Note that you will still need to configure Fluent-Bit before it will work.

* Configure kubectl context to use the correct context to ensure you are installing into the right cluster

```bash
kubectl config get-contexts
kubectl config use-context ${context_name}
```

* Install the helm chart

```bash
helm repo update
helm install fluent-bit library/fluent-bit --namespace fluent-bit --create-namespace
```

* Verify the pods are now running:

```bash
kubectl get pod -o wide -n fluent-bit
```

## Configure Fluent-Bit

To configure Fluent-Bit to send logs to external systems such as Splunk, refer to the Fluent-Bit documentation:

<https://docs.fluentbit.io/manual/installation/kubernetes#configure-fluent-bit>

For configuration specific to Splunk refer to this document:

<https://docs.fluentbit.io/manual/data-pipeline/outputs/splunk>

* Below is an example YAML configmap that will send pod logs to Splunk (replace `${splunk_hec_fqdn}` and `${splunk_token}` with the values provided by OSS Splunk team):

  * Open a VI editor:

  ```bash
  vi fluent-bit.yaml
  ```

  * Add the content below:

  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: fluent-bit
    namespace: fluent-bit
  data:
    fluent-bit.conf: |
      [SERVICE]
          Daemon Off
          Flush 1
          Log_Level info
          Parsers_File /fluent-bit/etc/parsers.conf
          HTTP_Server On
          HTTP_Listen 0.0.0.0
          HTTP_Port 2020
          Health_Check On

      [INPUT]
          Name tail
          Path /var/log/containers/*.log
          multiline.parser docker, cri
          Tag kube.*
          Mem_Buf_Limit 5MB
          Skip_Long_Lines On

      [FILTER]
          Name kubernetes
          Match kube.*
          Merge_Log On
          Keep_Log Off
          K8S-Logging.Parser On
          K8S-Logging.Exclude On

      [OUTPUT]
          Name splunk
          Match '*'
          Host ${splunk_hec_fqdn}
          Splunk_Token ${splunk_token}
          Port 443
          TLS On
          TLS.Verify Off

  ```

  * Save and quit:

  ```bash
  :wq!
  ```

* Apply the configmap by first removing the default one and then recreating it:

```bash
kubectl delete cm -n fluent-bit fluent-bit
kubectl apply -f fluent-bit.yaml
```

* Restart the fluent-bit daemonset pods:

```bash
kubectl delete pod -n fluent-bit $(k get pod -n fluent-bit --no-headers | awk '{print $1}')
```

* Verify fluent-bit daemonset pods are running:

```bash
kubectl get pod -o wide -n fluent-bit
```

