#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2016 IBM
# Author: Prudhvi Miryala<mprudhvi@linux.vnet.ibm.com>
#

# check the ssh into peer machine
# check the scp into peer machine

import time
import hashlib
from avocado import main
from avocado import Test
from avocado.utils.software_manager import SoftwareManager
from avocado.utils import process


class ScpTest(Test):
    '''
    check the ssh into peer
    check the scp into peer
    '''
    def setUp(self):
        '''
        To check and install dependencies for the test
        '''
        sm = SoftwareManager()
        for pkg in ["openssh-clients", "net-tools"]:
            if not sm.check_installed(pkg) and not sm.install(pkg):
                self.skip("%s package is need to test" % pkg)
        self.peer = self.params.get("peerip")
        self.user = self.params.get("user_name")

    def testscpandssh(self):
        '''
        check scp and ssh
        '''
        cmd = "ssh %s@%s echo hi" % (self.user, self.peer)
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("unable to ssh into peer machine")
        process.run("dd if=/dev/zero of=/tmp/tempfile bs=1024000000 count=1",
                    shell=True)
        time.sleep(15)
        md_val1 = hashlib.md5(open('/tmp/tempfile', 'rb').read()).hexdigest()
        time.sleep(5)
        cmd = "timeout 600 scp /tmp/tempfile %s@%s:/tmp" %\
              (self.user, self.peer)
        ret = process.system(cmd, shell=True, verbose=True)
        time.sleep(15)
        if ret != 0:
            self.fail("unable to copy into peer machine")
        cmd = "timeout 600 scp %s@%s:/tmp/tempfile /tmp" %\
              (self.user, self.peer)
        ret = process.system(cmd, shell=True, verbose=True)
        time.sleep(15)
        if ret != 0:
            self.fail("unable to copy from peer machine")
        md_val2 = hashlib.md5(open('/tmp/tempfile', 'rb').read()).hexdigest()
        time.sleep(5)
        if not md_val1 == md_val2:
            self.fail("Test Failed")

    def tearDown(self):
        '''
        remove data both peer and host machine
        '''
        self.log.info('removing data')
        cmd = "rm /tmp/tempfile"
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("unable to remove data from client")
        msg = "rm /tmp/tempfile"
        cmd = "ssh %s \"%s\"" % (self.peer, msg)
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("unable to remove data from peer")


if __name__ == "__main__":
    main()
