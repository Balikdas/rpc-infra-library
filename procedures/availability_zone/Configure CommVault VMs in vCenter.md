# Configure CommVault VMs in vCenter

For the new build vCenter or VSA VM, below are the details of configurations needed for CommVault at vCenter and VM level.

## Add vCenter Role Creation

- Create the list of permissions in a file named `CommVault-VSA.txt`:

```text
Alarm.Acknowledge
Alarm.SetStatus
Cryptographer.AddDisk
Cryptographer.Access
Cryptographer.Encrypt
Datastore.AllocateSpace
Datastore.Browse
Datastore.Config
Datastore.FileManagement
Datastore.Rename
Datastore.UpdateVirtualMachineFiles
Extension.Register
Extension.Unregister
Extension.Update
Global.CancelTask
Global.Diagnostics
Global.DisableMethods
Global.EnableMethods
Global.Licenses
Global.LogEvent
Global.ManageCustomFields
Global.SetCustomField
Host.Config.AdvancedConfig
Host.Config.Connection
Host.Config.Storage
Host.Config.SystemManagement
Network.Assign
StorageProfile.Update
StorageProfile.View
Resource.AssignVAppToPool
Resource.AssignVMToPool
Resource.ColdMigrate
Resource.HotMigrate
VApp.ApplicationConfig
VApp.Import
VApp.InstanceConfig
System.Anonymous
System.Read
System.View
VirtualMachine.Config.AddExistingDisk
VirtualMachine.Config.AddNewDisk
VirtualMachine.Config.AddRemoveDevice
VirtualMachine.Config.AdvancedConfig
VirtualMachine.Config.Annotation
VirtualMachine.Config.CPUCount
VirtualMachine.Config.ChangeTracking
VirtualMachine.Config.DiskExtend
VirtualMachine.Config.DiskLease
VirtualMachine.Config.EditDevice
VirtualMachine.Config.HostUSBDevice
VirtualMachine.Config.Memory
VirtualMachine.Config.MksControl
VirtualMachine.Config.RawDevice
VirtualMachine.Config.ReloadFromPath
VirtualMachine.Config.RemoveDisk
VirtualMachine.Config.Rename
VirtualMachine.Config.ResetGuestInfo
VirtualMachine.Config.Resource
VirtualMachine.Config.Settings
VirtualMachine.Config.SwapPlacement
VirtualMachine.Config.Unlock
VirtualMachine.Config.UpgradeVirtualHardware
VirtualMachine.GuestOperations.Execute
VirtualMachine.GuestOperations.Modify
VirtualMachine.GuestOperations.Query
VirtualMachine.Interact.DeviceConnection
VirtualMachine.Interact.PowerOff
VirtualMachine.Interact.PowerOn
VirtualMachine.Interact.Reset
VirtualMachine.Interact.Suspend
VirtualMachine.Inventory.Create
VirtualMachine.Inventory.CreateFromExisting
VirtualMachine.Inventory.Delete
VirtualMachine.Inventory.Move
VirtualMachine.Inventory.Register
VirtualMachine.Inventory.Unregister
VirtualMachine.Provisioning.Clone
VirtualMachine.Provisioning.CloneTemplate
VirtualMachine.Provisioning.Customize
VirtualMachine.Provisioning.DeployTemplate
VirtualMachine.Provisioning.DiskRandomAccess
VirtualMachine.Provisioning.DiskRandomRead
VirtualMachine.Provisioning.GetVmFiles
VirtualMachine.Provisioning.MarkAsTemplate
VirtualMachine.Provisioning.MarkAsVM
VirtualMachine.Provisioning.ModifyCustSpecs
VirtualMachine.Provisioning.PromoteDisks
VirtualMachine.Provisioning.ReadCustSpecs
VirtualMachine.State.CreateSnapshot
VirtualMachine.State.RemoveSnapshot
VirtualMachine.State.RenameSnapshot
VirtualMachine.State.RevertToSnapshot
InventoryService.Tagging.AttachTag
InventoryService.Tagging.CreateTag
InventoryService.Tagging.CreateCategory
InventoryService.Tagging.EditTag
InventoryService.Tagging.EditCategory
InventoryService.Tagging.ModifyUsedByForTag
InventoryService.Tagging.ModifyUsedByForCategory
```

- Create Powershell the script named `CommVault-VSA.ps1` to create a Role name "Commvault-VSA":

```powershell
param ([string]$Role = $(Read-Host "Role"), [string]$Server = $(Read-Host "Server"))

# Read the permissions file
$PermissionsFile = "CommVault-VSA.txt"
$cvPermissions = @()

Get-Content $PermissionsFile | foreach-Object{$cvPermissions += $_}

# Connect to vCenter and check to see if the role exists
import-module VMware.VimAutomation.Core
Set-PowerCLIConfiguration -InvalidCertificateAction Ignore -Confirm:$false
Connect-VIServer -server $Server

$existingRole = Get-VIRole -name $Role -ErrorAction SilentlyContinue
$privs = Get-VIPrivilege -Server $Server -id $cvPermissions -ErrorAction SilentlyContinue

# Create or update the role
if (!$existingRole) {New-VIRole -name $Role -Privilege $privs -Server $Server}
else {Set-VIRole -Role $Role -AddPrivilege $privs -Server $Server}

# Disconnect from the server
Disconnect-VIServer -server $Server -Confirm:$FALSE
```

- Run the script

```bash
pwsh -file CommVault-VSA.ps1 -Role "Commvault-VSA" -Server ${vcenter_server_fqdn}
```

- Add a global permission (propagated to children) for the CommVault backup service account `svc_eng_cvbkp_adsso` with role "Commvault-VSA"

## Extra Configuration for VSA VMs

- Add secondary SCSI controller (without any disk attach) for each VSA VM
- Create Anti-affinity rule for VSA VMs
- Add `Virtual Machine console user` permission to the VSA VM folder for below AD groups:

```text
OSSAD_IT_Platform_Engineering_Build
oss_backup_admin
hcl_infra_linux_admin
```
