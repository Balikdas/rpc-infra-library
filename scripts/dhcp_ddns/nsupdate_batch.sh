#!/bin/bash
#
# A wrapper script to run batch operations against nsupdate.sh

# Config
nsupdate="/root/nsupdate.sh"     # Path to the nsupdate.sh script

# Input vars from args
operation=$1
hosts=$2
rrtype=$3

usage () {
  echo "Usage: $0 {operation} {hosts_file} {rrtype}"
  echo "operation: {add|delete}"
  echo "hosts_file: {path_to_file}"
  echo "rrtype: {dns_rr_type}"
  echo "{hosts_file} is a space delimited file in the format: {hostname} {ip}"
  echo "example: $0 add hosts A"
  exit 1
}

if [[ $# -ne 3 ]]; then
  echo "ERROR: Incorrect number of arguments"
  usage
fi

if [[ ${operation} != "add" ]] && [[ ${operation} != "delete" ]]; then
  echo "ERROR: Invalid operation. Supported operations: add delete"
  usage
fi

if [[ ! -f $hosts ]]; then
  echo "ERROR: hosts_file $hosts does not exist"
  usage
fi

if [[ ${rrtype} != "A" ]] && [[ ${rrtype} != "AAAA" ]] && [[ ${rrtype} != "PTR" ]]; then
  echo "ERROR: Unsupported RR type. Supported types: A AAAA PTR"
  usage
fi

if [[ $rrtype == "A" ]] || [[ $rrtype == "AAAA" ]]; then
    cat $hosts | while read line; do
        host=`echo $line | awk '{print $1}'`
        ip=`echo $line | awk '{print $2}'`
        $nsupdate $operation $host $rrtype $ip
    done
fi

if [[ $rrtype == "PTR" ]]; then
    cat $hosts | while read line; do
        host=`echo $line | awk '{print $1}'`
        ip=`echo $line | awk '{print $2}'`
        rev1=`echo $ip | cut -d. -f4`
        rev2=`echo $ip | cut -d. -f3`
        rev3=`echo $ip | cut -d. -f2`
        rev4=`echo $ip | cut -d. -f1`
        $nsupdate $operation $rev1.$rev2.$rev3.$rev4.in-addr.arpa $rrtype $host.
    done
fi
