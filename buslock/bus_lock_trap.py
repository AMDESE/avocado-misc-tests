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
# Copyright: 2025 AMD
# @Author(s): Ravi Bangoria <ravi.bangoria@amd.com>
#             Kalpana Shetty <Kalpana.Shetty@amd.com>
# File: bus_lock_trap.py
# Description: Test Bus Lock Trap feature. Buslock trap allows OSes to trap after every buslock, which allows them to limit how many
#              buslocks are occurring in a system. The Bus Lock Trap is any atomic operation whose operand crosses two cache lines.
#              Since the operand spans two cache lines and the operation must be atomic, the system locks the bus while the CPU accesses
#              the two cache lines.

import os
import subprocess
import shutil
from subprocess import Popen, PIPE
from avocado import Test
from avocado import skipUnless
from avocado.utils import cpu, git, genio, build, process, linux_modules
from avocado.utils import archive
from avocado.utils.software_manager.manager import SoftwareManager

BUS_LOCK_TRAP_CPUID = "0x00000007 0x00"

class bus_lock_trap(Test):
    def setUp(self):
        '''
        Install pre-requisites packages.
        '''
        smm = SoftwareManager()
        for package in ['gcc', 'make']:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel('%s is needed for the test to be run' % package)
        shutil.copyfile(self.get_data('bus_lock.c'),
                        os.path.join(self.teststmpdir, 'bus_lock.c'))
        shutil.copyfile(self.get_data('Makefile'),
                        os.path.join(self.teststmpdir, 'Makefile'))
        build.make(self.teststmpdir)

    def cpuid_tool_build(self):
        '''
        Build/Install cpuid from source tarball
        '''
        tarball = self.fetch_asset(
                "https://etallen.com/cpuid/cpuid-20250419.src.tar.gz")
        archive.extract(tarball, self.teststmpdir)
        self.sourcedir = os.path.join(
                self.teststmpdir, os.path.basename(tarball.split('.src.tar.')[0]))
        build.make(self.sourcedir)

    def test_CPUID(self):
        '''
        Feature availability check using cpuid
        '''
        self.cpuid_tool_build()

        self.log.info("Check Bus Lock Trap CPUID feature")
        # CPUID: CPUID_Fn00000007_ECX_x00 bit 24 BusLock_Trap
        cmd = "cpuid -1 -r -l 0x7 -s 0x0"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = proc.communicate()
        cpuidDatahex = stdout.split('\n')
        for line in cpuidDatahex:
            if BUS_LOCK_TRAP_CPUID in line:
                regs = line.split(" ")
                # Check Bus Lock Trap CPUID feature. (EAX=07H, ECX=00H):ECX.[bit 24]
                bus_lock_trap = int(regs[7][6:14], 16)
                if (bus_lock_trap & 0x1000000):
                    self.log.info(
                            "PASS: CPUID check pass: Bus Lock Trap feature supported on the system")
                else:
                    self.cancel(
                            "CPUID check fail: Bus Lock Trap feature Unsupported on the system")

    def test_detect_bus_lock(self):
        '''
        Detect Bus Lock Trap feature availability from /proc/cpuinfo
        '''
        self.log.info("Detect Bus Lock Trap feature enablement from /proc/cpuinfo")
        cpu_info = genio.read_file("/proc/cpuinfo")
        if 'bus_lock_detect' in cpu_info:
            self.log.info("PASS: Bus Lock Trap cpu feature supported")
        else:
            self.cancel("Bus Lock Trap cpu feature unsupported")

    def test_kernel_config(self):
        '''
        Check for kernel config - CONFIG_X86_BUS_LOCK_DETECT
        '''
        self.log.info("Check kernel config - CONFIG_X86_BUS_LOCK_DETECT")
        if linux_modules.check_kernel_config("CONFIG_X86_BUS_LOCK_DETECT")\
                == linux_modules.ModuleConfig.NOT_SET:
            self.cancel("Config CONFIG_X86_BUS_LOCK_DETECT is not set")
        else:
            self.log.info("PASS: Config CONFIG_X86_BUS_LOCK_DETECT is enabled")

    def check_dmesg(self):
        # Check in dmesg for "bus_lock trap"
        ret = 0
        dmesg_info = Popen(["dmesg"], stdout=PIPE, universal_newlines=True)
        dmesg_log = Popen(["grep", "bus_lock"], stdin=dmesg_info.stdout, stdout=PIPE,
                        universal_newlines=True).communicate()[0]
        dmesg_info.stdout.close()

        if "bus_lock trap" in dmesg_log:
            ret = 1
            self.log.info("PASS: Bus Lock Trap feature pass")
        return ret

    def test_bus_lock(self):
        '''
        Run "bus_lock" to test bus lock trap functionality
        '''
        self.log.info("Bus lock trap functionality test")
        os.chdir(self.teststmpdir)
        cmd = "./bus_lock"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = proc.communicate()
        # "./bus_lock" test return "10" as o/p and dmesg will be updated with bus_lock entry
        if (proc.returncode == 10 and self.check_dmesg()):
            self.log.info("PASS: Bus Lock Trap Test Pass");
        else:
            self.fail("Bus Lock Trap test failed");
