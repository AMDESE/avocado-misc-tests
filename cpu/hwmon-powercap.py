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
#
import os
import random
import subprocess
import re
import platform
import time
from avocado import Test
from avocado import skipIf
from avocado.utils import process, distro, cpu
from functools import reduce
import sys
import glob

def get_family_model():
    stream = os.popen('cat /proc/cpuinfo | grep "cpu family\\|model" | grep -v "name" | sort -n | uniq')
    lines = stream.readlines()
    family = int(lines[0].split(':')[1].strip())
    model = int(lines[1].split(':')[1].strip())
    return (family, model)

def get_cpu_list_str(cpu_list):
    if not cpu_list:
        return ""

    ranges = []
    start = cpu_list[0]
    end = cpu_list[0]

    for i in range(1, len(cpu_list)):
        if cpu_list[i] == end + 1:
            end = cpu_list[i]
        else:
            if start == end:
                ranges.append(f"{start}")
            else:
                ranges.append(f"{start}-{end}")
            start = cpu_list[i]
            end = cpu_list[i]

    if start == end:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}-{end}")

    return ",".join(ranges)

class hwmon_powercap(Test):
    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")

    def setUp(self):

        (family, model) = get_family_model()
        if family < 26:
            self.cancel("sysfs based powercap tests are only supported Zen5 onwards")

        self.hsmp_platform_nodes = glob.glob('/sys/devices/platform/AMDI0097:0[0-9]')
        if len(self.hsmp_platform_nodes) == 0:
            self.cancel("HSMP platform node /sys/devices/platform/AMDI0097:0X not present. Please install the HSMP module and retry")

        hwmon_glob = glob.glob(f'/sys/devices/platform/AMDI0097:00/hwmon/hwmon[0-9]')
        if len(hwmon_glob) == 0:
            self.cancel("HSMP-HWMON node /sys/devices/platform/AMDI0097:00/hwmon/hwmonX is not exposed by this version of the kernel.")

        path = "/sys/devices/power"
        if not os.path.isdir(path):
            self.cancel("RAPL module not found. Retry with \"modprobe rapl\"")
        energy_path = "/sys/devices/power/events/energy-pkg"
        if not os.path.exists(energy_path):
            self.cancel("RAPL energy-pkg event not found. Retry after enabling the package-energy feature from BIOS")

        if os.geteuid() != 0:
            self.cancel("User is not sudo")
        ret = os.system("perf --version")
        if ret != 0:
            self.cancel("Perf not found. Retry after installing the relavant perf tool for this kernel.")

    def read_sysfs_int(self, path):
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        return int(lines[0].strip())

    def write_sysfs_int(self, path, value):
        value_str = f'{value}'
        fd = open(path, 'w')
        fd.write(value_str)
        fd.close()

    def read_topology_attr(self, cpu, attr):
        path = f"/sys/devices/system/cpu/cpu{cpu}/topology/{attr}"
        return self.read_sysfs_int(path)

    def compute_package_cpus_map(self):
        self.package_cpus_map = {}
        self.rapl_pkg_energy_cpu = {}
        covered_package_cores = []

        num_cpus = int(process.system_output("nproc"))
        for i in range(num_cpus):
            package_id = self.read_topology_attr(i, 'physical_package_id')
            if package_id not in self.package_cpus_map.keys():
                self.package_cpus_map[package_id] = [] #This will be a list of all the primary threads of this package
                self.rapl_pkg_energy_cpu[package_id] = i #This will the representative for this package. RAPL energy MSR will be read here.

            core_id = self.read_topology_attr(i, 'core_id')
            self.log.info(f"CPU {i} physical_package_id = {package_id}, core_id = {core_id}")

            if (package_id, core_id) not in covered_package_cores:
                covered_package_cores.append((package_id, core_id))
                self.package_cpus_map[package_id].append(i) #We pick one representative from each core.

        for i in sorted(self.package_cpus_map.keys()):
            path = f'/sys/devices/platform/AMDI0097:0{i}'
            if not os.path.isdir(path):
                self.cancel(f"The HSMP node {path} for Package {i} does not exist. Cancelling the test.")

    def get_energy_consumed(self, cpu):
        try:
            _cpustr = f"{cpu}"
            result = subprocess.run(
                ['sudo', 'perf', 'stat', '-C', _cpustr, '-e', 'power/energy-pkg/', '--', 'sleep', '1'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            perf_output = result.stderr
            match_pattern = re.search(r'([\d.]+)\s+Joules', perf_output)
            if match_pattern:
                energy_joules = float(match_pattern.group(1))
                return energy_joules
            else:
                print("Energy value not found in output.")
                return None
        except subprocess.CalledProcessError as e:
            print("Error executing perf:", e)
            print("stderr:", e.stderr)
            return None

    def get_pkg_hwmon_path(self, pkg_id):
        hwmon_glob = f'/sys/devices/platform/AMDI0097:0{pkg_id}/hwmon/hwmon[0-9]'
        hwmon_path = glob.glob(hwmon_glob)[0]
        return hwmon_path

    def get_pkg_power_cap_path(self, pkg_id):
        hwmon_path = self.get_pkg_hwmon_path(pkg_id)
        power1_cap_path = f'{hwmon_path}/power1_cap'
        return power1_cap_path

    def get_pkg_power_cap_max_path(self, pkg_id):
        hwmon_path = self.get_pkg_hwmon_path(pkg_id)
        power1_cap_max_path = f'{hwmon_path}/power1_cap_max'
        return power1_cap_max_path

    def get_pkg_power_cap(self, pkg_id):
        power_cap_uW  = self.read_sysfs_int(self.get_pkg_power_cap_path(pkg_id))
        return power_cap_uW // (1000*1000)

    def get_pkg_power_cap_max(self, pkg_id):
        power_cap_max_uW  = self.read_sysfs_int(self.get_pkg_power_cap_max_path(pkg_id))
        return power_cap_max_uW // (1000*1000)

    def set_pkg_power_cap(self, pkg_id, power_cap_W):
        power_cap_uW = power_cap_W * 1000 * 1000
        path = self.get_pkg_power_cap_path(pkg_id)
        self.write_sysfs_int(path, power_cap_uW)

    # Loads all the primary threads of the package with busy-tasks
    def load_one_package(self, pkg_id):
        pkg_cpus_list = self.package_cpus_map[pkg_id]
        pkg_cpu_list_str = get_cpu_list_str(sorted(pkg_cpus_list))
        start=0
        end=len(pkg_cpus_list) - 1

        command = f"for i in `seq {start} {end}`; do taskset -c {pkg_cpu_list_str} yes > /dev/null & done"
        process.system(command, shell=True, ignore_bg_processes=True)
        self.log.info(f"Loaded CPUs {pkg_cpu_list_str} of Pkg {pkg_id}")

    # Validates that the current energy of the package@pkg_id is within the power-cap
    # Returns {True, False} depending on whether the validation is successful or not.
    def validate_pkg_energy(self, pkg_id, power_cap):
        cpu = self.rapl_pkg_energy_cpu[pkg_id]
        upper_bound = self.compute_power_cap_upper_bound(power_cap)
        # Retry 10 times to ensure we dont get a false negative
        for i in range(10):
            energy = self.get_energy_consumed(cpu)
            self.log.info(f"Energy of Package {pkg_id} with power_cap {power_cap}W is {energy}W")
            if energy < upper_bound:
                return True

        return False

    # Computes the upper-bound of the power-cap for energy validation.
    # The function allows for a tolerance of 1%.
    def compute_power_cap_upper_bound(self, power_cap):
        # Add a 1% headroom.
        return (1.01 * power_cap)

    # Slowly increases the power-cap for @pkg_id from @min_power_cap to
    # @max_power_cap in steps of 25W and validates that the
    # socket-power for @pkg-id is within the set power-cap.
    #
    # Returns True on success, False on failure.
    def power_cap_test(self, pkg_id, min_power_cap, max_power_cap):
        for power_cap in range(int(min_power_cap), int(max_power_cap), 25):
            self.log.info(f"Setting power_cap {power_cap} W for Package {pkg_id}")
            self.set_pkg_power_cap(pkg_id, power_cap)
            success = self.validate_pkg_energy(pkg_id, power_cap)
            if not success:
                return success
        return True

    def test(self):
        # Get the list of package-die-group map on this system
        self.compute_package_cpus_map()
        # Loop over all packages in the system
        for pkg_id in self.package_cpus_map.keys():
            orig_power_cap = self.get_pkg_power_cap(pkg_id)

            self.log.info(f"Original power_cap is {orig_power_cap} W for Package {pkg_id}")
            max_power_cap = self.get_pkg_power_cap_max(pkg_id)
            min_power_cap = max_power_cap / 2

            self.load_one_package(pkg_id)

            # Increase the power-cap from min_power_cap to max_power_cap in steps of 50W and validate that the package energy is lower than the power-cap
            success = self.power_cap_test(pkg_id, min_power_cap, max_power_cap)
            self.set_pkg_power_cap(pkg_id, orig_power_cap)
            restored_power_cap = self.get_pkg_power_cap(pkg_id)
            self.log.info(f"Restored power_cap of Package {pkg_id} to {restored_power_cap} W")

            # Kill all the "yes" instances
            process.system("sudo pkill yes")

            if not success:
                self.fail(f"Package {pkg_id} failed the hwmon-powercap test")
        self.log.info(f"PASS: Validated monotonicity of the package energy counter using perf")
