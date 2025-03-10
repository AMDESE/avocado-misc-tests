#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (c) 2025 AMD Corporation
# @Author(s): Kalpana Shetty <Kalpana.Shetty@amd.com>
#             Babu Moger <Babu.Moger@amd.com>
# @Module Name: qos_common.py
# @Description: Includes common functions used in pqos tests
# @History:  Created Jan 10 2025 - Created

import sys
import subprocess
import os.path
import logging
from avocado.utils import distro
from avocado.utils.software_manager.manager import SoftwareManager

class CommonLib:
    @classmethod
    def Run(self, cmd):
        """
        Run a cmd[], return the exit code, stdout, and stderr.
        """
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = proc.communicate()

        return proc.returncode, stdout, stderr

    def install_preq(self):
        """
        Install cpuid, msr-tools and intel-cmt-cat
        """
        logging.info("Installing pre-requisites packages")
        sm = SoftwareManager()
        dist = distro.detect()
        deps = ['libtool']
        if dist.name in ['Ubuntu', 'rhel']:
            for package in deps:
                if not sm.check_installed(package) and not sm.install(package):
                    logging.error("%s is needed for the qos tests to run" % package)
        else:
            logging.error("Unsupported distro")
            return -1

        # Install the latest version of cpuid which has bug fixes
        logging.info("Installing cpuid from source")
        exitcode, stdout, _ = CommonLib.Run("wget https://etallen.com/cpuid/cpuid-20250419.src.tar.gz")
        if (exitcode == 0):
            exitcode, stdout, _ = CommonLib.Run("tar xvf cpuid-20250419.src.tar.gz")
            if (exitcode == 0):
                exitcode, stdout, _ = CommonLib.Run("cd cpuid-20250419; make; make install")
                if (exitcode == 0):
                    exitcode, stdout, _ = CommonLib.Run("rm -rf cpuid-20250419.src.tar.gz cpuid-20250419")

        # Install msr-tools from source
        logging.info("Installing msr-tools package")
        exitcode, stdout, _ = CommonLib.Run("git clone https://github.com/intel/msr-tools.git")
        if (exitcode == 0):
            exitcode, stdout, _ = CommonLib.Run("cd msr-tools; ./autogen.sh; make install")
            if (exitcode == 0):
                exitcode, stdout, _ = CommonLib.Run("rm -rf msr-tools")
                logging.info(stdout)

        # Install intel-cmd-cat from source
        logging.info("Installing intel-cmt-cat package")
        exitcode, stdout, _ = CommonLib.Run("git clone https://github.com/intel/intel-cmt-cat.git")
        if (exitcode == 0):
            exitcode, stdout, _ = CommonLib.Run("cd intel-cmt-cat; make; make install")
            if (exitcode == 0):
                exitcode, stdout, _ = CommonLib.Run("rm -rf intel-cmt-cat")
                logging.info(stdout)
