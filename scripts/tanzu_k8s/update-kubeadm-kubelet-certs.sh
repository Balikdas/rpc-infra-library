#!/bin/bash

rotate_kubeadm_certs(){
  URL=http://100.102.1.1:8080/api/v1alpha1/certs
  response=$(curl -s -w "\n%{http_code}" -X DELETE $URL)
  http_code=$(tail -n1 <<< "$response")
  echo "cert rotation response code  $http_code"
  if [ "$http_code" != "200" ]; then
    content=$(sed '$ d' <<< "$response")
    echo "cert rotation failed with error $content"
  else
    echo "successfully rotated the certs"
    certs_expiry_after=$(kubeadm certs check-expiration)
    echo "certs expiry after rotation $certs_expiry_after"
  fi
}

check_kubeadm_cert_expiry() {
    expired_certs=$(kubeadm certs check-expiration | grep -i 'invalid')

    if [[ -n "$expired_certs" ]]; then
      return 0
    else
      return 1
    fi
}

backup_kubelet_certs() {
    echo "Backing up kubelet certificates..."
    mkdir -p /home/admin/kubelet-certs-backup
    mv /etc/kubernetes/kubelet.conf /home/admin/kubelet-certs-backup/
    cp /var/lib/kubelet/pki/kubelet-client* /home/admin/kubelet-certs-backup/
}

create_kubeadm_config() {
    echo "Creating kubeadm config..."

    cat << EOF > /home/admin/kubeadm.config
apiServer:
  extraArgs:
    authorization-mode: Node,RBAC
    profiling: "false"
  timeoutForControlPlane: 4m0s
apiVersion: kubeadm.k8s.io/v1beta3
certificatesDir: /etc/kubernetes/pki
clusterName: photon
controlPlaneEndpoint: 100.102.1.1:6443
controllerManager:
  extraArgs:
    leader-elect: "false"
    node-cidr-mask-size-ipv6: "112"
    profiling: "false"
dns:
  imageRepository: projects.registry.vmware.com/tkg
  imageTag: v1.10.1_vmware.2
etcd:
  local:
    dataDir: /common/vmware/snc/etcd
    extraArgs:
      cipher-suites: TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
    imageRepository: projects.registry.vmware.com/tkg
    imageTag: v3.5.7_vmware.2
imageRepository: projects.registry.vmware.com/tkg
kind: ClusterConfiguration
kubernetesVersion: v1.26.5+vmware.2
networking:
  dnsDomain: cluster.local
  podSubnet: 100.100.0.0/16,2001:db8:1::/112
  serviceSubnet: 100.101.0.0/16,2001:db8:2::/112
scheduler:
  extraArgs:
    leader-elect: "false"
    profiling: "false"
EOF
}

generate_kubelet_config() {
    echo "Generating kubelet config..."
    kubeadm kubeconfig user --org system:nodes --client-name system:node:photon --config /home/admin/kubeadm.config > /etc/kubernetes/kubelet.conf
}

restart_kubelet() {
    echo "Restarting kubelet..."
    systemctl restart kubelet
}

update_kubelet_config() {
    echo "Updating kubelet config with new certificate paths..."
    sed -i 's|client-certificate: .*$|client-certificate: /var/lib/kubelet/pki/kubelet-client-current.pem|' /etc/kubernetes/kubelet.conf
    sed -i 's|client-key: .*$|client-key: /var/lib/kubelet/pki/kubelet-client-current.pem|' /etc/kubernetes/kubelet.conf
}

check_node_readiness() {
    echo "Checking node readiness..."
    while true; do
        STATUS=$(kubectl get nodes photon --kubeconfig=/home/admin/.kube/config -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
        if [ "$STATUS" == "True" ]; then
            echo "Node is up (Ready)."
            break
        else
            echo "Node is not ready or down."
        fi
        sleep 5
    done
}

check_tcxproduct_readiness() {
    echo "Waiting until tcx installer to create tcxproduct"
    sleep 120

    echo "Checking tcxproduct resource readiness..."
    START_TIME=$(date +%s)

    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED_TIME=$((CURRENT_TIME - START_TIME))

        if [ $ELAPSED_TIME -ge 1200 ]; then
            echo "Timeout reached after 20 minutes. Not all tcxproduct resources are ready."
            break
        fi

        NOT_READY=$(kubectl get tcxproduct --all-namespaces --kubeconfig=/home/admin/.kube/config -o json | jq '.items[] | select(.status.conditions[] | select(.type == "Ready" and .status != "True")) | .metadata.name')

        RESOURCE_COUNT=$(kubectl get tcxproduct --all-namespaces --kubeconfig=/home/admin/.kube/config -o json | jq '.items | length')

        if [ -z "$NOT_READY" ] && [ "$RESOURCE_COUNT" -eq 2 ]; then
            echo "All tcxproduct resources are ready!"
            break
        else
            echo "Some tcxproduct resources are not ready:"
            echo "$NOT_READY"
            echo "Waiting for 5 seconds before checking again..."
        fi

        sleep 5
    done
}

copy_kubeconfig() {
  cp /etc/kubernetes/admin.conf /home/admin/.kube/config
  cp /etc/kubernetes/admin.conf /root/.kube/config
}

update_kubeconfig_secret() {
    PROPERTIES_FILE="/common/configs/appliance.properties"
    KUBECONFIG_FILE="/etc/kubernetes/admin.conf"
    SECRET_NAME="kubeconfig-secret"
    SECRET_KEY="kubeconfig"

    APPLIANCE_ROLE=$(grep "^applianceRole=" "$PROPERTIES_FILE" | cut -d'=' -f2 | tr -d '\r')

    if [ "$APPLIANCE_ROLE" == "Manager" ]; then
        NAMESPACE="tca-mgr"
    else
        NAMESPACE="tca-cp-cn"
    fi

    KUBECONFIG_B64=$(base64 -w 0 "$KUBECONFIG_FILE")

kubectl apply --kubeconfig /etc/kubernetes/admin.conf -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${NAMESPACE}
type: Opaque
data:
  ${SECRET_KEY}: ${KUBECONFIG_B64}
EOF
}

main() {
    backup_kubelet_certs
    create_kubeadm_config
    generate_kubelet_config
    restart_kubelet
    update_kubelet_config
    restart_kubelet

    cert_expired=$(check_kubeadm_cert_expiry; echo $?)
    if [[ "cert_expired" -eq 0 ]]; then
        echo "Kubeadm certs are expired. Renewing them"
        rotate_kubeadm_certs
    else
        echo "Kubeadm certs are active"
    fi

    copy_kubeconfig
    update_kubeconfig_secret
    check_node_readiness
    check_tcxproduct_readiness
}

main