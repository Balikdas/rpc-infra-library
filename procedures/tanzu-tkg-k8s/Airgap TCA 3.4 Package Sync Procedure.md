# Airgap TCA 3.4 Package Sync Procedure

- Backup the existing `/usr/local/airgap` folder:

```bash
mv /usr/local/airgap /usr/local/airgap.$(date +%Y%m%d)
```

- Copy the Airgap appliance upgrade ISO to the `/opt/` directory on the Airgap server

```bash
ls -l /opt/TCA_AIRGAP_APPLIANCE-upgrade-bundle-3.4.0-24865547.iso
-rw-r--r-- 1 root root 3260311552 Dec  1 17:36 /opt/TCA_AIRGAP_APPLIANCE-upgrade-bundle-3.4.0-24865547.iso
```

- Mount the ISO under `/mnt/cdrom`:

```bash
mount /opt/TCA_AIRGAP_APPLIANCE-upgrade-bundle-3.4.0-24865547.iso /mnt/cdrom
```

- Copy the required files from the ISO to the `/usr/local/airgap` folder and fix the permissions:

```bash
cp -r /mnt/cdrom/os-files/usr/local/airgap /usr/local/
mv /usr/local/airgap/scripts.cap4 /usr/local/airgap/scripts
find /usr/local/airgap -type d -exec chmod ug+rx {} \;
find /usr/local/airgap -type f -exec chmod ug+rw {} \;
find /usr/local/airgap -type f -name '*.sh' -exec chmod ug+x {} \;
chmod ug+x /usr/local/airgap/scripts/bin/agctl
```

- Unmount the ISO

```bash
umount /mnt/cdrom
```

- Create the configuration patch:

```bash
cd /usr/local/airgap/scripts
vi vars/user-inputs.diff
```

- Add the following lines (modify the server_fqdn as required):

```bash
42a43,44
> build_sync: "3.4.0-24874301"
>
54c56
< server_fqdn: airgap.example.com
---
> server_fqdn: rncc-harbor-sde-north-az01.cc.vf.rogers.com
110c112
< auto_generate: True
---
> auto_generate: False
143,145c145,147
< server_cert_path: /root/certs/star_example.com.crt
< server_cert_key_path: /root/certs/start_example.com.key
< ca_cert_path: /root/certs/example.com.crt
---
> server_cert_path: /usr/local/airgap/certs/cc.vf.rogers.com.crt
> server_cert_key_path: /usr/local/airgap/certs/cc.vf.rogers.com.key
> ca_cert_path: ""
```

- Patch the configuration:

```bash
patch vars/user-inputs.yml vars/user-inputs.yml.diff
```

- Configure the Harbor password:

```bash
echo "harbor_password: ${harbor_admin_password}" > vars/harbor-credential.yml
```

- Copy the certificates to the required location:

```bash
mkdir /usr/local/airgap/certs/
cp -p /etc/docker/certs.d/cc.vf.rogers.com/cc.vf.rogers.com.crt /usr/local/airgap/certs/cc.vf.rogers.com.crt
cp -p /etc/docker/certs.d/cc.vf.rogers.com/cc.vf.rogers.com.key /usr/local/airgap/certs/cc.vf.rogers.com.key
```

- Run the sync operation:

```bash
bin/agctl sync
```

- Tail the resulting log file and monitor the logs in `/usr/local/airgap/logs`
