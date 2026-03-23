#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Advanced Micro Devices, Inc.
# @Author(s): Kalpana Shetty <Kalpana.Shetty@amd.com>
# Babu Moger <Babu.Moger@amd.com>
# @Module Name: sysfs-qos-rmid-pin-test.py
# @Description: Detect Assignable Memory Bandwidth Counter (AMBC) also known as RMID Pinning feature.
#               Check for number of assignable counters supported and how many assignable counters are available.
#               Test assign/unassign the counter associated with the mbm_total_bytes event on all domains.
#               Validate and test assign/unassign the counter associated with the mbm_total_bytes even for single domain.
# @History:  Created Feb 20 2026 - Created

import os
import avocado
from avocado import Test
from avocado.utils import genio, process
from lib.qos_common import *
from lib.qos_resctrllib import ResctrlSchemata

MBM_ASSIGN_MODE = "/sys/fs/resctrl/info/L3_MON/mbm_assign_mode"
MBM_ASSIGN_CNT = "/sys/fs/resctrl/info/L3_MON/num_mbm_cntrs"
MBM_AVAIL_CNT = "/sys/fs/resctrl/info/L3_MON/available_mbm_cntrs"
MBM_L3_ASSIGN = "/sys/fs/resctrl/mbm_L3_assignments"

class RMID(Test):
    @avocado.skipIf(not(os.path.exists("/sys/fs/resctrl")), 'Skipping test, No support for QOS')

    def setUp(self):
        self.log.info("Mount resctrl")
        if ResctrlSchemata().is_mounted():
            ResctrlSchemata().umount()
        if not ResctrlSchemata().mount():
            self.fail("Unable to mount resctrl")

    # Detect ABMC feature aka RMID Pinning support
    def test_rmid_support(self):
        # Check if ABMC is supported
        if not os.path.exists(MBM_ASSIGN_MODE):
            self.cancel("MBM assignment mode file not found, RMID Pinning (ABMC) not supported by the kernel")

        #Check for "mbm event"
        mbm_mode = genio.read_one_line(MBM_ASSIGN_MODE)
        self.log.info(f"MBM Mode {mbm_mode}")
        if "[mbm_event]" in mbm_mode:
            self.log.info(f"PASS: MBM event mode detected - {mbm_mode}, RMID Pinning (ABMC) supported")
        else:
            self.cancel("RMID Pinning (ABMC), MBM event is not enabled")

    # Test to check assignable counters supported
    def test_check_assign_cnters(self):
        # Check how many assignable counters are supported
        if not os.path.exists(MBM_ASSIGN_CNT):
            self.cancel("Assignable MBM counters file not found, check resctrl mounted")
        mbm_assign_cnters = genio.read_one_line(MBM_ASSIGN_CNT)
        if (mbm_assign_cnters):
            self.log.info("PASS: Assignable MBM counters = %s" % mbm_assign_cnters)
        else:
            self.fail(f"Unexpected content in {MBM_ASSIGN_CNT}")

    # Test to check available counters in each domain
    def test_check_avail_cnters(self):
        # Check how many assignable counters are available for assignment in each domain.
        if not os.path.exists(MBM_AVAIL_CNT):
            self.cancel("Available MBM counters file not found, check resctrl mounted")
        mbm_avail_cnters = genio.read_one_line(MBM_AVAIL_CNT)
        if (mbm_avail_cnters):
            self.log.info(f"PASS: Available MBM counters = {mbm_avail_cnters}")
        else:
            self.fail(f"Unexpected content in {MBM_AVAIL_CNT}")

    # Test assign/unassign mbm_total_bytes even on all domains in "e" mode
    def test_rmid_assign_event_all_domains(self):
        # Assign a counter associated with the mbm_total_bytes event on all domains in exclusive mode
        if not os.path.exists(MBM_L3_ASSIGN):
            self.cancel("MBM L3 Assignment file not found, check resctrl mounted")
        assignment_e = "mbm_total_bytes:*=e"
        exitcode, stdout, _ = CommonLib.Run(f"echo {assignment_e} > {MBM_L3_ASSIGN}")
        if (exitcode == 0):
            self.log.info("PASS: Able to write MBM event on all domains in exclusive mode")
        else:
            self.fail("Failed to write MBM event, check resctrl mounted")
        # Unassign a counter associated with the mbm_total_bytes event on all domains
        assignment_clr = "mbm_total_bytes:*=_"
        exitcode, stdout, _ = CommonLib.Run(f"echo {assignment_clr} > {MBM_L3_ASSIGN}")
        if (exitcode == 0):
            self.log.info("PASS: Able to unassign MBM event on all domains")
        else:
            self.fail("Failed to unassign / clear MBM event")

    def get_mbm_path(self, l3_id):
        num = int(f"{l3_id}")
        if num <= 9:
            mon_data = f"mon_L3_0{num}"
        else:
            mon_data = f"mon_L3_{num}"
        mbm_path = f"/sys/fs/resctrl/mon_data/{mon_data}"
        if not os.path.exists(mbm_path):
            self.fail(f"L3 monitoring data path does not exists - {mbm_path}")
        return mbm_path

    def single_assign_unassign_event(self, l3_id):
        # Assign a counter associated with the mbm_total_bytes event on single domains in exclusive mode
        if not os.path.exists(MBM_L3_ASSIGN):
            self.cancel("MBM L3 Assignment file not found, check resctrl mounted")
        assignment_e = f"mbm_total_bytes:{l3_id}=e"
        exitcode, stdout, _ = CommonLib.Run(f"echo {assignment_e} > {MBM_L3_ASSIGN}")
        if (exitcode == 0):
            self.log.info("PASS: Able to write MBM event on a single domain in exclusive mode")
        else:
            self.fail("Failed to write MBM event, check resctl mounted")

        # Validate the mon_total_bytes
        mbm_path = self.get_mbm_path(l3_id)
        self.log.info(f"mbm_path = {mbm_path}")
        exitcode, stdout, _ = CommonLib.Run(f"cat {mbm_path}/mbm_total_bytes")
        if (exitcode == 0):
            mbm_total_bytes = int(stdout)
            if isinstance(mbm_total_bytes, int):
                self.log.info(f"PASS: Able to read mbm_total_bytes = {mbm_total_bytes}")
            else:
                self.fail(f"The mbm_total_bytes is not an integer value {mbm_total_bytes}")
        else:
            self.fail(f"Failed to read mbm_total_bytes {exitcode}")

        # Unassign a counter associated with the mbm_total_bytes event on a single domain
        assignment_clr = f"mbm_total_bytes:{l3_id}=_"
        exitcode, stdout, _ = CommonLib.Run(f"echo {assignment_clr} > {MBM_L3_ASSIGN}")
        if (exitcode == 0):
            self.log.info("PASS: Able to unassign MBM event on a single domain")
        else:
            self.fail("Failed to unassign / clear MBM event")

        # Validate the mon_total_bytes, it should be "Unassigned" value
        mbm_path = self.get_mbm_path(l3_id)
        exitcode, stdout, _ = CommonLib.Run(f"cat {mbm_path}/mbm_total_bytes")
        if (exitcode ==0):
            mbm_total_bytes = stdout.splitlines()
            if f"{mbm_total_bytes}" == f"['Unassigned']":
                self.log.info(f"PASS: Able to read mbm_total_bytes = {mbm_total_bytes}")
            else:
                self.fail(f"The mbm_total_bytes value is not 'Unassigned': {mbm_total_bytes}")
        else:
            self.fail(f"Failed to read mbm_total_bytes {mbm_total_bytes}")

    # Validate and test assign/unassign the counter associated with the mbm_total_bytes event for single domain
    def test_rmid_assign_unassign_event(self):
        # Get cache/index3(L3) id
        cmd = "ls /sys/devices/system/cpu/cpu*/cache/index3/id | xargs -I{} sh -c 'cat {}' | sort -n | uniq"
        exitcode, stdout, _ = CommonLib.Run(cmd)
        if (exitcode == 0):
            self.log.info("PASS: Able to read L3 cache id")
            for l3_id in stdout.splitlines():
                self.log.info(f"{l3_id}")
                self.single_assign_unassign_event(l3_id)
        else:
            self.fail("Failed to read L3 id")

    def tearDown(self):
        self.log.info("Umount resctrl")
        if ResctrlSchemata().is_mounted():
            ResctrlSchemata().umount()
