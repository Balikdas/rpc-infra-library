# Integrate Linux Hosts with OSS-AD

This page documents the procedure to register (or re-register) your RHEL or Ubuntu host (VM or Bare Metal) with OSS-AD.

* All commands below must be run as root user.
* For RHEL6 and older, please contact us for support.

**Note: It may require to configure a proxy to access the URLs below.**

* Production Proxy:

```bash
export https_proxy=http://rncc-proxy-min.mgslb.net.rogers.com:80/
```

* Lab Proxy:

```bash
export https_proxy=http://rncc-proxy-min.mgslb.vf.rogers.com:80/
```

## Production

* RHEL 9:

```bash
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/rhel9_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* RHEL 8:

```bash
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/rhel8_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* RHEL 7:

```bash
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/rhel7_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* Ubuntu24:

```bash
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/ubuntu24_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-wlfdle.cc.net.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

## Lab

* RHEL 9:

```bash
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/rhel9_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* RHEL 8:

```bash
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/rhel8_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* RHEL 7:

```bash
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/rhel7_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```

* Ubuntu24:

```bash
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/ubuntu24_ad_integration.sh | bash -s -- ${space separated list of login groups}
curl -k https://rncc-web01-south.cc.vf.rogers.com/pub/scripts/ad/ad_sudo_provisioning.sh | bash -s -- ${space separated list of admin groups}
```
