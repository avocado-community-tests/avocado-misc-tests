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
# Copyright: 2018 IBM
# Author: Naresh Bannoth<nbannoth@in.ibm.com>
#

import time
import os
from avocado import main
from avocado.utils import process
from avocado.utils import linux_modules, genio
from avocado.utils import pci
from avocado import Test


class ModuleLoadUnload(Test):

    """
    This test is for driver module unload and load verification.
    :param module: Name of the driver module
    :param iteration: Number of time to unload and load the module
    :only_io True for single provide module and False for All pci modules
    """
    def setUp(self):
        """
        get parameters.
        """
        self.module = self.params.get('module', default=None).split(',')
        self.iteration = self.params.get('iteration', default=1)
        self.only_io = self.params.get('only_io', default=None)
        self.load_unload_sleep_time = 30
        self.error_modules = []
        self.mod_list = []
        self.uname = linux_modules.platform.uname()[2]

    def built_in_module(self, module):
        """
        checking whether the given module is built_in module or not
        """
        # self.uname = linux_modules.platform.uname()[2]
        path = "/lib/modules/%s/modules.builtin" % self.uname
        for each in genio.read_all_lines(path):
            out = process.getoutput(each.split('/')[-1])
            if module == out.split('.'[0]):
                return True
            return False

    def get_depend_modules(self, module):
        """
        Returns the dependent modules
        """
        config_path = os.path.join(os.path.abspath(''),
                                   "module_unload_load.py.data/config")
        for line in genio.read_all_lines(config_path):
            if module in line:
                return line.split('=')[-1]

    def module_load_unload(self, module_list):
        """
        Unloading and loading the given module
        """
        for mod1 in module_list:
            if linux_modules.module_is_loaded(mod1) is False:
                linux_modules.load_module(mod1)
                time.sleep(self.load_unload_sleep_time)

        for _ in range(0, self.iteration):
            for mdl in module_list:
                sub_mod = self.get_depend_modules(mdl)
                if sub_mod:
                    sub_mod = sub_mod.split(' ')
                    for mod in sub_mod:
                        if mod == 'multipath':
                            process.system("multipath -F", ignore_status=True)
                            cmd = "lsmod | grep -i ^%s" % mdl
                            for _ in range(20):
                                time.sleep(3)
                                out = process.getoutput(cmd).split(" ")[-1]
                                if out.strip() != '0':
                                    self.log.info("command value : %s\n" % out)
                                    process.system("multipath -F",
                                                   ignore_status=True)
                                    continue
                                else:
                                    break
                        else:
                            self.log.info("unloading sub module %s " % mod)
                            process.system("rmmod %s" % mod)
                self.log.info("unloading module %s " % mdl)
                process.system("rmmod %s" % mdl)
                time.sleep(self.load_unload_sleep_time)
                if linux_modules.module_is_loaded(mdl) is True:
                    self.error_modules.append(mdl)
                self.log.info("loading module : %s " % mdl)
                linux_modules.load_module(mdl)
                time.sleep(self.load_unload_sleep_time)
                if linux_modules.module_is_loaded(mdl) is False:
                    self.error_modules.append(mdl)

    def test(self):
        """
        Begining the test here
        """
        pci_addrs = []
        if self.module:
            for modl in self.module:
                self.mod_list.append(modl)
        elif self.only_io is True:
            pci_addrs = pci.get_pci_addresses()
            for pci1 in pci_addrs:
                self.mod_list.append(pci.get_driver(pci1))
        else:
            cmd = "find /lib/modules/%s/ -name /*.ko" % self.uname
            for line in process.getoutput(cmd).splitlines():
                driver = process.getoutput(line.split('/')[-1])
                self.mod_list.append(driver.split('.')[0])

        for mod in self.mod_list:
            if self.built_in_module(mod) is True:
                self.mod_list.remove(mod)
        self.module_load_unload(self.mod_list)

        if self.error_modules:
            self.error("few modules failed to load unload, please check logs")


if __name__ == "__main__":
    main()