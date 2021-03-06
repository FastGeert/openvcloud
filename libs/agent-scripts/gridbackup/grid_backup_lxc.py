from JumpScale import j

descr = """
Backup lxc machines
"""

category = "cloudbroker"
organization = "cloudscalers"
author = "deboeckj@codescalers.com"
license = "bsd"
version = "1.0"
roles = []
queue = "io"
async = True


def action(name, backupname, storageparameters):
    import time
    from JumpScale.baselib.backuptools import object_store
    from JumpScale.baselib.backuptools import backup
    import JumpScale.lib.lxc

    store = object_store.ObjectStore(storageparameters["storage_type"])
    bucketname = storageparameters["bucket"]
    mdbucketname = storageparameters["mdbucketname"]
    if storageparameters["storage_type"] == "S3":
        store.conn.connect(
            storageparameters["aws_access_key"],
            storageparameters["aws_secret_key"],
            storageparameters["host"],
            is_secure=storageparameters["is_secure"],
        )
    else:
        # rados has config on local cpu node
        store.conn.connect()
    f = None
    try:
        j.system.platform.lxc.btrfsSubvolCopy(name, backupname)
        f = j.system.platform.lxc.exportTgz(backupname, backupname)
        backupmetadata = []
        metadata = backup.backup(store, bucketname, f)
        backupmetadata.append(metadata)
        backup.store_metadata(store, mdbucketname, name, backupmetadata)
    finally:
        if f and j.system.fs.exists(f):
            j.system.fs.remove(f)
        if j.system.platform.lxc.btrfsSubvolExists(backupname):
            j.system.platform.lxc.btrfsSubvolDelete(backupname)

    return {"files": backupmetadata, "timestamp": time.time()}
