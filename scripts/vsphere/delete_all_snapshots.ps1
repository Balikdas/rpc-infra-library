$Server = Read-Host -Prompt "Enter vCenter Hostname/IP"
$VCUser = Read-Host -Prompt "Enter vCenter Username"
$Password = Read-Host -Prompt "Enter vCenter Password" -MaskInput

Connect-VIServer -server $Server -User $VCUser -Password $Password

$allSnapshots = Get-VM | Get-Snapshot

if ($allSnapshots) {
  foreach ($snap in $allSnapshots) {
    Write-Host "Deleting snapshot '$($snap.Name)' on VM '$($snap.VM.Name)'..." -ForegroundColor Yellow
    Remove-Snapshot -Snapshot $snap -Confirm:$false -RunAsync
  }
  Write-Host "All snapshot deletion tasks have been initiated." -ForegroundColor Green
}
else {
  Write-Host "No snapshots found in the environment." -ForegroundColor Cyan
}

Disconnect-VIServer -Confirm:$false
