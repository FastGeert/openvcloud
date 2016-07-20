from JumpScale import j

descr = """
Libvirt script to destroy a volume
"""

category = "libvirt"
organization = "cloudscalers"
author = "deboeckj@codescalers.com"
license = "bsd"
version = "1.0"
roles = []
async = True


def action(diskpaths):
    from CloudscalerLibcloud import openvstorage
    for path in diskpaths:
        path = openvstorage.getPath(path)
        if j.system.fs.exists(path):
            j.system.fs.remove(path)
    return True