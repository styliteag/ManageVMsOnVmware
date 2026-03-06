# ManageVMsOnVmware
Scripts do things with VMs on a VMware/VCenter

## Example
```./migrate_datastore_threaded.py -S "<HOSTorIPofVcenter>" -u "<username>" -p'<password>'  -s '<soucePool>' -d '<destinationPool>'   -t <numthreads>  -x "exclude" -n

./migrate_datastore.py -S <HOSTorIPofVcenter> -u <username> -p '<password>' -s <sourcePool> -d <destinationPool> --dryrun

./migrate_datastore_threaded.py -S <HOSTorIPofVcenter> -u <username> -p '<password>'  -s <sourcePool> -d <destinationPool>  --powerstate off -t 4 -x 'delete|test|off_|unused' -n
```
