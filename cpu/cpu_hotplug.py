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
# Copyright: 2017 IBM
# Author: Gautham R. Shenoy <ego@linux.vnet.ibm.com>
# Author: Shriya Kulkarni <shriyak@linux.vnet.ibm.com>
import random
import time
from avocado import Test
from avocado import main
from avocado.utils import process, cpu


class cpuhotplug_test(Test):
    """
    To test hotplug within core in random manner.
    """
    def setUp(self):
        """
        Get the number of cores and threads per core
        Set the SMT value to 4/8
        """
        command = "uname -p"
        if 'ppc' not in process.system_output(command, ignore_status=True):
            self.cancel("Processor is not ppc64")
        self.nfail = 0
        self.CORES = process.system_output("lscpu | grep 'Core(s) per socket:'"
                                           "| awk '{print $4}'", shell=True)
        self.SOCKETS = process.system_output("lscpu | grep 'Socket(s):'"
                                             "| awk '{print $2}'", shell=True)
        self.THREADS = process.system_output("lscpu | grep 'Thread(s) per core"
                                             ":'| awk '{print $4}'",
                                             shell=True)
        self.T_CORES = int(self.CORES) * int(self.SOCKETS)
        self.log.info(" Cores = %s and threads = %s "
                      % (self.T_CORES, self.THREADS))
        process.system_output("echo 8 > /proc/sys/kernel/printk", shell=True)
        self.max_smt = 4
        if cpu.get_cpu_arch().lower() == 'power8':
            self.max_smt = 8
        if cpu.get_cpu_arch().lower() == 'power6':
            self.max_smt = 2
        process.system_output("ppc64_cpu --smt=%s" % self.max_smt, shell=True)
        self.path = "/sys/devices/system/cpu"

    def test(self):
        """
        This script picks a random core and then offlines all its threads
        in a random order and onlines all its threads in a random order.
        """
        for x in range(1, 100):
            self.log.info("================= TEST %s ==================" % x)
            core_list = []
            core_list = self.random_gen_cores()
            for core in core_list:
                cpu_list = []
                cpu_list = self.random_gen_cpu(core)
                self.log.info("Offlining the threads : %s for "
                              "the core : %s" % (cpu_list, core))
                for cpu_num in cpu_list:
                    self.offline_cpu(cpu_num)
                cpu_list = self.random_gen_cpu(core)
                self.log.info("Onlining the threads : %s for "
                              "the core : %s" % (cpu_list, core))
                for cpu_num in cpu_list:
                    self.online_cpu(cpu_num)
        if self.nfail > 0:
            self.fail(" Unable to online/offline few cpus")

    def random_gen_cores(self):
        """
        Generate random core list
        """
        nums = [x for x in range(0, self.T_CORES)]
        random.shuffle(nums)
        self.log.info(" Core list is %s" % nums)
        return nums

    def random_gen_cpu(self, core):
        """
        Generate random cpu number for the given core
        """
        nums = [x for x in range(self.max_smt * core,
                ((self.max_smt * core) + self.max_smt))]
        random.shuffle(nums)
        return nums

    def offline_cpu(self, cpu_num):
        """
        Offline the particular cpu
        """
        cmd = "echo 0 > %s/cpu%s/online" % (self.path, cpu_num)
        process.system(cmd, shell=True)
        time.sleep(1)
        cmd = "cat %s/cpu%s/online" % (self.path, cpu_num)
        val = process.system_output(cmd, shell=True)
        if val != '0':
            self.nfail += 1
            self.log.info("Failed to offline the cpu %s" % cpu_num)

    def online_cpu(self, cpu_num):
        """
        Online the particular cpu
        """
        cmd = "echo 1 > %s/cpu%s/online" % (self.path, cpu_num)
        process.system(cmd, shell=True)
        time.sleep(1)
        cmd = "cat %s/cpu%s/online" % (self.path, cpu_num)
        val = process.system_output(cmd, shell=True)
        if val != '1':
            self.nfail += 1
            self.log.info("Failed to online the cpu %s" % cpu_num)


if __name__ == "__main__":
    main()
