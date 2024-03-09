#! /usr/bin/env pwsh

<#
.NOTES
  Script name: migrate_datastore.ps1
  Created on: 01/01/2023
  Author: Wim Bonis, wb@stylite.de
  Description: Migration of VMs to a new datastore
  Dependencies: None known
 
.SYNOPSIS
.DESCRIPTION
.PARAMETER Server
  IP odr DNS Name of VCenter Server (mandatory)
.PARAMETER Username
  Username to connect to VCenter Server (mandatory)
.PARAMETER Pwd
  Password to connect to VCenter Server (mandatory)
.PARAMETER DestinationDatastore
  Name of the destination datastore (must be a valid datastore name, mandatory)
.PARAMETER SourceDatastore
  Name of the source datastore (must be a valid datastore name, optional)
.PARAMETER PoweredOff
  Migrate only powered off VMs (default: false)
.PARAMETER VMNames
  List of VMs to migrate (default: all VMs)
  Can be a comma separated list of Names OR a wildcard expression (e.g. VMname*)
.PARAMETER FolderNames
  List of VM in Folders folders to migrate (default: all folders)
  Checks also one parent folder up (e.g. Foldername1/Foldername2/VMname)
  Can be a comma separated list of Names OR a wildcard expression (e.g. Foldername*)
.PARAMETER vMotionLimit
  Maximum number of vMotions to run in parallel (default: 0)
  When it is set to 0, it will wait the current vMotions to finish before starting the next one. (Single threaded)
.PARAMETER DelaySeconds
  Number of seconds to wait before checking for running vMotions (default: 30)
.PARAMETER ExcludeVMs
  List of VMs to exclude from migration (default: none)
  Can be a comma separated list of Names OR a wildcard expression (e.g. VMname*)
.PARAMETER DryRun
  Do not perform the migration, only show what would be done (default: false)

.EXAMPLE
  migrate_datastore.ps1 -Server IP -Username admin@vsphere.local -Pwd 'password' -DestinationDatastore 'poolBLUE-NFS-esx01' -VmNames turn*  -Verbose
.EXAMPLE
  migrate_datastore.ps1 -Server IP -Username admin@vsphere.local -Pwd 'password' -DestinationDatastore 'poolBLUE-NFS-esx01' -VmNames turn1,turn2 -SourceDatastore 'poolBLUE-NFS-esx02,


#>
#Requires -modules VMware.PowerCLI

[CmdletBinding()]
Param (
  [Parameter(Mandatory=$true,Position=0)][string]$Server = "vcenter",
  [Parameter(Mandatory=$true,Position=1)][string]$Username = "addministrator@vsphere.local",
  [Parameter(Mandatory=$true,Position=2)][string]$Pwd = "password",
  [Parameter(Mandatory=$true,Position=3)][string]$DestinationDatastore = "Datastore1",
  [string]$SourceDatastore,
  [switch]$PoweredOff = $false,
  [int]$vMotionLimit=0,
  [int]$DelaySeconds=30,
  [string[]]$ExcludeVMs = @(),
  [switch]$DryRun = $false,
  [string[]]$VMNames = @(),
  [string[]]$FolderNames = @()
)

function Wait-TaskvMotion_ispresent {
  [CmdletBinding()]
  Param(
    $TaskID
  )

  Write-Verbose "$(Get-Date)- Waiting for Task $TaskID to show up."
  # Wait for the Task to show up
  $Task = ((Get-Task -ID $TaskID | Where-Object { ( $_.Name -like "RelocateVM_Task" -and $_.State -like "Running")}) | Measure-Object).Count
  while ( $Task -eq 0 )
  {
    #Write-Verbose "." -NoNewline
    Start-Sleep (5)
    $Task = ((Get-Task -ID $TaskID | Where-Object { ( $_.Name -like "RelocateVM_Task" -and $_.State -like "Running")}) | Measure-Object).Count
  } # end while
  Write-Verbose " Wait Completed."

} # end function

function Wait-TaskvMotions {
  [CmdletBinding()]
  Param(
    [int] $vMotionLimit=1,
    [int] $DelaySeconds=30
  )

  # Wait because Task do not show up immediately
  # Start-Sleep ($DelaySeconds)

  Write-Host "    $(Get-Date)- Waiting for not more than $($vMotionLimit) vMotions to run."

  while ( ((Get-Task | Where-Object { ($_.Name -like "RelocateVM_Task" -and $_.State -like "Running")} | Measure-Object).Count) -ge $vMotionLimit  )
  {
   Write-Verbose "    $(Get-Date)- Waiting $($DelaySeconds) seconds before checking again."
   Start-Sleep ($DelaySeconds)
  }
  Write-Verbose "    $(Get-Date) - Proceeding."
} # end function

if ($vCenter) {
  Connect-VIServer $vCenter
}
##Write-Output "Hello World!"
# Import the VMware PowerCLI module
#Write-Output "Importing VMware.PowerCLI module..."
Import-Module VMware.PowerCLI
#Write-Output "Imported VMware.PowerCLI module"

## Set-PowerCLIConfiguration -Scope User -InvalidCertificateAction ignore

# Connect to the vCenter server
$vi = Connect-VIServer -Server $server -User $username -Password $pwd -Force

# Check the connection status
if ($vi.isconnected) {
  Write-Output "Successfully connected to vCenter server $server"
} else {
  Write-Output "Failed to connect to vCenter server $server"
  exit
}



if ($DestinationDatastore) {
  $DestDatastore = Get-Datastore -Name $DestinationDatastore
  if ($DestDatastore) {
    Write-Output "Destination Datastore: $DestDatastore"
    $DestDatastoreID = $DestDatastore.Id
  } else {
    Write-Output "Destination Datastore $DestinationDatastore not found"
    exit
  }
} else {
  Write-Output "Destination Datastore not specified"
  exit
}

# Get a list of all running virtual machines
# $vms = Get-VM | Where-Object {$_.PowerState -eq "PoweredOn"} | Sort-Object Name 

$vms = Get-VM | Sort-Object UsedSpaceGB -Descending

if ($PoweredOff -eq $false) {
  $vms = $vms | Where-Object {$_.PowerState -eq "PoweredOn"}
} else {
  $vms = $vms | Where-Object {$_.PowerState -ne "PoweredOn"}
}

if ($VMNames) {
  if (@($VMNames).count -eq 1) {
    $vms = $vms | Where-Object {$_.Name -like "$VMNames"}
  } else {
    $vms = $vms | Where-Object {$_.Name -in $VMNames }
  }
}
if($FolderNames) {
  if (@($FolderNames).count -eq 1) {
    $vms = $vms | Where-Object {$_.Folder.Name -like "$FolderNames*" -or $_.Folder.Parent.Name -like "$FolderNames"} 
  } else {
    $vms = $vms | Where-Object {$_.Folder.Name -in $FolderNames -or $_.Folder.Parent.Name -in $FolderNames}
  }
}

if ($SourceDatastore) {
  $SourceDatastoreID = (Get-Datastore -Name $SourceDatastore).Id
  if ($SourceDatastoreID) {
    Write-Output "Source Datastore ID: $SourceDatastoreID"
  } else {
    Write-Output "Source Datastore $SourceDatastore not found"
    exit
  }
  $vms = $vms | Where-Object {$SourceDatastoreID -in $_.DatastoreIdList}
}
if ($DestDatastoreID) {
  $vms = $vms | Where-Object {$DestDatastoreID -notin $_.DatastoreIdList}
}

if ($ExcludeVMs) {
  if (@($ExcludeVMs).count -eq 1) {
    $vms = $vms | Where-Object {$_.Name -notmatch "$ExcludeVMs"}
  } else {
    $vms = $vms | Where-Object {$_.Name -notin $ExcludeVMs}
  }
}

# Check if there are any running VMs
if ($vms) {
  Write-Host "=============================================================="
  foreach ($vm in $vms) {
    $UsedSpaceGB = [math]::Round($vm.UsedSpaceGB,2)
    Write-Host " VM: $($vm.Name) - $($UsedSpaceGB)GB - $($vm.Folder.Name) - $($vm.PowerState)"
  }
  Write-Host "=============================================================="
  # Perform a storage vMotion for each VM
  foreach ($vm in $vms) {
    Write-Host "Performing storage vMotion for VM $($vm.Name) to $($DestDatastore.Name)"
    if ($DryRun -eq $false) {
      if ($vMotionLimit -gt 0) {
        Wait-TaskvMotions -vMotionLimit $vMotionLimit -DelaySeconds $DelaySeconds
        $task = Move-VM -VM $vm -Datastore $DestDatastore -Confirm:$false -WhatIf:$DryRun -RunAsync
        if ($null -eq $task) {
          Write-Host "$(Get-Date)- Error: vMotion for $($vm.Name) failed"
          # Exit powershell script with error
          Exit-PSHostProcess -ExitCode 1
        }
        Write-Verbose "Task   : $($task) submitted"
        Write-Verbose "Task ID: $($task.Id)"
        Wait-TaskvMotion_ispresent -TaskID $task.Id
      } else {
        # Single theraded
        $now = Get-Date
        Write-Host "$(Get-Date)- Starting vMotion for $($vm.Name)"
        $task = Move-VM -VM $vm -Datastore $DestDatastore -Confirm:$false -WhatIf:$DryRun 
        # Check for errors
        if ($null -eq $task) {
          Write-Host "$(Get-Date)- Error: vMotion for $($vm.Name) failed"
          # Exit with error
          exit
        }
        Write-Host "$(Get-Date)- Finished vMotion for $($vm.Name)"
        $timetaken = (Get-Date) - $now
        # Time in Seconds
        $seconds = $timetaken.TotalSeconds
        Write-Host "       - Time taken: $($timetaken)" 
        Write-Host "         $([math]::Round($seconds,2)) seconds"
        Write-Host "         $([math]::Round($seconds/60,2)) minutes"
        Write-Host "       - Time per GB: $([math]::Round($seconds/$UsedSpaceGB,2)) seconds"
        Write-Host "       - Time per TB: $([math]::Round((1024/60)*$seconds/$UsedSpaceGB,2)) minutes"
        #Write-Host "       - Transfer rate: $([math]::Round($UsedSpaceGB/$seconds,2)) GB/s"
        Write-Host "       - Transfer rate: $([math]::Round($UsedSpaceGB*8/$seconds,2)) Gb/s"
        
      }
    } else {
      Write-Host "Dry Run: $($vm.Name) would be moved to $($DestDatastore.Name)"
    }
  }
} else {
  Write-Host "There are no VMs matching to migrate"
}

# Disconnect from the vCenter server
Disconnect-VIServer -Server $server -Confirm:$false
