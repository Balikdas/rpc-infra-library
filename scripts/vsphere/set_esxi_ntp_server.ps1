[CmdletBinding()]
param (
  [Parameter(Mandatory = $true, HelpMessage = "Enter the vCenter FQDN or IP address")]
  [string]$vCenter,

  [Parameter(Mandatory = $true, HelpMessage = "Enter the NTP Server FQDN or IP address")]
  [string]$NTPServer
)

# Import PowerCLI Module safely
if (-not (Get-Module -Name VMware.PowerCLI -ErrorAction SilentlyContinue)) {
  Import-Module VMware.PowerCLI -ErrorAction SilentlyContinue
}

# Validate PowerCLI availability
if (-not (Get-Command Connect-VIServer -ErrorAction SilentlyContinue)) {
  Write-Error "VMware PowerCLI module is not installed. Please run 'Install-Module VMware.PowerCLI'."
  exit
}

try {
  # Connect to vCenter Server
  Write-Host "Connecting to vCenter: $vCenter..." -ForegroundColor Yellow
  $Session = Connect-VIServer -Server $vCenter -ErrorAction Stop
    
  # Automatically discover all connected or maintenance-mode hosts
  Write-Host "Discovering all managed ESXi hosts..." -ForegroundColor Yellow
  $ESXiHosts = Get-VMHost | Where-Object { $_.ConnectionState -in "Connected", "Maintenance" }
    
  if (-not $ESXiHosts) {
    Write-Warning "No active ESXi hosts found on $vCenter."
    return
  }

  Write-Host "Found $($ESXiHosts.Count) host(s). Starting NTP configuration..." -ForegroundColor Cyan

  foreach ($ESXi in $ESXiHosts) {
    Write-Host "Processing host: $($ESXi.Name)" -ForegroundColor Cyan
        
    try {
      # Get current NTP configuration
      $NTPConfig = Get-VMHostNtpServer -VMHost $ESXi
            
      # Remove existing NTP servers if present to ensure clean state
      if ($NTPConfig) {
        Remove-VMHostNtpServer -VMHost $ESXi -NTPserver $NTPConfig -Confirm:$false | Out-Null
      }
            
      # Add the new NTP server
      Add-VMHostNtpServer -VMHost $ESXi -NTPserver $NTPServer | Out-Null
            
      # Set NTP service policy to start and stop with host (Automatic)
      $NTPService = Get-VmHostService -VMHost $ESXi | Where-Object { $_.Key -eq "ntpd" }
      Set-VMHostService -HostService $NTPService -Policy "Automatic" | Out-Null
            
      # Restart NTP service to apply changes immediately
      Restart-VMHostService -HostService $NTPService -Confirm:$false | Out-Null
            
      Write-Host "Successfully updated NTP for $($ESXi.Name)" -ForegroundColor Green
    }
    catch {
      Write-Error "Failed to update NTP on $($ESXi.Name). Error: $_"
    }
  }
}
catch {
  Write-Error "Failed to connect to vCenter $vCenter. Error: $_"
}
finally {
  # Disconnect from vCenter safely if connected
  if ($Session -and $Session.IsConnected) {
    Disconnect-VIServer -Server $vCenter -Confirm:$false | Out-Null
    Write-Host "Disconnected from vCenter." -ForegroundColor Yellow
  }
}
