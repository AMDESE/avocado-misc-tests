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
# Copyright: 2026 Advanced Micro Devices, Inc.
# Author: Sumit Kumar <sumitkum@amd.com>
#
"""
Avocado test suite to validate FRED (Flexible Return and Event Delivery) enablement.
"""

from avocado import Test
from avocado.core.decorators import skipIf
from avocado.utils import cpu, linux_modules, dmesg, process
from avocado.utils.software_manager.manager import SoftwareManager


def fred_supported():
    """Check CPUID leaf 0x7, subleaf 0x1, EAX bit 17 for FRED support."""
    try:
        out = process.run("cpuid -l 0x7 -s 0x1 -r", ignore_status=True).stdout_text
        for line in out.splitlines():
            if "eax=" in line.lower():
                eax_val = int(line.lower().split("eax=")[1].split()[0], 16)
                return bool(eax_val & (1 << 17))
        return False
    except process.CmdError:
        return False


class FredFeatureTest(Test):
    """Validation test for AMD FRED feature enablement."""

    @skipIf(cpu.get_vendor() != "amd", "Requires AMD platform")
    def setUp(self):
        """Check CPU flags, kernel config, and cmdline param prerequisites."""
        try:
            smm = SoftwareManager()
            if not smm.check_installed("cpuid") and not smm.install("cpuid"):
                self.cancel("cpuid package not found and installing failed")

            if not fred_supported():
                self.cancel("FRED feature not supported on this platform")
            if not linux_modules.check_kernel_config("CONFIG_X86_FRED"):
                self.cancel('Required "CONFIG_X86_FRED" not set')
            if not dmesg.check_kernel_cmdline_param("fred=on"):
                self.cancel("Required Kernel cmdline param 'fred=on' not found")
            if not cpu.cpu_has_flags(["fred"]):
                self.cancel("Required CPU flag 'fred' is missing")
        except process.CmdError as err:
            self.cancel(f"Prerequisite check failed: {err}")
        except Exception as err:
            self.cancel(str(err))

    def test(self):
        """Validate Fred feature enablement on the system."""
        try:
            dmesg_logs = dmesg.collect_errors_dmesg(["Initialize FRED on CPU"])
            journalctl_logs = dmesg.collect_journalctl_logs("Initialize FRED on CPU")

            if not dmesg_logs and not journalctl_logs:
                self.fail("FRED is not initialised")

            cpu_count = cpu.online_count()
            if len(dmesg_logs) == cpu_count or len(journalctl_logs) == cpu_count:
                self.log.info("FRED initialized across all CPUs.")
            else:
                self.fail("FRED is not initialised on all CPUs of the system.")
        except process.CmdError as err:
            self.fail(f"Log collection failed: {err}")
        except Exception as err:
            self.fail(str(err))
