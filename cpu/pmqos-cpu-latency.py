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
import glob

CPUIDLE_PRESENT = os.path.exists('/sys/devices/system/cpu/cpuidle')
CPUIDLE_DRIVER_PRESENT = CPUIDLE_PRESENT and 'none' not in open('/sys/devices/system/cpu/cpuidle/current_driver', 'r').read()

class pmqos_cpu_latency(Test):
    @skipIf(cpu.get_vendor() != "amd", "This test is only supported for AMD platforms")
    @skipIf(not CPUIDLE_PRESENT, "cpuidle subsystem does not exist")
    @skipIf(not CPUIDLE_DRIVER_PRESENT, "No cpuidle driver found")

    def setUp(self):
        path = "/sys/devices/system/cpu/cpuidle"
        if not os.path.isdir(path):
            self.fail("CPUIdle directory does not exist")
        if os.geteuid() != 0:
            self.fail("User is not sudo")
        if not os.path.exists("/dev/cpu_dma_latency"):
            self.fail("cpu_dma_latency file does not exist")

    def compute_cstate_paths(self, cpu='cpu0'):
        base_path = f'/sys/devices/system/cpu/{cpu}/cpuidle/'
        cstate_dirs = sorted(glob.glob(os.path.join(base_path, 'state*')))

        cstate_paths = []
        for state_dir in cstate_dirs:
            time_path = os.path.join(state_dir, 'time')
            latency_path = os.path.join(state_dir, 'latency')
            if os.path.exists(time_path) and os.path.exists(latency_path):
                cstate_paths.append({
                    'state': os.path.basename(state_dir),
                    'time_path': time_path,
                    'latency_path': latency_path
                })
        self.cstate_paths = cstate_paths

    def read_state_attrs(self, attr_path):
        attr_dict = {}
        for entry in self.cstate_paths:
            with open(entry[attr_path], "r") as f:
                attr_dict[entry['state']] = int(f.read().strip())
        return attr_dict

    def read_state_times(self):
        return self.read_state_attrs('time_path')

    def read_state_latencies(self):
        return self.read_state_attrs('latency_path')

    def capture_state_latencies(self):
        self.latencies = self.read_state_latencies()
        self.log.info(f"Wakeup latencies (us): {self.latencies}")

    def open_cpu_dma_latency(self):
        self.fd = open("/dev/cpu_dma_latency", "wb", buffering=0)

    def write_cpu_dma_latency(self, lat_val_us):
        self.fd.write(lat_val_us.to_bytes(4, byteorder=sys.byteorder))
        self.log.info(f"Wrote latency constraint: {lat_val_us} µs.")

    def do_sleep(self):
        sleep_time_s = self.sleep_time
        self.log.info(f"Sleeping for {sleep_time_s}s...")
        time.sleep(sleep_time_s)

    def get_latency_constrained_residencies(self, lat_val_us):
        self.write_cpu_dma_latency(lat_val_us)
        cpu = self.cpu

        #Wake up the CPU before measuring the idle durations.
        os.system(f"taskset -c {cpu} yes& sleep 1; pkill yes");

        before = self.read_state_times()
        self.do_sleep()
        after = self.read_state_times()

        self.log.info("C-state residencies (us):")
        residencies = {}
        for state in before:
            delta = (after[state] - before[state])
            residencies[state] = delta
            self.log.info(f"  {state}: {delta} us")
        return residencies

    def validate_cstate_residency(self, lat_val_us, residencies_dict):
        # Determine expected behavior
        undesired_states_entered = {}
        good_states_idle_duration = 0
        latencies_dict = self.latencies
        total_residency = 0

        for state, latency in latencies_dict.items():
            residency = residencies_dict[state]
            total_residency = total_residency + residency
            if latency <= lat_val_us:
                good_states_idle_duration += residency
            else:
                if residency > 0:
                    undesired_states_entered[state] = (latency, residency)

        if total_residency == 0:
            self.log.info(f"No Idle state entered. Retrying test for PMOS latency {lat_val_us} us")
            return -1

        if len(undesired_states_entered.keys()) != 0:
            error_string = f"For latency constraint of {lat_val_us} us, spent "
            for state, (latency, residency) in undesired_states_entered.items():
                error_string += f"{residency} ms in {state} (latency : {latency} us), "
            self.fail(f"FAIL: {error_string}")

        if good_states_idle_duration == 0:
            self.fail(f"FAIL: None of the states with latency atmost {lat_val_us} us have been entered")

        return 0

    def latency_constrained_residency_test(self, lat_val_us):
        max_retries = 10
        for i in range(max_retries):
            residencies_dict = self.get_latency_constrained_residencies(lat_val_us)
            ret = self.validate_cstate_residency(lat_val_us, residencies_dict)
            if ret == 0:
                return
            self.do_sleep()
        self.cancel(f"The target CPU is busy for {max_retries} iterations. Retry after ensuring that there is no load on the system")

    def test(self):
        num_cpus = int(process.system_output("nproc"))
        cpu = random.choice(range(num_cpus))
        self.cpu = cpu
        self.log.info(f"Targetting CPU {cpu}")
        cpu_str = f"cpu{cpu}"

        self.compute_cstate_paths(cpu_str)
        self.capture_state_latencies()
        self.open_cpu_dma_latency()
        self.sleep_time = 1

        max_latency = 0
        for latency_value_us in self.latencies.values():
            if max_latency < latency_value_us:
                max_latency = latency_value_us

            if latency_value_us > 0:
                latency_value_us -= 1

            # Validate the cstate_residency by setting cpu_dma_latency to latency_value_us
            self.latency_constrained_residency_test(latency_value_us)

        #Validate the case that when the latency constraint is greater than all the state-latencies
        self.latency_constrained_residency_test(max_latency + 1)

        self.log.info("PASS : Validated the PMQoS cpu_dma_latency")
