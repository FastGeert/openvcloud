from JumpScale import j
from JumpScale.portal.portal import exceptions
from JumpScale.portal.portal.auth import auth
from cloudbrokerlib.baseactor import BaseActor
import requests
import urllib
import math


class cloudbroker_image(BaseActor):
    def _checkimage(self, imageId):
        if not self.models.image.exists(imageId):
            raise exceptions.BadRequest('Image with id "%s" not found' % imageId)
        return self.models.image.get(imageId)

    @auth(['level1', 'level2', 'level3'])
    def delete(self, imageId, **kwargs):
        """
        Delete an image
        param:imageId id of image
        result bool
        """
        self.models.image.updateSearch({'id': imageId}, {'$set': {'status': 'DESTROYED'}})
        self.models.stack.updateSearch({'images': imageId}, {'$pull': {'images': imageId}})
        return True

    @auth(['level1', 'level2', 'level3'])
    def enable(self, imageId, **kwargs):
        """
        Enable an image
        param:imageId id of image
        result bool
        """
        image = self._checkimage(imageId)
        if image.status == 'DESTROYED':
            raise exceptions.BadRequest('Can not enable a destroyed image')
        self.models.image.updateSearch({'id': imageId}, {'$set': {'status': 'CREATED'}})

    @auth(['level1', 'level2', 'level3'])
    def disable(self, imageId, **kwargs):
        """
        Disable an image
        param:imageId id of image
        result bool
        """
        image = self._checkimage(imageId)
        if image.status == 'DESTROYED':
            raise exceptions.BadRequest('Can not disable a destroyed image')
        self.models.image.updateSearch({'id': imageId}, {'$set': {'status': 'DISABLED'}})

    @auth(['level1', 'level2', 'level3'])
    def updateNodes(self, imageId, enabledStacks, **kwargs):
        enabledStacks = enabledStacks or list()
        image = self._checkimage(imageId)
        enabledStacks = [int(x) for x in enabledStacks]
        self.models.stack.updateSearch({'id': {'$in': enabledStacks}}, {'$addToSet': {'images': image.id}})
        self.models.stack.updateSearch({'id': {'$nin': enabledStacks}}, {'$pull': {'images': image.id}})
        return True

    def _getImageSize(self, url):
        try:
            resp = requests.head(url)
            if resp.status_code != 200:
                raise exceptions.BadRequest('Failed to get url size, {}: {}'.format(resp.status_code, resp.content))
            if 'Content-Length' not in resp.headers:
                raise exceptions.BadRequest('Failed to get url size')
            bytesize = resp.headers['Content-Length']
        except requests.ConnectionError:
            raise exceptions.BadRequest('Failed to connect to url')
        except requests.exceptions.InvalidSchema:
            try:
                con = urllib.urlopen(url)
                bytesize = con.headers.getheader('content-length')
            except:
                raise exceptions.BadRequest('Failed to get url size')
        try:
            bytesize = int(bytesize)
        except:
            raise exceptions.BadRequest('Failed to get url size')
        return bytesize

    @auth(['level1', 'level2', 'level3'])
    def createImage(self, name, url, gid, imagetype, username=None, password=None, accountId=None, **kwargs):
        if accountId and not self.models.account.exists(accountId):
            raise exceptions.BadRequest("Specified accountId does not exists")
        bytesize = self._getImageSize(url)
        ctx = kwargs['ctx']
        ctx.events.runAsync(self._createImage,
                            (name, url, gid, imagetype, bytesize, username, password, accountId, kwargs),
                            {},
                            'Creating Image {}'.format(name),
                            'Finished Creating Image',
                            'Failed to create Image',
        )
        return True

    @auth(['level1', 'level2', 'level3'])
    def edit(self, imageId, name=None, username=None, password=None, accountId=None, **kwargs):
        if accountId and not self.models.account.exists(accountId):
            raise exceptions.BadRequest("Specified accountId does not exists")
        image = self.models.image.get(imageId)
        image.name = name if name else image.name 
        image.username = username if username else image.username  
        image.password = password if password else image.password
        image.accountId = accountId if accountId else image.accountId
        self.models.image.set(image)

    def _createImage(self, name, url, gid, imagetype, bytesize, username, password, accountId, kwargs):
        ctx = kwargs['ctx']
        gbsize = int(math.ceil(j.tools.units.bytes.toSize(bytesize, '', 'G')))
        provider = self.cb.getProviderByGID(gid)
        image = self.models.image.new()
        image.name = name
        image.gid = gid
        image.type = imagetype
        image.username = username
        image.password = password
        image.accountId = accountId or 0
        image.status = 'CREATING'
        image.size = gbsize
        image.id = self.models.image.set(image)[0]
        volume = provider.create_volume(gbsize, 'templates/image_{}'.format(image.id), data=False)
        self.models.image.updateSearch({'id': image.id}, {'$set': {'referenceId': volume.vdiskguid}})
        image.referenceId = volume.vdiskguid
        try:
            size = provider._execute_agent_job(
                    'cloudbroker_import_image',
                    role='storagedriver',
                    url=url,
                    timeout=3600,
                    volumeid=volume.id,
                    eventstreamid=ctx.events.eventstreamid,
                    disksize=gbsize,
                    ovs_connection=provider.ovs_connection,
                    istemplate=True
            )
        except BaseException as e:
            j.errorconditionhandler.processPythonExceptionObject(e)
            provider.destroy_volume(volume)
            if self.models.image.exists(image.id):
                self.models.image.delete(image.id)
            raise
        self.models.image.updateSearch({'id': image.id}, {'$set': {'status': 'CREATED', 'size': size}})
        self.models.stack.updateSearch({'gid': gid}, {'$addToSet': {'images': image.id}})
        return True

    @auth(['level1', 'level2', 'level3'])
    def createCDROMImage(self, name, url, gid, accountId=None, **kwargs):
        if accountId and not self.models.account.exists(accountId):
            raise exceptions.BadRequest("Specified accountId does not exists")
        bytesize = self._getImageSize(url)
        ctx = kwargs['ctx']
        ctx.events.runAsync(self._createCDROMImage,
                            (name, url, gid, bytesize, accountId, kwargs),
                            {},
                            'Creating CD-ROM Image {}'.format(name),
                            'Finished Creating CD-ROM Image',
                            'Failed to create CD-ROM Image',
        )
        return True

    def _createCDROMImage(self, name, url, gid, bytesize, accountId, kwargs):
        ctx = kwargs['ctx']
        gbsize = int(math.ceil(j.tools.units.bytes.toSize(bytesize, '', 'G')))
        provider = self.cb.getProviderByGID(gid)
        disk = self.models.disk.new()
        disk.name = name
        disk.gid = gid
        disk.accountId = None
        disk.status = 'CREATING'
        disk.type = 'C'
        disk.sizeMax = gbsize
        disk.id = self.models.disk.set(disk)[0]
        volume = provider.create_volume(gbsize, 'rescuedisk/disk_{}'.format(disk.id), data=False)
        self.models.disk.updateSearch({'id': disk.id}, {'$set': {'referenceId': volume.id}})
        disk.referenceId = volume.id
        try:
            size = provider._execute_agent_job(
                    'cloudbroker_import_image',
                    role='storagedriver',
                    url=url,
                    timeout=3600,
                    volumeid=volume.id,
                    eventstreamid=ctx.events.eventstreamid,
                    disksize=gbsize,
                    ovs_connection=provider.ovs_connection,
            )
        except BaseException as e:
            j.errorconditionhandler.processPythonExceptionObject(e)
            provider.destroy_volume(volume)
            if self.models.disk.exists(disk.id):
                self.models.disk.delete(disk.id)
            raise
        self.models.disk.updateSearch({'id': disk.id}, {'$set': {'status': 'CREATED', 'sizeMax': size}})
