from JumpScale import j

descr = """
Will set the `url` and `lastModified` fields with default values
"""

category = "libvirt"
organization = "greenitglobe"
author = "ali.chaddad@gig.tech"
license = "bsd"
version = "2.0"
roles = ["master"]
async = True


def action():
    ccl = j.clients.osis.getNamespace("cloudbroker")
    ccl.image.updateSearch({"url": None}, {"$set": {"url": "", "lastModified": 0}})
