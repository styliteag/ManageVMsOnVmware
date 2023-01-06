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
       description="This is tool to remove snapshots from virtual machine")
   parser.add_argument('-S', '--vcHost', dest='host', action='store',
                       help='VC host to connect. (Required)')
   parser.add_argument('-u', '--user', default='administrator@vsphere.local',
                       help='User name of vc host. (Default: \'administrator@vsphere.local\')')
   parser.add_argument('-p', '--password', default='Admin!23',
                       help='Password of vc host.')
   parser.add_argument('-d', '--Datastore', dest='datastore',
                       help="Specify the source datastore.")
   parser.add_argument('-k', '--vm', dest='vm',
                       help="Specify the VM names need to be relocated. (Regular Expression, Case insitiv). Sample: --vm vmxxx")
   parser.add_argument('-f', '--folder', dest='folder',
                       help="Specify the Folder name need to be relocated. (Regular Expression, Case insitiv). Sample: --folder kunde1")
   parser.add_argument('-o', '--poweredon', dest='poweredon', default=False, action="store_true",
                       help="only powered on VMs\nSample: --poweredon")
   parser.add_argument('-s', '--snapshot', dest='snapshot', 
                       help="only Snapshots with name\nSample: --snapshot snapname")
   parser.add_argument('-t', '--threads', dest='threads', default=1, type=int,
                       help="number of Tasks to start in the vCenter at the same time\nSample: --threads 3")
   parser.add_argument('-v', '--verbose', dest='verbose', default=0, action="count",
                       help="verbose\nSample: -vv")
   parser.add_argument('-x', '--exclude', dest='exclude', 
                       help="exclude\nSample: --exclude VM-NAME123")
   
   parser.add_argument('-n', '--dryrun', dest='dryrun', default=False, action="store_true",
                       help="dry-run\nSample: --dryrun")
   args = parser.parse_args()
   #if args.action not in ('relocate_vm','listVMs') or not args.host:
   #   parser.print_help()
   return args

def list_snapshots_recursively(snapshots):
    snapshot_data = []
    for snapshot in snapshots:
        snap_text = "Name: %s; Description: %s; CreateTime: %s; State: %s" % (
                                        snapshot.name, snapshot.description,
                                        snapshot.createTime, snapshot.state)
        snapshot_data.append(snap_text)
        snapshot_data = snapshot_data + list_snapshots_recursively(
                                        snapshot.childSnapshotList)
    return snapshot_data


def get_snapshots_by_name_recursively(snapshots, snapname):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.name == snapname:
            snap_obj.append(snapshot)
        else:
            snap_obj = snap_obj + get_snapshots_by_name_recursively(
                                    snapshot.childSnapshotList, snapname)
    return snap_obj


def get_current_snap_obj(snapshots, snapob):
    snap_obj = []
    for snapshot in snapshots:
        if snapshot.snapshot == snapob:
            snap_obj.append(snapshot)
        snap_obj = snap_obj + get_current_snap_obj(
                                snapshot.childSnapshotList, snapob)
    return snap_obj


def snapshotRemove(vm, snapshotname, dryrun, verbose):
    if verbose: print("Removing snapshot: " + snapshotname + " from VM: " + vm.name)
    snap_obj = get_snapshots_by_name_recursively(vm.snapshot.rootSnapshotList, snapshotname)
    # if len(snap_obj) is 0; then no snapshots with specified name
    if len(snap_obj) == 1:
        snap = snap_obj[0].snapshot
        print("  " + vm.name + " " + snap)
        if not dryrun:
            task.WaitForTask(snap.RemoveSnapshot_Task(removeChildren=True))
            print("Snapshot removed:" + vm.name + " " + snapshotname)

def snapshotRemoveAll(vm, dryrun, verbose):
    if verbose: print("Removing all snapshots from VM: " + vm.name + ":")
    snaps = list_snapshots_recursively(vm.snapshot.rootSnapshotList)
    for snap in snaps:
        print("  " + vm.name + " " + snap)

    #t1 = vm.removesnapshot(spec=pyVmomi.vim.vm.RelocateSpec(datastore=destination_ds))
    #t1 = vm.RemoveAllSnapshots_Task()
    if not dryrun:
        task.WaitForTask(vm.RemoveAllSnapshots())
        print("Snapshot removed:" + vm.name)
    return

def main():
    args = GetArgs()
    #if not args.datastore:
    #    print("-d/--datastore is required!")
    #    return

    verbose = args.verbose

    si = SmartConnect(host=args.host, user=args.user, pwd=args.password, disableSslCertValidation=True)
    vm_list = []
    datacenters = si.content.rootFolder.childEntity
    for datacenter in datacenters:
        if verbose >= 2: print("Datacenter: " + datacenter.name)

        # List VMs
        vm_view = si.content.viewManager.CreateContainerView(datacenter, [pyVmomi.vim.VirtualMachine], True)
        vms_list = vm_view.view
        vm_view.Destroy()

        threads = []
        # Loop through VMs
        for vm in vms_list:
            if verbose >= 2: print("VM: " + vm.name)
            if not args.folder or (args.folder and re.search(args.folder,vm.parent.name+"/"+vm.parent.parent.name ,re.IGNORECASE)):
                if verbose >= 2: print("  VM Folder: " + vm.parent.name)
                if not args.vm or (args.vm and re.search(args.vm, vm.name,re.IGNORECASE)):
                    if verbose >= 2: print("  VM name: " + vm.name)
                    if not (args.exclude and (args.exclude and re.search(args.exclude, vm.name,re.IGNORECASE ))):
                        if verbose >= 2: print("  VM not excluded: " + vm.name)
                        if not args.poweredon or (args.poweredon and vm.runtime.powerState == "poweredOn"):
                            if verbose >=1: print("  Considering VM:" + vm.name)
                            # Look if the VM has a Disk on the Datastore (if specified)
                            is_on_ds = False
                            if args.datastore:
                                if verbose >=2: print("  Checking if VM is on Datastore " + args.datastore)
                                for device in vm.config.hardware.device:
                                    if isinstance(device, pyVmomi.vim.vm.device.VirtualDisk):
                                        if device.backing.datastore.name == args.datastore:
                                            if verbose: print("  Found on Datastore " + args.datastore + ": "+ vm.name)
                                            is_on_ds = True
                                            break
                            # Move only if not specified or if specified and found on DS
                            if not args.datastore or is_on_ds:
                                if vm.snapshot:
                                    #print("  Snapshots:")
                                    for snapshot in vm.snapshot.rootSnapshotList:
                                        #print("    " + snapshot.name)
                                        ##if snapshot.name == "snapshot":
                                        if verbose: print("Found some snapshots on VM:")
                                        if args.threads > 1:
                                            # start a thread if we have less than args.threads
                                            if len(threads) >= args.threads: 
                                                print("Waiting for a thread to finish")
                                            while len(threads) >= args.threads:
                                                # wait for a thread to finish
                                                print(".", end='', flush=True)
                                                time.sleep(30)
                                                for t in threads:
                                                    if not t.is_alive():
                                                        threads.remove(t)
                                                        break
                                            if args.snapshot:
                                                # Remove specific snapshot
                                                t = threading.Thread(target=snapshotRemove, args=(vm, args.snapshot, args.dryrun, verbose))
                                            else:
                                                # Remove all snapshots
                                                t = threading.Thread(target=snapshotRemoveAll, args=(vm, args.dryrun, verbose))
                                            threads.append(t)
                                            t.start()
                                        else:
                                            if args.snapshot:
                                                # Remove specific snapshot
                                                if verbose: print("  Removing snapshot: " + args.snapshot + " on " + vm.name )
                                                snapshotRemove(vm, args.snapshot, args.dryrun, verbose)
                                            else:
                                                # Remove all snapshots
                                                if verbose: print("  Removing All snapshots on: " + vm.name )
                                                snapshotRemoveAll(vm, args.dryrun, verbose)

    if args.threads > 1:
        # wait for threads to finish
        for t in threads:
            time.sleep(30)
            t.join()

    Disconnect(si)


if __name__ == "__main__":
   main()