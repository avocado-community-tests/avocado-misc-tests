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
#
# Copyright: 2016 IBM
# Author: Manvanthara B Puttashankar <manvanth@linux.vnet.ibm.com>


"""
smartctl - controls  the Self-Monitoring, Analysis and Reporting
Technology (SMART) system built into most ATA/SATA and SCSI/SAS
hard drives and solid-state drives
"""

from avocado import Test
from avocado.utils.software_manager import SoftwareManager
from avocado.utils import process
from avocado import main


class SmartctlTest(Test):

    """
    This scripts performs S.M.A.R.T relavent tests using smartctl tool
    on one or more disks
    """

    def setUp(self):

        """
        Checking if the required packages are installed,
        if not found packages will be installed
        """

        smm = SoftwareManager()
        if not smm.check_installed("smartctl"):
            self.log.info("smartctl should be installed prior to the test")
            if smm.install("smartmontools") is False:
                self.skip("Unable to install smartctl")
        self.option = self.params.get('option')
        self.disks = self.params.get('disk')
        self.timeout = self.params.get("timeout", default="2400")
        if self.disks is '' or self.option is '':
            self.skip(" Test skipped!!, please ensure Block device and \
            options are specified in yaml file")
        cmd = "df -h /boot | grep %s" % (self.disks)
        if process.system(cmd, ignore_status=True, shell=True,
                          timeout=self.timeout) == 0:
            self.skip(" Skipping it's OS disk")

    def test(self):
        """
        executes S.M.A.R.T options using smartctl tool
        """
        self.log.info("option %s on %s Disks" % (self.option, self.disks))
        cmd = "smartctl %s %s" % (self.option, self.disks)
        if self.option == "--test=long":
            cmd += " && sleep 120 && smartctl -X %s && smartctl -A %s" \
                % (self.disks, self.disks)
        if process.system(cmd, ignore_status=True, shell=True,
                          timeout=self.timeout):
            self.fail("Smartctl option %s FAILS" % self.option)


if __name__ == "__main__":
    main()
