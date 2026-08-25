#!/bin/bash

# Config
ttl=3600
server_fwd=172.30.14.9
server_rev=172.30.14.12

# Input vars from args
command=$1
fqdn=$2
type=$3
data=$4

usage () {
  echo "Usage: $0 {command} {fqdn} {type} {data}"
  echo "command: {add|delete}"
  echo "fqdn: {dns_fqdn}"
  echo "type: {dns_rr_type}"
  echo "data: {dns_data}"
  echo "example: $0 add bob.foo.com A 192.168.10.1"
  exit 1
}

if [[ $# -ne 4 ]]; then
  echo "ERROR: Incorrect number of arguments"
  usage
fi

if [[ ${command} != "add" ]] && [[ ${command} != "delete" ]]; then
  echo "ERROR: Invalid command. Supported commands: add delete"
  usage
fi

if [[ ${type} != "A" ]] && [[ ${type} != "AAAA" ]] && [[ ${type} != "PTR" ]]; then
  echo "ERROR: Unsupported RR type. Supported types: A AAAA PTR"
  usage
fi

# Config
ttl=3600
if [[ $type == "PTR" ]]; then
  server=$server_rev
else
  server=$server_fwd
fi

# Run nsupdate
nsupdate <<EOF
server ${server}
update ${command} ${fqdn} ${ttl} ${type} ${data}
show
send
answer
EOF
