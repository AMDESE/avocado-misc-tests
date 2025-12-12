#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# @Author(s): Kalpana Shetty <Kalpana.Shetty@amd.com>
# Babu Moger <Babu.Moger@amd.com>
# @Module Name: sysfs-qos-mbm-test.py
# @Description: Check for Resctrl support and L3 cache allocation detection.
# @History:  Created Jan 10 2025 - Created

import re
import time
import subprocess
import platform
import os.path
import avocado
from avocado import Test
from lib.qos_common import *
from lib.qos_resctrllib import ResctrlSchemata

RESCTRL_PATH = "/sys/fs/resctrl"
testDir = os.path.join(RESCTRL_PATH, "test1")

class Resctrl(Test):
    ## PQOS - Resctrl supported on the platform
    #
    #  Objective:
    #  Verify if resctrl is detected on platform
    #
    #  Instruction:
    #  Run "dmesg |grep -i resctrl" and check in /boot/config-`uname -r` file for resctrl
    #
    #  Result:
    #  Observe "CONFIG_X86_CPU_RESCTRL" in output
    @avocado.skipIf(not(os.path.exists("/sys/fs/resctrl")), 'Skipping test, No support for QOS')
    def test_pqos_resctrl_detection(self):
        ResctrlSchemata().resctrl_detection()

    ## PQOS - Mount the resctrl FS
    #
    #  Objective:
    #  Check if we can mount the resctrl FS
    def test_pqos_resctrl_mount(self):
        self.log.info("Mount resctrl")
        ResctrlSchemata().umount()
        if not ResctrlSchemata().mount():
            return False

        self.log.info("Create COS directory")
        if not os.path.exists(testDir):
            os.makedirs(testDir)
        self.log.info("Directory %s created", testDir)

    ## PQOS - Allocate 0-3 CPU's to cpu_list
    # and Assign the required bandwidth to core complex 0 directly
    #Because each unit is 1/8 GBps, the value of 64 allocates 8GBs to core complex 0
    def test_pqos_resctrl_allocate(self):
        time.sleep(5)
        self.log.info("Assign CPU list and half cache to core complex 0")
        (exitstatus, stdout, _) = CommonLib.Run(["echo '0-3' > {0}/cpus_list".format(testDir)])
        assert exitstatus == 0
        (exitstatus, stdout, _) = CommonLib.Run(["echo 'MB:0=64' > {0}/schemata".format(testDir)])
        assert exitstatus == 0
        self.log.info("Settings done as below")
        (_, stdout, _) = CommonLib.Run(["cat {0}/cpus_list".format(testDir)])
        self.log.info("CPU list:" + stdout)
        (_, stdout, _) = CommonLib.Run(["cat {0}/schemata".format(testDir)])
        self.log.info("Schemata:" + stdout)

    ## PQOS - L3 CAT verify allocation using memtester
    #
    #  Objective:
    #  Execute memtester for a while and verify CAT allocation
    #
    #  Instruction:
    #  1. Run the "taskset -c 0 100M > /dev/tmp &" to run memtester
    #  2. Monitor the cache occupancy
    #  Result:
    #  Observe in output file
    #    - MBM should be 8GB
    def test_pqos_mbm_monitor(self):
        log_file = os.path.join(self.outputdir,"sysfs-qos-mbm.log")
        logging.info("Execute memtester")
        run_memtest = subprocess.Popen("taskset -c 0 memtester 100M 5 > /dev/tmp", shell=True)

        while run_memtest.poll() is None:
            time.sleep(2)
            _, first_read, _ = CommonLib.Run("cat /sys/fs/resctrl/test1/mon_data/mon_L3_00/mbm_total_bytes")
            time.sleep(1)
            _, second_read, _ = CommonLib.Run("cat /sys/fs/resctrl/test1/mon_data/mon_L3_00/mbm_total_bytes")
            delta = int(second_read) - int(first_read)
            command = "echo 'scale=3; {0}/1024/1024' | bc -l".format(delta)
            _, total_mem, _ = CommonLib.Run(command)
            CommonLib.Run("echo 'Total memory bandwidth {0}MB/s' >> {1}".format(total_mem, log_file))
            time.sleep(0.5)

        logging.info("Memtester completed")
        logging.info("-" * 30)
        logging.info("Check for MBM logs in %s" %log_file)
        fpointer = open(log_file, "r")
        match = False
        for i in fpointer.readlines():
            line = re.findall(r'[7|8]\d{3}', i)
            if line:
                logging.info("Match found: %s", line)
                match = True
                break
            else:
                logging.error("Failed to get 8MB memory bandwidth")
        fpointer.close()
        if match == False:
            self.fail("Failed to get 8MB memory bandwidth, check the debug.log")
        logging.info("=" * 30)

    def test_pqos_reset(self):
        time.sleep(5)
        self.log.info("Umount resctrl")
        ResctrlSchemata().umount()
