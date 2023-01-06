# ManageVMsOnVmware
Scripts do things with VMs on a VMware/VCenter

## Example
```./migrate_datastore_threaded.py -S "<HOSTorIPofVcenter>" -u "<username>" -p'<password>'  -s '<soucePool>' -d '<destinationPool>'   -t <numthreads>  -x "exclude" -n