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
# Copyright (C) 2025 AMD Inc.
# Author: Swapnil Sapkal <swapnil.sapkal@amd.com>

import os
import shutil
import yaml
from avocado import Test
from avocado import skipIf
from avocado.utils import cpu, build, process
from avocado.utils.software_manager.manager import SoftwareManager

# All C source files and the Makefile needed to build the test binary.
AVX512_DATA_FILES = [
    "avx512.yaml",
    "avx512_check.c",
    "test_avx512f.c",
    "test_avx512bw.c",
    "test_avx512dq.c",
    "test_avx512cd.c",
    "test_avx512vl.c",
    "test_avx512ifma.c",
    "test_avx512vbmi.c",
    "test_avx512vbmi2.c",
    "test_avx512vnni.c",
    "test_avx512bitalg.c",
    "test_avx512vpopcntdq.c",
    "Makefile",
]

class Avx512(Test):
    """
    AVX-512 instruction set validation for AMD EPYC (Zen 4+).

    Detects AVX-512 subsets via CPUID, verifies them against expected
    platform flags, and runs functional correctness tests for each
    supported subset.  Each subset has a dedicated C test file that
    exercises all representative instructions for that flag.

    :avocado: tags=cpu,avx512,amd
    """

    @skipIf(cpu.get_vendor() != "amd",
            "This test is only supported on AMD platforms")
    @skipIf(cpu.get_x86_amd_zen() < 4,
            "AVX-512 requires Zen 4 or later")
    def setUp(self):
        smm = SoftwareManager()
        for package in ["gcc", "make"]:
            if not smm.check_installed(package) and not smm.install(package):
                self.cancel("%s is needed for the test to be run" % package)

        for file_name in AVX512_DATA_FILES:
            self.copyutil(file_name)

        os.chdir(self.workdir)
        build.make(self.workdir)

        self.avx512_bin = os.path.join(self.workdir, "avx512_check")
        if not os.path.isfile(self.avx512_bin):
            self.cancel("Failed to compile avx512_check")

        self.zen_ver = cpu.get_x86_amd_zen()

        with open(os.path.join(self.workdir, "avx512.yaml")) as fp:
            cfg = yaml.safe_load(fp)
        flag_map = cfg.get("avx512_expected_flags", {})
        zen_key = "zen%d" % self.zen_ver
        self.expected_flags = flag_map.get(zen_key, [])

    def copyutil(self, file_name):
        shutil.copyfile(
            self.get_data(file_name),
            os.path.join(self.workdir, file_name),
        )

    def _get_detected_flags(self):
        """Run the detect subcommand and return the set of flags found."""
        result = process.run(
            "%s detect" % self.avx512_bin, ignore_status=True
        )
        output = result.stdout.decode().strip()
        if result.exit_status != 0:
            self.fail("AVX-512 detection failed: %s" % output)
        return set(output.splitlines())

    def test_detect_flags(self):
        """
        Verify that the CPUID-reported AVX-512 flags match the expected
        set for this Zen generation.
        """
        detected = self._get_detected_flags()
        self.log.info("Detected AVX-512 flags: %s", sorted(detected))

        expected = set(self.expected_flags)
        if not expected:
            self.cancel(
                "No expected AVX-512 flag list for Zen %d" % self.zen_ver
            )

        self.log.info("Expected AVX-512 flags for Zen %d: %s",
                       self.zen_ver, sorted(expected))

        missing = expected - detected
        if missing:
            self.fail(
                "Missing expected AVX-512 flags for Zen %d: %s"
                % (self.zen_ver, sorted(missing))
            )

        extra = detected - expected
        if extra:
            self.log.info(
                "Extra AVX-512 flags beyond expected set: %s", sorted(extra)
            )

        self.log.info("All expected AVX-512 flags are present")

    def test_functional_correctness(self):
        """
        Run functional correctness tests for all supported AVX-512 subsets.
        Each test executes actual AVX-512 instructions and verifies results.
        """
        result = process.run(
            "%s verify_all" % self.avx512_bin, ignore_status=True
        )
        output = result.stdout.decode()
        self.log.info("Functional test output:\n%s", output)

        if result.exit_status != 0:
            failed_lines = [
                line for line in output.splitlines() if line.startswith("FAIL")
            ]
            self.fail(
                "AVX-512 functional correctness failures:\n%s"
                % "\n".join(failed_lines)
            )

        passed = [
            line for line in output.splitlines() if line.startswith("PASS")
        ]
        self.log.info(
            "All %d functional correctness tests passed", len(passed)
        )

    def test_individual_verify(self):
        """
        Run individual verify for each detected flag to ensure per-subset
        isolation (catches issues masked by verify_all ordering).
        """
        detected = self._get_detected_flags()
        failures = []

        for flag in sorted(detected):
            result = process.run(
                "%s verify %s" % (self.avx512_bin, flag),
                ignore_status=True,
            )
            output = result.stdout.decode().strip()
            self.log.info("[%s] %s", flag, output)

            if result.exit_status == 1:
                failures.append(flag)
            elif result.exit_status == 2:
                self.log.info("Skipped %s (no functional test)", flag)

        if failures:
            self.fail(
                "Individual verify failed for: %s" % sorted(failures)
            )

        self.log.info("All individual AVX-512 verify tests passed")
