# Dynatrace Kubernetes Operator Install

This document describes the procedure to install Dynatrace in a tenant workload Kubernetes cluster.

## Prerequisites

The below steps are required to install the Helm chart into Harbor before it can be used to install Dynatrace into the cluster

- Pull the Helm repo to a local machine and extract it

```bash
helm pull oci://public.ecr.aws/dynatrace/dynatrace-operator
tar zxvf dynatrace-operator-${version}.tgz
```

- Modify the `values.yaml` to match the environment (either lab or prod):

```bash
cd dynatrace-operator
vi values.yaml
```

- Edit the below lines to match the environment:

PROD:

```yaml
imageRef:
  repository: "harbor.cc.net.rogers.com/dynatrace/dynatrace-operator" #path to repo
  tag: "" #defaults to chart version
```

LAB:

```yaml
imageRef:
  repository: "harbor.cc.vf.rogers.com/dynatrace/dynatrace-operator" #path to repo
  tag: "" #defaults to chart version
```

- Create a new tarball of the Helm chart

```bash
cd ..
tar czvf dynatrace-operator-${version}.tgz dynatrace-operator
```

- Upload the `dynatrace-operator-${version}.tgz` file to Harbor:

  - Log in to Harbor OCI Registry

  ```bash
  helm registry login ${harbor_url}
  ```

  - Push the Chart to Harbor as OCI Artifact

  ```bash
  helm push dynatrace-operator${version}.tgz oci://${harbor_url}/dynatrace
  ```

  - Verify Upload

  ```bash
  helm show chart oci://${harbor_url}/dynatrace/dynatrace-operator --version ${version}
  ```

  - Or check Harbor UI under Artifacts (OCI charts appear as artifacts, not under "Helm Charts").
  - The chart will automatically be replicated to all Harbor instances

- Pull the image from the Dynatrace public repo and retag/push it to Harbor

  **Update the version tag to match the chart version**
  **Update the Harbor URL to match environment (lab or prod)**

```bash
docker pull public.ecr.aws/dynatrace/dynatrace-operator:${version}
docker tag public.ecr.aws/dynatrace/dynatrace-operator:${version} ${harbor_url}/dynatrace/dynatrace-operator:${version}
docker push ${harbor_url}/dynatrace/dynatrace-operator:${version}
```

## Installation Steps

These steps are to install the Dynatrace Operator. Followed by this will be the installation of the dynakube YAML provided by the Dynatrace team.

- Install the Dynatrace Operator:

```bash
kubectl config use-context ${target_cluster_context}
helm install dynatrace oci://${harbor_url}/dynatrace/dynatrace-operator --version ${version} --create-namespace --namespace dynatrace
 ```

- Wait for the Operator and Webhook pods to come up and be ready:

```bash
watch kubectl get pods -n dynatrace
```

- Apply the Dynakube YAML file (provided by the Dynatrace team)

  **This file is specific to each cluster. Do not reuse/apply this file in other clusters**
  
  **NOTE: There are additional parameters to be added to the Dynakube manifest. Refer to [Dynakube.md](Dynakube.md)**

```bash
kubectl apply -f dynakube.yaml
```

- Monitor the process with the below command:

```bash
watch kubectl get pods -n dynatrace
```

- Wait until all pods are Running and reporting ready and alive.
- Check the logs of the ActiveGate pod once it is up, it will report any conenctivity / login problems etc in its log.
