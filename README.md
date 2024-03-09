# ManageVMsOnVmware
Scripts do things with VMs on a VMware/VCenter

## Example
```./migrate_datastore_threaded.py -S "<HOSTorIPofVcenter>" -u "<username>" -p'<password>'  -s '<soucePool>' -d '<destinationPool>'   -t <numthreads>  -x "exclude" -n

./migrate_datastore.py -S ***REMOVED*** -u ***REMOVED*** -p '***REMOVED***' -s ***REMOVED*** -d ***REMOVED*** --dryrun

./migrate_datastore_threaded.py -S ***REMOVED*** -u ***REMOVED*** -p '***REMOVED***'  -s ***REMOVED*** -d ***REMOVED***  --powerstate off -t 4 -x 'delete|test|off_|unused' -n
```
