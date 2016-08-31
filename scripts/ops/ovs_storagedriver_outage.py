#!/usr/bin/env jspython
from JumpScale import j
import sys
import netaddr
import itertools


def main(ipaddress):
    scl = j.clients.osis.getNamespace('system')
    ccl = j.clients.osis.getNamespace('cloudbroker')
    lcl = j.clients.osis.getNamespace('libcloud')
    pcl = j.clients.portal.getByInstance('main')

    if scl.node.count({'netaddr.ip': ipaddress, 'roles': 'storagedriver'}) == 0:
        print('Could not find storagedriver node with IP Address %s' % ipaddress)
        sys.exit(1)
    query = {'$query': {'referenceId': {'$regex': ipaddress.replace('.', '\.')},
                        'status': {'$ne': 'DESTROYED'}
                        },
             }
    disks = ccl.disk.search(query)[1:]
    diskids = [disk['id'] for disk in disks]
    print(diskids)
    query = {'$query': {'disks': {'$in': diskids},
                        'status': {'$ne': 'DESTROYED'}
                        },
             }
    vms = ccl.vmachine.search(query)[1:]
    print(vms)
    runningvms = []
    for vm in vms:
        vmdata = pcl.actors.cloudapi.machines.get(vm['id'])
        if vmdata['state'] == 'RUNNING':
            print('Stopping vm %(name)s' % vmdata)
            pcl.actors.cloudapi.machines.stop(vm['id'])
            runningvms.append(vm['id'])

    storagedrivers = scl.node.search({'netaddr.ip': {'$ne': ipaddress}})[1:]
    storagedriverips = []
    for storagedriver in storagedrivers:
        for netaddress in storagedriver['netaddr']:
            for ip, cidr in zip(netaddress['ip'], netaddress['cidr']):
                network = netaddr.IPNetwork('%s/%s' % (ip, cidr))
                if network.IPAddress(ipaddress) in network:
                    storagedriverips.append(ip)

    storagedriverips = itertools.cycle(storagedriverips)
    for vm in vms:
        storagedriverip = next(storagedriverips)
        for diskid in vm['disks']:
            disk = ccl.disk.get(diskid)
            disk.referenceId = disk.referenceId.replace(ipaddress, storagedriverip)
            ccl.disk.set(disk)
        domainkey = 'domain_%s' % (vm['referenceId'].replace('-', ''))
        xml = lcl.domain.get(domainkey)
        xml = xml.replace(ipaddress, storagedriverip)
        lcl.domain.set(xml, domainkey)

    vmcount = len(runningvms)
    for idx, vmid in enumerate(runningvms):
        print("Starting vm %s/%s" % (idx + 1, vmcount))
        pcl.actors.cloudapi.machines.start(vmid)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ipaddress', help='IP Address of the failted OVS node', required=True)
    options = parser.parse_args()
    main(options.ipaddress)
