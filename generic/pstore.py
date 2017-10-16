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
# Copyright: 2017 IBM
# Author: Pavithra <pavrampu@linux.vnet.ibm.com>

import time
import os
from avocado import Test
from avocado import main
from virttest import remote
from avocado.utils import process
from avocado.utils.software_manager import SoftwareManager


class PSTORE(Test):
    '''
    This script verifies persistent storage. It trigeres crash on the machine configured
    in config.yaml file and verifies the files under /sys/fs/pstore. It also
    generates sosreport and checks whether these files are included in sosreport.
    '''

    def run_cmd_out(self, cmd):
        return process.system_output(cmd, shell=True, ignore_status=True, sudo=True).strip()

    def setUp(self):
        sm = SoftwareManager()
        if not sm.check_installed("openssh*") and not sm.install("openssh*"):
            self.cancel("Fail to install openssh required for this test.")
        self.ip = self.params.get('ip', default='')
        self.user_name = self.params.get('user_name')
        self.password = self.params.get('password')
        self.prompt = self.params.get('prompt', default='')

    def test(self):
        log_file = os.path.join(self.srcdir, "file")
        session_int = remote.RemoteRunner("ssh", self.ip, 22, self.user_name, self.password,
                                          self.prompt, "\n", log_file, 100, 10, None)
        session_int.run("cat /boot/config-`uname -r` | grep PSTORE", 600, "True")
        if not self.run_cmd_out("cat %s | grep -Eai 'CONFIG_PSTORE=y'" % log_file):
            self.fail("Pstore in not configured")
        session1 = remote.remote_login("ssh", self.ip, 22, self.user_name, self.password,
                                       self.prompt, "\n", None, 100, None, None, False)
        session1.sendline('echo "c" > /proc/sysrq-trigger;')
        time.sleep(600)
        self.log.info("Connecting after reboot")
        session2 = remote.RemoteRunner("ssh", self.ip, 22, self.user_name, self.password,
                                       self.prompt, "\n", log_file, 100, 10, None)
        session2.run("ls -lrt /sys/fs/pstore", 100, "True")
        file_list = ['common-nvram', 'dmesg-nvram']
        for files in file_list:
            if files not in open(log_file).read():
                self.fail("%s is not saved" % files)
        process.run("echo "" > %s" % log_file, ignore_status=True, sudo=True, shell=True)
        session2.run("cat /etc/os-release", 600, "True")
        if "rhel" in open(log_file).read():
            session2.run("yum install sos", 600, "True")
        if "Ubuntu" in open(log_file).read():
            session2.run("yum install sosreport", 600, "True")
        session2.run("sosreport --no-report --batch --build", 100, "True")
        dir_name = self.run_cmd_out("cat %s | grep located | cut -d':' -f2" % log_file).strip()
        sosreport_dir = os.path.join(dir_name, '/sys/fs/pstore/')
        session2.run("ls -lrt %s" % sosreport_dir, 100, "True")
        for files in file_list:
            if files not in open(log_file).read():
                self.fail("%s is not saved" % files)


if __name__ == "__main__":
    main()
