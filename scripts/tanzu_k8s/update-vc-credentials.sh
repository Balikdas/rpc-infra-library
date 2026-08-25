#!/usr/bin/env bash
# KM - Use this script to update the vcenter credentials on TCA-CP nodes and K8s management clusters
#Copyright (c) 2022 VMware, Inc. All rights reserved.
#set -x
VERSION=1.0.0
EXIT_CODE=0
TIMEOUT_COUNT=24 ## Total 24*TIMEVAL seconds
TIMEVAL=10 # Unit Seconds
CURRENT_CLUSTER=""
CURRENT_MANAGEMENT_CLUSTER=""
declare -A FAILED_CLUSTERS_ARRAY
declare -A SUCCESSFUL_CLUSTERS_ARRAY

Logf() {
    if [ "${CURRENT_CLUSTER}" != "" ]; then
        echo -e "`date '+%Y-%m-%d %H:%M:%S'` [$1] [CLUSTER: ${CURRENT_CLUSTER}] $2"
    else
        echo -e "`date '+%Y-%m-%d %H:%M:%S'` [$1] $2"
    fi
}
Errorf() { Logf "ERROR" "$@"; }
Warnf() { Logf "WARNING" "$@"; }
Infof() { Logf "INFO" "$@"; }

get_current_vc_server_address() {
    namespace=${2:-$1}
    kubectl get secret ${1}-vsphere-cpi-addon -n ${namespace} -o jsonpath='{.data.values\.yaml}'| base64 -d | grep 'server' | awk '{print $2;}'
}

get_current_vc_username() {
    namespace=${2:-$1}
    # Suppose NSX-T username is empty
    kubectl get secret ${1}-vsphere-cpi-addon -n ${namespace} -o jsonpath='{.data.values\.yaml}'| base64 -d | grep 'username'  | awk '{if(length($2)>2) print $2;}'
}

get_current_vc_password() {
    namespace=${2:-$1}
    # Suppose NSX-T username is empty
    kubectl get secret ${1}-vsphere-cpi-addon -n ${namespace} -o jsonpath='{.data.values\.yaml}'| base64 -d | grep 'password' | awk '{if(length($2)>2) print $2;}'
}

append_to_failed_clusters_array() {
    tmp=${FAILED_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]}
    if [ "$tmp" == "" ]; then
        FAILED_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]=${CURRENT_CLUSTER}
    else
        FAILED_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]="$tmp ${CURRENT_CLUSTER}"
    fi
}

append_to_successful_clusters_array() {
    tmp=${SUCCESSFUL_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]}
    if [ "$tmp" == "" ]; then
        SUCCESSFUL_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]=${CURRENT_CLUSTER}
    else
        SUCCESSFUL_CLUSTERS_ARRAY[${CURRENT_MANAGEMENT_CLUSTER}]="$tmp ${CURRENT_CLUSTER}"
    fi
}

restart_capv_pods() {
    # Restart CAPV pod
    kubectl -n capv-system delete pod --selector=control-plane=controller-manager
}

restart_cpi_pods() {
    kubeopt=""
    if [ -f /tmp/${CURRENT_CLUSTER}-kubeconfig ]; then
        kubeopt="--kubeconfig /tmp/${CURRENT_CLUSTER}-kubeconfig"
    fi
    # Restart CPI pod
    kubectl $kubeopt rollout restart daemonset vsphere-cloud-controller-manager -n kube-system
}

get_vc_password_by_server_address_and_username() {
    jq -r '.vcenters[] | select(.server == "'$1'") | .accounts[] | select(.username == "'$2'") | .password // ""' ${INPUT_CONFIG}
}

verify_tkg_context() {
    tkg_id=`curl -s GET 'http://127.0.0.1:8888/api/v1/managementclusters' | jq -r '.[] | select( .clusterName == "'${CURRENT_CLUSTER}'" ) | .tkgID'`
    password=`curl -s GET "http://127.0.0.1:8888/api/v1/tkgcontext/${tkg_id}?plaintext=true" | jq -r '.vsphere.password'`
    if [ "$password" == "$1" ]; then
        Infof "VC credential on TKG context of management cluster ${CURRENT_CLUSTER} was updated successfully"
    else
        Warnf "VC credential on TKG context of management cluster ${CURRENT_CLUSTER} was not as expected."
        return 1
    fi
}

verify_capv_credentials() {
    password=`kubectl get secret capv-manager-bootstrap-credentials -n capv-system -o jsonpath='{.data.credentials\.yaml}'| base64 -d | grep 'password' | awk '{print $2;}'`
    if [ "$password" == "$1" ]; then
        Infof "VC credential on CAPV secret of management cluster ${CURRENT_CLUSTER} was updated successfully"
    else
        Warnf "VC credential on CAPV secret of management cluster ${CURRENT_CLUSTER} was not as expected."
        return 1
    fi
}

verify_cpi_credentials() {
    namespace=${2:-tkg-system}
    # Suppose NSX-T username is empty
    password=`kubectl get secret ${CURRENT_CLUSTER}-vsphere-cpi-addon -n $namespace -o jsonpath='{.data.values\.yaml}'| base64 -d | grep 'password'  | awk '{if(length($2)>2) print $2;}'`
    if [ "$password" != "$1" ]; then
        Warnf "VC credential on CPI secret was not as expected."
        return 1
    fi
    # Verify CPI configmap
    kubeopt=""
    if [ -f /tmp/${CURRENT_CLUSTER}-kubeconfig ]; then
        kubeopt="--kubeconfig /tmp/${CURRENT_CLUSTER}-kubeconfig"
    fi
    set -o pipefail
    password=`kubectl $kubeopt -n kube-system get configmaps vsphere-cloud-config -o jsonpath='{.data.vsphere\.conf}'| grep password | awk -F \" '{print $2;}'`
    if [ $? -ne 0 ]; then
        # Be compatiable with old format
        cpi_secret_name=`kubectl $kubeopt -n kube-system get configmaps vsphere-cloud-config -o jsonpath='{.data.vsphere\.conf}'| grep 'secret-name =' | awk -F \" '{print $2;}'`
        cpi_secret_namespace=`kubectl $kubeopt -n kube-system get configmaps vsphere-cloud-config -o jsonpath='{.data.vsphere\.conf}'| grep 'secret-namespace =' | awk -F \" '{print $2;}'`
        password=`kubectl $kubeopt -n ${cpi_secret_namespace} get secrets ${cpi_secret_name} -o jsonpath='{.data}' | jq -r '. | to_entries | map(select(.key|test(".*password"))) | map(.value) | .[]' | base64 -d`
    fi
    if [ "$password" != "$1" ]; then
        Warnf "VC credential on CPI configMap was not as expected."
        return 1
    fi
    Infof "VC credential on CPI secret was updated successfully"
    return 0
}

verify_csi_credentials() {
    namespace=${2:-tkg-system}
    kubectl get secret ${CURRENT_CLUSTER}-vsphere-csi-addon -n $namespace 1>/dev/null 2>&1
    if [ $? -ne 0 ]; then
        return 0 #No need to check csi as not found
    fi
    password=`kubectl get secret ${CURRENT_CLUSTER}-vsphere-csi-addon -n $namespace -o jsonpath='{.data.values\.yaml}'| base64 -d | grep password | awk '{print $2;}'`
    if [ "$password" == "$1" ]; then
        Infof "VC credential on CSI secret was updated successfully"
        return 0
    else
        Warnf "VC credential on CSI secret was not as expected."
        return 1
    fi
}

verify_management_cluster_update() {
    verify_tkg_context $1 && verify_capv_credentials $1 && verify_cpi_credentials $1 && verify_csi_credentials $1
}

update_secret_for_vmconfig() {
    # Handle vmconfig logic
    Infof "Start to update VC $1 credentials for VMConfig-Operator"
    kubectl get secret $1 -n tca-system 1>/dev/null 2>&1
    if [ $? -eq 0 ]; then
        vmconfig_username=`kubectl get secret $1 -n tca-system -o jsonpath='{.data.username}' | base64 -d`
        vmconfig_password=`get_vc_password_by_server_address_and_username $1 ${vmconfig_username}`
        if [ "${vmconfig_password}" == "" ]; then
            Warnf "Couldn't find credentials of username ${vmconfig_username} for VC $1. Skip to update VMConfig Secret"
            return 0
        fi
        kubectl patch secret $1 -n tca-system -p '{"data": {"password": "'`echo -n "${vmconfig_password}" | base64`'"}}'
    else
        cat <<EOF > /tmp/vmconfig-secret.yml
apiVersion: v1
data:
  password: `echo -n "$3" | base64`
  username: `echo -n "$2" | base64`
kind: Secret
metadata:
  annotations:
    telco.vmware.com/failoverdisable: "true"
  name: ${1}
  namespace: tca-system
type: Opaque
EOF
        kubectl apply -f /tmp/vmconfig-secret.yml
    fi
}

update_secret() {
    server=$1
    name=$2
    namespace=${3:-tca-system}
    username=`kubectl get secret $name -n $namespace -o jsonpath='{.data.username}' | base64 -d`
    old_password=`kubectl get secret $name -n $namespace -o jsonpath='{.data.password}' | base64 -d`
    new_password=`get_vc_password_by_server_address_and_username $server $username`
    if [ $? -ne 0 ] || [ "${new_password}" == "" ]; then
        Infof "Fail to find VC $server credentials for username $username. Skip to update it."
        return 0
    fi
    if [ "${old_password}" == "${new_password}" ]; then
        Infof "Passwords are the same. No need to update secret $namespace/${secret_name}"
        # Handle for VMconfig secret
        update_secret_for_vmconfig $server $username ${old_password}
        return $?
    fi
    verify_vc_credentials $server $username ${new_password} && \
        update_secret_for_vmconfig $server $username ${new_password} && \
        kubectl patch secret $name -n $namespace -p '{"data": {"password":"'`echo -n ${new_password} | base64`'"}}'
}

update_vc_prime() {
    vc_primes=(`kubectl get vcenterprimes -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_primes}" == "" ]; then
        update_secret_for_vmconfig ${vc_server} ${vc_username} ${vc_password}
        Warnf "Couldn't find any vCenterPrime. Skip to update."
        return 0
    fi
    ret=0
    for item in ${vc_primes[@]}
    do
        Infof "Start to update vcenterPrime ${item} credentials"
        server=`kubectl get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.server.address}'`
        secret_name=`kubectl get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.server.credentialRef.name}'`
        secret_namespace=`kubectl get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.server.credentialRef.namespace}'`
        update_secret ${server} ${secret_name} ${secret_namespace}
        if [ $? -ne 0 ]; then
            Errorf "Fail to update vCenterPrime credentials"
            ret=1
        fi
    done
    return $ret
}

update_vc_sub() {
    vc_subs=(`kubectl get vcentersubs -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_subs}" == "" ]; then
        Warnf "Couldn't find any vCenterSub. Skip to update."
        return 0
    fi
    ret=0
    for item in ${vc_subs[@]}
    do
        Infof "Start to update vCenterSub ${item} credentials"
        server=`kubectl get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.server.address}'`
        secret_name=`kubectl get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.server.credentialRef.name}'`
        secret_namespace=`kubectl get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.server.credentialRef.namespace}'`
        update_secret ${server} ${secret_name} ${secret_namespace}
        if [ $? -ne 0 ]; then
            Errorf "Fail to update vCenterSub ${item} credentials"
            ret=1
        fi
    done
    return $ret
}

update_tkg_context() {
    password=$1
    tkg_id=`curl -s GET 'http://127.0.0.1:8888/api/v1/managementclusters' | jq -r '.[] | select( .clusterName == "'${CURRENT_CLUSTER}'" ) | .tkgID'`
    echo ${tkg_id}
    old_password=`curl -s GET "http://127.0.0.1:8888/api/v1/tkgcontext/${tkg_id}?plaintext=true" | jq -r '.vsphere.password'`
    if [ "${old_password}" == "${password}" ]; then
        Infof "Passwords are the same. No need to update TKG context"
        return 0
    fi
    Infof "Start to update TKG context for cluster ${CURRENT_CLUSTER}"
    content=`curl -s GET "http://127.0.0.1:8888/api/v1/tkgcontext/${tkg_id}?plaintext=true" | jq -c -r --arg pwd "$password" '.vsphere.password =  $pwd'`
    echo ${content}
    curl --fail-with-body -X PUT "http://127.0.0.1:8888/api/v1/tkgcontext/${tkg_id}" --data "${content}"
}

update_cpi_secret() {
    cpi_content=`kubectl get secret ${CURRENT_CLUSTER}-vsphere-cpi-addon -n ${2:-${CURRENT_CLUSTER}} -o jsonpath='{.data.vsphereconf-custom\.lib\.txt}'`
    if [ "${cpi_content}" == "" ]; then
        Infof "No need to update CPI secret"
        return 0
    fi
    echo "${cpi_content}" | base64 -d > /tmp/${CURRENT_CLUSTER}-cpi
    sed -i "/^password = */c password = \"$1\"" /tmp/${CURRENT_CLUSTER}-cpi
    encoded_content=`base64 -w 0 /tmp/${CURRENT_CLUSTER}-cpi`; rm -f /tmp/${CURRENT_CLUSTER}-cpi
    kubectl patch secret ${CURRENT_CLUSTER}-vsphere-cpi-addon -n ${2:-${CURRENT_CLUSTER}} -p '{"data": {"vsphereconf-custom.lib.txt":"'${encoded_content}'"}}'
}

verify_vc_credentials() {
    session_id=`curl -s --fail-with-body -k -X POST https://$1/rest/com/vmware/cis/session -u "$2":"$3"`
    if [ $? -ne 0 ]; then
        Errorf "Fail to login VC $1 with provided username $2 and password."
        return 1
    fi
    curl -k -X DELETE -H "vmware-api-session-id: `echo ${session_id} | jq -r .value`" https://$1/rest/com/vmware/cis/session
    return 0
}

update_management_cluster() {
    vc_server=`get_current_vc_server_address ${CURRENT_CLUSTER} tkg-system`
    if [ $? -ne 0 ] || [ "${vc_server}" == "" ]; then
        Errorf "Couldn't get current VC server address"
        return 1
    fi
    vc_username=`get_current_vc_username ${CURRENT_CLUSTER} tkg-system`
    vc_password=`get_vc_password_by_server_address_and_username ${vc_server} ${vc_username}`
    if [ $? -ne 0 ] || [ "${vc_password}" == "" ]; then
        Infof "Fail to find VC ${vc_server} credentials for username ${vc_username}. Skip to update it."
        return 0
    fi
    verify_vc_credentials ${vc_server} ${vc_username} ${vc_password} || return 1
    update_tkg_context ${vc_password} && \
        tanzu management-cluster credentials update --vsphere-password ${vc_password} --vsphere-user ${vc_username} -v 9 && \
        update_cpi_secret ${vc_password} tkg-system && \
        restart_capv_pods && restart_cpi_pods && \
        update_vc_prime && update_vc_sub
    if [ $? -ne 0 ]; then
        Errorf "Fail to update vc credentials for management cluster"
        append_to_failed_clusters_array
        return 1
    fi
    i=0
    while [ $i -lt ${TIMEOUT_COUNT} ]
    do
        Infof "Waiting for VC credentials on management cluster updated.."
        verify_management_cluster_update ${vc_password}
        if [ $? -ne 0 ]; then
            i=$(( i+1 )); sleep ${TIMEVAL}s
        else
            Infof "VC credentials on management cluster ${CURRENT_CLUSTER} are updated successfully"
            append_to_successful_clusters_array
            return 0
        fi
    done
    Errorf "Fail to update vc credentials for management cluster ${CURRENT_CLUSTER}"
    append_to_failed_clusters_array
    return 1
}

update_workload_cluster() {
    Infof "Start to update vc credentials on workload cluster ${CURRENT_CLUSTER}"
    vc_server=`get_current_vc_server_address ${CURRENT_CLUSTER}`
    if [ $? -ne 0 ] || [ "${vc_server}" == "" ]; then
        Errorf "Couldn't get current VC server address"
        return 0
    fi
    vc_username=`get_current_vc_username ${CURRENT_CLUSTER}`
    old_password=`get_current_vc_password ${CURRENT_CLUSTER}`
    vc_password=`get_vc_password_by_server_address_and_username ${vc_server} ${vc_username}`
    if [ "${vc_password}" == "${old_password}" ]; then
        Infof "Passwords of username ${vc_username} for VC ${vc_server} are the same. Skip to update workload cluster ${CURRENT_CLUSTER}"
        return 0
    fi
    verify_vc_credentials ${vc_server} ${vc_username} ${vc_password} || return 1
    # Get current workload cluster kubeconfig
    kubectl get secrets -n ${CURRENT_CLUSTER} ${CURRENT_CLUSTER}-kubeconfig -o jsonpath='{.data.value}' | base64 -d > /tmp/${CURRENT_CLUSTER}-kubeconfig
    tanzu cluster credentials update ${CURRENT_CLUSTER} -n ${CURRENT_CLUSTER} --vsphere-password ${vc_password} --vsphere-user ${vc_username} -v 9 && \
        update_cpi_secret ${vc_password} && restart_cpi_pods
    if [ $? -ne 0 ]; then
        Errorf "Fail to update vc credentials for workload cluster ${CURRENT_CLUSTER}"
        append_to_failed_clusters_array
        return 1
    fi
    i=0
    while [ $i -lt ${TIMEOUT_COUNT} ]
    do
        Infof "Waiting for VC credentials on workload cluster ${CURRENT_CLUSTER} updated.."
        verify_cpi_credentials ${vc_password} ${CURRENT_CLUSTER} && verify_csi_credentials ${vc_password} ${CURRENT_CLUSTER}
        if [ $? -ne 0 ]; then
            i=$(( i+1 )); sleep ${TIMEVAL}s
        else
            Infof "VC credentials on workload cluster ${CURRENT_CLUSTER} are updated successfully"
            append_to_successful_clusters_array
            break
        fi
    done
    clean_temporary_files
    if [ $i -ge ${TIMEOUT_COUNT} ]; then
        Errorf "Fail to update vc credentials for workload cluster ${CURRENT_CLUSTER}"
        append_to_failed_clusters_array
        return 1
    fi
    return 0
}

update_workload_clusters() {
    wc_clusters=(`kubectl get clusters -A -o json | jq -r '.items[] | select(.metadata.namespace != "tkg-system") | .metadata.name'`)
    ret=0
    for cluster in ${wc_clusters[@]}
    do
        CURRENT_CLUSTER=${cluster}
        update_workload_cluster || ret=$?
    done
    return $ret
}

clean_temporary_files() {
    if [ -f /tmp/vmconfig_secret.yml ]; then
        rm -f /tmp/vmconfig_secret.yml
    fi
    if [ -f /tmp/${CURRENT_CLUSTER}-kubeconfig ]; then
        rm -f /tmp/${CURRENT_CLUSTER}-kubeconfig
    fi
    if [ -f /tmp/${CURRENT_CLUSTER}-cpi ]; then
        rm -f /tmp/${CURRENT_CLUSTER}-cpi
    fi
}

dump_handled_clusters_summary() {
    if [ ${#SUCCESSFUL_CLUSTERS_ARRAY[@]} -gt 0 ]; then
        Infof "VC passwords on these following clusters are updated successfully."
        for cluster in ${!SUCCESSFUL_CLUSTERS_ARRAY[@]}
        do
            echo -e "- $cluster: ${SUCCESSFUL_CLUSTERS_ARRAY[$cluster]}"
        done
    fi
    if [ ${#FAILED_CLUSTERS_ARRAY[@]} -gt 0 ]; then
        Errorf "VC passwords on these following clusters are updated in failure."
        for cluster in ${!FAILED_CLUSTERS_ARRAY[@]}
        do
            echo -e "- $cluster: ${FAILED_CLUSTERS_ARRAY[$cluster]}"
        done
    fi
}

main() {
    managementclusters=(`jq -r .managementclusters[] ${INPUT_CONFIG}`)
    if [ $? -ne 0 ]; then
        Errorf "Couldn't parse input file ${INPUT_CONFIG}. It must be in JSON format."
        exit 1
    fi
    for cluster in ${managementclusters[@]}
    do
        CURRENT_MANAGEMENT_CLUSTER=$cluster
        kubectl config use-context "${cluster}-admin@${cluster}" &&  tanzu login --server ${cluster}
        if [ $? -ne 0 ]; then
            Errorf "No management cluster ${cluster} was found"
            continue
        fi
        if [ ! -z ${WORKLOAD_CLUSTER} ]; then
            CURRENT_CLUSTER=""
            exist=(`kubectl get clusters -A -o json | jq -r '.items[] | select(.metadata.name == "'${WORKLOAD_CLUSTER}'") | .metadata.name'`)
            if [ "$exist" == "" ]; then
                Infof "No workload cluster named as ${WORKLOAD_CLUSTER} found on management cluster ${cluster}."
                continue
            fi
            CURRENT_CLUSTER=${WORKLOAD_CLUSTER} && update_workload_cluster
        else
            CURRENT_CLUSTER=${cluster}
            Infof "Start to upgrade VC credentials on management cluster ${CURRENT_CLUSTER}"
            update_management_cluster && update_workload_clusters || EXIT_CODE=$?
        fi
    done
    CURRENT_CLUSTER=""
    Infof "VC credentials update process is done."
    dump_handled_clusters_summary
}

usage() {
    echo -e "This script is used to update VC password for management clusters and workload clusters. It should only be ran on TCA-CP within root user directly. Supported TCA Version 2.0.0"
    echo -e "\nUsage:\n   `basename $0` [option...]"
    echo -e "\nOptions:"
    echo "  -f, --config                 Config file for VC accounts. Should be JSON format."
    echo "  -w, --workload-cluster       Only run on specific workload cluster."
    echo "  -v, --version                Show current script version."
}

while [[ $# -gt 0 ]]; do
    case $1 in
        '--config'|-f)
        INPUT_CONFIG=$2
        shift
        ;;
        '--version'|-v)
        echo ${VERSION}
        exit 0
        ;;
        '--help'|-h)
        usage
        exit 0
        ;;
        '--workload-cluster'|-w)
        WORKLOAD_CLUSTER=$2
        shift
        ;;
        *)
        break
        ;;
    esac
    shift
done
set +u
if [ -z ${INPUT_CONFIG} ] || [ ! -f ${INPUT_CONFIG} ]; then
    Errorf "Couldn't find input file ${INPUT_CONFIG}. Please make sure provide the right path."
    usage; exit 1
fi

set +e
set -o pipefail
main
exit ${EXIT_CODE}
