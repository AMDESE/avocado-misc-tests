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
import re

class rapl_core(Test):
    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")
    def setUp(self):
        path = "/sys/devices/power_core"
        if not os.path.isdir(path):
            self.cancel("RAPL module not found. Retry with \"modprobe rapl\"")
        energy_path = "/sys/devices/power_core/events/energy-core"
        if not os.path.exists(energy_path):
            self.cancel("RAPL energy-core event not found. Retry after enabling the core-energy feature from BIOS")

        if os.geteuid() != 0:
            self.cancel("User is not sudo")
        ret = os.system("perf --version")
        if ret != 0:
            self.cancel("Perf not found. Retry after installing the relavant perf tool for this kernel.")

    def read_topology_attr(self, cpu, attr):
        path = f"/sys/devices/system/cpu/cpu{cpu}/topology/{attr}"
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        return int(lines[0].strip())

    def compute_package_cpu_map(self):
        self.package_cpu_map = {}

        num_cpus = int(process.system_output("nproc"))
        for i in range(num_cpus):
            package_id = self.read_topology_attr(i, 'physical_package_id')
            self.log.info(f"CPU {i} physical_package_id = {package_id}")
            if package_id not in self.package_cpu_map.keys():
                self.package_cpu_map[package_id] = [] #This will be a list of all the CPUs in this package
            self.package_cpu_map[package_id].append(i)

    def get_energy_consumed(self, cpu):
        try:
            _cpustr = f"{cpu}"
            result = subprocess.run(
                ['sudo', 'perf', 'stat', '-C', _cpustr, '-e', 'power_core/energy-core/', '--', 'sleep', '1'],
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

    # Loads one cpu with busy work.
    def load_one_cpu(self, cpu):
        process.system(f"taskset -c {cpu} yes > /dev/null &", shell=True, ignore_bg_processes=True)
        self.log.info(f"Loaded CPU {cpu}")

    # Validates that the current energy of the the core containing @cpu is greater than lower_limit.
    # Returns (success, current_energy) where status {True, False} depending on whether the validation is successful or not.
    def validate_core_energy(self, cpu, lower_limit):
        # Retry 10 times to ensure we dont get a false negative
        for i in range(10):
            energy = self.get_energy_consumed(cpu)
            self.log.info(f"Energy after loading CPU {cpu} is {energy}")
            if energy > lower_limit:
                return (True, energy)

        return (False, energy)

    # Computes the lower-limit for energy validation.
    # If strict is False, the function allows for a tolerance of 1%.
    def compute_energy_lower_limit(self, energy, strict = True):
        if strict:
            return energy
        # If not strict lower the limit by 1%
        return (0.99 * energy)

    # Loads the CPU validates if the core energy monotonically increases.
    # Returns True on success, False on failure.
    def load_and_test(self, cpu):
        prev_energy = self.get_energy_consumed(cpu) #This is the energy when the package is idle
        self.log.info(f"Energy before loading CPU {cpu} is {prev_energy}")

        self.load_one_cpu(cpu)

        (success, energy) = self.validate_core_energy(cpu, self.compute_energy_lower_limit(prev_energy))
        if not success:
            return success

        prev_energy = energy
        return True

    def get_random_cpu(self, list_of_all_cpus, list_of_excluded_cpus):
        newlist = [x for x in list_of_all_cpus if x not in list_of_excluded_cpus]
        return random.choice(newlist)

    def test(self):
        # Get the list of CPUs present in each package
        self.compute_package_cpu_map()
        # Loop over all packages in the system
        for pkg_id in self.package_cpu_map.keys():
            covered_cpus = []
            # Perform the validate for 5 random CPUs from the package
            for i in range(5):
                cpu = self.get_random_cpu(self.package_cpu_map[pkg_id], covered_cpus)
                success = self.load_and_test(cpu)
                # Kill all the yes instances
                process.system("sudo pkill yes")
                if not success:
                    self.fail("Core energy counter failed the monotonicity test")
                covered_cpus.append(cpu)
        self.log.info(f"PASS: Validated monotonicity of the core energy counter using perf")
