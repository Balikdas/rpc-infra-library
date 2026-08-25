#!/bin/bash

# Uncomment one of the configuration sections below and set the correct rhelVersion.
# Proxy should not be required if eFCR has been implemented to allow connection from
# SDE networks to Satellite server in MIN. Note that DNS integration is required.

# Lab Config
#satelliteHost=rncc-satellite-south.cc.vf.rogers.com
#activationKey=ak-lab-os-rhel-7-latest
#rhelVersion=7Server
#useProxy=false
#proxyHost=rncc-proxy-min.mgslb.vf.rogers.com
#proxyPort=80

# Prod Config
#satelliteHost=rncc-satellite-wlfdle.cc.net.rogers.com
#activationKey=ak-prod-os-rhel-7-latest
#rhelVersion=7Server
#useProxy=false
#proxyHost=rncc-proxy-min.mgslb.net.rogers.com
#proxyPort=80

if [[ $useProxy == "true" ]]; then
  subscription-manager unregister
  subscription-manager clean
  yum clean all
  rm -rf /etc/rhsm/facts/uuid.facts
  rm -rf /etc/sysconfig/systemid
  rm -rf /var/cache/yum/*
  yum erase katello-* -y
  rpm -e `rpm -qva | grep katello`
  curl -O --proxy ${proxyHost}:${proxyPort} https://${satelliteHost}/pub/katello-ca-consumer-latest.noarch.rpm
  rpm -Uvh katello-ca-consumer-latest.noarch.rpm
  subscription-manager register --org="Rogers_Network" --activationkey=${activationKey} --proxy ${proxyHost}:${proxyPort} --release ${rhelVersion}

else
 
  subscription-manager unregister
  subscription-manager clean
  yum clean all
  rm -rf /etc/rhsm/facts/uuid.facts
  rm -rf /etc/sysconfig/systemid
  rm -rf /var/cache/yum/*
  yum erase katello-* -y
  rpm -e `rpm -qva | grep katello`
  curl -O --insecure https://${satelliteHost}/pub/katello-ca-consumer-latest.noarch.rpm
  rpm -Uvh katello-ca-consumer-latest.noarch.rpm
  subscription-manager register --org="Rogers_Network" --activationkey=${activationKey} --release ${rhelVersion}

fi