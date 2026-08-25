#!/bin/bash

# This script will provision sudo groups in /etc/sudoers.d on RHEL.
# It takes a list of groups to provision for sudo access as arguments.

# Check args

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 {ad_group1} [ad_groupN] ..."
  exit 1
fi

echo 'Starting RHEL8 AD User sudo provisioning...'

# All commands must be executed as root
user=`whoami`
if [[ ${user} -ne 'root' ]]; then
  echo "This script MUST be run as root. Terminating"
  exit 1
fi

# Backup config to /var/tmp/ad_sudo_provision/
date=`date +%Y%m%d`
backupdir=/var/tmp/ad_sudo_provision/_${date}/backup
mkdir -p ${backupdir}
cp -ax /etc/sudoers ${backupdir}/
cp -p /etc/sudoers.d/* ${backupdir}/

# Create sudoers config files per group
for i in "$@"; do
   group=`echo ${i} | sed 's| |\\\ |g'`
   file=`echo ${i} | sed 's| |\\ |g'`
   echo "%${group}  ALL=(ALL)       ALL" > /etc/sudoers.d/"${file}"
done

# Done
echo "Finished provisioning sudo users"