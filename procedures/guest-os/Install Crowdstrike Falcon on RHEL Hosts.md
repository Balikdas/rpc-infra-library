# Crowdstrike Falcon Install on RHEL Hosts

This procedure outlines how to install the Crowdstrike Falcon Sensor on RHEL.

**Note**: Prerequisite is for the RHEL host to be integrated with RHEL Satellite.

## Installation Procedure

- Install the CS Falcon binaries from RHEL Satellite:

```bash
dnf -y install falcon-sensor
```

- Configure the CS Falcon with Customer ID and Proxy:

```bash
/opt/CrowdStrike/falconctl -s --cid=DC6E92F373F54834A292E1BDF07F85D5-B2
/opt/CrowdStrike/falconctl -s --aph='rncc-proxy-min.mgslb.net.rogers.com' --app='80'
systemctl enable falcon-sensor --now
```

- Reboot the VM

```bash
reboot
```

- Once the VM is rebooted, verify the running install is functional and RFM state is `false`:

```bash
systemctl status falcon-sensor
journalctl -u falcon-sensor
/opt/CrowdStrike/falconctl -g --rfm-state
```
