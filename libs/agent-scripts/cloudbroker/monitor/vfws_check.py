from JumpScale import j

descr = """
Checks whether vfw can reach its gw
"""

organization = 'cloudscalers'
author = "deboeckj@codescalers.com"
version = "1.0"
category = "monitor.vfw"

enable = True
async = True
log = False
roles = ['fw',]
queue = 'process'
period = 3600

def action():
    import JumpScale.grid.osis
    import JumpScale.baselib.mailclient
    import netaddr
    import JumpScale.lib.routeros

    osiscl = j.core.osis.getClientByInstance('main')
    vfwcl = j.core.osis.getClientForCategory(osiscl, 'vfw', 'virtualfirewall')
    cloudspacecl = j.core.osis.getClientForCategory(osiscl, 'cloudbroker', 'cloudspace')
    ROUTEROS_PASSWORD = j.application.config.get('vfw.admin.passwd')
    cidders = j.application.config.getDict('vfw.public.cidrs')
    gws = j.application.config.getDict('vfw.public.gw')

    networks = []
    for c in cidders:
        networks.append(netaddr.IPNetwork('%s/%s' % (c, cidders[c])))

    def getDefaultGW(publicip):
        ipaddress = netaddr.IPAddress(publicip)
        subnet = None
        for net in networks:
            if ipaddress in net:
                subnet = str(net.network)
        if not subnet:
            return None
        return gws[subnet]

    result = dict()
    cloudspaces = dict()
    def processCloudSpace(cloudspace):
        cloudspaceid = cloudspace['id']
        cloudspaces[cloudspaceid] = cloudspace
        if cloudspace['status'] != 'DESTROYED':
            if cloudspace['networkId']:
                gwip = getDefaultGW(cloudspace['publicipaddress'])
                try:
                    vfw = vfwcl.get("%s_%s" % (j.application.whoAmI.gid, cloudspace['networkId']))
                    if j.system.net.tcpPortConnectionTest(vfw.host, 8728, 7):
                        routeros = j.clients.routeros.get(vfw.host, 'vscalers', ROUTEROS_PASSWORD)
                    else:
                        result[cloudspaceid] = 'Could not connect to routeros %s' % vfw.host
                        return
                except Exception, e:
                    result[cloudspaceid] = str(e)
                    return
                if gwip:
                    pingable = routeros.ping(gwip)
                    if not pingable:
                        result[cloudspaceid] = 'Could not ping %s'  % gwip
                else:
                    result[cloudspaceid] = 'No GW assigned'
    for cloudspace in cloudspacecl.search({'gid': j.application.whoAmI.gid})[1:]:
        print "Checking CoudspaceId: %(id)s NetworkId: %(networkId)s PUBIP: %(publicipaddress)s" % cloudspace
        processCloudSpace(cloudspace)
    if result:
        body = """
Some VFW have connections issues please investigate

"""
        for cloudspaceid, message in result.iteritems():
            cloudspace = cloudspaces[cloudspaceid]
            body += "* CoudspaceId: %(id)s NetworkId: %(networkId)s PUBIP: %(publicipaddress)s\n" % cloudspace
            body += "  ** %s \n\n" % message
        j.clients.email.send("support@mothership1.com", "monitor@mothership1.com", "VFW Check", body)
        print body
    return result


if __name__ == '__main__':
    result = action('ca1')
    import yaml
    import json
    with open('/root/vfws_check.json', 'w') as fd:
        json.dump(result, fd)
    print yaml.dump(result)
