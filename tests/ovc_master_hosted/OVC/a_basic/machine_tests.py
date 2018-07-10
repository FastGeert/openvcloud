# coding=utf-8
import unittest
import uuid
import random
import time
from ....utils.utils import BasicACLTest, VMClient
from nose_parameterized import parameterized
from JumpScale.portal.portal.PortalClient2 import ApiError
from JumpScale.baselib.http_client.HttpClient import HTTPError


class BasicTests(BasicACLTest):
    def setUp(self):
        super(BasicTests, self).setUp()
        self.acl_setup()

    @parameterized.expand(['RUNNING',
                           'HALTED'])
    def test001_reboot_vm(self, initial_status):
        """ OVC-001
        *Test case for reboot machine with different initial status (Running/Halted).*

        **Test Scenario:**

        #. create virtual machine vm, should succeed
        #. set the vm to required status, should succeed
        #. reboot machine with initial status, should succeed
        """
        self.lg('%s STARTED' % self._testID)

        self.lg('- create virtual machine vm, should succeed')
        self.machine_id = self.cloudapi_create_machine(self.cloudspace_id,
                                                       self.account_owner_api)

        self.lg('- set the vm to required status, should succeed')
        if initial_status == 'HALTED':
            self.api.cloudbroker.machine.stop(machineId=self.machine_id, reason='testing')
            self.assertEqual(self.api.cloudapi.machines.get(machineId=self.machine_id)['status'],
                             initial_status)
        else:
            self.assertEqual(self.api.cloudapi.machines.get(machineId=self.machine_id)['status'],
                             initial_status)

        self.lg('- reboot machine with initial status [%s], should succeed' % initial_status)
        self.api.cloudbroker.machine.reboot(machineId=self.machine_id, reason='testing')
        self.assertEqual(self.api.cloudapi.machines.get(machineId=self.machine_id)['status'],
                         'RUNNING')

        self.lg('%s ENDED' % self._testID)

    @parameterized.expand(['Ubuntu 16.04 x64',
                           'Windows 2012r2 Standard'])
    def test002_create_vmachine_withbig_disk(self, image_name):
        """ OVC-002
        *Test case for create machine with different Windows/Linux images available.*

        **Test Scenario:**

        #. validate the image is exists, should succeed
        #. get all available sizes to use, should succeed
        #. create machine using given image with specific size 2000, should succeed
        """
        self.lg('%s STARTED' % self._testID)

        self.lg('1- validate the image is exists, should succeed')
        images = self.api.cloudapi.images.list()
        self.assertIn(image_name,
                      [image['name'] for image in images],
                      'Image [%s] not found in the environment available images' % image_name)
        image = [image for image in images if image['name'] == image_name][0]
        self.lg('- using image [%s]' % image_name)
        self.lg('2- get all available sizes to use and choose one random, should succeed')
        sizes = self.api.cloudapi.sizes.list(cloudspaceId=self.cloudspace_id)
        sizes = [size for size in sizes if size['id'] in range(1, 7)]
        size = random.choice(sizes)

        self.lg('- using image [%s] with memory size [%s]' % (image_name, size['memory']))
        if 'Windows' in image_name:
            while True:
                disksize = random.choice(size['disks'])
                if disksize > 25:
                    break
        else:
            disksize = random.choice(size['disks'])
        self.lg('- using image [%s] with memory size [%s] with disk '
                '[%s]' % (image_name, size['memory'], disksize))
        machine_id = self.cloudapi_create_machine(cloudspace_id=self.cloudspace_id,
                                                  size_id=size['id'],
                                                  image_id=image['id'],
                                                  disksize=disksize)
        self.lg('- done using image [%s] with memory size [%s] with disk '
                '[%s]' % (image_name, size['memory'], disksize))
        self.lg('3- add new disk with random size, should succeed')
        new_disk_name = str(uuid.uuid4()).replace('-', '')[0:10]
        new_disk_size = random.choice(size['disks'])
        self.lg('- using image [%s] with memory size [%s] with disk '
                '[%s] adding new disk with size [%s]' % (image_name, size['memory'],
                                                         disksize, new_disk_size))
        disk_id = self.api.cloudapi.machines.addDisk(machineId=machine_id,
                                                     diskName=new_disk_name,
                                                     description=new_disk_name,
                                                     size=new_disk_size,
                                                     type='D')
        machine_disks = self.api.cloudapi.machines.get(machineId=machine_id)['disks']
        self.assertIn(new_disk_name, [disk['name'] for disk in machine_disks])
        self.assertIn(disk_id, [disk['id'] for disk in machine_disks])
        self.lg('- delete machine to free environment resources, should succeed')
        self.api.cloudapi.machines.delete(machineId=machine_id)

        self.lg('%s ENDED' % self._testID)

    @parameterized.expand(['online', 'offline'])    
    def test003_create_machine_with_resize(self, machine_status):
        """ OVC-003
        *Test case for testing resize operation with all combinations*

        **Test Scenario:**

        #. Creating machine with random disksize and random size
        #. Stop the machine, if offline resize.
        #. Resize the machine with all possible combinations, should succeed
        #. Start the machine, if offline resize.
        #. Check that the machine is updated.
        """

        self.lg('- Get all available sizes to use and choose one random and create vm with it , should succeed')
        sizes = self.api.cloudapi.sizes.list(cloudspaceId=self.cloudspace_id)
        sizes = [size for size in sizes if size['id'] in range(1, 7)]
        selected_size = random.choice(sizes)
        disksize = random.choice(selected_size['disks'])

        self.lg('- using memory size [%s] with disk [%s]' % (selected_size['memory'], disksize))
        machineId = self.cloudapi_create_machine(
            cloudspace_id=self.cloudspace_id,
            size_id=selected_size['id'],
            disksize=disksize
        )

        for size in sizes:
            if machine_status == "online":
                if size['memory'] < selected_size['memory']:
                    self.lg('resize running machine with memory size less than selected size, should fail')
                    with self.assertRaises(ApiError) as e:
                        self.account_owner_api.cloudapi.machines.resize(machineId=machineId, sizeId=size['id'])
                    self.assertEqual(e.exception.message, '400 Bad Request')
                    continue

            if machine_status == "offline":
                self.lg('- Stop the machine')
                self.account_owner_api.cloudapi.machines.stop(machineId=machineId)
                machineInfo = self.api.cloudapi.machines.get(machineId=machineId)
                self.assertEqual(machineInfo['status'], 'HALTED')

            self.lg('- Resize the machine with {} status with all possible combinations, should succeed'.format(machine_status))
            self.account_owner_api.cloudapi.machines.resize(machineId=machineId, sizeId=size['id'])

            if machine_status == "offline":
                self.lg('- Start the machine')
                self.account_owner_api.cloudapi.machines.start(machineId=machineId)
                time.sleep(5)

            self.lg('- Check that the machine is updated')
            machineInfo = self.api.cloudapi.machines.get(machineId=machineId)
            self.assertEqual(machineInfo['status'], 'RUNNING')
            self.assertEqual(machineInfo['sizeid'], size['id'])
            vm_client = VMClient(machineId)
            response = vm_client.execute(" cat /proc/meminfo")
            meminfo = response[1].read()
            mem_total = int(meminfo[meminfo.find("MemTotal")+9:meminfo.find("kB")])/1024
            self.assertAlmostEqual(mem_total, size['memory'], delta=400)
            response = vm_client.execute(" grep -c ^processor /proc/cpuinfo ")
            self.assertEqual(int(response[1].read()), size['vcpus'])

            self.lg('%s ENDED' % self._testID)

    def test004_create_machine_with_resize_in_halted(self):
        """ OVC-004
        *Test case for testing resize operation in the halted machine*

        **Test Scenario:**

        #. Creating machine with random disksize and random size
        #. Stop the machine
        #. Resize the machine
        #. Resize it again
        #. Start the machine
        #. Check that the machine is updated with the last resized info
        """

        self.lg('1- Get all available sizes to use and choose one random and create vm with it , should succeed')
        sizes = self.api.cloudapi.sizes.list(cloudspaceId=self.cloudspace_id)
        sizes = [size for size in sizes if size['id'] in range(1, 7)]
        selected_size = random.choice(sizes)
        disksize = random.choice(selected_size['disks'])

        self.lg('2- using memory size [%s] with disk [%s]' % (selected_size['memory'], disksize))
        machineId = self.cloudapi_create_machine(
            cloudspace_id=self.cloudspace_id,
            size_id=selected_size['id'],
            disksize=disksize
        )

        self.lg('3- Stop the machine')
        self.account_owner_api.cloudapi.machines.stop(machineId=machineId)

        for size in sizes:

            if size['id'] not in range(1, 7):
                continue

            machineInfo = self.api.cloudapi.machines.get(machineId=machineId)
            self.assertEqual(machineInfo['status'], 'HALTED')

            self.lg('4- Resize the machine with all possible combinations, should succeed')
            self.account_owner_api.cloudapi.machines.resize(machineId=machineId, sizeId=size['id'])

        self.lg('5- Start the machine')
        self.account_owner_api.cloudapi.machines.start(machineId=machineId)

        self.lg('6- Check that the machine is updated')
        machineInfo = self.api.cloudapi.machines.get(machineId=machineId)
        self.assertEqual(machineInfo['status'], 'RUNNING')
        self.assertEqual(machineInfo['sizeid'], 6)

        self.lg('%s ENDED' % self._testID)

    @parameterized.expand(['Ubuntu 16.04 x64',
                           'Windows 2012r2 Standard'])
    def test005_add_disks_to_vmachine(self, image_name):
        """ OVC-005
        *Test case for create machine with different Windows/Linux images available and add all disks to it.*

        **Test Scenario:**

        #. validate the image is exists, should succeed
        #. get all available sizes to use, should succeed
        #. create machine using given image with random size
        #. Add all possible disks to this virtual machine
        """
        self.lg('%s STARTED' % self._testID)

        self.lg('1- validate the image is exists, should succeed')
        images = self.api.cloudapi.images.list()
        self.assertIn(image_name,
                      [image['name'] for image in images],
                      'Image [%s] not found in the environment available images' % image_name)
        image = [image for image in images if image['name'] == image_name][0]
        self.lg('- using image [%s]' % image_name)
        self.lg('2- get all available sizes to use and choose one random, should succeed')
        sizes = self.api.cloudapi.sizes.list(cloudspaceId=self.cloudspace_id)
        sizes = [size for size in sizes if size['id'] in range(1, 7)]
        size = random.choice(sizes)

        disksize = random.choice(size['disks'])
        if image_name == 'Windows 2012r2 Standard':
           while disksize < 25:
               disksize = random.choice(size['disks'])
        self.lg('- using image [%s] with memory size [%s] with disk '
                '[%s]' % (image_name, size['memory'], disksize))
        machine_id = self.cloudapi_create_machine(cloudspace_id=self.cloudspace_id,
                                                  size_id=size['id'],
                                                  image_id=image['id'],
                                                  disksize=disksize)
        self.wait_for_status('RUNNING', self.api.cloudapi.machines.get,
                             machineId=machine_id)
        self.lg('- done using image [%s] with memory size [%s] with disk '
                '[%s]' % (image_name, size['memory'], disksize))

        for new_disk_size in size['disks']:
            self.lg('- add new disk with [%s] size, should succeed' % new_disk_size)
            new_disk_name = str(uuid.uuid4()).replace('-', '')[0:10]
            self.lg('- using image [%s] with memory size [%s] with disk '
                    '[%s] adding new disk with size [%s]' % (image_name, size['memory'],
                                                             disksize, new_disk_size))
            disk_id = self.api.cloudapi.machines.addDisk(machineId=machine_id,
                                                         diskName=new_disk_name,
                                                         description=new_disk_name,
                                                         size=new_disk_size,
                                                         type='D')
            machine_disks = self.api.cloudapi.machines.get(machineId=machine_id)['disks']
            self.assertIn(new_disk_name, [disk['name'] for disk in machine_disks])
            self.assertIn(disk_id, [disk['id'] for disk in machine_disks])

        self.lg('- delete machine to free environment resources, should succeed')
        self.api.cloudapi.machines.delete(machineId=machine_id)

        self.lg('%s ENDED' % self._testID)

    def test006_machine_snapshots(self):
        """ OVC-006
        *Test case  for restoring certain snapshots for multiple snapshots*

        **Test Scenario:**

        #. create virtual machine with name: 'snapshotvm'
        #. add portforward for the created virtual machine
        #. get a physical node ID
        #. write a machine script on a physical node
        #. Take 6 different snapshots for the created virtual machine
        #. Rollback to the 3rd snapshot
        #. check if the rolling back have succeed
        #. create snapshot by passing number in the name param and then list snapshots, should succeed.
        #. disable the account, should succeed
        #. Try to create snapshot, should fail with 403 forbidden
        #. Try to start the VM, should fail with 403 forbidden

        """

        self.lg('- create virtual machine with name: \'snapshotvm\'')
        self.machine_id = self.cloudapi_create_machine(self.cloudspace_id, self.account_owner_api,
                                                       'snapshotvm', disksize=10)

        self.lg('- add portforward for the created virtual machine')
        cs_publicip = self.add_portforwarding(self.machine_id, api=self.account_owner_api, cs_publicport=2000)
        time.sleep(10)
        machine = self.account_owner_api.cloudapi.machines.get(machineId=self.machine_id)
        account = machine['accounts'][0]

        self.lg('- get a physical node ID')
        nodeID = 2

        self.lg('- write a machine script on a physical node')
        machine_script = '#!/usr/bin/env/python ' \
                         '\nfrom JumpScale import j ' \
                         '\nimport sys ' \
                         '\nresult = sys.argv[6] \nlogin = sys.argv[1] ' \
                         '\npassword = sys.argv[2] \nport = sys.argv[3] ' \
                         '\ncsip = sys.argv[4] \niter = sys.argv[5] ' \
                         '\nconnection = j.remote.cuisine.connect(csip, port, password, login) ' \
                         '\nconnection.fabric.state.output["running"]=False ' \
                         '\nconnection.fabric.state.output["stdout"]=False ' \
                         '\nconnection.user(login) \nif result == "result": ' \
                         '\n   print(connection.run("ls -1 | wc -l")) ' \
                         '\nelse: ' \
                         '\n   connection.run("echo Testing > snapshot%s.txt"%(iter))'

        for line in machine_script.splitlines():
            self.execute_command_on_physical_node('cd; echo \'%s\' >> machine_script.py' % line, nodeID)

        try:
            self.lg('- Take 6 different snapshots for the created virtual machine')
            for i in range(6):
                self.execute_command_on_physical_node('cd; python machine_script.py %s %s 2000 %s %s none'
                                                      % (account['login'], account['password'], cs_publicip, i + 1),
                                                      nodeID)
                self.account_owner_api.cloudapi.machines.stop(machineId=self.machine_id)
                self.wait_for_status('HALTED', self.account_owner_api.cloudapi.machines.get,
                                     machineId=self.machine_id)

                self.account_owner_api.cloudapi.machines.snapshot(machineId=self.machine_id,
                                                                  name='snapshot%s' % (i + 1))

                self.account_owner_api.cloudapi.machines.start(machineId=self.machine_id)
                self.wait_for_status('RUNNING', self.account_owner_api.cloudapi.machines.get,
                                     machineId=self.machine_id)
                for _ in range(6):
                    try:
                        self.execute_command_on_physical_node('cd; python machine_script.py %s %s 2000 %s %s result'
                        % (account['login'], account['password'], cs_publicip, i), nodeID)
                        break
                    except:
                        time.sleep(10)

            self.lg('- Rollback to the 3rd snapshot')
            self.account_owner_api.cloudapi.machines.stop(machineId=self.machine_id)
            self.wait_for_status('HALTED', self.account_owner_api.cloudapi.machines.get,
                                 machineId=self.machine_id)
            snapshots = self.account_owner_api.cloudapi.machines.listSnapshots(machineId=self.machine_id)
            snapshots.sort()
            self.account_owner_api.cloudapi.machines.rollbackSnapshot(machineId=self.machine_id,
                                                                      epoch=snapshots[2]['epoch'])
            self.account_owner_api.cloudapi.machines.start(machineId=self.machine_id)
            self.wait_for_status('RUNNING', self.account_owner_api.cloudapi.machines.get,
                                 machineId=self.machine_id)
            for _ in range(6):
                try:
                    self.execute_command_on_physical_node('cd; python machine_script.py %s %s 2000 %s %s result'
                    % (account['login'], account['password'], cs_publicip, i), nodeID)
                    break
                except:
                    time.sleep(10)

            self.lg('check if the rolling back have succeed')
            count_files = self.execute_command_on_physical_node('cd; python machine_script.py %s %s 2000 %s %s result'
                                                                % (
                                                                account['login'], account['password'], cs_publicip, i),
                                                                nodeID)
            self.assertEqual('3', count_files[0])
        finally:
            self.execute_command_on_physical_node('cd; rm machine_script.py', nodeID)
        
        self.lg('- create snapshot by passing number in the name param and then list snapshots, should succeed')
        name = str(random.randint(10,100))
        self.account_owner_api.cloudapi.machines.snapshot(machineId=self.machine_id, name=name)
        snapshots = self.account_owner_api.cloudapi.machines.listSnapshots(machineId=self.machine_id)
        self.assertIn(name, [x['name'] for x in snapshots])

        self.lg('- disable the account, should succeed')
        self.api.cloudbroker.account.disable(accountId=self.account_id, reason='testing')
        account = self.account_owner_api.cloudapi.accounts.get(accountId=self.account_id)
        self.assertEqual(account['status'], 'DISABLED')

        self.lg('- try to create snapshot, should fail with 403 forbidden')
        with self.assertRaises(ApiError) as e:
            self.account_owner_api.cloudapi.machines.snapshot(machineId=self.machine_id,
                                                              name='snapshot22')
        self.lg('- expected error raised %s' % e.exception.message)
        self.assertEqual(e.exception.message, '403 Forbidden')

        self.lg('- try to start the VM, should fail with 403 forbidden')
        with self.assertRaises(ApiError) as e:
            self.account_owner_api.cloudapi.machines.start(machineId=self.machine_id)

        self.lg('- expected error raised %s' % e.exception.message)
        self.assertEqual(e.exception.message, '403 Forbidden')

        self.lg('%s ENDED' % self._testID)

    def test007_cleanup_vxlans_for_stopped_deleted_vms(self):
        """ OVC-007
        *Test case  for cleaning up vxlans for stopped or deleted VMs*

        **Test Scenario:**

        #. create virtual machine
        #. make sure there is a coressponding vxlan and space bridge
        #. stop the virtual machine
        #. check that vxlan and space bridge are deleted
        #. start the virtual machine
        #. check again on vxlan and space bridge, should be found
        #. delete the virtual machine
        #. check once more on vxlan and space bridge, shouldn't be found

        """

        self.lg('1- create virtual machine')
        machineId = self.cloudapi_create_machine(self.cloudspace_id, self.account_owner_api,
                                                 'cleanupvm', disksize=10)
        self.wait_for_status('RUNNING', self.api.cloudapi.machines.get,
                             machineId=machineId)
        self.lg('2- make sure there is a coressponding vxlan and space bridge')
        nodeID = self.get_machine_nodeID(machineId)
        machine = self.account_owner_api.cloudapi.machines.get(machineId=machineId)
        devicename = machine['interfaces'][0]['deviceName']
        NetId_hexa = devicename.split('-')[2]

        output = self.execute_command_on_physical_node('cd /sys/class/net; ls | grep %s'
                                                       % devicename, nodeID)
        self.assertEqual(output.split('\n')[0], devicename)
        output = self.execute_command_on_physical_node('cd /sys/class/net; ls | grep vx-%s'
                                                       % NetId_hexa, nodeID)
        self.assertEqual(output.split('\n')[0], 'vx-%s' % NetId_hexa)
        output = self.execute_command_on_physical_node('cd /sys/class/net; ls | grep space_%s'
                                                       % NetId_hexa, nodeID)
        self.assertEqual(output.split('\n')[0], 'space_%s' % NetId_hexa)

        self.lg('check if the routeros on the same node')
        try:
            output = self.execute_command_on_physical_node('virsh list --all | grep -o -F routeros_%s'
                                                        % NetId_hexa, nodeID)
        except:
            output = False
            
        if not output:
            self.lg('3- stop the virtual machine')
            self.account_owner_api.cloudapi.machines.stop(machineId=machineId)
            self.wait_for_status('HALTED', self.account_owner_api.cloudapi.machines.get,
                                 machineId=machineId)

            self.lg('4- check that vxlan and space bridge are deleted')
            output = self.execute_command_on_physical_node('if [ ! -d "/sys/class/net/vx-%s" ]; '
                                                           'then echo notfound;fi' % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'notfound')
            output = self.execute_command_on_physical_node('if [ ! -d "/sys/class/net/space_%s" ]; '
                                                           'then echo notfound;fi' % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'notfound')

            self.lg('5- start the virtual machine')
            self.account_owner_api.cloudapi.machines.start(machineId=machineId)
            self.wait_for_status('RUNNING', self.account_owner_api.cloudapi.machines.get,
                                 machineId=machineId)

            self.lg('6- check again on vxlan and space bridge, should be found')
            nodeID = self.get_machine_nodeID(machineId)
            output = self.execute_command_on_physical_node('cd /sys/class/net; ls | grep vx-%s'
                                                           % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'vx-%s' % NetId_hexa)
            output = self.execute_command_on_physical_node('cd /sys/class/net; ls | grep space_%s'
                                                           % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'space_%s' % NetId_hexa)

            self.lg('7- delete the virtual machine')
            self.api.cloudapi.machines.delete(machineId=machineId)

            self.lg('8- check once more on vxlan and space bridge, shouldn\'t be found')
            output = self.execute_command_on_physical_node('if [ ! -d "/sys/class/net/vx-%s" ]; '
                                                           'then echo notfound;fi' % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'notfound')
            output = self.execute_command_on_physical_node('if [ ! -d "/sys/class/net/space_%s" ]; '
                                                           'then echo notfound;fi' % NetId_hexa, nodeID)
            self.assertEqual(output.split('\n')[0], 'notfound')

        self.lg('%s ENDED' % self._testID)

    @parameterized.expand(['تست_عربى',
                           'утрчиогфрыуи',
                           'é€èêëâæüéêæâàâ',
                           'ωβνμκλπιυρσζαωθ',
                           'îöşüû«»“âç'])
    def test008_test_different_Language(self, language):
        """ OVC-008
        *Test case  for testing different language*

        **Test Scenario:**

        #. create an account with different language
        #. create a cloud space with different language
        #. create virtual machine with different language
        #. stop the virtual machine
        #. start the virtual machine
        #. delete the virtual machine
        #. delete the cloud space
        #. delete the account
        """
        language = language.decode('utf-8')
        language += str(random.randrange(1, 1000))

        self.lg('- create an account with %s name' % (language))
        self.accountId = self.api.cloudbroker.account.create(language, self.username, self.email)
        self.assertEqual(self.api.cloudapi.accounts.get(accountId=self.accountId)['id'], self.accountId)

        self.lg('- create cloudspace with %s name' % (language))
        self.cloudspaceId = self.api.cloudapi.cloudspaces.create(
            accountId=self.accountId, location=self.location, access='ARCXDU',
            name=language)
        self.assertEqual(self.api.cloudapi.cloudspaces.get(cloudspaceId=self.cloudspaceId)['id'], self.cloudspaceId)

        self.lg('- create virtual machine with %s name' % (language))
        sizes = self.api.cloudapi.sizes.list(cloudspaceId=self.cloudspace_id)
        sizes = [size for size in sizes if size['id'] in range(1, 7)]
        size = random.choice(sizes)

        sizeId = size['id']
        disksize = random.choice(size['disks'])
        self.machineId = self.api.cloudapi.machines.create(cloudspaceId=self.cloudspaceId, name=language,
                                                           sizeId=sizeId,
                                                           imageId=self.get_image()['id'], disksize=disksize)
        self.assertEqual(self.api.cloudapi.machines.get(machineId=self.machineId)['id'], self.machineId)

        self.lg('- stop the virtual machine')
        self.api.cloudapi.machines.stop(machineId=self.machineId)
        self.wait_for_status('HALTED', self.api.cloudapi.machines.get,
                             machineId=self.machineId,
                             timeout=120)

        self.lg('- start the virtual machine')
        self.api.cloudapi.machines.start(machineId=self.machineId)
        self.wait_for_status('RUNNING', self.api.cloudapi.machines.get,
                             machineId=self.machineId,
                             timeout=120)

        self.lg('- delete the virtual machine')
        self.api.cloudapi.machines.delete(machineId=self.machineId)

        self.lg('- Delete the cloud space')
        self.wait_for_status('DEPLOYED', self.api.cloudapi.cloudspaces.get,
                             cloudspaceId=self.cloudspaceId,
                             timeout=120)
        self.api.cloudbroker.cloudspace.destroy(accountId=self.accountId,
                                                cloudspaceId=self.cloudspaceId,
                                                reason='Test %s' % self._testID)
        self.wait_for_status('DESTROYED', self.api.cloudapi.cloudspaces.get,
                             cloudspaceId=self.cloudspaceId,
                             timeout=120)

        self.lg('- delete the account')
        self.api.cloudbroker.account.delete(accountId=self.accountId, reason="testing")
        self.wait_for_status('DESTROYED', self.api.cloudapi.accounts.get,
                             accountId=self.accountId,
                             timeout=120)

        self.lg('%s ENDED' % self._testID)

    def test009_access_docker_on_vm(self):
        """ OVC-009
        *Test case for publically accessing docker on vm*

        **Test Scenario:**

        #. create virtual machine with name: 'dockervm'
        #. add portforward for the created virtual machine
        #. add portforward for the docker
        #. get a physical node ID
        #. write a machine script on a physical node
        #. run the machine script , should return True
        """
        self.lg('- create virtual machine with name: \'dockervm\'')
        images = self.api.cloudapi.images.list()
        image = [image for image in images if image['name'] == 'Ubuntu 16.04 x64'][0]

        machine_id = self.cloudapi_create_machine(self.cloudspace_id, self.account_owner_api,
                                                       'dockervm', disksize=10, image_id=image['id'])

        self.lg('- add portforward for the created virtual machine')
        cs_publicip = self.add_portforwarding(machine_id, api=self.account_owner_api, cs_publicport=3000, vm_port=22)
        machine = self.account_owner_api.cloudapi.machines.get(machineId=machine_id)
        account = machine['accounts'][0]

        self.lg('- add portforward for the docker')
        self.add_portforwarding(machine_id, api=self.account_owner_api, cs_publicport=2000, vm_port=2000)

        self.lg('- get a physical node ID')
        nodeID = self.get_physical_node_id(self.cloudspace_id)

        # This machine scripts makes sure that i can access vm and docker form a public network
        # and makes sure that i can control the docker form inside the vm and can execute commands
        # on the docker itself.
        self.lg('- write a machine script on a physical node')
        machine_script = '#!/usr/bin/env/python ' \
                         '\nfrom JumpScale import j ' \
                         '\nimport sys ' \
                         '\nfrom fabric import network ' \
                         '\nlogin = sys.argv[1] \npassword = sys.argv[2] ' \
                         '\ncsip = sys.argv[3] \nvm_port = int(sys.argv[4]) ' \
                         '\ndocker_port = sys.argv[5] \nresults = [] ' \
                         '\nconnection_vm = j.remote.cuisine.connect(csip, vm_port, password, login)' \
                         '\nconnection_vm.user(login)' \
                         '\nconnection_vm.fabric.state.output["running"]=False' \
                         '\nconnection_vm.fabric.state.output["stdout"]=False' \
                         '\nconnection_vm.apt_get("update")' \
                         '\nconnection_vm.apt_get("install docker.io")' \
                         '\nconnection_vm.run("echo %s | sudo -S docker run --hostname=dockertest ' \
                         '--name=dockertest -i -t -d -p 2000:22 kheirj/ssh-docker:V3"%password)' \
                         '\nconnection_vm.run("echo %s | sudo -S docker stop dockertest"%password) ' \
                         '\nstopped = connection_vm.run("echo %s | sudo -S docker ps -a | grep -c Exited"%password)' \
                         '\nresults.append(stopped.endswith("1"))' \
                         '\nconnection_vm.run("echo %s | sudo -S docker start dockertest"%password)' \
                         '\nstarted = connection_vm.run("echo %s | sudo -S docker ps -a | grep -c Up"%password)' \
                         '\nresults.append(started.endswith("1"))' \
                         '\nnetwork.disconnect_all()' \
                         '\nconnection_docker = j.remote.cuisine.connect(csip, docker_port, "rooter", "root")' \
                         '\nconnection_docker.user("root")' \
                         '\nconnection_docker.fabric.state.output["running"]=False' \
                         '\nconnection_docker.fabric.state.output["stdout"]=False' \
                         '\nresults.append(connection_docker.run("hostname") == "dockertest")' \
                         '\nconnection_docker.run("cd; touch docker.txt")' \
                         '\nresults.append(connection_docker.run("cd; ls -1 | wc -l") == "1")' \
                         '\nprint(results.count(results[0]) == len(results))'

        for line in machine_script.splitlines():
            self.execute_command_on_physical_node('cd; echo \'%s\' >> machine_script.py' % line, nodeID)

        try:
            self.lg('#. run the machine script on the, should return True')
            flag = self.execute_command_on_physical_node('cd; python machine_script.py %s %s %s 3000 2000'
                                                         %(account['login'], account['password'],
                                                           cs_publicip), nodeID)
            self.lg('flag%s'%flag)
            self.assertEqual('True', flag[len(flag)-5:len(flag)-1])
        finally:
            self.execute_command_on_physical_node('cd; rm machine_script.py', nodeID)

        self.lg('%s ENDED' % self._testID)

    def test010_enable_disable_fireWall(self):
        """ OVC-010
        *Test case  for testing enable and disable virtual firewall*

        **Test Scenario:**

        #. create a cloud space
        #. deploy the cloud space
        #. stop the Virtual fire wall
        #. start the virtual fire wall
        """

        self.lg('%s STARTED' % self._testID)
        self.lg('1- Create a new cloudspace')
        cloudspaceId = self.cloudapi_cloudspace_create(self.account_id,
                                                       self.location,
                                                       self.account_owner)

        self.lg('- deploy cloudspace, should succeed')
        self.api.cloudapi.cloudspaces.deploy(cloudspaceId=cloudspaceId)
        self.wait_for_status('DEPLOYED', self.api.cloudapi.cloudspaces.get,
                         cloudspaceId=cloudspaceId)

        self.assertTrue(self.api.cloudbroker.cloudspace.stopVFW(cloudspaceId=cloudspaceId))
        time.sleep(60)
        self.assertTrue(self.api.cloudbroker.cloudspace.startVFW(cloudspaceId=cloudspaceId))
        self.lg('%s ENDED' % self._testID)

    def test011_windowsVM_with_different_sizes(self):
        """ OVC-015
        *Test case  for testing that creating a VM with windows image must use a disksize greater than 25GB*

        **Test Scenario:**

        #. create a cloud space
        #. deploy the cloud space
        #. get the windows machine image id
        #. create a VM with a windows image and disksize=10, should return 400 error
        #. create a VM with a windows image and disksize=20, should return 400 error
        #. create a VM with a windows image and disksize=25, should succeed
        """
        self.lg('%s STARTED' % self._testID)
        self.lg('1- Create a new cloudspace')
        cloudspaceId = self.cloudapi_cloudspace_create(self.account_id,
                                                       self.location,
                                                       self.account_owner)

        self.lg('- deploy cloudspace, should succeed')
        self.api.cloudapi.cloudspaces.deploy(cloudspaceId=cloudspaceId)
        self.wait_for_status('DEPLOYED', self.api.cloudapi.cloudspaces.get,
                         cloudspaceId=cloudspaceId)

        self.lg('- ')
        images = self.api.cloudapi.images.list()
        imageId = False
        for image in images:
            if 'Windows' in image['name']:
                imageId = int(image['id'])
        self.assertTrue(imageId, 'No windows image found on the environment')
        self.lg('- Get all sizes')
        diskSizes = self.api.cloudapi.sizes.list(cloudspaceId)[0]['disks']
        basic_sizes = [10, 20]
        for diskSize in basic_sizes:
            self.lg('- Create a new machine with disk size %s' % diskSize)
            with self.assertRaises(HTTPError) as e:
                self.cloudapi_create_machine(cloudspaceId,image_id=imageId,disksize=diskSize)

            self.assertEqual(e.exception.status_code, 400)

        self.lg('%s ENDED' % self._testID)

    def test012_create_machine_with_account_resourcelimit(self):
        """ OVC-016
        *Test case for create vm under account that has resource limit*

        **Test Scenario:**

        #. Create account and set resource limits.
        #. Create cloudspace, should succeed.
        #. Create extra cloudspace, should fail.
        #. Create machine under the account limits.
        #. Create another machine under the account limits.
        #. Create extra machine, should fail
        """
        self.lg('Create account (A1)')
        account_name = str(uuid.uuid4()).replace('-', '')[0:10]
        account_id = self.cloudbroker_account_create(
            name=account_name,
            username=self.username,
            email=self.email,
            maxCPUCapacity=2,
            maxMemoryCapacity=2,
            maxNumPublicIP=1,
            maxVDiskCapacity=100
        )

        self.lg('Create cloudspace, should succeed')
        cloudspace_id = self.cloudapi_cloudspace_create(
            account_id=account_id,
            location=self.location,
            access=self.username
        )

        self.lg('Create extra cloudspace, should fail')
        with self.assertRaises(HTTPError) as e:
            self.cloudapi_cloudspace_create(account_id=account_id, location=self.location, access=self.username)
        self.assertEqual(e.exception.status_code, 400)

        self.lg('Create machine under the account limits')
        self.assertTrue(self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=1024, vcpus=1, disksize=50))

        self.lg('Create another machine under the account limits')
        self.assertTrue(self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=1024, vcpus=1, disksize=50))

        self.lg('Create extra machine, should fail')
        with self.assertRaises(HTTPError) as e:
            self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=1024, vcpus=1, disksize=50)
        self.assertEqual(e.exception.status_code, 400)

    def test013_delete_nonexisting_machine(self):
        """ OVC-017
        *Test case for deleting non existing machine*

        **Test Scenario:**

        #. Delete a non existing machine, should return 404.
        """
        self.lg('Delete a non existing machine, should return 404')
        with self.assertRaises(HTTPError) as e:
            self.api.cloudapi.machines.delete(machineId=1010101010)
        self.assertEqual(e.exception.status_code, 404)

    def test015_restore_insufficient_account_resources(self):
        """ OVC-015

        *Test case for restoring a deleted machine when it would exceed the account resource limits*

        **Test Scenario:**

        #. Create and delete a VM within resource limit
        #. Create another VM or reset the account limits so restoring the VM would exceed them, should fail
        """
        self.lg('Creating account')
        account_name = str(uuid.uuid4()).replace('-', '')[0:10]
        account_id = self.cloudbroker_account_create(
            name=account_name,
            username=self.username,
            email=self.email,
            maxCPUCapacity=2,
            maxMemoryCapacity=2,
            maxVDiskCapacity=100
        )

        self.lg('Creating cloudspace')
        cloudspace_id = self.cloudapi_cloudspace_create(
            account_id=account_id,
            location=self.location,
            access=self.username
        )

        self.lg('Creating test machine')
        test_machine_id = self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=1024, vcpus=1, disksize=50)

        self.lg('Deleting test machine')
        self.api.cloudapi.machines.delete(machineId=test_machine_id)

        self.lg('Creating machine to hog all the resources')
        hog_machine_id = self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=2048, vcpus=2, disksize=100)

        self.lg('Restoring test machine, should fail due to resource limit reached')
        with self.assertRaises(HTTPError) as e:
            self.api.cloudbroker.machine.restore(machineId=test_machine_id)
        self.assertEqual(e.exception.status_code, 400)

    def test016_restore_insufficient_cloudspace_resources(self):
        """ OVC-016

        *Test case for restoring a deleted machine when it would exceed the cloudspace resource limits*

        **Test Scenario:**

        #. Create and delete a VM within resource limit
        #. Create another VM or reset the cloudspace limits so restoring the VM would exceed them, should fail
        """
        self.lg('Creating account')
        account_name = str(uuid.uuid4()).replace('-', '')[0:10]
        account_id = self.cloudbroker_account_create(
            name=account_name,
            username=self.username,
            email=self.email,
        )

        self.lg('Creating cloudspace')
        cloudspace_id = self.cloudapi_cloudspace_create(
            account_id=account_id,
            location=self.location,
            access=self.username,
            maxCPUCapacity=2,
            maxMemoryCapacity=2,
            maxVDiskCapacity=100
        )

        self.lg('Creating test machine')
        test_machine_id = self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=1024, vcpus=1, disksize=50)

        self.lg('Deleting test machine')
        self.api.cloudapi.machines.delete(machineId=test_machine_id)

        self.lg('Creating machine to hog all the resources')
        hog_machine_id = self.cloudapi_create_machine(cloudspace_id=cloudspace_id, memory=2048, vcpus=2, disksize=100)

        self.lg('Restoring test machine, should fail due to resource limit reached')
        with self.assertRaises(HTTPError) as e:
            self.api.cloudbroker.machine.restore(machineId=test_machine_id)
        self.assertEqual(e.exception.status_code, 400)
