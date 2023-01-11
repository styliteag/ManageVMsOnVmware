# Check if there are any running VMs
# if ($vms) {
#     # Set the maximum number of concurrent jobs
#     $maxJobs = 3
#     # Initialize a counter for the number of jobs
#     $jobCount = 0
#     # Perform a storage vMotion for each VM
#     foreach ($vm in $vms) {
#       # Start a background job for the vMotion
#       $job = Start-Job -ScriptBlock {
#         param($vm, $datastore)
#         Write-Host "Performing storage vMotion for VM $($vm.Name)..."
#         Move-VM -VM $vm -Datastore $datastore -Confirm:$false
#       } -ArgumentList $vm, $datastore
#       # Increment the job counter
#       $jobCount += 1
#       # Wait for the job to complete if the maximum number of jobs has been reached
#       if ($jobCount -ge $maxJobs) {
#         Wait-Job $job | Out-Null
#         # Get the job results
#         Receive-Job $job
#         # Decrement the job counter
#         $jobCount -= 1
#       }
#     }
#     # Wait for any remaining jobs to complete
#     while ($jobCount -gt 0) {
#       Wait-Job | Out-Null
#       # Get the job results
#       Receive-Job
#       # Decrement the job counter
#       $jobCount -= 1
#     }
#   } else {
#     Write-Host "There are no running VMs on this server"
#   }
