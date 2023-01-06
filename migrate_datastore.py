#! /usr/bin/env python3

import argparse


from pyVim.connect import SmartConnect, Disconnect
import pyVmomi
from pyVim import task

import re

def GetArgs():
   parser = argparse.ArgumentParser(
       description="This is tool to migrate virtual machine to adatastore")
   parser.add_argument('-S', '--vcHost', dest='host', action='store',
                       help='VC host to connect. (Required)')
   parser.add_argument('-u', '--user', default='administrator@vsphere.local',
                       help='User name of vc host. (Default: \'administrator@vsphere.local\')')
   parser.add_argument('-p', '--password', default='Admin!23',
                       help='Password of vc host.')
   parser.add_argument('-s', '--sourceDatastore', dest='sourecedatastore',
                       help="Specify the source datastore.")
   parser.add_argument('-d', '--ds', dest='datastore',
                       help="Specify the destination datastore.")
   parser.add_argument('-k', '--vm', dest='vm',
                       help="Specify the VM names need to be relocated. (Regular Expression, Case insitiv). Sample: --vm vmxxx")
   parser.add_argument('-f', '--folder', dest='folder',
                       help="Specify the Folder name need to be relocated. (Regular Expression, Case insitiv). Sample: --folder kunde1")
   parser.add_argument('-v', '--verbose', dest='verbose', default=False, action="store_true",
                       help="verbose\nSample: --debug 1")
   parser.add_argument('-x', '--exclude', dest='exclude', 
                       help="exclude\nSample: --exclude VM-NAME123")
   parser.add_argument('-n', '--dryrun', dest='dryrun', default=False, action="store_true",
                       help="dry-run\nSample: --dryrun")
#   parser.add_argument('-P', '--provisionType', dest='provisionType', default='thick',
#                       help='Virtual disk provision type, supports: thin, thick; if omitted, thick will be taken',)
   args = parser.parse_args()
   #if args.action not in ('relocate_vm'\
   #   'listVMs') or not args.host:
   #   parser.print_help()
   return args

def main():
    args = GetArgs()
    if not args.datastore:
        print("-d/--datastore is required!")
        return

    vcenter_server = args.host
    username = args.user
    password = args.password
    dest_datastore = args.datastore
    verbose = args.verbose

    si = SmartConnect(host=vcenter_server, user=username, pwd=password, disableSslCertValidation=True)
    vm_list = []
    datacenters = si.content.rootFolder.childEntity
    for datacenter in datacenters:
        if verbose: print("Datacenter: " + datacenter.name)

        # Search for Destination Datastore
        found_ds = False
        destination_ds = []
        for ds in datacenter.datastoreFolder.childEntity:
            obj_type = type(ds).__name__
            if obj_type == 'vim.Datastore':
                if ds.name == dest_datastore:
                    if verbose: print("Found destination datastore: " + ds.name)
                    found_ds = True
                    destination_ds = ds
        if found_ds == False:
            print("Destination datastore not found")
            exit()

        # List VMs
        vm_view = si.content.viewManager.CreateContainerView(datacenter, [pyVmomi.vim.VirtualMachine], True)
        vms_list = vm_view.view
        vm_view.Destroy()

        # Loop through VMs
        for vm in vms_list:
            if verbose: print("VM: " + vm.name)
            is_on_dest_ds = False
            if args.sourecedatastore:
                is_on_src_ds = False
            else:
                is_on_src_ds = True
            for device in vm.config.hardware.device:
                if isinstance(device, pyVmomi.vim.vm.device.VirtualDisk):
                    if device.backing.datastore.name == args.datastore:
                        is_on_dest_ds = True
                        if verbose: print("  Found on DEST Datastore " + args.datastore + ": "+ vm.name)
                    if args.sourecedatastore and device.backing.datastore.name == args.sourecedatastore:
                        is_on_src_ds = True
                        if verbose: print("  Found on SOURCE Datastore " + args.sourecedatastore + ": "+ vm.name)
            if not is_on_dest_ds and is_on_src_ds:
                if vm.runtime.powerState == "poweredOn":
                    if verbose: print("VM is powered on")
                    if verbose: print("Folder name: " + vm.parent.name)
                    if not args.folder or (args.folder and re.search(args.folder,vm.parent.name+"/"+vm.parent.parent.name ,re.IGNORECASE)):
                        if not args.vm or (args.vm and re.search(args.vm, vm.name,re.IGNORECASE)):
                            if args.exclude and (args.exclude and re.search(args.exclude, vm.name,re.IGNORECASE )):
                                print("NOT Migrating VM: (excluded)" + vm.name)
                            else:
                                print("Migrating VM: " + vm.name)
                                if not args.dryrun:
                                    t = vm.Relocate(spec=pyVmomi.vim.vm.RelocateSpec(datastore=destination_ds))
                                    task.WaitForTask(t)
                                    print("VM migrated")
                                else:
                                    print("Dryrun: VM not migrated")
        #break
    Disconnect(si)


if __name__ == "__main__":
   main()