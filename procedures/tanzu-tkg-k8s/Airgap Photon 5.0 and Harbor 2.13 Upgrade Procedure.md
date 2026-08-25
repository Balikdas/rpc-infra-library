# Airgap Photon 5.0 and Harbor 2.13 Upgrade Procedure

- Shutdown Harbor

```bash
cd /opt/harbor
systemctl stop harbor
docker-compose down
systemctl disable harbor
```

- Disable the Harbor Anycast VIP in AVI Controller

- Upgrade Photon OS to latest minor version and then reboot:

```bash
tdnf -y install photon-upgrade
photon-upgrade.sh --assume-yes
reboot
```

- Configure TDNF repos:

```bash
cd /etc/yum.repos.d/
rm photon-3.repo photon3-updates.repo photon-4.repo photon4-updates.repo photon-5.repo photon5-updates.repo photon-telco-debuginfo.repo photon-telco-updates.repo
sed -i 's/enabled=0/enabled=1/g' photon-release.repo photon.repo photon-updates.repo photon-extras.repo
```

- Upgrade Photon OS to version 5.0 and then reboot:

```bash
photon-upgrade.sh --upgrade-os --assume-yes
reboot
```

- Downgrade Ansible to 2.14 due to a known issue with 2.18

```bash
tdnf downgrade ansible -y
```

- Backup existing Harbor database and configs

```bash
cp -r /opt/harbor /opt/harbor.$(date +%Y%m%d)
cp -r /data/harbor/database /data/harbor/database.$(date +%Y%m%d)
```

- Prepare Harbor 2.9 Upgrade

```bash
cd /opt/
curl -LO https://github.com/goharbor/harbor/releases/download/v2.9.0/harbor-offline-installer-v2.9.0.tgz
tar zxvf harbor-offline-installer-v2.9.0.tgz
cd harbor
```

- Upgrade Harbor to version 2.9

```bash
rm harbor.v2.7.4.tar.gz
docker image load -i harbor.v2.9.0.tar.gz
docker run -it --rm -v /:/hostfs goharbor/prepare:v2.9.0 migrate -i /opt/harbor/harbor.yml
./install.sh --with-trivy
```

- Wait for the Harbor service to start up (wait until all services are healthy and verify login to the Harbor UI works and image artifacts are present)

```bash
watch docker ps
```

- Prepare Harbor 2.11 Upgrade

```bash
cd /opt/
curl -LO https://github.com/goharbor/harbor/releases/download/v2.11.0/harbor-offline-installer-v2.11.0.tgz
tar zxvf harbor-offline-installer-v2.11.0.tgz
cd harbor
```

- Upgrade Harbor to version 2.11

```bash
rm harbor.v2.9.0.tar.gz
docker image load -i harbor.v2.11.0.tar.gz
docker run -it --rm -v /:/hostfs goharbor/prepare:v2.11.0 migrate -i /opt/harbor/harbor.yml
./install.sh --with-trivy
```

- Wait for the Harbor service to start up (wait until all services are healthy and verify login to the Harbor UI works and image artifacts are present)

```bash
watch docker ps
```

- Prepare Harbor 2.13 Upgrade

```bash
cd /opt/
curl -LO https://github.com/goharbor/harbor/releases/download/v2.13.1/harbor-offline-installer-v2.13.1.tgz
tar zxvf harbor-offline-installer-v2.13.1.tgz
cd harbor
```

- Upgrade Harbor to version 2.13

```bash
rm harbor.v2.11.0.tar.gz
docker image load -i harbor.v2.13.1.tar.gz
docker run -it --rm -v /:/hostfs goharbor/prepare:v2.13.1 migrate -i /opt/harbor/harbor.yml
./install.sh --with-trivy
```

- Wait for the Harbor service to start up (wait until all services are healthy and verify login to the Harbor UI works and image artifacts are present)

```bash
watch docker ps
```

- Fix `docker-compose.yml` and restart Harbor

```bash
vi docker-compose.yml
```

- Replace the `networks:` block at the end of the file with the following:

```yaml
networks:
  harbor:
    external: false
    ipam:
      driver: default
      config:
        - subnet: 100.65.0.0/16
  harbor-chartmuseum:
    external: false
    ipam:
      driver: default
      config:
        - subnet: 100.66.0.0/16
```

- Copy the `docker-compose.yml` to `docker-compose.yml.saved` for later use

```bash
cp -p docker-compose.yml docker-compose.yml.saved
```

- Restart Harbor

```bash
docker-compose down
docker-compose up -d
```

- Migrage charts to OCI (modify the Harbor FQDN and Harbor password as required):

**Important:** Take note of any failed chart migrations and advise app teams to re-upload them as OCI objects.

```bash
docker run -it --rm --net=host -v /data/harbor/chart_storage:/chart_storage goharbor/migrate-chart:1.1.0 --hostname rncc-harbor-sde-north-az01.cc.vf.rogers.com --password '${harbor_admin_password}'
```

- Re-enable Harbor service

```bash
systemctl enable harbor
```

- Re-enable the Harbor Anycast VIP in AVI Controller
