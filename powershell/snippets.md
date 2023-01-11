
 Get-VM | Get-Snapshot | Where { $_.name -like "#Patching#*" -and $_.created -lt (get-date).addDays(-7) } | Remove-Shapshot -confirm:$false -whatif



Get-VM VM1 | Move-VM -Destination (Get-VMHost ESX-02.pnl.com)



Get-VMHost ESX-01.pnl.com | Get-VM | Move-VM -Destination (Get-VMHost ESX-02.pnl.com)