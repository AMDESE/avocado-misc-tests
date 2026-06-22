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
# Copyright: 2017 IBM
# Author:Shriya Kulkarni <shriyak@linux.vnet.ibm.com>
import os
import random
import subprocess
import re
import platform
from avocado import Test
from avocado import skipIf
from avocado.utils import process, distro, cpu
from avocado.utils.software_manager.manager import SoftwareManager
from functools import reduce

IS_POWER_NV = 'PowerNV' in open('/proc/cpuinfo', 'r').read()
IS_AMD = 'AuthenticAMD' in open('/proc/cpuinfo', 'r').read()
IS_MWAIT_DISABLED = 'idle=nomwait' in open('/proc/cmdline', 'r').read()
CPUIDLE_PRESENT = os.path.exists('/sys/devices/system/cpu/cpuidle')
CPUIDLE_DRIVER_PRESENT = CPUIDLE_PRESENT and 'none' not in open('/sys/devices/system/cpu/cpuidle/current_driver', 'r').read()

class cpuidle(Test):
    """
    Test to validate the number of cpu idle states
    """

    @skipIf(not IS_POWER_NV and not IS_AMD, "This test is not supported on this platform")
    @skipIf(not CPUIDLE_PRESENT, "cpuidle subsystem does not exist")
    @skipIf(not CPUIDLE_DRIVER_PRESENT, "No cpuidle driver found")
    def setUp(self):
        smm = SoftwareManager()
        detected_distro = distro.detect()
        if 'Ubuntu' in detected_distro.name:
            deps = ['linux-tools-common', 'linux-tools-%s'
                    % platform.uname()[2]]
        else:
            deps = ['kernel-tools']
        for package in deps:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel('%s is needed for the test to be run' % package)
        ret = os.system("cpupower --version")
        if ret != 0:
            self.cancel('cpupower not found, it is needed for the test to be run')

    """
    Checks if the list of strings @le matches with the list of strings
    @lo.

    If @exact_match == True, it checks if lo[i] is an exact match of
    le[i] for every i.

    However, if @exact_match is False, it checks if le[i] is a prefix
    of lo[i], i.e. a partial match.

    Returns True if le matches with lo. Returns False otherwise
    """
    def check_match(self, lo, le, exact_match = True):
        if exact_match == True:
            result = ((le > lo) - (le < lo)) == 0
            return result

        if len(le) != len(lo):
            return False

        ziplist = list(zip(le, lo))
        check_prefix = lambda p : p[0] in p[1]
        results_list = list(map(check_prefix, ziplist))
        result = reduce(lambda x,y: x and y, results_list)

        return result

    def test(self):
        """
        Validate the number of cpu idle states against device tree
        """
        for var in range(1, 10):
            cpu_num = random.choice(cpu.cpu_online_list())
            self.log.info("--------CPU: %s--------" % cpu_num)
            states = process.system_output("cpupower -c %s idle-info --silent"
                                           " | grep 'Number of idle states:' |"
                                           "awk '{print $5}'"
                                           % cpu_num, shell=True).decode("utf-8")
            observed_states = []
            observed_flags = []
            for i in range(1, int(states)):
                val = process.system_output("cat /sys/devices/system/cpu/"
                                            "cpu%s/cpuidle/state%s/"
                                            "name" % (cpu_num, i)).decode("utf-8")
                flag = process.system_output("cat /sys/devices/system/cpu/"
                                            "cpu%s/cpuidle/state%s/"
                                            "desc" % (cpu_num, i)).decode("utf-8")

                if not IS_AMD and 'power8' in cpu.get_family():
                    val = self.set_idle_states(val)
                observed_flags.append(flag)
                observed_states.append(val)
            exact_match = True
            if IS_AMD:
                # This is assuming that we are running on EPYC. We
                # should see 2 idle states there. One corresponding to
                # a shallow idle state. Another corresponding to a
                # deep state.
                # Note: AMD non-server parts may have more idle state.
                #       This test is not intended for those parts (yet...!)
                expected_states = ["C1", "C2"]
                if IS_MWAIT_DISABLED:
                    expected_flags = ["ACPI HLT", "ACPI IOPORT"]
                else:
                    expected_flags = ["ACPI FFH MWAIT", "ACPI IOPORT"]
                exact_match = False
            else:
                expected_states = self.read_from_device_tree()

            res = self.check_match(observed_states, expected_states, exact_match)
            if IS_AMD:
                res = res and self.check_match(observed_flags, expected_flags, exact_match)

            if res == True:
                self.log.info("PASS : Validated the idle states")
            else:
                self.log.info(" cpupower tool : %s and expected states"
                              ": %s" % (observed_states, expected_states))
                if IS_AMD:
                    self.log.info ("Observed flags : %s. Expected flags : %s" %(observed_flags, expected_flags))
                self.fail("FAIL: Please check the idle states")

    def read_from_device_tree(self):
        """
        Read from device tree
        """
        os.chdir('/proc/device-tree/ibm,opal/power-mgt')
        cmd_args = ['lsprop', 'ibm,cpu-idle-state-names']
        output_string = subprocess.Popen(
            cmd_args, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
        output = re.findall('\"[a-zA-Z0-9_]+\"', output_string)
        output = [x.strip("\"") for x in output]
        if 'winkle' in output:
            output.pop()
        return output

    def set_idle_states(self, val):
        """
        Small and caps issue while reading idle states from device tree and
        cpupower tool, which results in mismatch.Hence it needs to be
        corrected only for P8.
        """
        if val == 'Nap':
            return 'nap'
        if val == 'FastSleep':
            return 'fastsleep_'
