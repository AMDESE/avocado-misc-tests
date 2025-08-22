#!/usr/bin/env python
#
# Copyright: 2025 AMD
# Author(s): Manali Shukla <Manali.Shukla@amd.com>
#            Kalpana Shetty <Kalpana.Shetty@amd.com>
# File: tlbi_test.py
# Description: TLBi is the short name for "TLB broadcast invalidation" feature introduced in AMD processors.
#              This feature is detected by CPUID_80000008_EBX[3].

import os
import subprocess
from subprocess import Popen, PIPE
from avocado import Test
from avocado import skipUnless
from avocado.utils import cpu, build, linux_modules
from avocado.utils import archive
from avocado.utils.software_manager.manager import SoftwareManager

TLBI_CPUID = "0x80000008 0x00"

class TLBi(Test):
    '''
    The TLBi test detects feature support by checking CPUID_80000008_EBX[3].
    The test will fail if TLBi is not detected on the system. If the feature is detected, the test will
    additionally validate whether the kernel is built with CONFIG_BROADCAST_TLB_FLUSH to confirm TLBi is
    enabled in the kernel.
    '''
    def cpuid_tool_build(self):
        '''
        Build/Install cpuid from source tarball
        '''
        self.url_cpuid_tool = self.params.get('url_cpuid_tool',
                default="https://etallen.com/cpuid/cpuid-20250419.src.tar.gz")
        tarball = self.fetch_asset(self.url_cpuid_tool)
        archive.extract(tarball, self.teststmpdir)
        self.sourcedir = os.path.join(
                self.teststmpdir, os.path.basename(tarball.split('.src.tar.')[0]))
        if build.make(self.sourcedir, extra_args='install', ignore_status=True):
            self.fail("Build failed, please check the debug log for more information.")

    def kernel_config_check(self):
        '''
        Check for kernel config - CONFIG_BROADCAST_TLB_FLUSH
        '''
        self.log.info("Check kernel config - CONFIG_BROADCAST_TLB_FLUSH")
        if linux_modules.check_kernel_config("CONFIG_BROADCAST_TLB_FLUSH")\
                == linux_modules.ModuleConfig.NOT_SET:
            self.cancel("Config CONFIG_BROADCAST_TLB_FLUSH is not set")
        else:
            self.log.info("PASS: Config CONFIG_BROADCAST_TLB_FLUSH is enabled, so TLBI is enabled")

    @skipUnless('x86_64' in cpu.get_arch() and 'amd' in cpu.get_vendor(),
                "This test runs on x86-64/amd platform.")
    def setUp(self):
        '''
        Install pre-requisites packages.
        '''
        smm = SoftwareManager()
        for package in ['gcc', 'make']:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel('%s is needed for the test to be run' % package)

    def test_CPUID(self):
        '''
        TLBi feature availability check using cpuid
        '''
        self.cpuid_tool_build()
        self.log.info("Check TLBi CPUID feature")

        # CPUID: CPUID_80000008_EBX[3], i.e bit 3 is set
        cmd = "cpuid -1 -r -l 0x80000008"
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = proc.communicate()
        if (stderr):
            self.fail("cpuid command failed %s" % stderr)
        else:
            cpuidDatahex = stdout.split('\n')
            for line in cpuidDatahex:
                if TLBI_CPUID in line:
                    regs = line.split(" ")
                    # Check Tlbi CPUID feature, EBX[3]
                    tlbi = int(regs[6][6:14], 16)
                    # Check the bit 3
                    if (tlbi & 0x8):
                        self.log.info(
                            "PASS: TLBi feature supported on the system")
                    else:
                        self.cancel(
                            "TLBi feature unsupported on the system")
            # System is detected with TLBi support, check for kernel config.
            self.kernel_config_check()
