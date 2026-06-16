#!/usr/bin/env python
#
# Copyright: 2025 AMD
# @Author(s): Benjamin Cheatham <Benjamin.Cheatham@amd.com>
#             Kalpana Shetty <Kalpana.Shetty@amd.com>
# File: cxl_test.py
# Description:
#              The CXL test suite includes platform device tests where CXL devices are emulated,
#              and these emulated device tests are executed using the ndctl utility. The test
#              suite depends on the kernel CXL selftest modules (located under tools/testing/cxl
#              in the kernel source) being built and set up to enable running the emulated CXL tests.
#
#              The second set of tests includes running tests on a physical CXL 2.0/3.0 card on the system.
import os
import shutil
import configparser
from avocado import Test
from avocado import skipUnless
from avocado.utils import cpu, git, genio, process, distro, linux_modules
from avocado.utils.software_manager.manager import SoftwareManager

class cxl_test(Test):
    @skipUnless('x86_64' in cpu.get_arch(),
                "This test runs on x86-64 platform.")

    def run_cmd(self, cmd):
        os.chdir(self.teststmpdir)
        run_cmd = os.path.join("./" + cmd + ".py")
        os.chmod(run_cmd, 0o755)
        output = process.system_output(run_cmd, shell=True, ignore_status=True,
                                            sudo=True).decode("utf-8")
        for line in output.splitlines():
            if 'FAIL:' in line:
                err = line.split('FAIL:')[-1]
                self.fail("%s, check the debug log" % err)
                break
            elif 'CANCEL:' in line:
                err = line.split('CANCEL:')[-1]
                self.cancel("%s, check the debug log" % err)
                break
            else:
                self.log.info("Test case pass: %s" % line)

    def setUp(self):
        '''
        Install pre-requisites packages.
        '''
        self.pwd = os.getcwd()
        self.dist = distro.detect()
        if self.dist.name not in ['Ubuntu', 'debian', 'anolis', 'openEuler']:
            self.cancel('Unsupported OS %s' % self.dist.name)

        smm = SoftwareManager()
        for package in ['gcc', 'make', 'meson-1.5', 'cmake', 'libkmod-dev', 'cargo',
                        'libudev-dev', 'libjson-c-dev', 'libtracefs-dev', 'asciidoctor',
                        'keyutils', 'libkeyutils-dev', 'libiniparser-dev', 'libtraceevent-dev',
                        'daxctl', 'libdaxctl-dev']:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel('%s is needed for the ndctl cxl test to be run' % package)
        cargo_pkg_cmd = "cargo install uefisettings"
        process.system(cargo_pkg_cmd, shell=True, sudo=True, ignore_status=True)
        self.bin_path = "PATH=$PATH:/root/.cargo/bin"
        export_path_cmd = "export %s" % self.bin_path
        process.system(export_path_cmd, shell=True, sudo=True, ignore_status=True)

        self.url_ndctl = self.params.get('url_ndctl',
                default="https://github.com/pmem/ndctl")
        git.get_repo(self.url_ndctl, branch='main', destination_dir=self.workdir)
        for file_name in ['cxl-numa.py', 'daxctl.py', 'driver-basic.py', 'uefi.py', 'online-offline.py']:
            shutil.copyfile(self.get_data(file_name),
                        os.path.join(self.teststmpdir, file_name))
        self.config_parameters = []

    def _check_kernel_config(self, config_parameter):
        ret = linux_modules.check_kernel_config(config_parameter)
        if ret == linux_modules.ModuleConfig.NOT_SET:
            return 1

    def verify_CXL_config(self):
        '''
        Verify CXL kernel config
        '''
        config_file_path = self.get_data('cxl_kernel_config.cfg')
        config = configparser.ConfigParser()
        try:
            config.read(config_file_path)
        except configparser.Error as e:
            self.fail(f"Failed to parse config file: {e}")
        if config.has_section('CXL_Kernel_Cfg'):
            kernel_cfg_list = config.get('CXL_Kernel_Cfg', 'cfg_list').split(',')
            self.log.info("debug: CFG list = %s" % kernel_cfg_list)
            for cxl_config in kernel_cfg_list:
                if (self._check_kernel_config(cxl_config)):
                    self.cancel("CXL config parameters not enabled: %s" % cxl_config)
                else:
                    self.log.info("debug: CXL kernel config set %s" % cxl_config)

    def test_cxl_numa(self):
        '''
        Run cxl-numa
        '''
        self.run_cmd("cxl-numa")

    def test_daxctl(self):
        '''
        Run daxctl
        '''
        self.run_cmd("daxctl")

    def test_driver_basic(self):
        '''
        Run basic cxl driver tests
        '''
        self.run_cmd("driver-basic")

    def test_online_offline(self):
        '''
        Run online/offline tests
        '''
        self.run_cmd("online-offline")

    def test_ndctl_cxl(self):
        '''
        Run ndctl cxl tests
        '''
        # Verify cxl kernel configs are set
        self.verify_CXL_config()
        os.chdir(self.workdir)
        process.run("meson setup build", sudo=True, shell=True, ignore_status=True)
        process.run("meson compile -C build", sudo=True, shell=True, ignore_status=True)

        cmd = "meson test -C build --no-rebuild --list --suite cxl | awk '{print $3}'"
        output = process.system_output(cmd, shell=True, ignore_status=True,
                                     sudo=True).decode("utf-8")
        self.log.info("CXL Test Lists: %s" % output)
        # Split lines and skip tests that causing kernel panic
        skip_tests = {"cxl-sanitize.sh", "cxl-translate.sh", "cxl-security.sh", "cxl-poison.sh", \
                "cxl-qos-class.sh", "cxl-elc.sh"}
        tests = [
            line.strip()
            for line in output.splitlines()
            if line.strip() and line.strip() not in skip_tests
        ]
        # Join into space-separated string
        test_list = " ".join(tests)
        self.log.info("Actual test lists: %s" % test_list)
        self.log.info("Running ndctl cxl tests....")
        cmd = "meson test -C build --no-rebuild --suite cxl %s" % test_list
        results = process.system_output(cmd, shell=True, ignore_status=True,
                                     sudo=True).decode("utf-8")
        self.log.info("results: %s" % results)
        for line in results.splitlines():
            if "Fail:" in line:
                self.fail_count = int(line.split(':')[-1].strip())
                if self.fail_count > 0:
                    self.fail("ndctl cxl tests failed, fail count = %d, check the debug log" % self.fail_count)
            if "Skipped:" in line:
                self.skip_count = int(line.split(':')[-1].strip())
                if self.skip_count > 0:
                    self.cancel("ndctl cxl tests skipped, skipped test count = %d, check the debug log" % self.skip_count)
            if "Ok:" in line:
                self.ok_count = int(line.split(':')[-1].strip())
                if self.ok_count == "12":
                    self.log.info("ndctl cxl tests passed.")
