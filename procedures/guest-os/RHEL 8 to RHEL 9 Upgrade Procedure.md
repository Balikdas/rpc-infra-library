# RHEL 8.x Upgrade to RHEL9 Procedure

## Step 1: Reintegrate to Satellite and update to 8.10

```bash
curl -k https://rncc-satellite-wlfdle.cc.net.rogers.com/pub/rhel8-latest-prod.sh | bash
dnf -y update && reboot
```

## Step 2: Prepare and upgrade to RHEL 9.6 EUS

```bash
dnf -y install leapp-upgrade vdo
dnf -y remove falcon-sensor valgrind valgrind-gdb valgrind-scripts valgrind-devel valgrind-docs
dnf -y remove --oldinstallonly
leapp answer --section check_vdo.confirm=True
sed -i s/^AllowZoneDrifting=.*/AllowZoneDrifting=no/ /etc/firewalld/firewalld.conf
leapp upgrade --target 9.6 --channel eus && reboot
```

## Step 3: Reinstall CS Falcon and remove old kernels

```bash
dnf -y install falcon-sensor
/opt/CrowdStrike/falconctl -s --cid=DC6E92F373F54834A292E1BDF07F85D5-B2 -f
/opt/CrowdStrike/falconctl -s --aph='rncc-proxy-min.mgslb.net.rogers.com' --app='80' -f
systemctl enable falcon-sensor --now
dnf -y remove --oldinstallonly
```
