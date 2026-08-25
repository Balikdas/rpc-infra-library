# Create and Destroy LUKS on LVM

This procedure details how to encrypt and securely erase an existing LVM logical volume.

## Prerequisites

* Create an existing LVM logical volume with the appropriate size for the data you want to encrypt.

## Create LUKS Encrypted Partition from Existing LVM Logical Volume

**Note:** Once this procedure is completed, the passphrase for the encrypted volume needs to be entered each time the machine is booted.

* Encrypt the volume (enter a passphrase when prompted):

```bash
cryptsetup luksFormat /dev/mapper/vg_app_sdb-lv_app_encrypted 
```

* Open the LUKS device (enter the passphrase from the step above when prompted):

```bash
cryptsetup open /dev/mapper/vg_app_sdb-lv_app_encrypted encrypted_volume
```

* Create the `/etc/fstab` entry:

```bash
echo "/dev/mapper/encrypted_volume /encrypted_volume      xfs     defaults                     0 0" >> /etc/fstab
```

* Create the `/etc/crypttab` entry:

```bash
echo "encrypted_volume /dev/mapper/vg_app_sdb-lv_app_encrypted none luks" >> /etc/crypttab
```

* Create and mount the filesystem:

```bash
mkfs.xfs /dev/mapper/encrypted_volume
mount /encrypted_volume
```

## Securely Erase an Existing LUKS Encrypted LVM Logical Volume

* Unmount and erase LUKS keys (permanantly makes all data unavailable):

```bash
umount /encrypted_volume
cryptsetup close /dev/mapper/encrypted_volume
cryptsetup luksErase /dev/mapper/vg_app_sdb-lv_app_encrypted
```

* Zero out the volume data:

```bash
dd if=/dev/zero of=/dev/mapper/vg_app_sdb-lv_app_encrypted status=progress
```
