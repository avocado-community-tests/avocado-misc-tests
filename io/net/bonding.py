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
# bonding test
# Channel bonding enables two or more network interfaces to act as one,
# simultaneously increasing the bandwidth and providing redundancy.


import time
import os
import socket
import fcntl
import struct
from avocado import main
import netifaces
from avocado import Test
from avocado.utils.software_manager import SoftwareManager
from avocado.utils import distro
from avocado.utils import process


class Bonding(Test):
    '''
    Channel bonding enables two or more network interfaces to act as one,
    simultaneously increasing the bandwidth and providing redundancy.
    '''
    def setUp(self):
        '''
        To check and install dependencies for the test
        '''
        detected_distro = distro.detect()
        sm = SoftwareManager()
        depends = []
        if detected_distro.name == "Ubuntu":
            depends.append("openssh-client")
        if detected_distro.name == "redhat":
            depends.append("openssh-clients")
        if detected_distro.name == "Suse":
            depends.append("openssh")
        for pkg in depends:
            if not sm.check_installed(pkg) and not sm.install(pkg):
                self.skip("%s package is need to test" % pkg)
        interfaces = netifaces.interfaces()
        self.user = self.params.get("username", default="root")
        self.host_interfaces = self.params.get("host_interfaces",
                                               default="").split(",")
        if not self.host_interfaces:
            self.skip("user should specify host interfaces")
        self.peer_interfaces = self.params.get("peer_interfaces",
                                               default="").split(",")
        for self.host_interface in self.host_interfaces:
            if self.host_interface not in interfaces:
                self.skip("interface is not available")
        self.peer_ip1 = self.params.get("peerip", default="")
        if not self.peer_interfaces or self.peer_ip1 == "":
            self.skip("peer machine should available")
        msg = "ip addr show  | grep %s | grep -oE '[^ ]+$'" % self.peer_ip1
        cmd = "ssh %s@%s %s" % (self.user, self.peer_ip1, msg)
        self.peer_if1 = process.system_output(cmd, shell=True).strip()
        if self.peer_if1 == "":
            self.fail("test failed because peer interface can not retrieved")
        self.bond_name = self.params.get("bondname", default="tempbond")
        self.mode = self.params.get("bonding_mode", default="")
        if self.mode == "":
            self.skip("test skipped because mode not specified")
        self.host_ips = []
        self.peer_ips = [self.peer_ip1]
        for val in self.host_interfaces:
            cmd = "ip -f inet -o addr show %s | awk '{print $4}' | cut -d /\
                  -f1" % val
            local_ip = process.system_output(cmd, shell=True).strip()
            if local_ip == "":
                self.fail("test failed because local ip can not retrieved")
            self.host_ips.append(local_ip)
        for val in self.peer_interfaces:
            msg = "ip -f inet -o addr show %s | awk '{print $4}' | cut -d /\
                  -f1" % val
            cmd = "ssh %s@%s \"%s\"" % (self.user, self.peer_ip1, msg)
            peer_ip = process.system_output(cmd, shell=True).strip()
            cmd = 'echo %s | cut -d " " -f4' % peer_ip
            peer_ip = process.system_output(cmd, shell=True).strip()
            if peer_ip == "":
                self.fail("test failed because peer ip can not retrieved")
            self.peer_ips.append(peer_ip)
        self.peer_interfaces.insert(0, self.peer_if1)
        self.net_mask = []
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for val in self.host_interfaces:
            mask = socket.inet_ntoa(fcntl.ioctl(st.fileno(), 0x891b,
                                                struct.pack('256s',
                                                val))[20:24]).strip('\n')
            self.net_mask.append(mask)
        self.bonding_slave_file = "/sys/class/net/%s/bonding/slaves"\
                                  % self.bond_name

    def bond_remove(self, arg1):
        '''
        bond_remove
        '''
        if arg1 == "local":
            self.log.info("Bonding configuration removed on laocal")
            self.log.info("------------------------------------------------")
            for ifs in self.host_interfaces:
                cmd = "ifconfig %s down" % ifs
                if process.system(cmd, shell=True, ignore_status=True) != 0:
                    self.log.info("unable to bring down the interface")
                cmd = "ifconfig %s down" % ifs
                if process.system(cmd, shell=True, ignore_status=True) != 0:
                    self.log.info("unable to bring down the interface")
                cmd = "echo -%s > %s" % (ifs, self.bonding_slave_file)
                if process.system(cmd, shell=True, ignore_status=True) != 0:
                    self.log.info("bond removing failed in local machine")
            cmd = "echo -%s > /sys/class/net/bonding_masters" % self.bond_name
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.log.info("bond removing command failed in local machine")
            time.sleep(5)
        else:
            self.log.info("Bonding configuration removed on Peer machine")
            self.log.info("------------------------------------------------")
            cmd = ''
            cmd += 'ifconfig %s down;' % self.bond_name
            for val in self.peer_interfaces:
                cmd += 'ifconfig %s down;' % val
            for val in self.peer_interfaces:
                cmd += 'ip addr flush dev %s;' % val
            for val in self.peer_interfaces:
                cmd += 'echo "-%s" > %s;' % (val, self.bonding_slave_file)
            cmd += 'echo "-%s" > /sys/class/net/bonding_masters;'\
                   % self.bond_name
            cmd += 'ifconfig %s %s netmask %s up;sleep 5;'\
                   % (self.peer_if1, self.peer_ip1, self.net_mask[0])
            peer_cmd = "ssh %s@%s \"%s\"" % (self.user, self.peer_ip1, cmd)
            if process.system(peer_cmd, shell=True, ignore_status=True) != 0:
                self.log.info("bond removing command failed in peer machine")

    def ping_check(self, arg1):
        '''
        ping check
        '''
        cmd = "ping -I %s %s -c 5" % (self.bond_name, self.peer_ip1)
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("ping failed in Mode %s, check bonding configuration"
                      % arg1)

    def bond_fail(self, arg1):
        '''
        bond fail
        '''
        for interface in self.host_interfaces:
            self.log.info("Failing interface %s for mode %s"
                          % (interface, arg1))
            cmd = "ifconfig %s down" % interface
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.fail("bonding not working when trying to down the\
                          interface %s " % interface)
            time.sleep(15)
            self.ping_check(arg1)
            cmd = "cat /proc/net/bonding/%s" % self.bond_name
            process.system_output(cmd, shell=True, verbose=True)
            cmd = "ifconfig %s up" % interface
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.fail("bonding not working when trying to up the\
                          interface %s" % interface)
            time.sleep(5)

    def bond_setup(self, arg1, arg2):
        '''
        bond setup
        '''
        if arg1 == "local":
            self.log.info("Configuring Bonding on Local machine")
            self.log.info("--------------------------------------")
            for ifs in self.host_interfaces:
                cmd = "ip addr flush dev %s" % ifs
                process.system(cmd, shell=True, ignore_status=True)
            for ifs in self.host_interfaces:
                cmd = "ifconfig %s down" % ifs
                process.system(cmd, shell=True, ignore_status=True)
            cmd = "modprobe bonding"
            process.system(cmd, shell=True, ignore_status=True)
            cmd = "echo +%s > /sys/class/net/bonding_masters" % self.bond_name
            process.system(cmd, shell=True, ignore_status=True)
            cmd = "echo %s > /sys/class/net/%s/bonding/mode"\
                  % (arg2, self.bond_name)
            process.system(cmd, shell=True, ignore_status=True)
            cmd = "echo 100 > /sys/class/net/%s/bonding/miimon"\
                  % self.bond_name
            process.system(cmd, shell=True, ignore_status=True)
            for val in self.host_interfaces:
                cmd = "echo '+%s' > %s"\
                      % (val, self.bonding_slave_file)
                if process.system(cmd, shell=True, ignore_status=True) != 0:
                    self.fail("Mode %s FAIL while bonding setup" % arg2)
                time.sleep(2)
            cmd = "cat /proc/net/bonding/%s | grep 'Bonding Mode' |\
                  cut -d ':' -f 2" % self.bond_name
            bond_name_val = process.system_output(cmd, shell=True).strip('\n')
            self.log.info("Trying bond mode %s [ %s ]"
                          % (arg2, bond_name_val))
            for ifs in self.host_interfaces:
                cmd = "ifconfig %s up" % ifs
                if process.system(cmd, shell=True, ignore_status=True) != 0:
                    self.fail("unable to interface up")
            cmd = "ifconfig %s %s netmask %s up"\
                  % (self.bond_name, self.host_ips[0], self.net_mask[0])
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.fail("bond setup command failed in local machine")
            time.sleep(5)
        else:
            self.log.info("Configuring Bonding on Peer machine")
            self.log.info("------------------------------------------")
            cmd = ''
            for val in self.peer_interfaces:
                cmd += 'ip addr flush dev %s;' % val
            for val in self.peer_interfaces:
                cmd += 'ifconfig %s down;' % val
            cmd += 'modprobe bonding;'
            cmd += 'echo +%s > /sys/class/net/bonding_masters;'\
                   % self.bond_name
            cmd += 'echo 0 > /sys/class/net/%s/bonding/mode;'\
                   % self.bond_name
            cmd += 'echo 100 > /sys/class/net/%s/bonding/miimon;'\
                   % self.bond_name
            for val in self.peer_interfaces:
                cmd += 'echo "+%s" > %s;' % (val, self.bonding_slave_file)
            for val in self.peer_interfaces:
                cmd += 'ifconfig %s up;' % val
            cmd += 'ifconfig %s %s netmask %s up;sleep 5;'\
                   % (self.bond_name, self.peer_ip1, self.net_mask[0])
            peer_cmd = "ssh %s@%s \"%s\"" % (self.user, self.peer_ip1, cmd)
            if process.system(peer_cmd, shell=True, ignore_status=True) != 0:
                self.fail("bond setup command failed in peer machine")

    def test_bonding(self):
        '''
        test options are mandatory
        ext test options are depends upon user
        '''
        self.log.info("Bonding")
        msg = "[ -d /sys/class/net/%s ]" % self.bond_name
        cmd = "ssh %s@%s %s" % (self.user, self.peer_ip1, msg)
        if process.system(cmd, shell=True, ignore_status=True) == 0:
            self.fail("bond name already exists on peer machine")
        self.bond_dir = os.path.join("/sys/class/net/", self.bond_name)
        if os.path.isdir(self.bond_dir):
            self.fail("bond name already exists on local machine")
        self.log.info("TESTING FOR MODE %s" % self.mode)
        self.log.info("-------------------------------------------------")
        self.bond_setup("peer", "")
        self.bond_setup("local", self.mode)
        cmd = "cat /proc/net/bonding/%s" % self.bond_name
        process.run(cmd, shell=True, verbose=True)
        self.ping_check(self.mode)
        self.bond_fail(self.mode)
        self.log.info("Mode %s OK" % self.mode)

    def tearDown(self):
        '''
        set the initial state
        '''
        self.bond_remove("local")
        for val1, val2, val3 in map(None, self.host_interfaces,
                                    self.host_ips, self.net_mask):
            cmd = "ifconfig %s %s netmask %s up"\
                  % (val1, val2, val3)
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.log.info("unable to bring up to original state in host")
            time.sleep(5)
        self.bond_remove("peer")
        for val1, val2, val3 in map(None, self.peer_interfaces,
                                    self.peer_ips, self.net_mask):
            msg = "ifconfig %s %s netmask %s up"\
                  % (val1, val2, val3)
            cmd = "ssh %s@%s \"%s\"" % (self.user, self.peer_ip1, msg)
            if process.system(cmd, shell=True, ignore_status=True) != 0:
                self.log.info("unable to bring up to original state in host")
            time.sleep(5)


if __name__ == "__main__":
    main()
