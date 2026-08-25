# ESXi Upgrade Procedure

This procedure outlines the steps to upgrade the OneCloud AZ ESXi hosts in a safe and efficient manner. It should be noted that it may be beneficial to also run NSX-T upgrades at the same time to avoid the number of vMotions required and to save time putting hosts in maintenance mode repeatedly.

The strategy for the upgrade is as follows:

1. Stage upgrade VIBs Depot on the bootstrap HTTP server
2. Put all hosts of the first fault domain into maintenance mode one by one
3. Execute the upgrade on all hosts in the fault domain in parallel and reboot
4. Take all hosts in the fault domain out of maintenance mode in parallel
5. Validate cluster health
6. Repeat steps 2-5 on remaining fault domains

## 1. Stage Upgrade VIBs Depot on Bootstrap Host

- Download the offline upgrade bundle for the target ESXi version from VMware Customer Connect and upload to the bootstrap server `/images` directory
- Execute the `tools/stage_esxi_upgrade.sh` script:

```bash
tools/stage_esxi_upgrade.sh /images/${offline_upgrade_bundle_file.zip}
```

- Modify the `tools/upgrade.sh` script to include the root password for the hosts and the path to the VIB Depot

```bash
# Configuration
export GOVC_INSECURE=1
export GOVC_USERNAME=root
export GOVC_PASSWORD='${host_root_pw}'
export GOVC_BINARY='/usr/local/bin/govc'
export DEPOT_URL='http://${bootstrap_host}/depot/${depot_dir}/index.xml'
export GOVC_HOST=$1
```

## 2. Put Fault Domain in Maintenance Mode

- Prepare a copy of the AZ's Ansible vars.yml that only includes the hosts in the fault domain being upgraded
- Manually shut down Edge VMs in fault domain being upgraded (Right click VM and choose Power > Shut Down Guest OS)
- Execute the `enter_mtce_mode_all.yml` playbook using the YAML file created in the first step

```bash
ansible-playbook -e "@playbooks/vars_${rack_number}.yml" playbooks/lib/esx/enter_mtce_mode_all.yml
```

- Monitor the progress of hosts going into maintenance mode. Keep an eye out for any VMs not being vMotioned and take appropriate action
- Once all hosts in the fault domain are in maintenance mode, move on to the next steps, but not before.

**NOTE:** Certain VMs will prevent the host entering maintenance mode, for example VMs with SR-IOV interfaces and CommVault VSA VMs. This will mean you have to manually vMotion or shut down these VMs before the host can enter maintenance mode. Ideally, these VMs should be moved to a dedicated cluster where they will not interfere with the general population of VMs that can support vMotion.

**WARNING:** Do not continue to the next step until all hosts in the fault domain are showing in maintenance mode

## 3. Execute ESXi Host Upgrades in Parallel

- Using the `parallel` command, execute the `tools/upgrade.sh` script on all hosts in the fault domain at the same time. Modify the example below to match your hosts:

```bash
parallel -P0 tools/upgrade.sh ::: wlfdle4000ru{01..16}r.cc.net.rogers.com   <<< modify the hosts site/rack and index to match
```

- Once the hosts install the patch they will be rebooted automatically. Monitor the hosts in vCenter or system console.
- **Optional:** Perform NSX-T VIB updates prior to bringing host out of maintenance mode (procedure covered in `NSX-T Upgrade Procedure.md`)
- When all hosts are back online and showing in Maintenance Mode in vCenter you can proceed below.

    **DO NOT CONTINUE UNTIL ALL HOSTS IN THE FAULT DOMAIN ARE SHOWING ONLINE AND IN MAINTENANCE MODE**

## 4. Exit all Hosts in Fault Domain from Maintenance Mode

- Using the `parallel` command, execute the `tools/exit_mtce_mode.sh` script on all hosts in the fault domain at the same time. Modify the example below to match your hosts:

```bash
parallel -P0 tools/exit_mtce_mode.sh ::: wlfdle4000ru{01..16}r.cc.net.rogers.com   <<< modify the hosts site/rack and index to match
```

## 5. Validate Cluster Health

- Execute a VSAN Skyline Health check on the cluster
- Verify alarms on the Cluster and Hosts level for all nodes in the cluster
- Re-taga any new vSAN File Service VMs in NSX-T under the `AppId: infra-nfs` tag, otherwise they will be unreachable due to DFW policy

## 6. Continue to Next Fault Domain

Only once the cluster is in a clean state should the next fault domain upgarde be attempted. Follow the steps 2-5 above to repeat for each fault domain in the AZ.
