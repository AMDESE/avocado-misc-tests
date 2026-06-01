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
# Copyright: 2016 IBM
# Author: Abdul Haleem <abdhalee@linux.vnet.ibm.com>

import os
import platform
import re
import glob
import shutil
import pathlib

from avocado import Test
from avocado.core.exceptions import TestCancel, TestFail
from avocado.utils import build, cpu, dmesg, memory, pci, process
from avocado.utils import distro, linux_modules
from avocado.utils import archive, git
from avocado.utils.software_manager.manager import SoftwareManager

IS_AMD = 'AuthenticAMD' in open('/proc/cpuinfo', 'r').read()

class kselftest(Test):
    """
    Linux Kernel Selftest available as a part of kernel source code.
    run the selftest available at tools/testing/selftest

    :see: https://www.kernel.org/doc/Documentation/kselftest.txt
    :source: https://github.com/torvalds/linux/archive/master.zip

    :avocado: tags=kernel
    """
    testdir = 'tools/testing/selftests'
    VFIO_ALLOW_UNSAFE_IRQ_PATHS = (
        ('/sys/module/iommufd/parameters/allow_unsafe_interrupts', 'iommufd',
         'iommufd vfio tests may fail'),
        ('/sys/module/vfio_iommu_type1/parameters/allow_unsafe_interrupts',
         'vfio_iommu_type1', 'vfio type1 tests may fail'),
    )

    def find_match(self, match_str, line, results_path=None):
        match = re.search(match_str, line)
        if match:
            if "SKIP" in line:
                self.error = "SKIP"
                if results_path:
                    output = process.run('grep "SKIP" %s' % results_path,
                                         ignore_status=True)
                    if output:
                        self.log.info("Testcase Skipped. Log from debug: %s, %s" %
                                      (match.group(0),
                                       output.stdout.decode("utf-8")))
                    else:
                        self.log.info("Testcase Skipped. Log from debug: %s" %
                                      match.group(0))
                else:
                    self.log.info("Testcase Skipped. Log from debug: %s" %
                                  match.group(0))
            else:
                self.error = True
                failed_test = match.group(0).strip()
                if failed_test not in self.failed_tests:
                    self.failed_tests.append(failed_test)
                self.log.info("Testcase failed. Log from debug: %s" % failed_test)

    def cpufreq_driver_match(self, driver):
        cpufreq_drv_file = f"/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"
        if os.path.exists(cpufreq_drv_file):
            cpufreq_drv = process.system_output(f"cat {cpufreq_drv_file}").decode('utf')
        else:
            self.cancel("sysfs cpufreq directory is not loaded")
        self.log.info("CPUFreq driver: %s" % cpufreq_drv)
        if cpufreq_drv != driver:
            self.cancel(f"kselftests cpufreq tests expected to run using\
                    the {driver} driver. Check if {driver} driver is configured on the system.")

    def setUp(self):
        """
        Resolve the packages dependencies and download the source.
        """
        smg = SoftwareManager()
        self.comp = self.params.get('comp', default='')
        self._iommu_hp_restore = None
        self.subtest = self.params.get('subtest', default='')
        self.subcomp_test = self.params.get('subcomp_test', default='')
        if self.comp == "mm" and self.subtest == "ksm_tests":
            self.test_type = self.params.get('test_type', default='-H')
            self.Size_flag = self.params.get('Size', default='-s')
            self.Dup_MM_Area = self.params.get('Dup_MM_Area', default='100')
        if self.comp == "cpufreq":
            if IS_AMD:
                self.cpufreq_driver_match('acpi-cpufreq')
            self.test_mode = self.params.get('test_mode', default='')
            self.testdir = 'tools/testing/selftests/cpufreq'
        if self.comp == "amd-pstate":
            if IS_AMD:
                self.cpufreq_driver_match('amd-pstate')
            if not linux_modules.module_is_loaded('amd-pstate-ut'):
                if not linux_modules.load_module('amd-pstate-ut'):
                    self.cancel("The system is not loaded with amd-pstate-ut module.\
                            Unable to load it. Try this test by loading amd-pstate-ut module")
            self.test_mode = self.params.get('test', default='')
            self.testdir = 'tools/testing/selftests/amd-pstate'
        if self.comp == "bpf":
            self.test_mode = self.params.get('test_mode', default='')
            self.testdir = 'tools/testing/selftests/bpf'

        self.build_option = self.params.get('build_option', default='-bp')
        self.run_type = self.params.get('type', default='upstream')
        self.detected_distro = distro.detect()
        if self.detected_distro.name == 'Ubuntu':
            self.distro_ver = int(self.detected_distro.version.split('.')[0])
        else:
            self.distro_ver = int(self.detected_distro.version)
        deps = ['gcc', 'make', 'automake', 'autoconf', 'rsync']
        if (self.comp == "powerpc"):
            if 'ppc' not in self.detected_distro.arch:
                self.cancel("Testing on a non powerpc platform")
        if self.detected_distro.name in ['Ubuntu', 'debian']:
            deps.extend(['libpopt0', 'libc6', 'libc6-dev', 'libcap-dev',
                         'libpopt-dev', 'libcap-ng0', 'libcap-ng-dev',
                         'libnuma-dev', 'libfuse-dev', 'elfutils', 'libelf-dev',
                         'libhugetlbfs-dev'])
        elif 'SuSE' in self.detected_distro.name:
            deps.extend(['glibc', 'glibc-devel', 'popt-devel', 'sudo',
                         'libcap2', 'libcap-devel', 'libcap-ng-devel',
                         'fuse', 'fuse-devel', 'glibc-devel-static',
                         'traceroute', 'iproute2', 'socat', 'libnuma-devel',
                         'coreutils'])
            if self.distro_ver >= 15:
                deps.extend(['libhugetlbfs-devel'])
            else:
                deps.extend(['libhugetlbfs-libhugetlb-devel'])
            if self.distro_ver >= 16:
                deps.extend(['libclang13'])
            else:
                deps.extend(['clang7'])
        elif self.detected_distro.name in ['centos', 'fedora', 'rhel']:
            deps.extend(['popt', 'glibc', 'glibc-devel', 'glibc-static',
                         'libcap-ng', 'libcap', 'libcap-devel',
                         'libcap-ng-devel', 'popt-devel',
                         'libhugetlbfs-devel', 'clang', 'traceroute',
                         'iproute-tc', 'socat', 'numactl-devel'])
            if self.detected_distro.name == 'rhel' and self.distro_ver >= 9:
                packages_remove = ['libhugetlbfs-devel']
                deps = list(set(deps)-set(packages_remove))
                deps.extend(['fuse3-devel'])
            else:
                deps.extend(['fuse-devel'])

        for package in deps:
            if not smg.check_installed(package) and not smg.install(package):
                self.cancel(
                    "Fail to install %s package" % (package))

        if self.run_type == 'custom' or self.run_type == 'upstream':
            if self.run_type == 'custom':
                linux_dir = self.params.get('linux_dir', default=None)
                if not linux_dir or not os.path.exists(linux_dir):
                    self.cancel(
                        "Custom kernel source directory %s does not exist" % (linux_dir))
                linux_dir = os.path.abspath(os.path.expanduser(linux_dir))
                if not os.path.exists(os.path.join(linux_dir, "tools/testing/selftests")):
                    self.cancel(
                        "Custom kernel source directory %s is not a valid kernel source" % linux_dir)
                if not os.path.exists(os.path.join(linux_dir, "Makefile")):
                    self.cancel(
                        "Custom kernel source directory %s lacks a Makefile" % linux_dir)
                self.buldir = linux_dir
            if self.run_type == 'upstream':
                location = self.params.get('location', default='https://github.c'
                                           'om/torvalds/linux/archive/master.zip')
                if re.match(r'^https|^git', location):
                    git_branch = self.params.get('branch', default='master')
                    path = ''
                    match = next(
                        (ext for ext in [".zip", ".tar", ".gz"] if ext in location), None)
                    if match:
                        tarball = self.fetch_asset("kselftest%s" % match,
                                                   locations=[location], expire='1d')
                        extracted_dir = archive.uncompress(
                            tarball, self.workdir)
                        path = glob.glob(os.path.join(
                            self.workdir, extracted_dir))
                    else:
                        git.get_repo(location, branch=git_branch,
                                     destination_dir=self.workdir)
                        path = glob.glob(self.workdir)
                    for l_dir in path:
                        if os.path.isdir(l_dir) and 'Makefile' in os.listdir(l_dir):
                            self.buldir = os.path.join(self.workdir, l_dir)
                            break
            self.sourcedir = os.path.join(self.buldir, self.testdir)
            if (self.comp != "cpufreq" and self.comp != "bpf" and self.comp != "amd-pstate"):
                self.sourcedir_comp = os.path.join(self.buldir, self.testdir, self.comp)
                if os.chdir(self.sourcedir_comp) is None:
                    if self.subcomp_test:
                        test_name = self.subcomp_test.split(":")[1]
                        for name in pathlib.Path(self.sourcedir_comp).rglob("%s*" % test_name):
                            self.log.info("Test case exists.")
                            break
                else:
                    self.cancel("Test component does not exists.")
                process.system("make headers -C %s" % self.buldir, shell=True,
                               sudo=True)
                process.system("make install -C %s" % self.sourcedir,
                               shell=True, sudo=True)
        else:
            # Make sure kernel source repo is configured
            if self.detected_distro.name in ['centos', 'fedora', 'rhel']:
                src_name = 'kernel'
                if self.detected_distro.name == 'rhel':
                    # Check for "el*a" where ALT always ends with 'a'
                    if platform.uname()[2].split(".")[-2].endswith('a'):
                        self.log.info('Using ALT as kernel source')
                        src_name = 'kernel-alt'
                self.buldir = smg.get_source(
                    src_name, self.workdir, self.build_option)
                self.buldir = os.path.join(
                    self.buldir, os.listdir(self.buldir)[0])
            elif self.detected_distro.name in ['Ubuntu', 'debian']:
                self.buldir = smg.get_source('linux', self.workdir)
            elif 'SuSE' in self.detected_distro.name:
                if not smg.check_installed("kernel-source") and not\
                        smg.install("kernel-source"):
                    self.cancel(
                        "Failed to install kernel-source for this test.")
                if not os.path.exists("/usr/src/linux"):
                    self.cancel("kernel source missing after install")
                self.buldir = "/usr/src/linux"

        self.sourcedir = os.path.join(self.buldir, self.testdir)
        if self.subtest == 'pmu/event_code_tests':
            pmu_test_dir = os.path.join(
                self.sourcedir, 'powerpc/pmu/event_code_tests')
            if not os.path.exists(pmu_test_dir):
                self.cancel("selftest not supported on distro")
        # cmsg_* tests from net/ subdirectory takes a lot of time to complete.
        # Until they have been root caused skip them.
        if self.comp == 'net':
            make_path = self.sourcedir + "/net/Makefile"
            process.system("sed -i 's/^.*cmsg_so_mark.sh/#&/g' %s" % make_path,
                           shell=True, sudo=True)
            process.system("sed -i 's/^.*cmsg_time.sh/#&/g' %s" % make_path,
                           shell=True, sudo=True)
        if (self.comp != "cpufreq" and self.comp != "bpf" and self.comp != "amd-pstate"):
            process.system("make headers -C %s" % self.buldir, shell=True,
                           sudo=True)
            if self.comp:
                build_str = '-C %s' % self.comp
            if build.make(self.sourcedir, extra_args='%s' % build_str):
                self.fail("Compilation failed, Please check the build logs !!")

    def test(self):
        """
        Execute the kernel selftest
        """
        self.error = False
        self.failed_tests = []
        kself_args = self.params.get("kself_args", default='')
        if self.comp == "bpf":
            self.bpf()
        if self.comp == "cpufreq":
            self.cpufreq()
        if self.comp == "amd-pstate":
            self.amd_pstate()
        if self.comp == "iommu":
            self.iommu()
        elif self.comp == "vfio":
            self.vfio()
        else:
            if self.subtest == "ksm_tests":
                self.ksmtest()
            else:
                if self.subtest:
                    test_comp = self.comp + "/" + self.subtest
                else:
                    test_comp = self.comp
                if self.subcomp_test:
                    self.subcomp_single_test()
                else:
                    make_cmd = 'make -C %s %s -C %s run_tests' % (
                        self.sourcedir, kself_args, test_comp)
                    self.result = process.run(
                        make_cmd, shell=True, ignore_status=True)
        log_output = self.result.stdout.decode('utf-8')
        results_path = os.path.join(self.outputdir, 'raw_output')
        with open(results_path, 'w') as r_file:
            r_file.write(log_output)
        for line in open(results_path).readlines():
            if self.run_type == 'upstream' or self.run_type == 'custom':
                if self.subcomp_test:
                    self.find_match(r'selftests:(.*) # SKIP', line, results_path)
                self.find_match(r'not ok (.*) selftests:(.*)', line, results_path)
                self.find_match(r'# not ok \d+ .* # exit=\d+', line, results_path)
            elif self.run_type == 'distro':
                if self.detected_distro.name == 'SuSE' and\
                        self.distro_ver == 12:
                    self.find_match(r'selftests:(.*)\[FAIL\]', line, results_path)
                else:
                    self.find_match(r'not ok (.*) selftests:(.*)', line, results_path)
                    self.find_match(r'# not ok \d+ .* # exit=\d+', line, results_path)

        if self.error:
            if self.error == "SKIP":
                self.cancel("Test case canceled. Refer to the log messages for the reason.")
            summary_lines = [
                "",
                "="*70,
                "FAILED SELFTESTS SUMMARY:",
                "="*70
            ]
            for idx, failed_test in enumerate(self.failed_tests, 1):
                summary_lines.append(f"{idx}. {failed_test}")
            summary_lines.extend([
                "="*70,
                f"Total failed tests: {len(self.failed_tests)}",
                "="*70,
                ""
            ])
            summary_msg = "\n".join(summary_lines)
            self.log.error(summary_msg)
            self.fail(f"Testcase failed during selftests. Total failed tests: {len(self.failed_tests)}")

    def run_cmd(self, cmd):
        """
        Run the command:
        Ex: ./ksm_tests -M
        """
        try:
            self.result = process.run(cmd, ignore_status=False, sudo=True)
            self.log.info(self.result)
        except process.CmdError as details:
            self.fail("Command %s failed: %s" % (cmd, details))

    def ksmtest(self):
        """
        Run the different ksm test types:
        Ex: -M (page merging)
        """
        ksm_test_dir = self.sourcedir + "/mm"
        ksm_test_bin = ksm_test_dir+"/ksm_tests"
        self.test_list = ["-M", "-Z", "-N", "-U", "-C"]
        if os.path.exists(ksm_test_bin):
            os.chdir(ksm_test_dir)
            if (self.test_type in ["-H", "-P"]):
                arg_payload = " ".join(["./ksm_tests", self.test_type,
                                       self.Size_flag, self.Dup_MM_Area])
                self.run_cmd(arg_payload)
            elif (self.test_type in self.test_list):
                arg_payload = " ".join(["./ksm_tests", self.test_type])
                self.run_cmd(arg_payload)
            else:
                self.cancel("Invalid test_type for ksm_tests:- {}"
                            .format(self.test_type))
        else:
            self.cancel("Invalid ksm_tests build path:- {}"
                        .format(ksm_test_dir))

    def bpf(self):
        """
        Execute the kernel bpf selftests
        """
        self.sourcedir = os.path.join(self.buldir, self.testdir)
        os.chdir(self.sourcedir)
        build.make(self.sourcedir)
        build.make(self.sourcedir, extra_args='run_tests')

    def cpufreq(self):
        """
        Execute the kernel cpufreq selftests
        """
        os.chdir(self.sourcedir)
        cmd = "./main.sh -t " + self.test_mode
        self.run_cmd(cmd)

    def amd_pstate(self):
        """
        Execute the kernel amd-pstate selftests
        """
        os.chdir(self.sourcedir)
        cmd = "./run.sh -c " + self.test_mode
        self.run_cmd(cmd)

    def subcomp_single_test(self):
        """
        Execute individual sub-component level tests
        """
        subcomp_dir = os.path.join(
            self.sourcedir, 'kselftest_install')
        os.chdir(subcomp_dir)
        test_run = "./run_kselftest.sh -t " + self.subcomp_test
        self.run_cmd(test_run)

    def iommu(self):
        """
        Execute the kernel iommufd selftests.
        """
        try:
            if IS_AMD:
                if not dmesg.check_kernel_logs("AMD-Vi"):
                    self.cancel("IOMMU is disabled.")

            if not linux_modules.configure_module("iommufd", "CONFIG_IOMMUFD"):
                self.cancel("iommufd module cannot be configured (CONFIG_IOMMUFD)")

            for config in ("CONFIG_IOMMUFD_TEST", "CONFIG_VFIO_DEVICE_CDEV"):
                if linux_modules.check_kernel_config(config) == \
                        linux_modules.ModuleConfig.NOT_SET:
                    self.cancel("%s is not enabled in the running kernel" % config)

            if IS_AMD:
                if linux_modules.check_kernel_config("CONFIG_AMD_IOMMU_IOMMUFD") == \
                        linux_modules.ModuleConfig.NOT_SET:
                    self.cancel("CONFIG_AMD_IOMMU_IOMMUFD is not enabled "
                                "in the running kernel")

            if not os.path.exists('/dev/iommu'):
                self.cancel("/dev/iommu not available after CONFIG_IOMMUFD setup")

            iommu_dir = os.path.join(self.sourcedir, 'iommu')
            if not os.path.isdir(iommu_dir):
                self.cancel("iommu selftest directory not found at %s" % iommu_dir)

            nr_hugepages = int(self.params.get('nr_hugepages', default=512))
            hp_path = '/sys/kernel/mm/hugepages/hugepages-%skB/nr_hugepages' % (
                memory.get_huge_page_size())
            if os.path.isfile(hp_path):
                try:
                    with open(hp_path, 'r') as hp_file:
                        prev_nr = int(hp_file.read().strip())
                except (OSError, ValueError) as err:
                    self.log.warn('Could not read prior nr_hugepages from %s: %s',
                                  hp_path, err)
                    prev_nr = None
                process.run('echo %d > %s' % (nr_hugepages, hp_path),
                            shell=True, sudo=True)
                if prev_nr is not None:
                    self._iommu_hp_restore = (hp_path, prev_nr)
                self.log.info('Reserved %d hugepages via %s', nr_hugepages, hp_path)
            else:
                self.log.warn('%s not found; hugetlb iommufd tests may fail',
                              hp_path)

            os.chdir(self.sourcedir)
            kself_args = self.params.get("kself_args", default='')
            if self.subtest == 'all':
                cmd = 'make %s -C iommu run_tests' % kself_args
                self.result = process.run(cmd, shell=True, ignore_status=True,
                                          sudo=True)
            else:
                test = self.subtest or 'iommufd'
                test_bin = os.path.join(iommu_dir, test)
                if not os.path.isfile(test_bin):
                    self.fail("%s binary not found - build may have failed" % test)
                os.chdir(iommu_dir)
                self.result = process.run('./%s' % test, shell=True,
                                          ignore_status=True, sudo=True)
                if self.result.exit_status != 0:
                    self.fail("./%s failed (exit %d)" % (test,
                                                         self.result.exit_status))
        except (TestCancel, TestFail):
            raise
        except Exception:
            self.cancel("Failed to setup and run iommufd kselftests")

    def _vfio_allow_unsafe_interrupts(self, val):
        for path, modname, warn_hint in self.VFIO_ALLOW_UNSAFE_IRQ_PATHS:
            if os.path.isfile(path):
                if val == 'Y':
                    process.run('echo Y > %s' % path, shell=True, sudo=True)
                    self.log.info('Interrupt remapping disabled; set '
                                  'allow_unsafe_interrupts=Y (%s)', modname)
                else:
                    res = process.run('echo N > %s' % path, shell=True,
                                      sudo=True, ignore_status=True)
                    if res.exit_status != 0:
                        self.log.warn('Could not set allow_unsafe_interrupts=N '
                                      'at %s', path)
                    else:
                        self.log.info('Set allow_unsafe_interrupts=N at %s',
                                      path)
            elif val == 'Y':
                self.log.warn('%s not found; %s', path, warn_hint)

    def vfio(self):
        """
        Execute the kernel vfio selftests.

        Requires a PCI device bound to vfio-pci via the upstream setup script.
        """
        try:
            if IS_AMD:
                if not dmesg.check_kernel_logs("AMD-Vi"):
                    self.cancel("IOMMU is disabled.")

            if platform.machine() not in ('x86_64', 'aarch64', 'arm64'):
                self.cancel("vfio selftests are not supported on this platform")

            self.pci_device = self.params.get('pci_device', default=None)
            if not self.pci_device:
                self.cancel("pci_device input must be provided for vfio kselftest.")
            if self.pci_device not in pci.get_pci_addresses():
                self.cancel("Please provide valid pci device input.")

            for mod, config in (("vfio", "CONFIG_VFIO"),
                                ("vfio_pci", "CONFIG_VFIO_PCI"),
                                ("iommufd", "CONFIG_IOMMUFD")):
                if not linux_modules.configure_module(mod, config):
                    self.cancel("%s module cannot be configured (%s)" % (mod,
                                                                         config))

            if linux_modules.check_kernel_config("CONFIG_VFIO_DEVICE_CDEV") == \
                    linux_modules.ModuleConfig.NOT_SET:
                self.cancel("CONFIG_VFIO_DEVICE_CDEV is not enabled")

            if IS_AMD:
                if linux_modules.check_kernel_config("CONFIG_AMD_IOMMU_IOMMUFD") == \
                        linux_modules.ModuleConfig.NOT_SET:
                    self.cancel("CONFIG_AMD_IOMMU_IOMMUFD is not enabled")

            if not os.path.exists('/dev/iommu'):
                self.cancel("/dev/iommu not available after CONFIG_IOMMUFD setup")

            if not dmesg.check_kernel_logs("Interrupt remapping enabled"):
                self._vfio_allow_unsafe_interrupts('Y')
            else:
                self.log.info('Interrupt remapping enabled; '
                              'allow_unsafe_interrupts not needed')

            nr_hugepages = int(self.params.get('nr_hugepages', default=512))
            hp_path = '/sys/kernel/mm/hugepages/hugepages-%skB/nr_hugepages' % (
                memory.get_huge_page_size())
            if os.path.isfile(hp_path):
                try:
                    with open(hp_path, 'r') as hp_file:
                        prev_nr = int(hp_file.read().strip())
                except (OSError, ValueError) as err:
                    self.log.warn('Could not read prior nr_hugepages from %s: %s',
                                  hp_path, err)
                    prev_nr = None
                process.run('echo %d > %s' % (nr_hugepages, hp_path),
                            shell=True, sudo=True)
                if prev_nr is not None:
                    self._iommu_hp_restore = (hp_path, prev_nr)
                self.log.info('Reserved %d hugepages via %s', nr_hugepages, hp_path)
            else:
                self.log.warn('%s not found; hugetlb vfio tests may fail',
                              hp_path)

            setup = os.path.join(self.sourcedir, 'vfio/scripts/setup.sh')
            if not os.path.isfile(setup):
                self.cancel("vfio setup script not found at %s" % setup)
            process.run('bash %s %s' % (setup, self.pci_device), shell=True,
                        sudo=True)

            vfio_dir = os.path.join(self.sourcedir, 'vfio')
            os.chdir(self.sourcedir)
            kself_args = self.params.get("kself_args", default='')
            if self.subtest == 'all':
                cmd = ("export VFIO_SELFTESTS_BDF='%s'; make %s -C vfio run_tests"
                       % (self.pci_device, kself_args))
                self.result = process.run(cmd, shell=True, ignore_status=True,
                                          sudo=True)
            else:
                test = self.subtest or 'vfio_iommufd_smoke_test'
                test_bin = os.path.join(vfio_dir, test)
                if not os.path.isfile(test_bin):
                    self.fail("%s binary not found - build may have failed" % test)
                os.chdir(vfio_dir)
                self.result = process.run('./%s %s' % (test, self.pci_device),
                                          shell=True, ignore_status=True,
                                          sudo=True)
                if self.result.exit_status != 0:
                    self.fail("./%s failed (exit %d)" % (test,
                                                         self.result.exit_status))
        except (TestCancel, TestFail):
            raise
        except Exception:
            self.cancel("Failed to setup and run vfio kselftests")

    def tearDown(self):
        if self._iommu_hp_restore:
            hp_path, prev_nr = self._iommu_hp_restore
            res = process.run('echo %d > %s' % (prev_nr, hp_path),
                              shell=True, sudo=True, ignore_status=True)
            if res.exit_status != 0:
                self.log.warn('Could not restore nr_hugepages to %d at %s',
                              prev_nr, hp_path)
            else:
                self.log.info('Restored nr_hugepages to %d via %s',
                              prev_nr, hp_path)
            self._iommu_hp_restore = None
        if (self.comp == 'vfio' and
                not dmesg.check_kernel_logs("Interrupt remapping enabled")):
            self._vfio_allow_unsafe_interrupts('N')
        self.log.info('Cleaning up')
        if self.comp == 'vfio' and getattr(self, 'pci_device', None):
            cleanup = os.path.join(self.sourcedir, 'vfio/scripts/cleanup.sh')
            if os.path.isfile(cleanup):
                process.run('bash %s %s' % (cleanup, self.pci_device),
                            shell=True, sudo=True, ignore_status=True)
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
