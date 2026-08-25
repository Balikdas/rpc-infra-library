# Configure ServiceNow vCenter Access

For the new build vCenters, below are the details of configurations needed for ServiceNow discovery at vCenter level.

## Create the Permission Mapping File

- Create the list of permissions in a file named `ServiceNowRole.txt`:

```text
System.Anonymous
System.Read
System.View
```

## Create the vCenter Host Mapping File

- Create the list of vCenter server FQDNs in a file named `ServiceNowVCs.txt`:

```text
rncc-svc-sde-wlfdle.cc.net.rogers.com
rncc-svc-rcmin-wlfdle.cc.net.rogers.com
[...]
```

## Create PowerShell Script for ServiceNow vCenter Access

- Create Powershell the script named `ServiceNowDiscovery.ps1` to create a Role name "ServiceNow Discovery Role" and create a top-level vCenter permission for the ServiceNow service account:

```powershell
param ([string]$Role = $(Read-Host "Role"), [string]$User = $(Read-Host "User"))

# Read the permissions file
$PermissionsFile = "ServiceNowRole.txt"
$Permissions = @()
Get-Content $PermissionsFile | foreach-Object{$Permissions += $_}

# Read the vCenter list file
$VcenterFile = "ServiceNowVCs.txt"
$Vcenters = @()
Get-Content $VcenterFile | foreach-Object{$Vcenters += $_}

# Get user credentials
$VCUser = Read-Host -Prompt "Enter vCenter Username"
$Password = Read-Host -Prompt "Enter vCenter Password" -MaskInput

# Iterate over the list of vCenters and run the commands
foreach ($Server in $Vcenters) {

  # Connect to vCenter and check to see if the role exists
  import-module VMware.VimAutomation.Core
  Set-PowerCLIConfiguration -InvalidCertificateAction Ignore -Confirm:$false
  Connect-VIServer -server $Server -User $VCUser -Password $Password

  $existingRole = Get-VIRole -name $Role -ErrorAction SilentlyContinue
  $privs = Get-VIPrivilege -Server $Server -id $Permissions -ErrorAction SilentlyContinue

  # Create or update the role
  if (!$existingRole) {New-VIRole -name $Role -Privilege $privs -Server $Server}
  else {Set-VIRole -Role $Role -AddPrivilege $privs -Server $Server}

  # Define top-level entity folder
  $RootFolder = Get-Folder -NoRecursion

  # Create the permission at the root level and propagate to children
  New-VIPermission -Entity $RootFolder -Principal $User -Role $Role -Propagate $true

  # Disconnect from the server
  Disconnect-VIServer -server $Server -Confirm:$FALSE

}
```

## Run the PowerShell Script

```bash
pwsh -file ServiceNowDiscovery.ps1 -Role "ServiceNow Discovery Role" -User "OSS.ROGERS.COM\serv_oss_vcentre_dis"
```
