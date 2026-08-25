#!/bin/bash

# This script will integrate a RHEL8 host with Rogers Active Directory. Note that 
# RHEL Satellite and DNS integration is a prerequisite. Uncomment one of the
# configuration sections below depending on your environment (lab or prod) and
# populate the adserviceacctpw variable with the actual password. Be sure to 
# remove the script from the server after the integration is completed so that the
# AD service account password is not exposed.

# AD service account
adserviceacct="rnccadmin"
adserviceacctpw="xxxxxxxx"

# Prod configuration
#ad_realm="oss.rogers.com"
#krb_realm="OSS.ROGERS.COM"
#ad_servers="ad1-to3.oss.rogers.com, ad1-wfd.oss.rogers.com, ad1-to5.oss.rogers.com"

# Lab configuration
#ad_realm="oss.vf.rogers.com"
#krb_realm="OSS.VF.ROGERS.COM"
#ad_servers="sv-ad01-rnoc-s.oss.vf.rogers.com, sv-ad01-rnoc-n.oss.vf.rogers.com"

##################################################################

# Check args

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 {ad_group1} [ad_groupN] ..."
  exit 1
fi
ad_groups=`echo $@ | sed 's/ /, /g'`

echo 'Starting RHEL9 AD integration...'

# This procedure only for RHEL9
grep 'Red Hat Enterprise Linux release 9' /etc/redhat-release
if [[ $? -ne 0 ]]; then
  echo "This script is only for RHEL 9.x. Terminating"
  exit 1
fi

# All commands must be executed as root
user=`whoami`
if [[ ${user} -ne 'root' ]]; then
  echo "This script MUST be run as root. Terminating"
  exit 1
fi

# Backup config to /var/tmp/ad_migration/
date=`date +%Y%m%d`
backupdir=/var/tmp/ad_migration_${date}/backup
mkdir -p ${backupdir}
cp -ax /etc/sssd/* ${backupdir}/
cp -p /etc/hosts ${backupdir}/
cp -p /etc/krb5.conf ${backupdir}/
cp -p /etc/krb5.keytab ${backupdir}/

# Remove existing configs
rm -rf /etc/sssd/*
rm -rf /etc/krb5.keytab

# Install packages
dnf install -y realmd adcli sssd sssd-ad samba-common-tools krb5-workstation oddjob oddjob-mkhomedir authselect
if [[ $? -ne 0 ]]; then
  echo "Package installation failed. Check Satellite integration status. Terminating"
  exit 1
fi

# Join domain
mkdir -p /var/log/sssd
hostname=`hostname -s`

# If hostname is more than 15 chars hash it and trim to 15
if [[ ${#hostname} -gt 15 ]]; then
  hostnamehash=`echo ${hostname} | sha256sum | sed 's/^\(.\{8\}\).*$/\1/'`
  hostnamefirst7=`echo ${hostname} | sed 's/^\(.\{7\}\).*$/\1/'`
  hostname="${hostnamefirst7}${hostnamehash}"
fi

# Join the domain
realm leave ${ad_realm}
realm discover ${ad_realm}
echo ${adserviceacctpw} | adcli --verbose join -U ${adserviceacct} --stdin-password -N ${hostname} -H ${hostname}.${ad_domain} --user-principal=${hostname}/${hostname}@${krb_realm} ${ad_realm}
nbname=`echo ${hostname^^}`
echo "[sssd]
domains = ${ad_realm}
config_file_version = 2
services = nss, pam

[nss]
debug_level = 3
filter_groups = root
filter_users = root

[pam]
debug_level = 3
reconnection_retries = 3
offline_credentials_expiration = 2
offline_failed_login_attempts = 3
offline_failed_login_delay = 5

[autofs]

[domain/${ad_realm}]
debug_level = 3
id_provider = ad
access_provider = simple
dyndns_update = False
ad_server = ${ad_servers}
ad_domain = ${ad_realm}
krb5_realm = ${krb_realm}
krb5_store_password_if_offline = True
realmd_tags = manages-system joined-with-adcli
ldap_sasl_authid = ${nbname}\$
ldap_id_mapping = True
ignore_group_members = True
cache_credentials = True
use_fully_qualified_names = False
default_shell = /bin/bash
fallback_homedir = /home/%u
simple_allow_groups = ${ad_groups}" > /etc/sssd/sssd.conf

# Cleanup sssd db cache
systemctl stop sssd
rm -rf /var/lib/sss/db/*

# Set authselect profile
authselect select sssd with-mkhomedir --force

# Set ownership and restart sssd
chown root:root /etc/sssd/sssd.conf
chmod og-rwx /etc/sssd/sssd.conf
chmod a+r /etc/krb5.conf
systemctl enable sssd
systemctl start sssd
systemctl enable oddjobd
systemctl start oddjobd

# Fix home dir permissions
ls -1 /home | while read line; do uid=`getent passwd ${line} | cut -d: -f3`; gid=`getent passwd ${line} | cut -d: -f4`; if [[ -n $gid && -n $uid ]]; then chown -R $uid:$gid /home/${line}; fi; done
