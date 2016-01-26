from JumpScale import j

descr = """
Libvirt script to create template
"""

name = "createtemplate"
category = "libvirt"
organization = "cloudscalers"
author = "deboeckj@codescalers.com"
license = "bsd"
version = "1.0"
roles = []
async = True


def action(machineid, templatename, imageid, sourcepath, pmachineip):
    import sys
    import math
    import time
    sys.path.append('/opt/OpenvStorage')
    from ovs.lib.vdisk import VDiskController
    from ovs.dal.lists.vdisklist import VDiskList
    from ovs.dal.lists.vpoollist import VPoolList
    from ovs.lib.vdisk import VDiskController, PMachineList
    pmguid = PMachineList.get_by_ip(pmachineip).guid
    from CloudscalerLibcloud.utils.libvirtutil import LibvirtUtil, lockDomain, unlockDomain
    pool = VPoolList.get_vpool_by_name('vmstor')

    # clone disk
    lockDomain(machineid)
    try:
        diskpath = sourcepath.replace('/mnt/vmstor/', '')
        sourcedisk = VDiskList.get_by_devicename_and_vpool(diskpath, pool)
        devicename = '%s' % int(time.time())
        newdiskdata = VDiskController.clone(sourcedisk.guid, None, devicename, pmachineguid=pmguid, machinename='templates/custom')
        VDiskController.set_as_template(newdiskdata['diskguid'])
        templateguid = newdiskdata['diskguid'].replace('-', '')
        location = newdiskdata['backingdevice']

        # update our model
        osiscl = j.clients.osis.getByInstance('main')
        imagemodel = j.clients.osis.getCategory(osiscl, 'cloudbroker', 'image')
        image = imagemodel.get(imageid)
        image.referenceId = templateguid
        image.status = 'CREATED'
        imagemodel.set(image)

        catimageclient = j.clients.osis.getCategory(osiscl, 'libvirt', 'image')
        catresourceclient = j.clients.osis.getCategory(osiscl, 'libvirt', 'resourceprovider')

        installed_images = catimageclient.list()
        if templateguid not in installed_images:
            cimage = dict()
            cimage['name'] = templatename
            cimage['id'] = templateguid
            cimage['UNCPath'] = location
            cimage['type'] = 'Custom Templates'
            cimage['size'] = int(math.ceil(sourcedisk.size / (1024 ** 3)))
            catimageclient.set(cimage)

        # register node if needed and update images on it
        nodekey = "%(gid)s_%(nid)s" % j.application.whoAmI._asdict()
        if not catresourceclient.exists(nodekey):
            rp = dict()
            rp['cloudUnitType'] = 'CU'
            rp['id'] = j.application.whoAmI.nid
            rp['gid'] = j.application.whoAmI.gid
            rp['guid'] = nodekey
            rp['images'] = [templateguid]
        else:
            rp = catresourceclient.get(nodekey)
            if not templateguid in rp.images:
                rp.images.append(templateguid)
        catresourceclient.set(rp)
        return image.dump()
    finally:
        unlockDomain(machineid)

if __name__ == '__main__':
    action('7ecf9fa8-de38-4dc5-8f4c-2d96c09b236a', 'test', 10, None)
