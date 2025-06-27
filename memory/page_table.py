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
# Copyright: 2022 AMD
# Author: Kalpana Shetty <kalpana.shetty@amd.com>
# File: page_table.py
# Description: Check for 5-level page table support and run page table tests.

import os
import subprocess
from subprocess import Popen, PIPE
from avocado import Test
from avocado import skipUnless
from avocado.utils import cpu, git, genio, build, process, linux_modules, distro, archive
from avocado.utils.software_manager.manager import SoftwareManager

LA57_CPUID = "0x00000007 0x00"

class PageTable(Test):
    """
    Tests 5-level, 4-level page table depending on the supported platform.
    Test case covers:
        * CPUID test,
        * Kernel level test and
        * Functionality tests runs on both 5-level or 4-level page table tests
          depending on 4-level or 5-level configured on the system.
          Basically, it run series of page table tests from "pg-table_tests.git" that covers
            - heap, mmap, shmat tests.
    Page table test url - https://github.com/sanskriti-s/pg-table_tests.git
    :avocado: tags=memory
    """

    def get_cpuid_tool(self):
        '''
        Install latest cpuid from source
        '''
        # Install the latest version of cpuid which has bug fixes
        self.log.info("Installing cpuid from source")
        self.url_cpuid_tool = self.params.get('url_cpuid_tool',
                default="https://etallen.com/cpuid/cpuid-20250419.src.tar.gz")
        tarball = self.fetch_asset(self.url_cpuid_tool)
        archive.extract(tarball, self.teststmpdir)
        cpuid_version = os.path.basename(tarball.split('.src.')[0])
        sourcedir = os.path.join(self.teststmpdir, cpuid_version)
        build.make(sourcedir, extra_args='install')

    @skipUnless('x86_64' in cpu.get_arch(),
                "This test runs on x86-64 platform.\
        If 5-level page table supported on other arch then\
        this condition can be removed")
    def setUp(self):
        '''
        Install pre-requisites packages
        Setup pg-table_tests.git
        '''
        smm = SoftwareManager()
        for package in ['gcc', 'make']:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel('%s is needed for the test to be run' % package)

        self.url_pg_table = self.params.get('url_pg_table',
                default="https://github.com/sanskriti-s/pg-table_tests.git")
        git.get_repo(self.url_pg_table, destination_dir=self.teststmpdir)
        os.chdir(self.teststmpdir)
        build.make(self.teststmpdir)

    def test_CPUID(self):
        self.log.info(" -- Check 5-level CPUID feature --")
        '''
        Feature availability check using cpuid
        '''
        self.get_cpuid_tool()

        cmd = "cpuid -1 -r"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = proc.communicate()
        cpuidDatahex = stdout.split('\n')

        for line in cpuidDatahex:
            # Check 5-level page table feature in CPUID(EAX=07H, ECX=00H):ECX.[bit 16]
            if LA57_CPUID in line:
                regs = line.split(" ")
                la57 = int(regs[6][6:14], 16)

                if (la57 & 0x10000):
                    self.log.info(
                            "PASS: CPUID check pass: 5-level page table feature supported on the system")
                else:
                    self.cancel(
                            "CPUID check fail: 5-level page table feature Unsupported on the system")

    def test_detect_5lvl(self):
        '''
        Detect 5-Level page table feature availability from /proc/cpuinfo
        '''
        cpu_info = genio.read_file("/proc/cpuinfo")
        if 'la57' in cpu_info:
            self.log.info("PASS: Detected 5-Level page table cpu support")
        else:
            self.cancel("5-Level page table is not supported on the CPU")

    def test_pg_table_tests(self):
        '''
        Run series of page tests(4 or 5 level) from "pg-table_tests.git" that covers functionality tests
                - heap, mmap, shmat tests.
        '''
        self.log.info("-- Testing the page table functionality tests --")

        output = process.run('./run-tests')
        err_msg = []
        for line in output.stdout.decode('utf-8').splitlines():
            if "failed" in line:
                err_msg.append(line)
        if err_msg:
            self.fail("Page Table Functionality tests failed: %s" % err_msg)
        else:
            self.log.info("PASS: Page Table Functionality tests passed")
