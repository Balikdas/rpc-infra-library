#!/bin/bash

satelliteHost=rncc-satellite-south.cc.vf.rogers.com
activationKey=ak-lab-os-rhel-9-eus
rhelVersion=`grep VERSION_ID /etc/os-release | awk -F\" '{print $2}'`
proxyHost=rncc-proxy-min.mgslb.vf.rogers.com
proxyPort=80

subscription-manager unregister
subscription-manager clean
dnf clean all
rm -rf /etc/rhsm/facts/uuid.facts
rm -rf /etc/sysconfig/systemid
rm -rf /var/cache/dnf/*
dnf erase katello-* -y
rpm -e `rpm -qva | grep katello`
curl -kO --proxy ${proxyHost}:${proxyPort} https://${satelliteHost}/pub/katello-ca-consumer-latest.noarch.rpm
rpm -Uvh katello-ca-consumer-latest.noarch.rpm
subscription-manager register --org="Rogers_Network" --activationkey=${activationKey} --release ${rhelVersion}
