#!/usr/bin/env bash
#Copyright (c) 2024 VMware by Broadcom, Inc. All rights reserved.


VERSION=3.0.0
VCENTER_IP=""
JOBNAME=""
JOBPHASE=""
KBS_SVC_IP=""
THUMBPRINT=""
TIMEVAL=15
CHECK=false
FORCE=false

MC_ID=""
TKG_ID=""
MGMT_CLUSTERS=""
MC_KUBECONFIG_FILE=""
KUBECTL=""
CURRENT_CLUSTER_NAME=""
CURRENT_CLUSTER_TYPE=""
TEMP_DIR="/tmp/vc_updator"
JOB_SPEC_FILE="job.json"

MC_VCENTER_IP=""

Logf() {
    echo -e "`date '+%Y-%m-%d %H:%M:%S'` [$1] $2"
}
Errorf() { Logf "ERROR" "$@"; }
Warnf() { Logf "WARNING" "$@"; }
Infof() { Logf "INFO" "$@"; }

get_k8s_bootstrapper_svc_ip() {
    KBS_SVC_IP=(`kubectl get svc -n tca-cp-cn k8s-bootstrapper-service | awk '{if (NR!=1) {print $3}}'`)
    Infof "k8s-bootstrapper-service ip address: "${KBS_SVC_IP}
}

get_vc_thumbprint() {
    THUMBPRINT=`openssl s_client -connect $VCENTER_IP:443 < /dev/null 2>/dev/null | openssl x509 -fingerprint -noout -in /dev/stdin | awk -F = '{print $2}'`
    Infof "vCenter $VCENTER_IP Thumbprint: $THUMBPRINT"
}


send_http_request() {
    local method=$1
    local uri=$2
    if [ "${method}" == "POST" ]; then
        curl -s -X ${method} http://${KBS_SVC_IP}:8888/${uri} -d "`cat ${TEMP_DIR}/${JOB_SPEC_FILE}`"
    else
        curl -s -X ${method} http://${KBS_SVC_IP}:8888/${uri}
    fi
    if [ $? -ne 0 ]; then
        echo "Failed to send http request with command ${cmd}, rc $?"
    fi
}

print_job_status() {
    resp=$(send_http_request "GET" "api/v2/jobs/${JOBNAME}")
    if [[ $resp =~ "record not found" ]]; then
        return 1
    elif [[ $resp =~ "Failed" ]]; then
        echo $resp
        exit 1
    fi

    JOBPHASE=(`echo $resp | jq -r .status.state`)
    echo ""
    echo "### Update Vc Thumbprint Job Status"
    echo "Job Name            : `echo $resp | jq -r .metadata.name`"
    echo "Creation Time       : `echo $resp | jq -r .metadata.creationTimestamp`"
    echo "Last Execution Time : `echo $resp | jq -r .status.lastExecutionTimestamp`"
    echo "Phase               : `echo $resp | jq -r .status.state`"
    echo "Progress            : `echo $resp | jq -r '.status.progress //0'`"
    echo "Retry Count         : `echo $resp | jq -r '.status.retryCount //0'`"

    echo "Sub Jobs            :"

    resp=$(send_http_request "GET" "api/v2/jobs/${JOBNAME}/subjobs")
    echo $resp | jq -cr .items[] | while read -r sj;
    do
        jobType=(`echo ${sj} | jq -r .spec.jobType`)
        phase=(`echo ${sj} | jq -r .status.state`)
        lastExecutionTimestamp=(`echo ${sj} | jq -r .status.lastExecutionTimestamp`)
        completionTimestamp=(`echo ${sj} | jq -r .status.completionTimestamp`)
        retryCount=(`echo ${sj} | jq -r '.status.retryCount //0'`)
        reason=`echo "${sj}" | jq -r '.status.reason'`

        printf "\tJob Type            : ${jobType}\n"
        printf "\tPhase               : ${phase}\n"

        if [ "${phase}" != "Succeeded" ]; then
            printf "\tLast Execution Time : ${lastExecutionTimestamp}\n"
            printf "\tRetry Count         : ${retryCount}\n"
            printf "\tReason              : ${reason}\n"
        else
            printf "\tCompletion Time     : ${completionTimestamp}\n"
        fi
        echo ""
    done
}

monitor_job_status() {
    while true; do
        if [ "${JOBPHASE}" == "Succeeded" ]; then
            return
        fi
        echo "Waiting for ${TIMEVAL} seconds to check updating vcenter thumbprint job status"
        sleep ${TIMEVAL}s
        print_job_status
    done
}

post_job() {
    Infof "Post ${JOBNAME} job"
    [ -d ${TEMP_DIR} ] || mkdir -p ${TEMP_DIR}

    read -r -d '' data <<EOF
{
    "metadata": {
        "name": "${JOBNAME}"
    },
    "spec": {
        "jobType": "UpdateVcThumbprint",
        "args": {
            "address": "${VCENTER_IP}"
        }
    }
}
EOF
    echo ${data} | jq > ${TEMP_DIR}/${JOB_SPEC_FILE}
    resp=$(send_http_request "POST" "api/v2/jobs")
    if [[ $resp =~ "Failed" ]]; then
        echo $resp
        exit 1
    fi
    JOBPHASE=""
    echo ${resp}
}

delete_job() {
    resp=$(send_http_request "DELETE" "api/v2/jobs/${JOBNAME}")
    if [[ $resp =~ "Failed" ]]; then
        echo $resp
        exit 1
    fi
}

get_mc_vcenter_ip() {
    resp=$(send_http_request "GET" "api/v1/tkgcontext/${TKG_ID}")
    if [ $? -ne 0 ]; then
        Infof "Failed to get TKG context ${TKG_ID}, rc: $?, resp ${resp}"
        return
    fi
    MC_VCENTER_IP=(`echo $resp | jq -r .vsphere.ip`)
}

update_vcenter_primes() {
    vc_primes=(`${KUBECTL} get vcenterprimes -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_primes}" == "" ]; then
        return 0
    fi
    for item in ${vc_primes[@]}
    do
        server=(`${KUBECTL} get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.server.address}'`)
        if [ "${server}" != ${VCENTER_IP} ]; then
            Infof "vCenterPrime ${item} belongs to vCenter ${server}, skip."
            continue
        fi
        tp=(`${KUBECTL} get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.subConfig.thumbprint}'`)
        if [ "${tp}" != "${THUMBPRINT}" ]; then
            ${KUBECTL} patch vcenterprimes -n tca-system ${item} -p '{"spec": {"subConfig": {"thumbprint": "'${THUMBPRINT}'"}}}' --type=merge
            Infof "Patched vCenterPrime ${item}, res: $?"
        else
            Infof "vCenterPrime ${item}/${server}'s thumbprint is unchanged."
        fi
    done
}

update_vcenter_subs() {
    vc_subs=(`${KUBECTL} get vcentersubs -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_subs}" == "" ]; then
        return 0
    fi
    for item in ${vc_subs[@]}
    do
        server=(`${KUBECTL} get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.server.address}'`)
        if [ "${server}" != ${VCENTER_IP} ]; then
            Infof "vCenterSub ${item} belongs to vCenter ${server}, skip."
            continue
        fi
        tp=(`${KUBECTL} get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.subConfig.thumbprint}'`)
        if [ "${tp}" != "${THUMBPRINT}" ]; then
            ${KUBECTL} patch vcentersubs -n tca-system ${item} -p '{"spec": {"subConfig": {"thumbprint": "'${THUMBPRINT}'"}}}' --type=merge
            Infof "Patched vCenterSub ${item}, res: $?"
        else
            Infof "vCenterSub ${item}/${server}'s thumbprint is unchanged."
        fi
    done
}

# scan the mcs to check whether it has vcprime/vcsub to update
scan_and_update_mc_vcthumbprint() {
    Infof "Management Cluster ${CURRENT_CLUSTER_NAME} is not located at ${VCENTER_IP}, scan it for any vCenterPrime/vCenterSub required to be updated ..."
    dump_mc_kubeconfig
    if [ "${KUBECTL}" == "" ]; then
        return
    fi
    update_vcenter_primes
    update_vcenter_subs
    Infof "Scanning Management Cluster ${CURRENT_CLUSTER_NAME} is completed."
}

update_clusters_vcthumbprint() {
    Infof "Updating tkg clusters associated ${VCENTER_IP} thumbprint with ${THUMBPRINT}"
    get_management_clusters
    job_required=0

    #for mc in ${MGMT_CLUSTERS[@]}
    while IFS= read -r mc
    do
        CURRENT_CLUSTER_NAME=(`echo ${mc} | jq -r .clusterName`)
        TKG_ID=(`echo ${mc} | jq -r .tkgID`)
        MC_ID=(`echo ${mc} | jq -r .id`)
        get_mc_vcenter_ip
        if [ "$MC_VCENTER_IP" == "${VCENTER_IP}" ]; then
            job_required=1
            continue
        fi
        scan_and_update_mc_vcthumbprint
    done <<< $(echo ${MGMT_CLUSTERS} | jq -c .[])

    if [ $job_required -eq 1 ]; then
        update_cluster_vcthumbprint_with_job
    fi
}

update_cluster_vcthumbprint_with_job() {
    # check existing job
    JOBNAME="UpdateClustersVcThumbprintFor-"${VCENTER_IP}
    Infof "Checking Existing Job ${JOBNAME} Status"
    print_job_status

    if [ $? -ne 0 ]; then
        post_job
    elif ${FORCE}; then
        Infof "FORCE option is set, delete existing job and post new one"
        delete_job
        while true; do
            sleep 3s
            Infof "Checking existing job deletion status"
            resp=$(send_http_request "GET" "api/v2/jobs/${JOBNAME}")
            if [[ $resp =~ "record not found" ]]; then
                break
            elif [[ $resp =~ "Failed" ]]; then
                echo $resp
                exit 1
            fi
        done
        post_job
    fi

    monitor_job_status
    if ${VERBOSE}; then
        check_cluster_resources_vcthumbprint
    fi
    Infof "Job ${JOBNAME} has been completed, delete the job"
    delete_job
}

get_management_clusters() {
    resp=$(send_http_request "GET" "api/v1/managementclusters")
    if [ $? -ne 0 ]; then
        Errorf "Failed to get all management clusters, rc: $?, resp ${resp}"
    fi
    #MGMT_CLUSTERS=(`echo ${resp} | jq -c .[]`)
    MGMT_CLUSTERS=${resp}
}

is_matched() {
    if [ "$1" == "$2" ]; then
        echo "Matched"
    else
        echo "Mismatched"
    fi
}

print_tp_with_two_indents() {
    printf "\t\tThumbprint        : %-32s %12s.\n" ${tp} $(is_matched "${tp}" "${THUMBPRINT}")
}

print_tp_with_three_indents() {
    printf "\t\t\tThumbprint        : %-32s %12s.\n" ${tp} $(is_matched "${tp}" "${THUMBPRINT}")
}


dump_mc_kubeconfig() {
    [ -d ${TEMP_DIR} ] || mkdir -p ${TEMP_DIR}
    KUBECTL=""
    MC_KUBECONFIG_FILE="${TEMP_DIR}/${MC_ID}.kc"
    send_http_request "GET" "api/v1/managementcluster/${MC_ID}/kubeconfig" > ${MC_KUBECONFIG_FILE}
    if [ $? -ne 0 ]; then
        printf "\t\tFailed to get management cluster ${MC_ID}'s kubeconfig, rc: $?\n"
        return
    fi
    KUBECTL="kubectl --kubeconfig ${MC_KUBECONFIG_FILE}"
}


check_vcenter_primes() {
    vc_primes=(`${KUBECTL} get vcenterprimes -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_primes}" == "" ]; then
        return 0
    fi
    for item in ${vc_primes[@]}
    do
        server=(`${KUBECTL} get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.server.address}'`)
        if [ "${server}" != ${VCENTER_IP} ]; then
            continue
        fi
        tp=(`${KUBECTL} get vcenterprimes -n tca-system ${item} -o jsonpath='{.spec.subConfig.thumbprint}'`)
        if [ "${tp}" != "" ]; then
            printf "\tTKO VCenter Prime Secrets :\n"
            printf "\t\t${item}/tca-system :\n"
            print_tp_with_three_indents
        fi
    done
}

check_vcenter_subs() {
    vc_subs=(`${KUBECTL} get vcentersubs -n tca-system -o jsonpath='{.items[*].metadata.name}'`)
    if [ $? -ne 0 ] || [ "${vc_subs}" == "" ]; then
        return 0
    fi
    for item in ${vc_subs[@]}
    do
        server=(`${KUBECTL} get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.server.address}'`)
        if [ "${server}" != ${VCENTER_IP} ]; then
            continue
        fi
        tp=(`${KUBECTL} get vcentersubs -n tca-system ${item} -o jsonpath='{.spec.subConfig.thumbprint}'`)
        if [ "${tp}" != "" ]; then
            printf "\tTKO VCenter Sub Secrets :\n"
            printf "\t\t${item}/tca-system :\n"
            print_tp_with_three_indents
        fi
    done
}

check_csi_secret() {
    namespace=$1
    if [ ${CURRENT_CLUSTER_TYPE} == "legacy" ]; then
        secret_name="${CURRENT_CLUSTER_NAME}-vsphere-csi-addon"
    else
        secret_name="${CURRENT_CLUSTER_NAME}-vsphere-csi-data-values"
    fi
    tp=(`${KUBECTL} get secret ${secret_name} -n ${namespace} -o jsonpath='{.data.values\.yaml}' 2>/dev/null | base64 -d | grep 'tlsThumbprint'  | awk '{if(length($2)>2) print $2;}'`)
    # If secret not found or tp not found in secret, return 0
    if [ $? -ne 0 ]; then
        return 0
    fi
    if [ "${tp}" != "" ]; then
        printf "\tTKG VSphere CSI Secret    :\n"
        print_tp_with_two_indents
    fi
}

check_cpi_secret() {
    namespace=$1
    if [ ${CURRENT_CLUSTER_TYPE} == "legacy" ]; then
        secret_name="${CURRENT_CLUSTER_NAME}-vsphere-cpi-addon"
    else
        secret_name="${CURRENT_CLUSTER_NAME}-vsphere-cpi-data-values"
    fi
    tp=(`${KUBECTL} get secret ${secret_name} -n ${namespace} -o jsonpath='{.data.values\.yaml}' 2>/dev/null | base64 -d | grep 'tlsThumbprint'  | awk '{if(length($2)>2) print $2;}'`)
    # If secret not found or tp not found in secret, return 0
    if [ $? -ne 0 ]; then
        return 0
    fi

    if [ "${tp}" != "" ]; then
        printf "\tTKG VSphere CPI Secret    :\n"
        print_tp_with_two_indents
    fi
}

check_vspherecluser() {
    namespace=$1
    if [ ${CURRENT_CLUSTER_TYPE} == "legacy" ]; then
        name=$namespace
    else
        name="${CURRENT_CLUSTER_NAME}-vsphere-cpi-data-values"
    fi
    tp=(`${KUBECTL} get vspherevm ${secret_name} -n ${namespace} -o jsonpath='{.data.values\.yaml}' 2>/dev/null | base64 -d | grep 'tlsThumbprint'  | awk '{if(length($2)>2) print $2;}'`)
    # If secret not found or tp not found in secret, return 0
    if [ $? -ne 0 ]; then
        return 0
    fi
    print_tp_with_two_indents
}

check_cluster_type() {
    if [ "$1" == "" ]; then
        namespace=${CURRENT_CLUSTER_NAME}
    else
        namespace=$1
    fi
    CURRENT_CLUSTER_TYPE="legacy"
    res=(`${KUBECTL} get cluster -n ${namespace} ${CURRENT_CLUSTER_NAME} -o jsonpath='{.metadata.labels}' | grep 'topology.cluster.x-k8s.io/owned'`)
    if [ "${res}" != "" ]; then
        CURRENT_CLUSTER_TYPE="classy"
    fi
}

check_workload_clusters() {
    wc_clusters=(`${KUBECTL} get clusters -A -o json | jq -r '.items[] | select(.metadata.namespace != "tkg-system") | .metadata.name'`)
    if [ ${#wc_clusters[@]} -eq 0 ]; then
        return
    fi

    printf "Workload Clusters         :\n"

    for cluster in ${wc_clusters[@]}
    do
        CURRENT_CLUSTER_NAME=${cluster}
        check_cluster_type
        printf "\tCluster Name              : ${CURRENT_CLUSTER_NAME}\n"
        printf "\tCluster Type              : ${CURRENT_CLUSTER_TYPE}\n"
        check_csi_secret "${CURRENT_CLUSTER_NAME}"
        check_cpi_secret "${CURRENT_CLUSTER_NAME}"
        echo ""
        # Add sleep to avoid occupying so much resources
        sleep 1
    done
}

check_cluster_resources_vcthumbprint() {
    # Check Management Clusters Resources
    get_management_clusters
    #for mc in ${MGMT_CLUSTERS[@]}
    echo ${MGMT_CLUSTERS} | jq -c .[] | while IFS= read -r mc
    do
        CURRENT_CLUSTER_NAME=(`echo ${mc} | jq -r .clusterName`)
        TKG_ID=(`echo ${mc} | jq -r .tkgID`)
        MC_ID=(`echo ${mc} | jq -r .id`)

        echo ""
        echo "Management Cluster ${CURRENT_CLUSTER_NAME}"

        dump_mc_kubeconfig
        if [ "${KUBECTL}" == "" ]; then
            continue
        fi
        check_cluster_type "tkg-system"
        printf "\tCluster Type              : ${CURRENT_CLUSTER_TYPE}\n"
        check_vcenter_primes
        check_vcenter_subs
        check_csi_secret "tkg-system"
        check_cpi_secret "tkg-system"
        check_workload_clusters
    done
}


usage() {
    echo -e "This script is used to update VC thumbprint for management clusters and workload clusters. It should only be ran on TCA-CP admin user directly. Supported TCA version is 3.0.0 or higher"
    echo -e "\nUsage:\n   `basename $0` [option...]"
    echo -e "\nOptions:"
    echo "  -d, --vc                     vCenter Server Address. Should be FQDN/IP."
    echo "  -c, --check                  Check whether cluster resources are updated."
    echo "  -F, --force                  Force applying the config instead of waiting for existing updating job completed."
    echo "  -v, --verbose                Run script in verbose mode."
    echo "  -V, --version                Show current script version."
}

main() {
    if [ "${VCENTER_IP}" == "" ]; then
        echo "vCenter Server Address is missing, please specify with -d or --vc."
        usage
        exit 1
    fi
    get_vc_thumbprint
    get_k8s_bootstrapper_svc_ip
    if ${CHECK}; then
        check_cluster_resources_vcthumbprint
    else
        update_clusters_vcthumbprint
    fi

    Infof "VC thumbprint update process is completed."
    [ ! -d ${TEMP_DIR} ] || rm -r ${TEMP_DIR}
}

while [[ $# -gt 0 ]]; do
    case $1 in
        '--vc'|-d)
        VCENTER_IP=$2
        shift
        shift
        ;;
        '--check'|-c)
        CHECK=true
        shift
        ;;
        '--version'|-V)
        echo ${VERSION}
        exit 0
        ;;
        '--verbose'|-v)
        VERBOSE=true
        shift
        ;;
        '--force'|-F)
        FORCE=true
        shift
        ;;
        '--help'|-h)
        usage
        exit 0
        ;;
        *)
        break
        ;;
    esac
done
set +u
set +e
set -o pipefail
main
exit $?