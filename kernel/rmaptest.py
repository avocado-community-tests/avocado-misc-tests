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
# Copyright: 2016 IBM
# Author:Praveen K Pandey <praveen@linux.vnet.ibm.com>
#
# Based on code by Martin J. Bligh <mbligh@google.com>
#   copyright: 2008 Google
#   https://github.com/autotest/autotest-client-tests/tree/master/rmaptest


import os
import shutil

from avocado import Test
from avocado import main
from avocado.utils import process
from avocado.utils.software_manager import SoftwareManager


class Rmaptest(Test):

    """
    Create lots of VMAs mapped by lots of tasks.  To tickle objrmap and the
    virtual scan.
    """

    def setUp(self):

        # Check for basic utilities
        smm = SoftwareManager()
        if not smm.check_installed("gcc") and not smm.install("gcc"):
            self.error('Gcc is needed for the test to be run')

        shutil.copyfile(os.path.join(self.datadir, 'rmap-test.c'),
                        os.path.join(self.srcdir, 'rmap-test.c'))

        os.chdir(self.srcdir)

        if 'CC' in os.environ:
            cc = '$CC'
        else:
            cc = 'cc'
        process.system('%s  -Wall -o rmaptest rmap-test.c' % cc)

    def test(self):

        nu_itr = self.params.get('nu_itr', default='10')
        nu_vma = self.params.get('nu_vma', default='10')
        size_vma = self.params.get('size_vma', default='100')
        task = self.params.get('task', default='100')
        number = self.params.get('number', default='10')

        arg = '-h -i%s -n%s -s%s -t%s -V%s -v' % (
            nu_itr, nu_vma, size_vma, task, number)

        # tests is a simple array of "cmd" "arguments"
        tests = [["rmaptest", arg + " file1.dat"],
                 ["rmaptest", arg + " file2.dat"],
                 ["rmaptest", arg + " file3.dat"],
                 ]

        for test in tests:
            cmd = '%s/%s  %s' % (self.srcdir, test[0], test[1])
            process.system(cmd)

if __name__ == "__main__":
    main()
