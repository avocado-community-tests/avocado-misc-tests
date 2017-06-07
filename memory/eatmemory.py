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
# Author: Santhosh G <santhog4@linux.vnet.ibm.com>

import os
from avocado import Test
from avocado.utils import build
from avocado.utils import memory
from avocado.utils import process
from avocado.utils import distro
from avocado.utils import archive
from avocado.utils.software_manager import SoftwareManager


class eatmemory(Test):

    """
    Memory stress test

    :avocado: tags=memory
    """
    def setUp(self):
        sm = SoftwareManager()
        detected_distro = distro.detect()
        deps = ['gcc', 'make']
        for package in deps:
            if not sm.check_installed(package) and not sm.install(package):
                self.error(package + ' is needed for the test to be run')
        url = 'https://github.com/julman99/eatmemory/archive/master.zip'
        tarball = self.fetch_asset("eatmemory.zip", locations=[url], expire='7d')
        archive.extract(tarball, self.srcdir)
        self.srcdir = os.path.join(self.srcdir, "eatmemory-master")
        build.make(self.srcdir)
        mem = self.params.get('memory_to_test', default=memory.memtotal())
        self.mem_to_eat = self._mem_to_mbytes(mem)
        if self.mem_to_eat is None:
            self.error("Memory '%s' not valid." % mem)

    @staticmethod
    def _mem_to_mbytes(mem):
        """
        Converts memory from bytes, Kbytes, Gbytes or Tbytes to Mbytes.
        If no unit is provided, we consider it's in Kbytes, which is the
        unit of /proc/meminfo.
        """
        multiplier = {'b': 2**0,
                      'k': 2**10,
                      'm': 2**20,
                      'g': 2**30,
                      't': 2**40}
        try:
            mem_in_bytes = int(mem) * multiplier['k']
        except ValueError:
            value = int(mem[:-1])
            unit = mem[-1].lower()
            if unit not in multiplier:
                return None
            mem_in_bytes = value * multiplier[unit]

        return mem_in_bytes / multiplier['m']

    def test(self):
        os.chdir(self.srcdir)
        mem_unit = 'M'
        cmd = './eatmemory %s%s' % (self.mem_to_eat, mem_unit)
        if process.system(cmd, ignore_status=True) == 0:
            self.log.info('Success eating %s%s of memory.',
                          self.mem_to_eat, mem_unit)
        else:
            self.fail('Not able to eat %s%s of memory.' %
                      (self.mem_to_eat, mem_unit))
