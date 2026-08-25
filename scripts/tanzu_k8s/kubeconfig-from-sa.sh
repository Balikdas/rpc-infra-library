#!/bin/bash
#
# This script will generate a kubeconfig file from a service account
# Usage: ./kubeconfig-from-sa.sh {namespace} {sa}
#

if [[ $# -ne 2 ]]; then
  echo "Error: Incorrect number of arguments"
  echo "Usage: $0 {namespace} {sa}"
  exit 1
fi

ns=$1
sa=$2
api=$(kubectl cluster-info | head -1 | awk '{print $7}' | sed -r "s/[[:cntrl:]]\[([0-9]{1,3};)*[0-9]{1,3}m//g")
cluster=$(kubectl config get-contexts | grep '\*' | awk '{print $3}')

secret=$(kubectl get sa -n ${ns} ${sa} -o jsonpath='{.secrets[0].name}')
ca=$(kubectl get secret ${secret} -n ${ns} -o jsonpath='{.data.ca\.crt}')
token=$(kubectl get secret ${secret} -n ${ns} -o jsonpath='{.data.token}' | base64 --decode)

if [[ -z ${api} || -z ${cluster} || -z ${ca} || -z ${sa} || -z ${ns} || -z ${api} || -z ${token} ]]; then
  echo "Error generating kubeconfig. Exiting"
  exit 1
fi

echo "apiVersion: v1
kind: Config
clusters:
- name: ${cluster}
  cluster:
    certificate-authority-data: ${ca}
    server: ${api}
contexts:
- name: ${sa}@${ns}@${cluster}
  context:
    cluster: ${cluster}
    user: ${sa}@${ns}@${cluster}
current-context: ${sa}@${ns}@${cluster}
users:
- name: ${sa}@${ns}@${cluster}
  user:
    token: ${token}"