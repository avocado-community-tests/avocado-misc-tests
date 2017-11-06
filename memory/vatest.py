#!/usr/bin/env python
#
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
# Author:Praveen K Pandey<praveen@linux.vnet.ibm.com>
#

import os
import shutil

from avocado import Test
from avocado import main
from avocado.utils import process,  build, memory
from avocado.utils.software_manager import SoftwareManager


class VATest(Test):
    """
    Performs Virtual address space validation

    :avocado: tags=memory, power
    """

    def setUp(self):
        '''
        Build VA Test
        '''

        # Check for basic utilities
        smm = SoftwareManager()
        for packages in ['gcc', 'make']:
            if not smm.check_installed(packages) and not smm.install(packages):
                self.cancle('%s is needed for the test to be run' % packages)

        data_dir = os.path.abspath(self.datadir)

        shutil.copyfile(os.path.join(data_dir, 'va_test.c'),
                        os.path.join(self.srcdir, 'va_test.c'))

        shutil.copyfile(os.path.join(data_dir, 'Makefile'),
                        os.path.join(self.srcdir, 'Makefile'))

        build.make(self.srcdir)

    def test(self):
        '''
        Execute VA test
        '''
        os.chdir(self.srcdir)
        scenario_arg = self.params.get('scenario_arg', default=1)

        if scenario_arg in [2, 3, 4]:
            if memory.meminfo.Hugepagesize.mb != 16:
                self.cancel(
                    "Test need to skip as 16MB huge need to configured")
            if scenario_arg == 4:
                memory.set_num_huge_pages(131072)
            else:
                memory.set_num_huge_pages(1024)
        elif scenario_arg in [5, 6, 7]:
            if memory.meminfo.Hugepagesize.gb != 16:
                self.cancel("Test need to skip as 16GB huge need to configured")
            if scenario_arg == 7:
                memory.set_num_huge_pages(2)
            else:
                memory.set_num_huge_pages(1)

        result = process.run('./va_test -s %s' %
                             scenario_arg, shell=True, ignore_status=True)
        for line in result.stdout.splitlines():
            if 'Problem' in line:
                self.fail("test failed, Please check debug log for failed"
                          "test cases")


if __name__ == "__main__":
    main()
