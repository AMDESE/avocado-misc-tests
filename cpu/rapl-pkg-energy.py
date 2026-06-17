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
# Authors: Dhananjay Ugwekar <dhananjay.ugwekar@amd.com>
#          Gautham R. Shenoy <gautham.shenoy@amd.com>
#
import os
import random
import subprocess
import re
import platform
import time
from avocado import Test
from avocado import skipIf
from avocado.utils import process, distro, cpu, linux_modules
from functools import reduce
import sys
import re

family_model_dict = {
    25 : {(0,  15)   : 'Zen3',
          (16, 31)   : 'Zen4',
          (160, 175) : 'Zen4c'},
    26 : {(0,   15)  : 'Zen5',
          (16,  31)  : 'Zen5c'}
}

die_group_mask_shift = {
                            'Zen3'  : {'mask' : 0b0110, 'shift' : 1},
                            'Zen4'  : {'mask' : 0b0011, 'shift' : 0},
                            'Zen4c' : {'mask' : 0b0011, 'shift' : 0},
                            'Zen5'  : {'mask' : 0b0011, 'shift' : 0},
                            'Zen5c' : {'mask' : 0b0011, 'shift' : 0}
}

def get_family_model():
    stream = os.popen('cat /proc/cpuinfo | grep "cpu family\\|model" | grep -v "name" | sort -n | uniq')
    lines = stream.readlines()
    family = int(lines[0].split(':')[1].strip())
    model = int(lines[1].split(':')[1].strip())
    return (family, model)

def get_platform_string(family, model):
    model_dict = family_model_dict[family]
    platform_string = ""

    for (start, end) in model_dict.keys():
        if model in range(start, end + 1):
            return model_dict[(start, end)]
    return None

class rapl(Test):
    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")

    def get_die_group_mask_shift(self):
        (family, model) = get_family_model()

        if family < 25:
            self.cancel("RAPL pkg-energy tests are supported only from Zen3")

        self.log.info("The platform has Family %02Xh, Model %02Xh\n" %(family, model))
        plat_string = get_platform_string(family, model)
        if plat_string == None:
            self.log.info("This is an unknown platform. Returning mask = 0x0, shift = 0")
            return (0, 0)
        mask  = die_group_mask_shift[plat_string]['mask']
        shift = die_group_mask_shift[plat_string]['shift']
        self.log.info("This is a %s platform. Mask = 0x%1x, Shift = %d" %(plat_string, mask, shift))
        return (mask, shift)

    def setUp(self):
        if not linux_modules.module_is_loaded('rapl'):
            if not linux_modules.load_module('rapl'):
                self.cancel("The system is not loaded with RAPL module. Unable to load it.")
        energy_path = "/sys/devices/power/events/energy-pkg"
        if not os.path.exists(energy_path):
            self.cancel("RAPL energy-pkg event not found. Retry after enabling the package-energy feature from BIOS")

        if os.geteuid() != 0:
            self.cancel("User is not sudo")
        ret = os.system("perf --version")
        if ret != 0:
            self.cancel("Perf not found. Retry after installing the relavant perf tool for this kernel.")
        (self.dg_mask, self.dg_shift) = self.get_die_group_mask_shift()

    def read_topology_attr(self, cpu, attr):
        path = f"/sys/devices/system/cpu/cpu{cpu}/topology/{attr}"
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        return int(lines[0].strip())

    def compute_package_die_group_map(self):
        self.package_die_group_map = {}
        self.rapl_pkg_energy_cpu = {}
        covered_package_dies = []

        num_cpus = int(process.system_output("nproc"))
        for i in range(num_cpus):
            package_id = self.read_topology_attr(i, 'physical_package_id')
            if package_id not in self.package_die_group_map.keys():
                self.package_die_group_map[package_id] = {} #This will be a dictionary where the keys will be die-group-ids
                self.rapl_pkg_energy_cpu[package_id] = i #This will the representative for this package. RAPL energy MSR will be read here.

            die_id = self.read_topology_attr(i, 'die_id')
            die_group_id = (die_id & self.dg_mask) >> self.dg_shift #Note: We will group all CPUs belonging to the same die-group
            self.log.info(f"CPU {i} physical_package_id = {package_id}, die_id = {die_id}, die_group_id = {die_group_id}")

            if die_group_id not in self.package_die_group_map[package_id].keys():
                self.package_die_group_map[package_id][die_group_id] = [] #List of all the CPUs in the die of this package

            if (package_id, die_id) not in covered_package_dies:
                covered_package_dies.append((package_id, die_id))
                self.package_die_group_map[package_id][die_group_id].append(i) #We pick one representative from each CCD.

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

    # Loads all the CPUs of the die with busy-tasks
    def load_one_die_group(self, pkg_id, die_group_id):
        die_group_cpu_list = self.package_die_group_map[pkg_id][die_group_id]
        for cpu in die_group_cpu_list:
            process.system(f"taskset -c {cpu} yes > /dev/null &", shell=True, ignore_bg_processes=True)
            self.log.info(f"Loaded CPU {cpu} of Pkg {pkg_id}, Die-Group {die_group_id}")

    # Validates that the current energy of the package@pkg_id is greater than lower_limit.
    # Returns (success, current_energy) where status {True, False} depending on whether the validation is successful or not.
    def validate_pkg_energy(self, pkg_id, die_group_id, lower_limit):
        cpu = self.rapl_pkg_energy_cpu[pkg_id] # self.get_rapl_pkg_energy_cpu(pkg_id)
        # Retry 10 times to ensure we dont get a false negative
        for i in range(10):
            energy = self.get_energy_consumed(cpu)
            self.log.info(f"Energy after loading Package {pkg_id}, Die-Group {die_group_id} is {energy}")
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

    # Loads the package one die at a time and validates if the package energy monotonically increases.
    # Returns True on success, False on failure.
    def load_and_test(self, pkg_id):
        prev_energy = self.get_energy_consumed(pkg_id) #This is the energy when the package is idle
        self.log.info(f"Energy before loading Package {pkg_id} is {prev_energy}")

        die_group_map =  self.package_die_group_map[pkg_id]
        for die_group_id in die_group_map.keys():
            self.load_one_die_group(pkg_id, die_group_id)
            (success, energy) = self.validate_pkg_energy(pkg_id, die_group_id, self.compute_energy_lower_limit(prev_energy))

            if not success:
                return success

            prev_energy = energy
        return True

    def test(self):
        # Get the list of package-die-group map on this system
        self.compute_package_die_group_map()
        # Loop over all packages in the system
        for pkg_id in self.package_die_group_map.keys():
            # Load CPUs of the package one die-group at a time and verify that energy count monotonically increases.
            success = self.load_and_test(pkg_id)
            # Kill all the yes instances
            process.system("sudo pkill yes")
            if not success:
                self.fail("Package energy counter failed the monotonicity test")
        self.log.info(f"PASS: Validated monotonicity of the package energy counter using perf")
