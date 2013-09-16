class DummyConnection():
    
    def listSizes(self):
        sizes = [{'memory': '1750', 'vcpus': 1, 'disk': 40, 'guid':
            '4da91a0d-18f5-47a5-ad97-7cf3b97cbc59', 'id': 1, 'name': u'BIG',
            'referenceId': ''},{'memory': '3600', 'vcpus': 2, 'disk': 20, 'guid':
            '4da91a0d-18f5-47a5-ad97-7cf3b97cbc59', 'id': 2, 'name': u'SMALL',
            'referenceId': ''}]
        return sizes


    def listImages(self):
        images = [{'UNCPath': 'vmhendrik.img',
            'description': '',
            'guid': '3c655a10-7e04-4d93-8ea1-ec5536d9689b',
            'id': 1,
            'name': 'ubuntu-2',
            'referenceId': '',
            'size': 10,
            'type': 'ubuntu'}, {'UNCPath': 'file:///ISOS/windows-2008.iso',
            'description': '',
            'guid': '3c655a10-7e04-4d93-8ea1-ec5536d9689b',
            'id': 2,
            'name': 'windows-2008',
            'referenceId': '',
            'size': 20,
            'type': 'WINDOWS'}]
        return images

class CloudBrokerConnection():
     NAMESPACE = 'libvirt'
     CATEGORY = 'domain'

     def __init__(self, ipaddress=None, port=None, secret=None):
         from JumpScale import j
         self._j = j
         import JumpScale.portal
         if ipaddress:
             self.client = j.core.portal.getPortalClient(ip=ipaddress, port=port, secret=secret)  
             self.libvirt_actor = self.client.getActor('libcloud', 'libvirt')
         else:
             self.libvirt_actor = j.apps.libcloud.libvirt
         self.db = self._getKeyValueStore()

     def _getKeyValueStore(self):
         import JumpScale.grid.osis
         client = self._j.core.osis.getClient()
         if self.NAMESPACE not in client.listNamespaces():
             client.createNamespace(self.NAMESPACE, 'blob')
         if self.CATEGORY not in client.listNamespaceCategories(self.NAMESPACE):
            client.createNamespaceCategory(self.NAMESPACE, self.CATEGORY)
         return self._j.core.osis.getClientForCategory(self.NAMESPACE, self.CATEGORY)

     def listSizes(self):
         return self.libvirt_actor.listSizes()

     def listImages(self):
         return self.libvirt_actor.listImages()
     






