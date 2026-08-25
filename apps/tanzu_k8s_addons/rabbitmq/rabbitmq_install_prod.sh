tanzu plugin install package
tanzu package repository add rabbitmqrepo --url harbor.cc.net.rogers.com/library/tanzu-rabbitmq-package-repo:1.4.0
tanzu package install rabbitmq -p rabbitmq.tanzu.vmware.com -v 1.4.0

