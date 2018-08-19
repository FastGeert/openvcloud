from JumpScale import j
from urlparse import urlparse

descr = """
This script updates nodes version
"""

category = "cloudbroker"
organization = "greenitglobe"
license = "bsd"
version = "1.0"
roles = []
async = True


def action(nodename):
    cmd = "kubectl --kubeconfig /root/.kube/config get service management-ssh -o=jsonpath='{.spec.clusterIP}'"
    host = j.system.process.execute(cmd)[1]
    try:
        mgt = j.remote.cuisine.connect(host, 22)
        mgt.run("installer node jsaction upgrade --name {}".format(nodename))
    except:
        j.errorconditionhandler.raiseOperationalWarning(
            "Can't update node {}".format(nodename)
        )
