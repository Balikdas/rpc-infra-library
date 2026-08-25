#!/bin/bash

satelliteHost=rncc-satellite-south.cc.vf.rogers.com
activationKey=ak-lab-os-rhel-7-latest
rhelVersion=7Server

subscription-manager unregister
subscription-manager clean
yum clean all
rm -rf /etc/rhsm/facts/uuid.facts
rm -rf /etc/sysconfig/systemid
rm -rf /var/cache/yum/*
yum erase katello-* -y
rpm -e `rpm -qva | grep katello`
curl -kO https://${satelliteHost}/pub/katello-ca-consumer-latest.noarch.rpm
rpm -Uvh katello-ca-consumer-latest.noarch.rpm
subscription-manager register --org="Rogers_Network" --activationkey=${activationKey} --release ${rhelVersion} --force
