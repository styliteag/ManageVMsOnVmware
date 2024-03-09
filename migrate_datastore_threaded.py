#! /usr/bin/env python3

import argparse
import threading
import time
import re

# import the vSphere Python SDK needed modules
import pyVmomi
from pyVim.connect import SmartConnect, Disconnect
from pyVim import task

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
                       help="Specify the VM names need to be relocated. (Regular Expression, Case insensitiv). Sample: --vm vmxxx")
   parser.add_argument('-f', '--folder', dest='folder',
                       help="Specify the Folder name need to be relocated. (Regular Expression, Case insensitiv). Sample: --folder kunde1")
   parser.add_argument('-t', '--threads', dest='threads', default=1, type=int,
                       help="number of Tasks to start in the vCenter at the same time\nSample: --threads 3")
   parser.add_argument('-v', '--verbose', dest='verbose', default=False, action="store_true",
                       help="verbose\nSample: --debug 1")
   parser.add_argument('-x', '--exclude', dest='exclude', 
                       help="exclude\nSample: --exclude VM-NAME123")
   parser.add_argument('-n', '--dryrun', dest='dryrun', default=False, action="store_true",
                       help="dry-run\nSample: --dryrun")
   parser.add_argument('-P', '--powerstate', dest='powerstate', default='on',
                       help="powerstate\nSample: --powerstate on|off default: on")

#   parser.add_argument('-P', '--provisionType', dest='provisionType', default='thick',
#                       help='Virtual disk provision type, supports: thin, thick; if omitted, thick will be taken',)
   args = parser.parse_args()
   #if args.action not in ('relocate_vm'\
   #   'listVMs') or not args.host:
   #   parser.print_help()
   return args

def GetResourcePools(entity):
   pools = []
   for pool in entity.resourcePool:
      pools += GetResourcePools(pool)
   pools.append(entity)
   return pools


def convert_to_template(vm,dc):
    if vm.config.template:
        print("VM is already a template")
    else:
        print("Converting to template")
        vm.MarkAsTemplate()

def convert_to_vm(vm,dc):
    if vm.config.template:
        print("Converting to VM")
        pools = GetResourcePools(dc.hostFolder.childEntity[0].resourcePool)
        if len(pools) == 0:
            print("No resource pool found")
            return
        vm.MarkAsVirtualMachine(pool=pools[0])
        time.sleep(5)
    else:
        print("VM is already a VM")

def relocate_vm(vm, destination_ds, source_dc, verbose):
    # Check if the VM is a template
    convert_back = False
    if vm.config.template:
        print("VM is a template! Convert to VM first")
        convert_to_vm(vm=vm,dc=source_dc)
        convert_back = True
    t1 = vm.Relocate(spec=pyVmomi.vim.vm.RelocateSpec(datastore=destination_ds))
    task.WaitForTask(t1)
    print("VM migrated:" + vm.name)

    if convert_back:
        print("Converting back to template")
        convert_to_template(vm=vm,dc=source_dc)
    return

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
    powerstate = args.powerstate

    if powerstate not in ('on', 'off'):
        print("Invalid powerState: " + powerstate)
        print("Setting powerState to off")
        powerstate = 'off'

    if powerstate == 'on':
        src_state = 'poweredOn'
    elif powerstate == 'off':
        src_state = 'poweredOff'

    si = SmartConnect(host=vcenter_server, user=username, pwd=password, disableSslCertValidation=True)
    vm_list = []
    datacenters = si.content.rootFolder.childEntity
    source_dc = None
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
                    source_dc = datacenter
        if found_ds == False:
            print("Destination datastore not found")
            exit()

        # List VMs
        vm_view = si.content.viewManager.CreateContainerView(datacenter, [pyVmomi.vim.VirtualMachine], True)
        vms_list = vm_view.view
        vm_view.Destroy()

        threads = []
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
                if vm.runtime.powerState == src_state:
                    if verbose: print("VM is $vm.runtime.powerState")
                    if verbose: print("Folder name: " + vm.parent.name)
                    if not args.folder or (args.folder and re.search(args.folder,vm.parent.name+"/"+vm.parent.parent.name ,re.IGNORECASE)):
                        if not args.vm or (args.vm and re.search(args.vm, vm.name,re.IGNORECASE)):
                            if args.exclude and (args.exclude and re.search(args.exclude, vm.name,re.IGNORECASE )):
                                print("NOT Migrating VM: (excluded):" + vm.name)
                            else:
                                print("Migrating VM: " + vm.name)
                                if not args.dryrun:
                                    # print the number of curent threads
                                    print("Current Number of my threads: " + str(len(threads)))
                                    if len(threads) >= args.threads: 
                                        print("Waiting for a thread to finish (" + str(len(threads)) + "/" + str(args.threads) + ")")
                                    while len(threads) >= args.threads:
                                        # wait for a thread to finish
                                        print(".", end='', flush=True)
                                        time.sleep(30)
                                        for t in threads:
                                            if not t.is_alive():
                                                threads.remove(t)
                                                break
                                    t = threading.Thread(target=relocate_vm, args=(vm, destination_ds, source_dc, verbose))
                                    threads.append(t)
                                    t.start()
                                else:
                                    print("Dryrun: VM not migrated")
        #break

    # wait for threads to finish
    for t in threads:
        t.join()

    Disconnect(si)


if __name__ == "__main__":
   main()