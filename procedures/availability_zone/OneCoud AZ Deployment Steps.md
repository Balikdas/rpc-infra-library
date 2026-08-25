# OneCloud AZ Deployment Steps

This document outlines at a high level the steps required to be executed manually before and after running the Ansible playbook to deploy a OneCloud AZ.

These steps will be updated as the Ansible solution is updated to automate more tasks. The steps should be executed in the order they are presented below.

## OneView Integration

- Add hosts to MIN DHCP (DDNS will handle adding hosts to DNS automatically)
- Add hosts to OneView (enabled maintanence mode in OneView to prevent alarms going to NOC)
- Create Server Profile Template in OneView for the AZ (or rack if legacy RNCC/Telco)
- Create Server Profiles for each host in OneView based on Server Profile Template
- Patch host firmware with latest RPC firmware bundle
- Confiure host ILO/BIOS according to Server Profile (should be done automatically when Server Profile is created)
- Verify each host firmware and BIOS/ILO settings applied successfully and host is free from alarms on OneView
- For each DL360 host, run the rncc-infra-cicd/scripts/ilo5_set_fan_speed.sh script and set fan speed to 50% minimum with increased cooling enabled

## Add DNS entries for Management VMs

- Add forward and reverse DNS entries for all Management VMs (can do this from any DDNS enabed DHCP server using `nsupdate` utility)

## Perform automated ESXi Hypervisor install

- Deploy ESXi manually to Bootstrap host (first management host)
- Deploy Bootstrap VM to Bootstrap host
- Using Bootstrap VM, deploy ESXi to all hosts

## Perform Ansible based automated AZ install

- Using Ansible playbooks from `rpc-infra-cicd` repo, deploy AZ base install

## vCenter Manual Steps

- Clear all "TPM Encryption Recovery Key Backup Alarm" warnings from all ESXi hosts
- Enable DRS on Management and Workload clusters (but not on Edge clusters)
  - DRS Automation: Fully Automated
- Enable VSAN Support Insight service on all VSAN clusters
- Enable VSAN Performance service on all VSAN clusters
- Enable Automatic Rebalance on all VSAN clusters
- Update VSAN Release Catalog
- Create a Native Key Provider in each vCenter and save the file in Sharepoint with passphrase protection using standard password
- Enable Data-at-Rest encryption on all VSAN clusters using Native key provider
- Modify VM Storage Policy "vSAN Default Storage Policy" to require Data-at-Rest encryption
  - When prompted, select "Apply to all VMs now"
- Create one VSAN Fault Domain per rack and add all hosts from the same rack to each FD
- Set VCLS VMs to use VSAN datastore (only for clusters that are running VSAN)
  - Click Cluster Name > Configure tab
  - Under vSphere Cluster Services click Datastores
  - Click Add and select the vSAN datastore
  - Wait for VCLS VMs to be redeployed
  - Ensure each VCLS VM is running on a different fault domain (rack). If not perform a vMotion to relocate them
- Create VM folder structure as per below (delete the "Discovered virtual machine" folder):

  - {Mgmt vCenter}
    - Backup VMs
    - Kubernetes
    - Management VMs

  - {Workload vCenter}
    - AVI Service Engine VMs
    - Backup VMs
    - Edge VMs
    - Kubernetes
    - Standalone VMs
      - ICSU
      - OSS
      - RPC
        - Enterprise Infra Platform Systems
        - Network Infra Platform Systems
      - Wireless
      - Wireline
    - vRA

- Move all Management VMs on Management vCenter into the Management VMs folder
- Remove all Kubernetes templates from Management vCenter keeping only the highest version
- Move the remaining Kubernetes template to the Kubernetes folder on the Management vCenter
- Move all 3 Kubernetes templates to the Kubernetes folder on the Workload vCenter
- Move all Edge VMs into the Edge VMs folder on the Worklkoad vCenter
- Configure AD on all vCenters:
  - Identity Source Type: Active Directory over LDAP
  - Identity Source Name: `OSS-AD`
  - Base distinguished name for users: `dc=oss,dc=rogers,dc=com`
  - Base distinguished name for groups: `dc=oss,dc=rogers,dc=com`
  - Domain Name: `oss.rogers.com`
  - Domain Alias: {blank}
  - Username: `rnccadmin@oss.rogers.com`
  - Password: {password}
  - Connect to: Specific domain controllers
  - Primary Server URL: `ldaps://ad1-to3.oss.rogers.com`
  - Secondary Server URL: `ldaps://ad1-wfd.oss.rogers.com`
  - Certificates (for LDAPS): {load AD certs}
- Set OSS-AD as default identity source
- Add OSS-AD group `rncc-vcenter-administrators` to local `Administrators` group
- Test login using AD user which is a member of `rncc-vcenter-administrators` (rncceng etc)
- In VAMI (https://{vCenter FQDN}:5480) and configure HTTP and HTTPS proxy as `http://rncc-proxy-min.mgslb.net.rogers.com:80/`
- Detatch all Baselines from Lifecycle Manager (Hosts & Clusters > Cluster > Updates > Baselines > Detach)
- Disable VSAN Cluster recommendations in Lifecycle Manager (Hosts & Clusters > Cluster > Updates > Cluster Settings > VSAN Recommendation)
- Deploy vSAN file service on Workload vCenter (NSX-T manual steps need to be done so the NFS VMs will have connectivity)
  - File service domain: cc.net.rogers.com
  - DNS Servers: 172.19.255.100,172.19.255.101
  - DNS Suffixes: cc.net.rogers.com
  - Directory service: {unchecked}
  - Network: oSeg-rcsinSrv-prv-nrt-nfs-01 (NSX)
  - Subnet mask: {from CIQ}
  - Gateway: {from CIQ}
  - IP: {from CIQ}
  - DNS Name: {from CIQ}
- Create a content library named "VRA Images" as a subscribed content library (from library of the same name on rncc-ivc-wlfdle) and sync all images
- Configure backups
  - In VAMI (https://{vCenter FQDN}:5480) click "Backup" menu and edit schedule
    - Backup Location: Choose bootstrap server in another site (eg for wlfdle, backup to rncc-bootstrap-sde-ml02-az01)
    - User name: vcbackup
    - Password: {password}
    - Encyrpt: {password}
    - Retain last: 7 backups
    - Data: Select all
  - Run a manual backup to confirm it is working

## Deploy additional VMs

- Deploy DHCP server in Workload vCenter
  - Clone existing DHCP server from another site (eg rncc-dhcp-sde-wlfdle-az01)
  - Cluster: WorkloadA
  - Folder: Standalone VMs > RPC > Network Infra Platform Systems
  - Boot the server and configure ens192 (Management VMs) and ens256 (Management ESX) interfaces with IPs from CIQ
  - Configure the /etc/hostname file with the correct hostname
  - Re-run the Satellite and AD integration scripts on the new DHCP server
  - Configure /etc/dhcp/dhcpd.conf with the correct values for the local site
  - Copy the /etc/dhcp/dhcp_reservation.inc from the local bootstrap VM to the DHCP VM
  - Check DHCP config with `dhcpd -t` and restart dhcpd
  - Reconfigure the bootstrap server /etc/dhcp/dhcpd.conf to only have configuration for the PXE network (ens224)
  - Empty and entries in /etc/dhcp/dhcp_reservation.inc on local bootstrap server
  - Check DHCP config with `dhcpd -t` and restart dhcpd on local bootstrap server
- Deploy VRO OVA file manually (automated deployment not working currently)
  - vCenter: Workload
  - Cluster: WorkloadA
  - Folder: Standalone VMs > RPC > Network Infra Platform Systems
  - Network: Management VMs
  - Hostname: {full FQDN from CIQ}
  - Kubernetes internal cluster CIDR: 100.64.0.0/22
  - Kubernetes internal service CIDR: 100.64.4.0/22
  - NTP Servers: 172.19.254.12
  - DNS Servers: 172.19.255.100,172.19.255.101
  - Default Gateway {from CIQ}
  - Domain Name: cc.net.rogers.com
  - Domain Search Path: cc.net.rogers.com
  - Network 1 IP Address: {from CIQ}
  - Network 1 Netmask: {from CIQ}
  - Add oSeg-rcsinSrv-prv-nrt-k8s network to VRO VM and add a file `/etc/systemd/network/99-eth1.network` in VRO CLI, then run `systemctl restart systemd-networkd`

    ```bash
    [Match]
    Name=eth1

    [Network]
    LinkLocalAddressing=no
    DHCP=yes

    [DHCP]
    ClientIdentifier=mac
    UseHostname=no
    UseDomains=no
    UseNTP=no
    UseRoutes=false
    ```

  - **NOTE**: For unknown reasons, sometimes the firstboot script will fail due to an issue with reaching NTP. Check the log file `/var/log/bootstrap/firstboot.log`. If this happenes, you can re-run the firstboot script manually: `/usr/lib/bootstrap/firstboot` and monitor the output.
  - Configure VRO Auth from CLI by running the command `vracli vro authentication wizard`:
    - Auth Provider Settings:
      - Auth Provider: vSphere
      - Hostname: {CP vCenter FQDN}
      - Admin Username: <svc-vro-vsphere@oss.rogers.com>
      - Admin group domain: vsphere.local
      - Admin group: Administrators
    - Reboot the appliance
  - Login to `https://{VRO FQDN}/orchestration-ui` and copy VRO package from another site to the new VRO VM
- Clone Harbor VM from another site (eg. rncc-harbor-sde-wlfdle-az01)
  - Modify /etc/hostname and eth0 interface config as per CIQ and reboot
  - Configure new harbor replication to push to all other harbors
  - Configure all existing harbors to push to this new harbor
- Clone Bastion VM from another site (eg. rncc-bastion-sde-wlfdle-az01)
  - Folder: Standalone VMs > RPC > Network Infra Platform Systems
  - Networks:
    - Management VMs
    - oSeg-rcsinSrv-prv-nrt-k8s
  - Re-run Satellite and AD integration scripts on new Bastion VM
  - Clean all app user accounts from /home directory (rm -rf /home/{app_account})
  - Clean all docker images from local docker daemon (docker image ls / docker rmi {image}:{tag})
- Deploy CommVault VSA VMs

## NSX-T Manual Steps

- Add OSS-AD as LDAP Identity Source
  - Name: `OSS-AD`
  - Domain Name: `oss.rogers.com`
  - Type: Active Directory over LDAP
  - Base DN: `dc=oss,dc=rogers,dc=com`
  - LDAP Servers: {click "Set"}
  - Add LDAP Server
    - FQDN: `ad1-to3.oss.rogers.com`
    - LDAP Protocol: LDAPS
    - Port: `636`
    - Enabled: Yes
    - Use StartTLS: Disabled
    - Bind Identity: `rnccadmin@oss.rogers.com`
    - Password: {password}
    - Click Add
    - Click Accept
    - Click Add again
  - Add LDAP Server
    - FQDN: `ad1-wfd.oss.rogers.com`
    - LDAP Protocol: LDAPS
    - Port: `636`
    - Enabled: Yes
    - Use StartTLS: Disabled
    - Bind Identity: `rnccadmin@oss.rogers.com`
    - Password: {password}
    - Click Add
    - Click Accept
    - Click Add again
  - Click Save
- Add User Role Assignment for OSS-AD group `rncc-nsx-administrators` as `Enterprise Admin`
- Add User Role Assignment for OSS-AD group `rncc-nsx-ro-users` as `Auditor`
- Logout and check OSS-AD is working by logging in from a user in the `rncc-nsx-administrators` AD group
- Under Networking tab, Global Networking Config menu, set Gateway Interface MTU to `8900`
- Add NAT rule to T1 router `t1-rcsinSrv-nrt`
  - Name: default-egress
  - Action: SNAT
  - Translated IP: {default nat from CIQ}
  - Priority: 9999
  - All other fields left blank
- Add segment profiles
  - Add DHCP segment profile
    - Type: Segment Security Profile
    - Name: dhcp-segment-security-profile
    - Rate Limits: Disabled
    - All other values left default
  - Add VSAN NFS IP Discovery profile:
    - Type: IP Discovery
    - Name: vsan-nfs-ip-discovery-profile
    - ARP Binding Limit: 5
    - All other values left default
  - Add VSAN NFS MAC Discovery profile
    - Type: MAC Discovery
    - Name: vsan-nfs-mac-discovery-profile
    - MAC Learning: {enabled}
    - All other values left default
- Configure segments
  - Set DHCP segment security profile on the below segments:
    - oSeg-rcsinSrv-prv-nrt-avictl-01
    - oSeg-rcsinSrv-prv-nrt-k8s-01
  - Set VSAN NFS IP Discovery and MAC Discovery on the below segment:
    - oSeg-rcsinSrv-prv-nrt-nfs-01
  - Set tag on oSeg-rcsinSrv-prv-nrt-k8s-01:
    - `NetId: prv-nrt-k8s`
  - Set tag on oSeg-rcsinSrv-prv-nrt-nfs-01
    - `NetId: prv-nrt-nfs`
- Configure T1 Gateway Firewall
  - In Security > Gateway Firewall
    - Disable GW firewall on t0-rcsinSrv
    - Enable GW firewall on t1-rcsinSrv-nrt (leave identity firewall disabled)
    - Disable GW firewall on t1-rcsinSrv-rt
- Set tags on VSAN NFS VMs
  - All VSAN File Service VMs tagged as `AppId: infra-nfs`
- Integrate with NSX Global Manager
  - Login to NSX Global Manager and go to System > Location Manager
    - Scroll to bottom and click "Add On Prem Location"
      - Location Name: NSX Manager VIP hostname from CIQ
      - FQDN: NSX Manager VIP FQDN
      - Username: (TBA Global Manager SVC account. Temporarily using <svc-avi-nsx@oss.rogers.com>)
      - Password: {password}
      - SHA-256 Thumprint: Thumprint of the NSX Manager VIP, can be obtained by running the below command:

        ```bash
        echo -n | openssl s_client -connect ${nsx_mgr_fqdn}:443 2>/dev/null | openssl x509 -noout -fingerprint -sha256 | tr -d ':'
        ```

      - Click "Check Version Compatibility"
      - Click Save
  - **IMPORTANT**: When prompted to import, click No to decline import.
- Configure backups
  - In System > Backup & Restore click Edit under SFTP Server
    - FQDN: Choose bootstrap server in another site (eg for wlfdle, backup to rncc-bootstrap-sde-ml02-az01)
    - Directory path: /home/nsxbackup
    - Username: nsxbackup
    - Password: {password}
    - Passphrase: {password}
    - Click Save and accept the SSH fingerprint
  - Click Edit under Schedule
    - Recurring backup: selected
    - Frequency: Weekly
    - Day of week: All days
    - Select Time: 0h 0min
    - Leave other settings default and click Save
  - Run a manual backup to ensure it is working
- Configure default drop rule in all NSX-T local managers
  - In Security > Distributed Firewall > Application set the rule named "Default Layer3 Rule" action to "Drop"
  - Click the gear icon beside the "Drop" rule and enable IPv4-IPv6 logging with teh label "default catch-all drop rule"

## AVI Manual Steps

- Login to first AVI node and configure admin credential (leave email blank)
  - Set passphrase: same as Admin credential
  - DNS resolvers:  172.19.255.100, 172.19.255.101
  - DNS Search Domain:  cc.net.rogers.com
  - Email/SMTP: none
  - Multi-tenant: leave as default
  - Select "Setup Cloud After" and click Save
  - Configure cluster in Administration > Cluster > Nodes
    - Cluster IP: {from CIQ}
    - Nodes: Add the AVI VM IP and name from CIQ
    - Wait about 5 minutes after clicking Save and login to cluster VIP
- Patch AVI
  - In Administration > Controller > Software upload latest AVI patch for TCP certified version
  - In Administration > Controller > System Update select the patch version and click Upgrade
  - Wait about 5 minutes for the upgrade to complete
- Confgure License
  - In Administration > Settings > Licensing select "Enterprise Tier" trial license
  - Add license key as per CIQ
  - Delete the Eval license
- Configure Proxy
  - SSH to AVI controller VIP as admin user
    - Execute the "shell" command and login as admin user
    - Run the command `configure systemconfiguration`
    - Run the command `proxy_configuration`
    - Run the command `host rncc-proxy-min.mgslb.net.rogers.com`
    - Run the command `port 80`
    - Run the command `save`
    - Exit the shell
- Configure Cloud Services
  - In Administration > Settings > Cloud Services click "Register Controller"
  - Login with your VMware Customer Connect account
  - Click Save (leave all settings default)
- Configure AD Authentication
  - In Administration > Sytem Settings > Authentication click edit
  - Select "Remote" and "Allow local user login"
  - Create Auth Profile
    - Name: OSS-AD
    - Type: LDAP
    - LDAP Servers: ad1-to3.oss.rogers.com and ad1-wfd.oss.rogers.com
    - LDAP Port: 636
    - Secure LDAP using TLS: checked
    - Base DN: dc=oss,dc=rogers,dc=com
    - Admin Bind DN: cn=rnccadmin,cn=users,dc=oss,dc=rogers,dc=com
    - Admin Bind Password: {password}
    - User Search DN: dc=oss,dc=rogers,dc=com
    - Group Search DN: dc=oss,dc=rogers,dc=com
    - Search Scope: Scope Subtree
    - User ID Attribute: sAMAccountName
    - Group Search Scope: Scope Subtree
    - Group Filter: (objectClass=group)
    - Group Member Attribute: member
    - Group Member Attribute is Full DN: checked
    - Ignore Refferrals: checked
  - Create admin Tenant and Role Mapping
    - LDAP Group: Member
    - Group Name: rncc-nsx-administrators
    - Super User: checked
    - Click Save
  - Create read only Tenant Role and Mapping
    - LDAP Group: Member
    - Group Name: rncc-nsx-ro-users
    - User Role: Selected
    - Roles: Create Role
      - Name: Read Only
      - Select all items as Read
      - Click Save
    - Tenants: All
    - Click Save
    - Test login using OSS-AD user in rncc-nsx-administrators group
- Configure local service account for AKO
  - In Administration > Accounts > Users click "Create"
    - Name: svc-ako-avi
    - Username: svc-ako-avi
    - Password: {password}
    - User Profile: No-Lockout-User-Account-Profile
    - Roles for All Tenants: Add Role
      - Tenant: admin
      - Role: System-Admin
    - Default Tenant: admin

- Add vCenter Cloud
  - In Infrastructure > Clouds click Create
  - Click VMware vCenter
  - Name: vCenter
  - Username: <svc-avi-vcenter@oss.rogers.com>
  - Password: {from CIQ}
  - vCenter Address: {vCenter WL FQDN from CIQ}
  - IPAM Profile: none
  - DNS Profile: none
  - State Based DNS Registration: Unchecked
  - Other Settings: default
  - DNS Resolver: Click Add
  - DNS Servers: 64.71.255.251, 64.71.255.252
  - Click Next
  - Select DHCP Enabled and Click Next
  - Management Network: Management VMs
  - IPv6 Auto Configuration: unchecked
- Add vCenter Credentials
  - In Administration > User Credentials click Create
  - Name: {vCenter WL name from CIQ}
  - Credentials Type: vCenter
  - Username: <svc-avi-vcenter@oss.rogers.com>
  - Password: {password}
  - Click Save
- Add NSX-T Credentials
  - In Administration > User Credentials click Create
  - Name: {NSX Manager VIP name from CIQ}
  - Credentials Type: NSX-T
  - Username: <svc-avi-nsx@oss.rogers.com>
  - Password: {password}
  - Click Save
- Add NSX-T Cloud
  - In Infrastructure > Clouds click Create
  - Click NSX-T Cloud
  - Name: NSX-T WL
  - Object Name Prefix: avi-wl
  - Credentials
    - NSX-T Addres: VIP FQDN of NSX manager
    - NSX-T Credentials: Select credentials created in above steps
  - Management Network
    - Transport Zone: tz-overlay
    - T1 Router: t1-rcsinSrv-nrt
    - Overlay Segment: oSeg-rcsinSrv-prv-nrt-avictl-01
  - Data Networks
    - Transport Zone: tz-overlay
    - T1 Router: t1-rcsinSrv-nrt
    - Overlay Segment: oSeg-rcsinSrv-prv-nrt-k8s-01
  - vCenter Servers:
    - Name: Name of WL vCenter as per CIQ
    - vCenter Address: Select IP from dropdown list
    - vCenter Credentials: Select credentials created in above steps
    - Content Library: AVI
  - IPAM Profile: none
  - DNS Profile: none
  - DNS Resolvers
    - Name: Infrastructure DNS
    - DNS Servers: 64.71.255.251, 64.71.255.252
- Configure Networks
  - In Infrastructure > Cloud Resources > Networks select NSX-T cloud
  - Edit oSeg-rcsinSrv-prv-nrt-avictl-01 and oSeg-rcsinSrv-prv-nrt-k8s-01 to enable DHCP and disable IPv6 auto configuration
  - Create a new network named "rcsinSrv-infra-vips"
    - Disable DHCP and IPv6 Auto Configuration
    - Routing Context: global
    - Add Subnet
      - Subnet: 0.0.0.0/0
      - Add Static IP pool
        - Disable Use Static IP for VIP and SE
        - Add IP range (single IP) of harbor VIP (eg. 99.212.164.1-99.212.164.1) and select Use for VIPs only
  - Create a new network named "rcsinSrv-vips"
    - Disable DHCP and IPv6 Auto Configuration
    - Routing Context: global
    - Add Subnet
      - Subnet: 0.0.0.0/0
- Add IPAM Profile
  - In Templates > Profiles click IPAM/DNS Profiles
  - Click Create > IPAM Profile
    - Name: AVI IPAM
    - Click Add Usable Network
      - Cloud for Usable Network: NSX-T WL
      - Select both rcsinSrv-infra-vips and rcsinSrv-vips
    - Click Save
- Add AVI IPAM profile to vCenter WL and NSX-T clouds
- Configure SE Group
  - In Infrastructure > Cloud Resources > Service Engine Group select NSX-T cloud
    - Edit the Default Group:
      - Elastic HA: Active/Active
      - VS per SE: 100
      - Max SE's: 2
      - SE Name Prefix (Advanced Tab): default_se_group
      - Add vCenter: Select WL vCenter
      - Host cluster scope: Cluster, Include Workload A
      - SE Folder: AVI Service Engine VMs
      - Datastore Scope: Shared, select vsanDS-WorkloadA
      - Leave other settings as default
- Create Harbor VS
  - In Applications > Virtual Services create a VS via Advanced Setup on NSX-T cloud
    - Name: harbor.cc.net.rogers.com
    - VS VIP: Create
      - Name: harbor.cc.net.rogers.com
      - T1 Router: t1-rcsinSrv-nrt
      - VIP: Harbor anycast VIP (99.212.164.1)
      - Leave other settings default
    - Application Profile: System-L4-Application
    - TCP/UDP Profile: System-TCP-Fast-Path
    - Services: port 443 and 8043
    - Pool: Create
      - Name: harbor.cc.net.rogers.com-pool
      - Default Port: 443
      - T1 Router: t1-rcsinSrv-nrt
      - Append Port: Never
      - Passive Health Monitor: disabled
      - Min Health Monitors: 2
      - Create TCP-443 Health Monitor
        - Name: TCP-443
        - Type: TCP
        - Successful Checks: 3
        - Failed Checks: 1
        - Send Interval: 3
        - Receive Timeout: 1
        - Health Monitor Port: 443
      - Create TCP-8043 Health Monitor
        - Name: TCP-8043
        - Type: TCP
        - Successful Checks: 3
        - Failed Checks: 1
        - Send Interval: 3
        - Receive Timeout: 1
        - Health Monitor Port: 8043
      - Click Next
      - Server IPs
        - {eth1 IP of Harbor server}:443
        - {eth1 IP of Harbor server}:8043
      - Click Next
      - Disable Port Translation: selected
      - Click Next then Save
    - Click Next twice
    - On Advanced screen, select Service Engine Group "Default-Group" and click Save
  - Configure Harbor anycast disable when down
    - SSH as admin to the AVI controller VIP
    - Enter the CLI using the `shell` command
    - Enter the configuration for the Harbor VIP and enable the `revoke_vip_route` feature:

```bash
configure virtualservice harbor.cc.net.rogers.com
revoke_vip_route
save
```

## TCA Manual Steps

- Configure TCA CP node via UI (port 9443)
  - Enter license key (Standalone) and click Activate
  - Enter city and click Continue
  - Leave system name unchanged
  - Set 'vSphere' as instance type
  - Skip to Administration tab and set the following:
    - NTP Server: 172.19.254.12
    - DNS Servers: 172.19.255.100 & 172.19.255.101
    - Proxy: {unset}
    - Click Dashboard tab and continue below
  - Add CP vCenter details and leave NSX-T blank (username <svc-tca-vcenter@oss.rogers.com>)
  - Add SSO URL of CP vCenter (same as login URL)
  - Add VRO server URL and credentials (username <svc-tca-vcenter@oss.rogers.com>)
  - Leave default Administrator group as vsphere.local\Administrators
  - Click Restart to finish config
- Configure TCA WL node
  - Enter license key (Standalone) and click Activate
  - Enter city and click Continue
  - Leave system name unchanged
  - Set 'vSphere' as instance type
  - Skip to Administration tab and set the following:
    - NTP Server: 172.19.254.12
    - DNS Servers: 172.19.255.100 & 172.19.255.101
    - Proxy: {unset}
    - Click Dashboard tab and continue below
  - Add WL vCenter NSX-T details (VC username <svc-tca-vcenter@oss.rogers.com>, NSX username <svc-tca-nsx@oss.rogers.com>)
  - Add SSO URL of WL vCenter (same as login URL)
  - Add VRO server URL and credentials (username <svc-tca-vcenter@oss.rogers.com>)
  - Leave default Administrator group as vsphere.local\Administrators
  - Click Restart to finish config
- Add new TCA CP node to TCA Global Manager
  - In Virtual Infrastructure menu, click Add
    - VIM type: vSphere
    - Cloud Name: {CP vCenter Name}
    - TCA CP URL: {TCA CP VM URL}
    - Username: <svc-tca-vcenter@oss.rogers.com>
    - Password: {password}
    - Tags: AppId=infra-mgmt
- Add new TCA WL node to TCA Global Manager
  - In Virtual Infrastructure menu, click Add
    - VIM type: vSphere
    - Cloud Name: {WL vCenter Name}
    - TCA CP URL: {TCA WL VM URL}
    - Username: <svc-tca-vcenter@oss.rogers.com>
    - Password: {password}
    - Tags: AppId=infra-tenant
- Deploy new Management K8s cluster
  - Login to TCA Global Manager
  - In CaaS Infrastructure click "Deploy Cluster" and select "Management Cluster (v1)"
  - Choose the CP vCenter for the site being deployed
  - Select the Management Cluster template
  - Name: As per CIQ
  - Password: {password}
  - Virtual IP: As per CIQ
  - vSphere Cluster: Management
  - Resource Pool: Resosurces
  - VM Folder: Kubernetes
  - Datastore: vsanDS-Management
  - DNS: 172.19.255.100 & 172.19.255.101
  - Airgap & Proxy: Airgap - select harbor.cc.net.rogers.com (Airgap)
  - Leave other values blank/default
  - Click Next
  - Network: Management VMs
  - Leave other values blank/default
  - Click Next
  - Click Deploy
- Configure Backups
  - In TCA Management UI (https://{TCA FQDN}:9443) go to Administration > Backup & Restore
  - Click FTP server setting
    - IP/Host name: Choose bootstrap server in another site (eg for wlfdle, backup to rncc-bootstrap-sde-ml02-az01)
    - Transfer protocol: SFTP
    - Port: 22
    - Username: tcabackup
    - Use Password: selected
    - Password: {password}
    - Backup directory: /home/tcabackup
    - Click Save
  - Click Scheduling
    - Backup Frequenct: DAILY
    - Hour of day: 0
    - Minute: 0
    - CLick Save
