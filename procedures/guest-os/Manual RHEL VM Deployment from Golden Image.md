# Manual RHEL VM Deployment from Golden Image

This procedure outlines the steps to deploy a VM from the golden images but without the use of VRA. This is useful for testing purposes or for deploying additional VMs in clusters that are not linked to VRA.

## Deployment Steps

* Deploy the VM from the `VRA Images` content library in vCenter
* Boot the VM and configure the hostname:

```bash
hostnamectl set-hostname ${vm_hostname}
```

* Configure the VM networking using NetworkManager CLI (`nmcli`):

```bash
nmcli con mod ens192 ipv4.method manual ipv4.adress ${ipv4_address}/{$netmask} ipv4.gateway ${ipv4_gateway} ipv4.dns ${ipv4_dns_server}
nmcli con up ens192
```

* Regenerate the ssh host keys:

```bash
rm -rf /etc/ssh/ssh_host*
ssh-keygen -A
systemctl restart sshd
```

* Temporarily allow root login via ssh:

```bash
sed -i 's/PermitRootLogin no/PermitRootLogin yes/g' /etc/ssh/sshd_config
systemctl restart sshd
```

* Set the root password:

```bash
passwd root
```

* Login as root user via SSH
* Integrate to RHEL Satellite using the procedure located here: <https://reqcentral.com/wiki/spaces/RPCIA/pages/804231902/Red+Hat+Satellite+Registration>
* Update software packages:

```bash
dnf -y update
```

* Install Crowdstrike Falcon using the procedure located here: <https://reqcentral.com/wiki/spaces/RPCIA/pages/639719944/Install+Crowdstrike+Falcon+on+RHEL>
* Configure NTP server (list of NTP servers can be found here: <https://reqcentral.com/wiki/spaces/RPCIA/pages/796694256/NTP+servers>)

```bash
echo "server ${ntp_ip}" >> /etc/chrony.conf
systemctl restart chronyd
```

* Integrate the VM with Active Directory and setup sudo, using the scripts located here: <https://github.com/RogersCommunications/rpc-infra-library/tree/main/scripts/active_directory>
* Disable the VRA account:

``` bash
passwd -l vra
```

* Disable root login via SSH:

```bash
sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config
systemctl restart sshd
```

* Reboot the VM

```bash
reboot
```
