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
# Copyright: 2026 Advanced Micro Devices, Inc.
# Author: Yazen Ghannam <yazen.ghannam@amd.com>

"""
Validate the SMCA Corrected Error Interrupt support added by:

    commit 4efaec6e16c2 ("x86/mce/amd: Support SMCA Corrected Error Interrupt")

On Scalable MCA systems the platform may manage the MCA thresholding limit and
send the MCA Thresholding interrupt to the OS. Two MCA_CONFIG bits express the
handshake (see smca_configure() in arch/x86/kernel/cpu/mce/amd.c):

  * MCA_CONFIG[IntPresent], bit 10 - platform -> OS: this bank can send an MCA
    Thresholding interrupt without the OS initializing thresholding.
  * MCA_CONFIG[IntEn], bit 40 - OS -> platform: the OS is ready to handle it.

The kernel sets IntEn (and adds the bank to thr_intr_banks) for every bank that
advertises IntPresent, provided the threshold interrupt vector was installed in
the APIC LVT (thr_intr_en, set by smca_enable_interrupt_vectors()).

This test checks both observable sides of that:

  1. the MSR contract - IntPresent implies IntEn, and
  2. the corroborating boot message showing the threshold vector
     (THRESHOLD_APIC_VECTOR, 0xf9) was assigned an APIC LVT offset:
         "LVT offset <N> assigned for vector 0xf9"

MSRs are read via non-interactive 'sudo -n dd' on /dev/cpu/*/msr, so the avocado
process need not be root (passwordless sudo required); no msr-tools needed.
"""

import os
import re
import struct

from avocado import Test
from avocado.utils import genio, process


# arch/x86/include/asm/mce.h, asm/msr-index.h, asm/irq_vectors.h
MSR_IA32_MCG_CAP = 0x179
MSR_AMD64_SMCA_MC0_CONFIG = 0xC0002004
SMCA_MCx_STRIDE = 0x10

# MCA_CONFIG bit positions (64-bit view; 'low' is bits[31:0], 'high' bits[63:32])
CFG_INT_PRESENT_BIT = 10        # low BIT(10)
CFG_INT_EN_BIT = 40             # high BIT(8) == bit 40

THRESHOLD_APIC_VECTOR = 0xF9

MACHINECHECK = '/sys/devices/system/machinecheck'


class SmcaThrInterrupt(Test):

    """
    :avocado: tags=ras,amd,mce,smca,x86_64,privileged
    """

    def setUp(self):
        cpuinfo = genio.read_file('/proc/cpuinfo')
        flags = ' %s ' % cpuinfo.replace('\n', ' ')
        if 'AuthenticAMD' not in cpuinfo:
            self.cancel("Test is only applicable to AMD processors")
        if ' smca ' not in flags:
            self.cancel("SMCA (Scalable MCA) not supported on this system")
        # thr_intr_en additionally requires SUCCOR; without it the kernel never
        # installs the threshold vector and never sets IntEn.
        if ' succor ' not in flags:
            self.cancel("SUCCOR not supported; the threshold interrupt vector "
                        "is not installed without it")

        self.int_present_bit = self.params.get('int_present_bit',
                                               default=CFG_INT_PRESENT_BIT)
        self.int_en_bit = self.params.get('int_en_bit', default=CFG_INT_EN_BIT)
        self.vector = self.params.get('threshold_vector',
                                      default=THRESHOLD_APIC_VECTOR)
        # A full per-CPU x per-bank sweep is one MSR read per bank per CPU. On
        # large systems (1000+ CPUs) that is tens of thousands of reads, so
        # sample CPUs by default. 0 means "every CPU"; the sampling is always
        # logged, never silent.
        self.max_cpus = self.params.get('max_cpus', default=8)

        self._msr_ok = None

    # ---- low level helpers -------------------------------------------------

    @staticmethod
    def _read_msr(msr, cpu=0):
        """Read a 64-bit MSR from /dev/cpu/<cpu>/msr via non-interactive
        'sudo -n dd'. Uses the kernel 'msr' driver (CONFIG_X86_MSR) directly, so
        no userspace package (msr-tools) is required.

        'skip' is the MSR number as a byte offset (iflag=skip_bytes); one 8-byte
        block is the register value, little-endian. Raises OSError on any
        failure so callers can uniformly skip: a #GP on an absent bank, an
        invalid/offline CPU, a missing msr node, or missing sudo.
        """
        cmd = ("sudo -n dd if=/dev/cpu/%d/msr bs=8 count=1 skip=%d "
               "iflag=skip_bytes status=none" % (cpu, msr))
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0 or len(result.stdout) != 8:
            raise OSError("MSR read failed for 0x%x on cpu%d" % (msr, cpu))
        return struct.unpack('<Q', result.stdout)[0]

    def _msr_available(self):
        """True if MSRs can be read via 'sudo -n dd'. Never prompts."""
        process.system('sudo -n modprobe msr', shell=True, ignore_status=True)
        if not os.path.exists('/dev/cpu/0/msr'):
            return False
        try:
            self._read_msr(MSR_IA32_MCG_CAP, 0)
            return True
        except OSError:
            return False

    def _get_msr_ok(self):
        if self._msr_ok is None:
            self._msr_ok = self._msr_available()
        return self._msr_ok

    def _num_banks(self, cpu):
        return self._read_msr(MSR_IA32_MCG_CAP, cpu) & 0xFF

    @staticmethod
    def _machinecheck_cpus():
        """CPU indices that have a machinecheck<cpu> sysfs dir (no root needed).
        This is the kernel's own view of MCE-capable online CPUs."""
        if not os.path.isdir(MACHINECHECK):
            return []
        cpus = []
        for name in os.listdir(MACHINECHECK):
            match = re.match(r'machinecheck(\d+)$', name)
            if match:
                cpus.append(int(match.group(1)))
        return sorted(cpus)

    def _sample_cpus(self):
        """Evenly-spaced sample of MCE-capable CPUs, always including the first.

        Returns (sampled, total). Sampling keeps the MSR sweep tractable on
        large systems; callers log both numbers so partial coverage is explicit.
        """
        cpus = self._machinecheck_cpus()
        if not cpus or not self.max_cpus or len(cpus) <= self.max_cpus:
            return cpus, len(cpus)
        step = len(cpus) / float(self.max_cpus)
        sampled = sorted({cpus[min(int(i * step), len(cpus) - 1)]
                          for i in range(self.max_cpus)})
        return sampled, len(cpus)

    # ---- tests -------------------------------------------------------------

    def test_config_int_enabled(self):
        """
        MCA_CONFIG contract: every bank advertising IntPresent (bit 10) must
        have IntEn (bit 40) set by the kernel.

        This is the direct, deterministic assertion of commit 4efaec6e16c2 and
        needs no error injection.
        """
        if not self._get_msr_ok():
            self.cancel("MSRs not readable via sudo dd; enable CONFIG_X86_MSR "
                        "(msr driver) and ensure passwordless sudo")

        cpus, total = self._sample_cpus()
        if not cpus:
            self.cancel("No MCE-capable CPUs found under %s" % MACHINECHECK)
        if len(cpus) != total:
            self.log.info("Sampling %d of %d MCE-capable CPUs (set max_cpus=0 "
                          "to check every CPU): %s", len(cpus), total,
                          ', '.join(str(c) for c in cpus))
        else:
            self.log.info("Checking all %d MCE-capable CPUs", total)

        present, missing, preset = [], [], []
        for cpu in cpus:
            try:
                nbanks = self._num_banks(cpu)
            except OSError:
                self.log.warning("cpu%d: MCG_CAP unreadable, skipping", cpu)
                continue
            for bank in range(nbanks):
                try:
                    cfg = self._read_msr(MSR_AMD64_SMCA_MC0_CONFIG +
                                         SMCA_MCx_STRIDE * bank, cpu)
                except OSError:
                    # Unpopulated/unimplemented bank - not an error.
                    continue
                int_present = bool(cfg & (1 << self.int_present_bit))
                int_en = bool(cfg & (1 << self.int_en_bit))
                if int_present:
                    present.append((cpu, bank))
                    if int_en:
                        self.log.info("cpu%d bank%d: IntPresent=1 IntEn=1 OK "
                                      "(MCA_CONFIG=0x%016x)", cpu, bank, cfg)
                    else:
                        missing.append("cpu%d bank%d (MCA_CONFIG=0x%016x)"
                                       % (cpu, bank, cfg))
                elif int_en:
                    # The kernel only sets IntEn when IntPresent is set, so this
                    # is platform-preset state. Informational, not a failure.
                    preset.append("cpu%d bank%d" % (cpu, bank))

        if not present:
            self.cancel("No bank advertises MCA_CONFIG[IntPresent] on the "
                        "sampled CPUs; this platform does not use "
                        "platform-managed MCA thresholding, so the SMCA "
                        "Corrected Error Interrupt is not applicable")

        self.log.info("%d bank(s) advertise IntPresent across %d CPU(s)",
                      len(present), len(cpus))
        if preset:
            self.log.info("IntEn set without IntPresent (platform-preset, not "
                          "set by the kernel): %s", ', '.join(preset))
        if missing:
            self.fail("MCA_CONFIG[IntEn] not set on bank(s) advertising "
                      "IntPresent: %s" % '; '.join(missing))

    def test_apic_lvt_vector_assigned(self):
        """
        Corroborating boot evidence: the threshold interrupt vector (0xf9) must
        have been assigned an APIC LVT offset, logged by reserve_eilvt_offset()
        as "LVT offset <N> assigned for vector 0xf9".

        The kernel only sets IntEn when that vector was installed (thr_intr_en),
        so the message and the MSR state must agree. Treated as inconclusive
        (CANCEL) if the kernel log no longer contains boot-time messages.
        """
        # \b anchors the end so vector 0xf9 cannot match a longer value.
        pattern = (r'LVT offset [0-9]+ assigned for vector 0x%02x\b'
                   % self.vector)
        found = process.run("sudo -n dmesg | grep -E -- '%s'" % pattern,
                            shell=True,
                            ignore_status=True).stdout.decode('utf-8',
                                                              'replace').strip()
        if found:
            for line in found.splitlines():
                self.log.info("APIC LVT assignment: %s", line.strip())
            return

        # Not found: distinguish "never happened" from "log wrapped past boot".
        if not self._dmesg_has_boot():
            self.cancel("Threshold vector 0x%02x LVT assignment message not "
                        "found, but the kernel log no longer contains boot "
                        "messages - inconclusive. Re-run after a fresh boot."
                        % self.vector)

        # Boot messages are present, so the message genuinely never appeared.
        # Only a failure if the feature is actually in use on this platform.
        if self._get_msr_ok() and self._any_int_present():
            self.fail("Bank(s) advertise MCA_CONFIG[IntPresent] but the "
                      "threshold vector 0x%02x was never assigned an APIC LVT "
                      "offset (no 'LVT offset N assigned for vector 0x%02x' in "
                      "the kernel log)" % (self.vector, self.vector))
        self.cancel("Threshold vector 0x%02x LVT assignment not logged and no "
                    "bank advertises IntPresent; the SMCA Corrected Error "
                    "Interrupt is not in use on this platform" % self.vector)

    # ---- helpers used by the dmesg check -----------------------------------

    @staticmethod
    def _dmesg_has_boot():
        """True if the kernel log still contains the boot banner, i.e. early
        boot messages have not been overwritten by ring-buffer wrap."""
        return process.run("sudo -n dmesg | grep -c -F 'Linux version'",
                           shell=True, ignore_status=True).exit_status == 0

    def _any_int_present(self):
        """True if any sampled bank advertises IntPresent."""
        cpus, _total = self._sample_cpus()
        for cpu in cpus:
            try:
                nbanks = self._num_banks(cpu)
            except OSError:
                continue
            for bank in range(nbanks):
                try:
                    cfg = self._read_msr(MSR_AMD64_SMCA_MC0_CONFIG +
                                         SMCA_MCx_STRIDE * bank, cpu)
                except OSError:
                    continue
                if cfg & (1 << self.int_present_bit):
                    return True
        return False
