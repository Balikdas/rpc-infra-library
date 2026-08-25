# RNCC Generic Upgrade Procedure

This document outlines the steps required to ugprade the RNCC Generic infrastructure to the target versions listed below:

## Target Versions (as of Q124)

|Product|Target Version|
|-------|--------------|
|VMware vCenter Server Appliance|8.0U2a (build 22617221)|
|VMware ESXi|8.0U2 (build 22380479)|
|VMware vSAN Standard Edition|8.0U2 (build 22380479)|
|VMware NSX|4.1.1|
|VMware Aria Operations|8.14.1 (build 22798982)|
|VMware Aria Operations for Logs|8.14.1 (build 22806512)|
|VMware Aria Operations for Networks|6.12.0 (build 1706185032)|
|VMware Aria Automation|8.16.0.33697 (build 23103949)|
|VMware Aria Suite Lifecycle|8.14.0.4 (build 22630472)|
|VMware Identity Manager|3.3.7.0 (build 21173100)|
|VMware Skyline|3.5.0.2|
|Service Pack for ProLiant (Gen10)|2023.09.00.04|
|Service Pack for ProLiant (Gen11)|2023.10.00.00|
|HPE OneView|8.70|
|Intel XXV710 Firmware|9.40|

## Upgrade High Level Steps

- Upgrade HPE OneView Global Dashboard
- Upgrade IVC (MGMT/CP) vCenters
- Upgrade vRLCM
- Upgrade vIDM
- Upgrade vROPS
- Upgrade vRLI (if lower than 8.12 upgrade to 8.12 first)
- Upgrade vRNI (can only upgrde 2 release versions at a time)
- Upgrade vRA
- Upgrade Skyline
- Upgrade other control plane VMs (DHCP/Bootstrap etc)
- Going AZ by AZ (starting with IVC):
  - Upgrade HPE OneView Local Applicances
  - Upgrade SVC (Workload) vCenter
  - Upgrade NSX (if lower than 3.2.2, must upgrade to 3.2.2 first)
  - Going host by host:
    - Upgrade ESXi via mub using provided upgrade script on bootstrap server
    - During reboot after ESXI upgrade, upgrade firmware using provided bundle (booted via UEFI HTTP from bootstrap server)
  - Upgrade VSAN disk format version once all hosts in cluster are at the required version
