# How to Reinstall an ESXi Host Using Bootstrap VM

This procedure outlines the steps to reinstall an ESXi host and re-add it to the cluster. This is required in the case of replacement of the system board or other changes such as replacement of failed TPM.

Please note that the below steps are high level only. This requires some knowledge of the Bootstrap server and rpc-infra-cicd GitHub library to execute. Some of the below steps may require script reconfiguration, which is not covered below.

ONLY EXECUTE THIS PROCEDURE IF YOU ARE FAMILIAR WITH IT AND KNOW WHAT YOU ARE DOING. IF YOU ARE NOT SURE, REACH OUT TO A SENIOR TEAM MEMBER FOR ASSISTANCE.

**Note:** This procedure is only valid for hosts/AZ which were installed using bootstrap server. For manually installed hosts, the server must be manually reinstalled.

## Prerequisites

- New ILO MAC updated in DHCP and server profile reapplied in HPE OneView (new MAC and admin password to be provided by HPE tech)
- Firmware bundle applied via Bootstrap server (consistent with other hosts in the cluster)
- ESXi host being reinstalled has been removed from vCenter and NSX (disconnect host and remove from inventory in vCenter and verify removed in NSX)

## ESXi Install

### Step 1 - Prepare the Bootstrap server with the ESXi image

- Login to the bootstrap server for the AZ the host is residing in
- Perform a `git pull` from the `/root/rpc-infra-cicd` folder to update the repo from GitHub
- Verify the configuration of the required scripts in `/root/rpc-infra-cicd/pipelines/availability_zone/scripts/`
- Download the ISO for the required ESXi version to the /images folder
- Run the script `/root/rpc-infra-cicd/pipelines/availability_zone/scripts/uefi_http_image_gen.sh ${path_to_ESXi_ISO}`
- Edit the `/etc/dhcp/dhcpd.conf` file to point to the filename `filename "http://boot.local/images/mboot.efi";` and comment out all other lines beginning with `filename`
- Verify the DHCP configuration with the command `dhcpd -t`
- Restart the DHCP server with the command `systemctl restart dhcpd`

### Step 2 - Run the automated ESXi install

- Run the script `/root/rpc-infra-cicd/pipelines/availability_zone/scripts/set_onetime_boot_http.sh ${esxi_host_ilo_fqdn}` to force UEFI HTTP boot on next boot
- From HPE OneView, open the server console of the ESXi host and reset the power to force it to reboot
- Monitor the progress of the installation
- Once the installation is successful, run the `/root/rpc-infra-cicd/pipelines/availability_zone/scripts/discover.sh` script to configure the mgmt VLAN
- After approximately 1-2 minutes the ESXi host should be reachable via its IP address, verify you can ping it from the Bootstrap VM before continuing.

### Step 3 - Run the Ansible Playbook to reconfigure the ESXi Host

- Retrieve the YAML manifest for the AZ/cluster that the ESXi host belongs to from GitHub (rpc-infra-gitops repo)
- Create a new YAML manifest from the AZ/cluster manifest that only includes the ESXi host being reinstalled and save it as `/root/rpc-infra-cicd/pipelines/availability_zone/ansible/playbooks/${esxi_hostname}.yml` on the bootstrap VM.
- Ensure that the new YAML parameters below are set to `false` or are not present in the YAML manifest:

```yaml
vcenter_deploy_mgmt_vm: false
vcenter_mgmt_cluster_create: false
vcenter_deploy_wl_vm: false
vcenter_wl_cluster_create: false
vcenter_wl_edge_cluster_create: false
license_vcenter_mgmt_enable: false
license_esx_mgmt_enable: false
license_vsan_mgmt_enable: false
license_vcenter_wl_enable: false
license_esx_wl_enable: false
license_vsan_wl_enable: false
license_esx_edge_enable: false
license_nsx_wl_enable: false
esxi_auto_exit_mtce_mode: false
vds_esx_create: false
vds_nsx_mgmt_create: false
vds_nsx_wl_create: false
vds_nsx_edge_bgp_tor_a_pg_create: false
vds_nsx_edge_bgp_tor_b_pg_create: false
vds_nsx_edge_overlay_pg_create: false
vsan_mgmt_enable: false
vsan_mgmt_claim_disks: false
vsan_wl_enable: false
vsan_wl_claim_disks: false
```

- Remove all NSX, TCA, VRO, AVI related configuration from the YAML manifest
- Run the playbook to re-configure and re-add the host to the cluster:

For Workload or Edge ESXi hosts:

```bash
cd /root/rpc-infra-cicd/pipelines/availability_zone/ansible
ansible-playbook -e @playbooks/${esxi_hostname}.yml playbooks/cluster_expansion_wl.yml
```

For Management ESXi hosts:

```bash
cd /root/rpc-infra-cicd/pipelines/availability_zone/ansible
ansible-playbook -e @playbooks/${esxi_hostname}.yml playbooks/cluster_expansion_mgmt.yml
```

- Monitor the progress of the playbook on the CLI as well as the progress in vCenter

### Step 4 - Validate the NSX Installation and Configuration

- Open the NSX Manager UI for the AZ the ESXi host is a member of
- Verify the host status under System > Fabric > Hosts and ensure the installation is complete and there are no errors.

### Step 5 - Validate the vSAN Cluster Status

- In the vCenter UI, run a Skyline Health check of the vSAN cluster and ensure there are no errors

### Step 6 - Remove the Host from ESXi Maintenance Mode

- In the vCenter UI, right click the ESXi host and select Maintenance Mode > Exit Maintenance Mode. The Host is now available for the cluster to host VMs.

### Step 7 - Update the ESXi root User Password

- SSH to the Host and update the ESXi root user password to the production password. Remember to disable SSH service afterwards.
