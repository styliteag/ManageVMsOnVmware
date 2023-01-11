#! /usr/bin/env pwsh

Import-Module VMware.PowerCLI

## Set-PowerCLIConfiguration -Scope User -InvalidCertificateAction ignore

# Connect to the vCenter server
$server = Connect-VIServer -Server $server -User $username -Password $password

# Get a list of all running virtual machines
$vms = Get-VM | Where-Object {$_.PowerState -eq "PoweredOn"} | Where-Object {$_.Name -eq "dev"} | Sort-Object Name 

for vm in $vms {
    Write-Host "Performing storage vMotion for VM $($vm.Name)..."
    ##Wait-mTaskvMotions -vMotionLimit 1 -DelaySeconds 10
    Move-VM -VM $vm -Datastore $datastore -Confirm:$false -WhatIf:$true -RunAsync
}