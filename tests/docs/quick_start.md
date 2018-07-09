## How to execute Tests ?

```
git clone https://github.com/0-complexity/openvcloud
cd openvcloud/tests
bash prepare.sh
```

### OVC Test
Needs to be run as a root
```
sudo -i
cd openvcloud/tests
nosetests-2.7 -s -v ovc_master_hosted/OVC/ --tc-file config.ini
```

### ACL Tests
Needs to be run as a root
```
sudo -i
cd openvcloud/tests
nosetests-2.7 -s -v ovc_master_hosted/ACL/ --tc-file config.ini
```

### Portal Tests

```
cd openvcloud/tests/ovc_master_hosted/Portal
export PYTHONPATH=./
```

#### Normal mode
```
nosetests-3.4 -s -v testcases/admin_portal/ --tc-file config.ini
```

#### Headless mode
```
xvfb-run -a nosetests-3.4 -s -v testcases/admin_portal/ --tc-file config.ini
```