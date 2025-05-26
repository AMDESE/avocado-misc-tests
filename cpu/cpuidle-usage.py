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
# Author: Dhananjay Ugwekar <dhananjay.ugwekar@amd.com>

import os
import random
import subprocess
import re
import platform
import time
from avocado import Test
from avocado import skipIf
from avocado.utils import process, distro, cpu
import sys

original_state = []

CPUIDLE_PRESENT = os.path.exists('/sys/devices/system/cpu/cpuidle')
CPUIDLE_DRIVER_PRESENT = CPUIDLE_PRESENT and 'none' not in open('/sys/devices/system/cpu/cpuidle/current_driver', 'r').read()

class cpuidle_usage(Test):
    """
    Functional tests for CPUIdle subsystem
    """
    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")
    @skipIf(not CPUIDLE_PRESENT, "cpuidle subsystem does not exist")
    @skipIf(not CPUIDLE_DRIVER_PRESENT, "No cpuidle driver found")
    def setUp(self):
        path = "/sys/devices/system/cpu/cpuidle"
        if not os.path.isdir(path):
            self.fail("FAIL: CPUIdle directory does not exist")
        if os.geteuid() != 0:
            self.fail("FAIL: User is not sudo")

    def count_cstates(self, cpu_id=0):
        path = f"/sys/devices/system/cpu/cpu{cpu_id}/cpuidle/"
        count = 0
        for item in os.listdir(path):
            if item.startswith("state"):
                count += 1
        return count

    def set_one_cpuidle_disable_val(self, cpu_id, disable_val, state_num):
        disable_path = f"/sys/devices/system/cpu/cpu{cpu_id}/cpuidle/state{state_num}/disable"
        ret =  process.system(f"echo {disable_val} > {disable_path}", shell=True, sudo=True)
        return ret

    def get_one_cpuidle_disable_val(self, cpu_id, state_num):
        disable_path = f"/sys/devices/system/cpu/cpu{cpu_id}/cpuidle/state{state_num}/disable"
        disable_val = process.system_output(f"cat {disable_path}")
        return disable_val

    def get_one_state_usage(self, cpu_id, state_num):
        usage_path = f"/sys/devices/system/cpu/cpu{cpu_id}/cpuidle/state{state_num}/usage"
        usage_count = int(process.system_output(f"cat {usage_path}"))
        return usage_count

    def save_cpuidle_disable_val(self, cpu_id, n_cstates):
        for state_num in range(0, n_cstates):
            disable_val = self.get_one_cpuidle_disable_val(cpu_id, state_num)
            original_state.append(int(disable_val))

    def restore_cpuidle_disable_val(self, cpu_id, n_cstates):
        # Restore original cpuidle state
        for state_num in range(0, n_cstates):
            disable_val = original_state[state_num]
            ret = self.set_one_cpuidle_disable_val(cpu_id, disable_val, state_num)
            if ret != 0:
                self.restore_cpuidle_disable_val(cpu_id, n_cstates)
                self.fail(f"FAIL: Unable to write to CPUIdle disable path for CPU: {cpu_id}, State: {state_num}")

    def set_cpuidle_disable_val(self, cpu_id, disable_val, n_cstates):
        # Write "disable_val" to all CPUIdle states
        for state_num in range(0, n_cstates):
            ret = self.set_one_cpuidle_disable_val(cpu_id, disable_val, state_num)
            if ret != 0:
                self.restore_cpuidle_disable_val(cpu_id, n_cstates)

    def cpuidle_usage_test(self, cpu_id, n_cstates):
        #Disable all the idle states for this CPU
        self.set_cpuidle_disable_val(cpu_id, 1, n_cstates)

        # Enable one CPUIdle state at a time and ensure that it is functional
        for state_num in range(0, n_cstates):

            ret = self.set_one_cpuidle_disable_val(cpu_id, 0, state_num)
            if ret != 0:
                self.restore_cpuidle_disable_val(cpu_id, n_cstates)
                self.fail(f"FAIL: Unable to write to CPUIdle disable path for CPU: {cpu_id}, State: {state_num}")

            # Wake the CPU up, so that the usage stats are updated
            process.system(f"taskset -c {cpu_id} timeout 0.1 yes > /dev/null &", shell=True, ignore_status=True)
            usage_count_before = self.get_one_state_usage(cpu_id, state_num)
            # Let the CPU sleep for 200 ms
            time.sleep(0.2)

            # Again wake the CPU up, so that the usage stats are updated
            process.system(f"taskset -c {cpu_id} timeout 0.1 yes > /dev/null &", shell=True, ignore_status=True)
            # Let the CPU sleep for another 200 ms just to be sure
            time.sleep(0.2)

            usage_count_after = self.get_one_state_usage(cpu_id, state_num)

            # Wake the CPU up, so that the usage stats are updated
            if usage_count_after <= usage_count_before:
                self.restore_cpuidle_disable_val(cpu_id, n_cstates)
                self.fail(f"FAIL: Usage count not increasing for CPU: {cpu_id} State: {state_num}")
            else:
                ret = self.set_one_cpuidle_disable_val(cpu_id, 1, state_num)
                if ret != 0:
                    self.restore_cpuidle_disable_val(cpu_id, n_cstates)
                    self.error(f"FAIL: Unable to write to CPUIdle disable path for CPU: {cpu_id}, State: {state_num}")

    def test(self):
        cpulist = []
        for var in range(1, 10):
            # Test for 10 CPUs selected at random. Ensure we test on a different CPU each time.
            while True:
                cpu_id = random.choice(cpu.cpu_online_list())
                if cpu_id not in cpulist:
                    cpulist.append(cpu_id)
                    break

            self.log.info("--------CPU: %s--------" % cpu_id)

            n_cstates = self.count_cstates(cpu_id)
            self.save_cpuidle_disable_val(cpu_id, n_cstates)

            self.cpuidle_usage_test(cpu_id, n_cstates)
            self.restore_cpuidle_disable_val(cpu_id, n_cstates)
        self.log.info("PASS : CPUIdle usage test successfully completed")
