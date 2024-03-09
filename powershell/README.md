Install-Module -Name VMware.PowerCLI -Scope CurrentUser -AllowClobber -SkipPublisherCheck

./migrate_datastore.ps1 --Server 10.40.4.10 --Username $USER --Pwd $PASS --DestinationDatastore poolGreen-NFS-esx01-nobackup --SourceDatastore poolRED01-NFS-esx01-nobackup --PoweredOff --ExcludeVMs 'unused|delete|test|off_' --vMotionLimit 2 --DryRun

/migrate_datastore.ps1 --Server 10.30.4.10 --Username $USER --Pwd $PASS --DestinationDatastore green-NFS-stynux01 --ExcludeVMs 'unused|delete|test|off_|old_' --vMotionLimit 3 --DryRun