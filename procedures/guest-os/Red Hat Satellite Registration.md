# Red Hat Satellite Registration

Most issues with fetching pacakges can be resolved by re-registering the host with Satellite.

This page documents the procedure to register (or re-register) your RHEL host (VM or Bare Metal) with Red Hat Satellite in lab and production.

* All commands below must be run as root user.
* For RHEL6 and older, please contact us for support.
* For RHEL7, please note that only the latest packages are supported (RHEL 7.9)

## Production

* RHEL 9 Latest (for RHEL hosts not locked to specific 9.x version):

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel9-latest-prod.sh | bash
```

* RHEL 9 Extended Update Support (for RHEL hosts locked to specific 9.x version):

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel9-eus-prod.sh | bash
```

* RHEL 8 Latest (for RHEL hosts not locked to specific 8.x version):

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel8-latest-prod.sh | bash
```

* RHEL 8 Extended Update Support (for RHEL hosts locked to specific 8.x version):

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel8-eus-prod.sh | bash
```

* RHEL 7 Latest (for RHEL hosts not locked to specific 7.x version):

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel7-latest-prod.sh | bash
```

## Lab

* RHEL 9 Latest (for RHEL hosts not locked to specific 9.x version):

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel9-latest-lab.sh | bash
```

* RHEL 9 Extended Update Support (for RHEL hosts locked to specific 9.x version):

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel9-eus-lab.sh | bash
```

* RHEL 8 Latest (for RHEL hosts not locked to specific 8.x version):

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel8-latest-lab.sh | bash
```

* RHEL 8 Extended Update Support (for RHEL hosts locked to specific 8.x version):

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel8-eus-lab.sh | bash
```

* RHEL 7 Latest (for RHEL hosts not locked to specific 7.x version):

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel7-latest-lab.sh | bash
```
