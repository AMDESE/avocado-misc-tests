#!/usr/bin/env python
#
# Copyright: 2025 AMD
# Author: Narasimhan V <narasimhan.v@amd.com>

import os
import shutil
import re

from avocado import Test
from avocado.utils import build, process, download, distro, genio
from avocado.utils.software_manager.manager import SoftwareManager


class SRSOTest(Test):
    """
    1. SRSO Selftest available as a part of kernel source code.
    run the selftest available at tools/testing/selftest/x86/srso.c

    2. check the sysfs for vulnerability status.

    :see: https://docs.kernel.org/admin-guide/hw-vuln/srso.html

    :avocado: tags=kernel
    """

    def setUp(self):
        """
        Setting the environment for the tests.
        """
        if 'selftest' in str(self.name):
            self.build_selftest()

    def build_selftest(self):
        """
        Resolve the packages dependencies and build the selftest.
        """
        smg = SoftwareManager()
        url = 'https://raw.githubusercontent.com/torvalds/linux/refs/' \
            'heads/master/tools/testing/selftests/x86/srso.c'
        self.url = self.params.get('url', default=url)

        self.detected_distro = distro.detect()
        if self.detected_distro.name == 'Ubuntu':
            self.distro_ver = int(self.detected_distro.version.split('.')[0])
        else:
            self.distro_ver = int(self.detected_distro.version)
        deps = ['gcc', 'make', 'automake', 'autoconf', 'rsync']

        for package in deps:
            if not smg.check_installed(package) and not smg.install(package):
                self.cancel("Fail to install %s package" % package)

        self.testfile = os.path.join(self.workdir, "srso.c")
        try:
            download.url_download(self.url, self.testfile)
        except:
            self.cancel('Downloading the selftest file failed')
        if build.make(self.workdir, extra_args='srso'):
            self.cancel('Building the selftest failed')

    def get_cmdline_dict(self):
        """
        Prepare a dictionary of kernel commandline parameters.
        """
        filename = '/proc/cmdline'
        cmdline = ""
        try:
            cmdline = genio.read_file(filename)
        except Exception as err:
            self.fail("%s file access failed. %s" % (filename, err))
        return dict(arg.split('=', 1) if '=' in arg else (arg, True)
                for arg in cmdline.split())

    def test_sysfs(self):
        """
        Check the vulnerability status from sysfs.
        """
        filename = '/sys/devices/system/cpu/vulnerabilities/spec_rstack_overflow'
        content = ""
        try:
            content = genio.read_file(filename)
        except Exception as err:
            self.fail("%s file access failed. %s" % (filename, err))

        # Since the vulnerability status depends on the kernel command line parameters,
        # we inform that as well to the user.
        cmdline_dict = self.get_cmdline_dict()
        parameter = "spec_rstack_overflow"
        message = ""
        if parameter in cmdline_dict:
            message = ", Kernel booted with %s=%s" % (parameter, cmdline_dict[parameter])

        if 'Vulnerable' in content:
            if 'Safe RET' in content:
                self.log.warn('Safe RET mitigation has been applied %s', message)
            elif 'Microcode' in content:
                self.log.warn('Microcode addressing mitigation has been applied %s', message)
            else:
                self.fail('Processor is vulnerable, and no mitigation applied %s' % message)

        # The vulnerability is mitigated via software microcode, but processor
        # is still vulnerable. So, we warn the user.
        elif 'Mitigation' in content:
            self.log.warn('Microcode addressing the mitigation has been applied %s', message)

    def test_srso_selftest(self):
        """
        Execute the SRSO selftest
        """
        os.chdir(self.workdir)
        result = process.run('./srso', shell=True, ignore_status=True)
        log_output = result.stdout.decode('utf-8')
        results_path = os.path.join(self.outputdir, 'raw_output')
        with open(results_path, 'w') as r_file:
            r_file.write(log_output)
        for line in open(results_path).readlines():
            if not line.startswith('RET'):
                continue
            match = re.search(r"\((\d+) retired <-> (\d+) mispredicted\)",
                              line)
            if match:
                retired_count = int(match.group(1))
                mispredicted_count = int(match.group(2))
                # The mispredicted and retired RETs should be almost equal if
                # mitigation works. Safe value for the difference is considered
                # to be 95%
                if int(mispredicted_count * 100 / retired_count) <= 95:
                    self.fail("Retired: %s, Mispredicted: %s."
                              "The mitigation does not work correctly."
                              % (retired_count, mispredicted_count))
            else:
                self.fail("The selftest run failed. Please check debug log")

    def tearDown(self):
        self.log.info('Cleaning up')
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
