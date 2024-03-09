# ManageVMsOnVmware
Scripts do things with VMs on a VMware/VCenter

## Example
```./migrate_datastore_threaded.py -S "<HOSTorIPofVcenter>" -u "<username>" -p'<password>'  -s '<soucePool>' -d '<destinationPool>'   -t <numthreads>  -x "exclude" -n

./migrate_datastore.py -S 10.40.4.10 -u packer@vms.sty -p '1607069684Aa$' -s poolRED01-NFS-esx01-nobackup -d poolGreen-NFS-esx01-nobackup --dryrun

./migrate_datastore_threaded.py -S 10.40.4.10 -u packer@vms.sty -p '1607069684Aa$'  -s poolRED01-NFS-esx01-nobackup -d poolGreen-NFS-esx01-nobackup  --powerstate off -t 4 -x 'delete|test|off_|unused' -n
```
