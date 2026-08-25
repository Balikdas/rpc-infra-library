# Crowdstrike Falcon Install on Ubuntu Hosts

This procedure outlines how to install the Crowdstrike Falcon Sensor on Ubuntu.

## Installation Procedure

- Download the CS Falcon binaries from the ICSU SharePoint site:

<https://rcirogers.sharepoint.com/:f:/r/sites/Information-Security/Security%20Operations/CSTM/Public%20Documents/Projects/CrowdStrike/Linux/Ubuntu?csf=1&web=1&e=PEIiZv>

- Install the CS Falcon binaries from the ICSU Sharepoint:

```bash
dpkg -i ${falcon_sensor_deb_file}
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
