!/bin/bash

satelliteHost=rncc-satellite-wlfdle.cc.net.rogers.com
activationKey=ak-prod-os-rhel-8-latest
rhelVersion=8
proxyHost=rncc-proxy-min.mgslb.net.rogers.com
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
