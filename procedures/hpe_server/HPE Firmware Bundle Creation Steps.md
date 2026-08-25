# How to Create an HPE Firmware Bundle

This document provides the steps required to create a firmware bundle for booting from UEFI HTTP boot to automate firmware upgrades on HPE DL380/360 servers.

## High Level Steps

* Download the BaseOS (latest RHEL release)
* Download the firmware images (SPP ISO + any third party firmware eg. Intel FW)
* Build the template VM for the BaseOS
* Extract the BaseOS contents to the build directory
* Copy the firmware to the build directory
* Generate the build image
* Testing the image
* Cleanup

## Environment Setup

The following environment setup is required. This is required to be run on a RHEL system (the commands below work on the bootstrap servers).

* Configure bootstrap server to support nested virtualization

```bash
echo 'options kvm_intel nested=1' > /etc/modprobe.d/kvm.conf
modprobe -r kvm_intel
modprobe kvm_intel nested=1
```

* Enable GuestOS virtualization on bootstrap server (in vCenter, under CPU settings)
* Install virtualization packages on bootstrap server

```bash
dnf -y update
dnf -y groupinstall "Virtualization Platform"
dnf -y install qemu-kvm virt-install edk2-ovmf iptables squashfs-tools-ng
systemctl enable --now libvirtd
```

* Disable firewalld

```bash
systemctl disable firewalld
systemctl mask firewalld
```

## Cleanup Previous Builds

Remove any existing data from previous builds.

* Remove the RHEL VM

```bash
virsh destroy rpc-firmware-bundle
virsh undefine rpc-firmware-bundle --nvram
rm -rf /images/rpc-firmware-bundle-build/workdir/rpc-firmware-bundle.img
rm -rf /images/rpc-firmware-bundle-build/workdir/rhel.iso
rm -rf /images/rpc-firmware-bundle-build/workdir/kickstart.cfg
rm -rf /var/www/html/static
```

* Unmount filesystems no longer needed

```bash
umount /images/rpc-firmware-bundle-build/baseos/boot/efi
umount /images/rpc-firmware-bundle-build/baseos/boot
umount /images/rpc-firmware-bundle-build/baseos
umount /images/rpc-firmware-bundle-build/firmware/isomnt
vgchange -an rhel
losetup -d /dev/loop0
```

* Remove files from build folder

```bash
rm -rf /images/rpc-firmware-bundle-build/baseos/*
rm -rf /images/rpc-firmware-bundle-build/firmware/*
rm -rf /images/rpc-firmware-bundle-build/workdir/*
rm -rf /images/rpc-firmware-bundle-build/output/*
```

## Create Build Directory Structure

* Create the build folder structure

```bash
mkdir -m 755 -p /images/rpc-firmware-bundle-build
cd /images/rpc-firmware-bundle-build
mkdir -m 755 baseos firmware output workdir
mkdir -m 755 firmware/isomnt
```

## Download BaseOS and Firmware

* Download the BaseOS ISO (latest RHEL release) from RH and save the ISO file to `/images/rpc-firmware-bundle-build/workdir/rhel.iso`
* Download the SPP ISO from HPE and save the ISO file to `/images/rpc-firmware-bundle-build/firmware/spp.iso`
* Download any other firmware installer software to be included in the bundle
  * Must by compatible with the RHEL we are installing into. Save software in `/images/rpc-firmware-bundle-build/firmware/`

## Create BaseOS VM

These steps are to create the BaseOS VM install from the RHEL DVD, to be copied to the image baseos folder.

* Create the kickstart file (this creates an empty root password so no password is required to login)

```bash
echo 'lang en_US.UTF-8
# Keyboard layouts
keyboard --vckeymap=us --xlayouts='us'
timezone UTC --utc
# Use text mode install
text
# Do not configure the X Window System
skipx
# Reboot after installation
reboot
# SELinux configuration
selinux --disable
# Firewall configuration for SSH
firewall --disabled
# No firstboot
firstboot --disable
# Root credential
rootpw SDF8ASd9f8&1@
# Clear the Master Boot Record
zerombr
# Remove partitions from the system
clearpart --all --initlabel
# Bootloader configuration
bootloader --location=mbr --driveorder=sda --append="rhgb quiet crashkernel=auto"
# Create partitions automatically
autopart
# Use only vda disk
ignoredisk --only-use=vda
# OS Image
cdrom

# Package Selection
%packages
@^Server
dracut-network
dracut-live
dracut-squash
%end

# Post script
%post
passwd -d root
sync
%end' > /images/rpc-firmware-bundle-build/workdir/kickstart.cfg
```

* Copy the kickstart file to the webserver directory

```bash
mkdir -m 755 -p /var/www/html/static
cp /images/rpc-firmware-bundle-build/workdir/kickstart.cfg /var/www/html/static/kickstart.cfg
chmod 644 /var/www/html/static/kickstart.cfg
systemctl restart httpd
```

* Create the VM (make sure the IP configuration below matches that of the virbr0 interface on the bootstrap server)

```bash
qemu-img create -f raw /images/rpc-firmware-bundle-build/workdir/rpc-firmware-bundle.img 20G
virt-install \
-n rpc-firmware-bundle \
-r 2048 \
--vcpus=2 \
--os-variant=rhel9.4 \
--boot uefi \
-w bridge:virbr0 \
--disk path=/images/rpc-firmware-bundle-build/workdir/rpc-firmware-bundle.img \
-l /images/rpc-firmware-bundle-build/workdir/rhel.iso \
--nographics \
-x "inst.ks=http://192.168.122.1/static/kickstart.cfg ksdevice=enp1s0" \
-x "console=ttyS0"
```

* After installation is completed, login to the RHEL VM as root from the VM console and perform additional configuration

```bash
virsh console rpc-firmware-bundle
```

* Configure the hostname (should be set to `rpc-firmware-bundle-gen{XX}-spp{YYYYMMDDVV}`) according to HPE server Gen and SPP version ID

```bash
hostnamectl set-hostname ${hostname}
```

* Configure dracut to include support for live images

```bash
echo 'add_dracutmodules+=" dmsquash-live livenet "' > /etc/dracut.conf.d/live.conf
dracut -N --regenerate-all --force
```

* Empty the `/etc/fstab` file of the RHEL VM

```bash
cp /dev/null /etc/fstab
```

* Configure proxy for YUM

```bash
echo 'proxy=http://rncc-proxy-min.mgslb.vf.rogers.com:80/' >> /etc/yum.conf
```

* Integrate to RHEL Satellite

```bash
curl -k https://rncc-satellite-south.cc.vf.rogers.com/pub/rhel8-eus-lab.sh | bash
```

* Add the HPE SDR Mellanox OFED repo

```bash
echo '[hpe-sdr-mlnx_ofed]
name = HPE Software Delivery Repo - Mellanox OFED
baseurl = https://downloads.linux.hpe.com/SDR/repo/mlnx_ofed/RHEL/8.8/x86_64/current/
enabled = 1
gpgcheck = 0' > /etc/yum.repos.d/hpe-sdr-mlnx_ofed.repo
```

* Install the HPE signed Mellanox Drivers

Note: There will be many errors reported during the installation and this is normal.

```bash
yum -y install hpe-mlnx-ofed
```

* Unregister from Satellite

```bash
subscription-manager unregister
subscription-manager clean
dnf clean all
rm -rf /etc/rhsm/facts/uuid.facts
rm -rf /etc/sysconfig/systemid
rm -rf /var/cache/dnf/*
dnf erase katello-* -y
rpm -e `rpm -qva | grep katello`
```

* Cleanup the YUM configs

```bash
rm -rf /etc/yum.repos.d/hpe-sdr-mlnx_ofed.repo
sed -i 's|proxy=http://rncc-proxy-min.mgslb.vf.rogers.com:80/||g' /etc/yum.conf
```

* Shutdown the RHEL VM

```bash
shutdown -h now
```

## Extract the VM root disk to the bundle environment

* Mount the VM root disk

```bash
losetup -P /dev/loop0 /images/rpc-firmware-bundle-build/workdir/rpc-firmware-bundle.img
vgchange -ay
mount /dev/mapper/rhel-root /images/rpc-firmware-bundle-build/baseos
mount /dev/loop0p2 /images/rpc-firmware-bundle-build/baseos/boot
mount /dev/loop0p1 /images/rpc-firmware-bundle-build/baseos/boot/efi
```

* Mount the SPP ISO to the firmware/isomnt folder

```bash
mount /images/rpc-firmware-bundle-build/firmware/spp.iso /images/rpc-firmware-bundle-build/firmware/isomnt
```

* Copy the SPP to the firmware directory under baseos

```bash
mkdir -m 755 -p /images/rpc-firmware-bundle-build/baseos/firmware/spp
cp -ax /images/rpc-firmware-bundle-build/firmware/isomnt/* /images/rpc-firmware-bundle-build/baseos/firmware/spp/
```

* Copy any other firmware to be installed to a subfolder of `/images/rpc-firmware-bundle-build/baseos/firmware`, example for E810 below.
  * Note: The software being copied needs to be unzipped/untar'd and ready to execute in its current form. Perform any tar/gz extraction before copying.

```bash
mkdir -m 755 -p /images/rpc-firmware-bundle-build/baseos/firmware/E810
cp -ax /images/rpc-firmware-bundle-build/firmware/E810 /images/rpc-firmware-bundle-build/baseos/firmware/
```

## Create the run.sh script

* Edit the content of the script below as required, and copy to the `/images/rpc-firmware-bundle-build/baseos/firmware/` folder

```bash
vi /images/rpc-firmware-bundle-build/baseos/firmware/run.sh
```

```bash
#!/bin/bash
basedir=/firmware

echo "Starting RPC firmware update service..."

# Install SPP
echo "Installing SPP..."
cd ${basedir}/spp
./launch_sum.sh --s --romonly --ignore_warnings
res=$?
cat /var/log/sum/localhost/sum_log.txt
echo "Result code: $res"
if [[ $res -ne 0 && $res -ne 1 && $res -ne 3 ]]; then
  echo "Error installing SPP. Exiting."
  exit 1;
fi
echo "SPP update complete, continuing..."

# Update XXV710 Firmware
echo "Executing Intel XXV710 firmware update..."
cd ${basedir}/700Series/Linux_x64
./nvmupdate64e -u
res=$?
echo "Result code: $res"
if [[ $res -ne 0 && $res -ne 14 && $res -ne 19 ]]; then
  echo "Error installing Intel XXV710 firmware. Exiting."
  exit 1;
fi
echo "Intel XXV710 firmware update complete, continuing..."

# Reboot
echo "All updates completed, rebooting..."
shutdown -r now
```

```bash
chmod 755 /images/rpc-firmware-bundle-build/baseos/firmware/run.sh
```

## Create systemd service to run the run.sh script on boot

```bash
echo '[Unit]
Description=RPC Firmware update service

[Service]
ExecStart=/firmware/run.sh
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target' > /images/rpc-firmware-bundle-build/baseos/usr/lib/systemd/system/rpc-firmware-update.service
```

```bash
chmod 644 /images/rpc-firmware-bundle-build/baseos/usr/lib/systemd/system/rpc-firmware-update.service
```

* Enable systemd service from chroot

```bash
chroot /images/rpc-firmware-bundle-build/baseos
systemctl enable rpc-firmware-update.service
exit
```

## Modify the boot environment and copy to output folder

* Overwrite the existing `/boot/efi/EFI/redhat/grub.cfg` file, replacing `${bundle_name}` with the actual bundle name (eg. `rpc-firmware-bundle-gen11-20250204`)

```bash
vi /images/rpc-firmware-bundle-build/baseos/boot/efi/EFI/redhat/grub.cfg
```

```bash
set prefix=(http,boot.local)/images/${bundle_name}/boot/grub2

export $prefix
configfile $prefix/grub.cfg
```

* Overwrite the existing `/boot/grub2/grub.cfg` file, replacing `${bundle_name}` with the actual bundle name (eg. `rpc-firmware-bundle-gen11-20250204`) and replacing `${interface}` with the interface name of the first interface (as seen when booted into RHEL OS):

```bash
vi /images/rpc-firmware-bundle-build/baseos/boot/grub2/grub.cfg
```

```bash
timeout=5
default=0

menuentry 'RPC firmware bundle "${bundle_name}"' {
    set gfxpayload=keep
    echo 'Loading kernel ...'
    linux (http,boot.local)/images/${bundle_name}/boot/vmlinuz root=live:http://boot.local/images/${bundle_name}/root.img rw rd.live.overlay.overlayfs=1 rd.live.ram=1 bootdev=${interface} audit=0 selinux=0
    echo 'Loading initial ramdisk ...'
    initrd (http,boot.local)/images/${bundle_name}/boot/initrd.img
}
```

* Copy the initrd and linux images to the `output/boot` folder (you will need to adjust the source file name to match the correct ones for your kernel and initrd version)

```bash
cp /images/rpc-firmware-bundle-build/baseos/boot/vmlinuz-5.14.0-503.11.1.el9_5.x86_64 /images/rpc-firmware-bundle-build/baseos/boot/vmlinuz
cp /images/rpc-firmware-bundle-build/baseos/boot/initramfs-5.14.0-503.11.1.el9_5.x86_64.img /images/rpc-firmware-bundle-build/baseos/boot/initrd.img
```

* Copy the files under `/boot` to the output folder

```bash
mkdir -m 755 -p /images/rpc-firmware-bundle-build/output/boot
cp -ax /images/rpc-firmware-bundle-build/baseos/boot/* /images/rpc-firmware-bundle-build/output/boot/
```

* Cleanup the unnecessary files in `output/boot`:

```bash
cd /images/rpc-firmware-bundle-build/output/boot
ls -l
```

The only files remaining in this directory should be as follows:

```bash
drwxr-x---  3 root root       17 Dec 31  1969 efi
drwx------. 3 root root       50 Feb  5 19:46 grub2
-rw-------. 1 root root 38098694 Feb  5 18:31 initrd.img
-rwxr-xr-x. 1 root root 14456952 Sep 30 12:37 vmlinuz
```

## Create the root squashfs

* Using the squashfs command create the compressed squashfs of the root filesystem, first unmounting the `/boot` folder (as it has already been copied to `output/boot`)

```bash
umount /images/rpc-firmware-bundle-build/baseos/boot/efi
umount /images/rpc-firmware-bundle-build/baseos/boot
cd /images/rpc-firmware-bundle-build/baseos/
mksquashfs . /images/rpc-firmware-bundle-build/output/root.img
chmod 644 /images/rpc-firmware-bundle-build/output/root.img
```

## Create the tarball of the output folder

* Ensure permissions are set correctly

```bash
find /images/rpc-firmware-bundle-build/output -type d -exec chmod 755 {} \;
find /images/rpc-firmware-bundle-build/output -type f -exec chmod 644 {} \;
```

* Create the tarball (replacing ${bundle_name} with the actual bundle name, eg. `rpc-firmware-bundle-gen11-20250204`)

```bash
cd /images/rpc-firmware-bundle-build
rm -rf ${bundle_name}
mv output ${bundle_name}
tar czvf /images/${bundle_name}.tar.gz ${bundle_name}
```

## Test the image

* Extract the image to the bootstrap `/var/www/html/images` folder

```bash
cd /var/www/html/images
tar zxvf /images/${bundle_name}.tar.gz
```

* Edit the `dhcpd.conf` on the bootstrap server to point to the UEFI image for the firmware bundle (replacing the URL after `filename` with the correct path)

```bash
vi /etc/dhcp/dhcpd.conf
```

```bash
# PXE VLAN
subnet 192.168.255.0 netmask 255.255.255.0 {
  allow booting;
  allow bootp;
  ddns-update-style none;
  ignore-client-updates;
  range 192.168.255.10 192.168.255.250;
  option domain-name-servers 192.168.255.1;
  option vendor-class-identifier "HTTPClient";
  filename "http://boot.local/images/rpc-firmware-bundle-gen10-spp2025110000/boot/efi/EFI/redhat/shimx64.efi";
  next-server 192.168.255.1;
  default-lease-time 60;
  max-lease-time 3600;
}
```

* Test the dhcpd configuration for errors

```bash
dhcpd -t
```

* Restart the DHCP server

```bash
systemctl restart dhcpd
```

* Boot one of the servers and press F11 from the BIOS screen to enter the One-time Boot Menu.
* Select the interface to boot from and the option "HTTP UEFI (IPv4)"
* When the server boots, you can login as root (does not require any password)
* Monitor the SUM log file `/var/tmp/sum/localhost/node.log`

### Notes

* If you get the error "Bad shim signature" try resetting the secureboot keys to factory default in the RBSU/BIOS of the server under Server Security > Secure Boot Settings > Advanced Secure Boot Options > Reset all keys to platform defaults

## Cleanup

Make sure to test that the image works properly before performing the cleanup steps.

* Remove the RHEL VM

```bash
virsh destroy rpc-firmware-bundle
virsh undefine rpc-firmware-bundle --nvram
rm -rf /images/rpc-firmware-bundle-build/workdir/rpc-firmware-bundle.img
rm -rf /images/rpc-firmware-bundle-build/workdir/rhel.iso
rm -rf /images/rpc-firmware-bundle-build/workdir/kickstart.cfg
rm -rf /var/www/html/static
```

* Unmount filesystems no longer needed

```bash
umount /images/rpc-firmware-bundle-build/baseos/boot/efi
umount /images/rpc-firmware-bundle-build/baseos/boot
umount /images/rpc-firmware-bundle-build/baseos
umount /images/rpc-firmware-bundle-build/firmware/isomnt
vgchange -an rhel
losetup -d /dev/loop0
```

* Remove files from build folder

```bash
rm -rf /images/rpc-firmware-bundle-build/baseos/*
rm -rf /images/rpc-firmware-bundle-build/firmware/*
rm -rf /images/rpc-firmware-bundle-build/workdir/*
rm -rf /images/rpc-firmware-bundle-build/output/*
```
