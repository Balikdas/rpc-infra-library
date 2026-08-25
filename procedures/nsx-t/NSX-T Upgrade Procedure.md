# NSX-T Upgrade Procedure

This procedure describes how to upgrade NSX-T in a safe and efficient manner in a OneCloud AZ by making use of rack/fault domain redundancy. This upgrade can be done in conjunction with the ESXi upgrade procedure to minimize the number of vMotions and Maintenance Mode operations.

The upgrade strategy is as follows:

1. Backup the and verify NSX-T environment
2. Obtain and upload the MUB upgrade package to the NSX-T Manager nodes
3. Upgrade edges
4. Prepare to upgrade hosts
5. Put fault domain in Maintenance Mode
6. Upgrade all hosts in fault domain
7. Take fault domain out of maintenance mode
8. Upgrade remaining fault domains
9. Upgrade NSX Managers

## 1. Backup the NSX-T Environment

- In NSX-T Manager go to System > Backup & Restore and take a backup of the node
- Under Home click on Alarms and verify there are no alarms. If there are any alarms, resolve them before moving ahead.

## 2. Load the MUB Upgrade Package to the NSX-T Manager Nodes

- Download the MUB upgrade package from VMware CustomerConnect
- In NSX-T Manager UI, upload the MUB package in the System > Upgrade menu
- When the package has uploaded click the Prepare button to extract and stage the image
- Click the Run Pre-Checks button and ensure all checks pass on Edge, Hosts and NSX Manager

## 3. Upgrade Edges

- Click Edges in the NSX Upgrade menu and click Start. 
- The Upgrade will run in serial mode and no special configuration is required.
- You can observe the status of the node upgrades by clicking on the group name

## 4. Prepare to Upgrade Hosts

- Click Edges in the NSX Upgrade menu
- Under Host Groups, add a custom host group for each fault domain using the rack no. as the name, eg "R4001"
  - Each group should contain only the hosts for that fault domain
  - The Upgrade Order for each group must be set to Parallel
  - The state for each group must be set to Disabled
  - The Upgrade Mode for each group must be set to In-Place
- Remove the deafult group (which now should not contain any hosts)

## 5. Put Fault Domain in Maintenance Mode

- Prepare a copy of the AZ's Ansible vars.yml that only includes the hosts in the fault domain being upgraded
- Maunally shut down Edge VMs in fault domain being upgraded (Right click VM and choose Power > Shut Down Guest OS)
- Execute the `enter_mtce_mode_all.yml` playbook using the YAML file created in the first step

```bash
ansible-playbook -e "@playbooks/vars_${rack_number}.yml" playbooks/lib/esx/enter_mtce_mode_all.yml
```

- Monitor the progress of hosts going into maintenance mode. Keep an eye out for any VMs not being vMotioned and take appropriate action
- Once all hosts in the fault domain are in maintenance mode, move on to the next steps, but not before.

**NOTE:** Certain VMs will prevent the host entering maintenance mode, for example VMs with SR-IOV interfaces and CommVault VSA VMs. This will mean you have to manually vMotion or shut down these VMs before the host can enter maintenance mode. Ideally, these VMs should be moved to a dedicated cluster where they will not interfere with the general population of VMs that can support vMotion.

**WARNING:** Do not continue to the next step until all hosts in the fault domain are showing in maintenance mode

## 6. Upgrade All Hosts in Fault Domain

- In the NSX Upgrade "Hosts" menu, under groups, elect the fault domain that was placed into mainenance mode and click "Actions"
- Set the state to Enabled
- Click Start
- The NSX VIBs will be updated on all hosts in the fault domain in parallel. You can monitor progress by clicking on the group name.
- Once all hosts in the fault fomain are successfully upgraded, continue the below steps, but not before.

## 7. Take Fault Domain Out of Maintenance Mode

- Using the `parallel` command, execute the `tools/exit_mtce_mode.sh` script on all hosts in the fault domain at the same time. Modify the example below to match your hosts:

```bash
parallel -P0 tools/exit_mtce_mode.sh ::: wlfdle4000ru{01..16}r.cc.net.rogers.com   <<< modify the hosts site/rack and index to match
```

## 8. Upgrade Remaining Fault Domains

- Repeat steps 5-7 above on the remaining fault domains
- Once all fault domains are upgraded, proceed to the below steps, but not before

## 9. Upgrade NSX Managers

- In the NSX Manager Upgrade menu, click "NSX Managers" and click start.
- The NSX Manager upgrade executes on one NSX Manager node at a time. You can monitor the progress from the NSX Manager
- During the upgrade process the NSX Managers will be rebooted and you may need to login again after the VIP moves to a new node

## Final Steps

Once the upgrade is complete, check alarms and health of NSX Managers, Edges, Hosts, TEPs (tunnels) and BGP neighbors (on the T0 router). Also perform a few ping tests on some random VMs to check connectivity.

Once the validation is complete, take another backup of the NSX environment by repeating step 1 above.
