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
       description="Tool to rename virtual machines")
   parser.add_argument('-S', '--vcHost', dest='host', action='store',
                       help='VC host to connect. (Required)')
   parser.add_argument('-u', '--user', default='administrator@vsphere.local',
                       help='User name of vc host. (Default: \'administrator@vsphere.local\')')
   parser.add_argument('-p', '--password', default='Admin!23',
                       help='Password of vc host.')
   parser.add_argument('-k', '--vm', dest='vm',
                       help="Specify the VM names to rename. (Regular Expression, Case insensitive). Sample: --vm vmxxx")
   parser.add_argument('-f', '--folder', dest='folder',
                       help="Specify the Folder name. (Regular Expression, Case insensitive). Sample: --folder kunde1")
   parser.add_argument('-o', '--poweredoff', dest='poweredoff', default=False, action="store_true",
                       help="only powered off VMs\nSample: --poweredoff")
   parser.add_argument('--suffix', dest='suffix',
                       help="Add suffix to VM name\nSample: --suffix _off")
   parser.add_argument('--prefix', dest='prefix',
                       help="Add prefix to VM name\nSample: --prefix OFF_")
   parser.add_argument('--remove-suffix', dest='remove_suffix',
                       help="Remove suffix from VM name\nSample: --remove-suffix _off")
   parser.add_argument('--remove-prefix', dest='remove_prefix',
                       help="Remove prefix from VM name\nSample: --remove-prefix OFF_")
   parser.add_argument('-t', '--threads', dest='threads', default=1, type=int,
                       help="number of Tasks to start in the vCenter at the same time\nSample: --threads 3")
   parser.add_argument('-v', '--verbose', dest='verbose', default=0, action="count",
                       help="verbose\nSample: -vv")
   parser.add_argument('-x', '--exclude', dest='exclude',
                       help="exclude\nSample: --exclude VM-NAME123")
   parser.add_argument('-n', '--dryrun', dest='dryrun', default=False, action="store_true",
                       help="dry-run\nSample: --dryrun")
   args = parser.parse_args()
   return args

def renameVM(vm, original_name, new_name, dryrun, verbose):
    if verbose: print("Renaming VM: {} -> {}".format(original_name, new_name))
    if not dryrun:
        task.WaitForTask(vm.Rename_Task(newName=new_name))
        print("VM renamed: {} -> {}".format(original_name, new_name))
    else:
        print("DRYRUN: Would rename VM: {} -> {}".format(original_name, new_name))

def processVM(vm, args, verbose):
    original_name = vm.name
    new_name = None
    
    # Check if we should add suffix/prefix
    if args.suffix:
        if not original_name.endswith(args.suffix):
            new_name = original_name + args.suffix
    elif args.prefix:
        if not original_name.startswith(args.prefix):
            new_name = args.prefix + original_name
    # Check if we should remove suffix/prefix
    elif args.remove_suffix:
        if original_name.endswith(args.remove_suffix):
            new_name = original_name[:-len(args.remove_suffix)]
    elif args.remove_prefix:
        if original_name.startswith(args.remove_prefix):
            new_name = original_name[len(args.remove_prefix):]
    
    if new_name and new_name != original_name:
        if verbose >= 1: print("  Processing VM: {} -> {}".format(original_name, new_name))
        return (vm, new_name)
    return None

def main():
    args = GetArgs()
    
    # Validate that exactly one rename operation is specified
    rename_ops = [args.suffix, args.prefix, args.remove_suffix, args.remove_prefix]
    if sum(1 for op in rename_ops if op) != 1:
        print("Error: Exactly one rename operation must be specified (--suffix, --prefix, --remove-suffix, or --remove-prefix)")
        return
    
    verbose = args.verbose

    si = SmartConnect(host=args.host, user=args.user, pwd=args.password, disableSslCertValidation=True)
    vm_list = []
    datacenters = si.content.rootFolder.childEntity
    threads = []
    
    for datacenter in datacenters:
        if verbose >= 2: print("Datacenter: " + datacenter.name)

        # List VMs
        vm_view = si.content.viewManager.CreateContainerView(datacenter, [pyVmomi.vim.VirtualMachine], True)
        vms_list = vm_view.view
        vm_view.Destroy()

        # Loop through VMs
        for vm in vms_list:
            if verbose >= 2: print("VM: " + vm.name)
            if not args.folder or (args.folder and re.search(args.folder, vm.parent.name+"/"+vm.parent.parent.name, re.IGNORECASE)):
                if verbose >= 2: print("  VM Folder: " + vm.parent.name)
                if not args.vm or (args.vm and re.search(args.vm, vm.name, re.IGNORECASE)):
                    if verbose >= 2: print("  VM name: " + vm.name)
                    if not (args.exclude and (args.exclude and re.search(args.exclude, vm.name, re.IGNORECASE))):
                        if verbose >= 2: print("  VM not excluded: " + vm.name)
                        # Check power state: if --poweredoff is set, only process powered off VMs
                        if not args.poweredoff or (args.poweredoff and vm.runtime.powerState == "poweredOff"):
                            if verbose >= 1: print("  Considering VM: " + vm.name + " (PowerState: " + vm.runtime.powerState + ")")
                            result = processVM(vm, args, verbose)
                            if result:
                                vm_obj, new_name = result
                                original_name = vm_obj.name
                                if args.threads > 1:
                                    # start a thread if we have less than args.threads
                                    if len(threads) >= args.threads: 
                                        print("Waiting for a thread to finish")
                                    while len(threads) >= args.threads:
                                        # wait for a thread to finish
                                        print(".", end='', flush=True)
                                        time.sleep(1)
                                        for t in threads:
                                            if not t.is_alive():
                                                threads.remove(t)
                                                break
                                    t = threading.Thread(target=renameVM, args=(vm_obj, original_name, new_name, args.dryrun, verbose))
                                    threads.append(t)
                                    t.start()
                                else:
                                    renameVM(vm_obj, original_name, new_name, args.dryrun, verbose)

    if args.threads > 1:
        # wait for threads to finish
        for t in threads:
            t.join()

    Disconnect(si)


if __name__ == "__main__":
   main()
