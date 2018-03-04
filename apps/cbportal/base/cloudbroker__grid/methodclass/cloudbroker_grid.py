from JumpScale import j
from JumpScale.portal.portal.auth import auth
from JumpScale.portal.portal import exceptions
from cloudbrokerlib.baseactor import BaseActor
import requests
from urlparse import urlparse
from os import path as os_path
import yaml

class cloudbroker_grid(BaseActor):

    def __init__(self):
        super(cloudbroker_grid, self).__init__()
        self.sysmodels = j.clients.osis.getNamespace('system')
        self.acl = j.clients.agentcontroller.get()
        self.pcl = j.clients.portal.getByInstance('main')

    @auth(['level1', 'level2', 'level3'])
    def purgeLogs(self, gid, age='-3d', **kwargs):
        return self.acl.executeJumpscript('cloudscalers', 'logs_purge', args={'age': age}, gid=gid, role='master', wait=False)['result']

    @auth(['level1', 'level2', 'level3'])
    def checkVMs(self, **kwargs):
        sessions = self.acl.listSessions()
        for nodeid, roles in sessions.iteritems():
            if 'master' in roles:
                gid = int(nodeid.split('_')[0])
                self.acl.executeJumpscript('jumpscale', 'vms_check', gid=gid, role='master', wait=False)
        return 'Scheduled check on VMS'


    @auth(['level1', 'level2', 'level3'])
    def rename(self, name, gid, **kwargs):
        location = next(iter(self.models.location.search({'gid': gid})[1:]), None)
        if not location:
            raise exceptions.NotFound('Could not find location with gid %s' % gid)
        location['name'] = name
        self.models.location.set(location)
        return True

    @auth(['level1', 'level2', 'level3'])
    def add(self, name, gid, locationcode, **kwargs):
        location = next(iter(self.models.location.search({'gid': gid})[1:]), None)
        if location:
            raise exceptions.Conflict("Location with gid %s already exists" % gid)
        location = self.models.location.new()
        location.gid = gid
        location.flag = 'black'
        location.locationCode = locationcode
        location.name = name
        self.models.location.set(location)
        return 'Location has been added successfully, do not forget to add networkids and public IPs'

    @auth(['level1', 'level2', 'level3'])
    def upgrade(self, url, **kwargs):
        manifest = requests.get(url).content
        version = os_path.splitext(os_path.basename(urlparse(url).path))[0]
        versionmodel = self.sysmodels.version.new()
        versionmodel.name = version
        versionmodel.url = url
        versionmodel.manifest = manifest
        versionmodel.creationTime = j.base.time.getTimeEpoch()
        versionmodel.status = 'INSTALLING'
        self.sysmodels.version.set(versionmodel)
        gids = [ x['gid'] for x in self.models.location.search({'$fields': ['gid']})[1:]]
        for gid in gids:
            self.acl.executeJumpscript('greenitglobe', 'delete_file', role='controllernode', gid=gid, wait=True, all=True, args={'path': '/var/ovc/updatelogs/update_env.log'})
            self.acl.executeJumpscript('greenitglobe', 'upgrade_cluster', role='controllernode',gid=gid, wait=False)
        return {'redirect_url': '/updating'}

    @auth(['level1', 'level2', 'level3'])
    def runUpgradeScript(self, **kwargs):
        upgrade_version = self.sysmodels.version.searchOne({'status': 'INSTALLING'})['name']
        current_version = self.sysmodels.version.searchOne({'status': 'CURRENT'})['name']
        location_url = self.pcl.actors.cloudapi.locations.getUrl()
        job = self.acl.executeJumpscript('greenitglobe', 'upgrader', role='controllernode', gid=j.application.whoAmI.gid,
                                        wait=True, args={'upgrade_version': upgrade_version,
                                                         'current_version': current_version,
                                                         'location_url': location_url})
        if job['state'] != 'OK':
            raise exceptions.Error("Couldn't execute upgrade script")
        return 'Upgrade script ran successfully'

    @auth(['level1', 'level2', 'level3'])
    def changeSettings(self, id, settings, **kwargs):
        if self.sysmodels.grid.count({'id': id}) == 0:
            raise exceptions.NotFound("No grid with id {} was found".format(id))
        try:
            settings = yaml.loads(settings)
        except:
            raise exceptions.BadRequest("settings needs to be in valid YAML format")
        if not isinstance(settings, dict):
            raise exceptions.BadRequest("settings needs to be in valid YAML format and needs to be an object")
        self.sysmodels.grid.updateSearch({'id': id}, {'$set': {'settings': settings}})
        return 'Changing settings done successfully'

