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
# Copyright (C) 2025 AMD Inc.
# Authors: Gautham R. Shenoy <gautham.shenoy@amd.com>
#          Swapnil Sapkal <swapnil.sapkal@amd.com>

import os
import sys
import shutil
from avocado import Test
from avocado import skipIf
from avocado.utils import cpu, build, process, topology
from avocado.utils.software_manager.manager import SoftwareManager


class CpuTopology(Test):
    """
    CpuTopology tests topology information present in the sysfs is
    matching with CPUID 8000_0026H.
    """

    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")
    @skipIf(
        cpu.get_x86_amd_zen() < 4,
        "This test is only supported on zen4 and later platforms",
    )
    def setUp(self):
        smm = SoftwareManager()
        package = "cpuid"
        if not smm.check_installed(package) and not smm.install(package):
            self.cancel("%s is needed for the test to be run" % package)

        flag = 1
        for i in range(0, os.cpu_count()):
            die_id = int(
                process.run(
                    f"cat /sys/devices/system/cpu/cpu{i}/topology/die_id", shell=True
                ).stdout.decode()
            )
            pkg_id = int(
                process.run(
                    f"cat /sys/devices/system/cpu/cpu{i}/topology/physical_package_id",
                    shell=True,
                ).stdout.decode()
            )
            if die_id != pkg_id:
                flag = 0
                break

        if flag == 1:
            self.cancel(
                "Physical package id is same as die id for all cpus which indicates that "
                "the kernel support is not present for CPUID 8000_0026H. Skipping the test."
            )

        files = ["cpuid.c", "Makefile"]
        for file_name in files:
            self.copyutil(file_name)

        os.chdir(self.workdir)
        build.make(self.workdir)

    def copyutil(self, file_name):
        shutil.copyfile(self.get_data(file_name), os.path.join(self.workdir, file_name))

    def test(self):
        self.log.info("Printing kernel topology information from sysfs.....")
        kernel_topo = topology.get_kernel_topology(f"{self.workdir}/cpuid")
        self.log.info(kernel_topo)

        self.log.info(
            "Printing kernel topology information from CPUIID 8000_0026H....."
        )
        cpuid_80000026_topo = topology.get_cpuid_80000026_topo()
        self.log.info(cpuid_80000026_topo)

        if kernel_topo != cpuid_80000026_topo:
            self.fail(
                "Test failed as the topology from sysfs is not matching with CPUID 8000_0026H"
            )
