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
Validate the kernel's Scalable MCA (SMCA) bank-type handling across every known
bank type: threshold sysfs short names and EDAC decoder long names, plus an
authoritative MCA_IPID (HWID, McaType) cross-check where MSRs are readable.

See smca_bank_types.md for what each test checks, the requirements, the YAML
inputs and coverage notes.
"""

import os
import re
import struct

from avocado import Test
from avocado.utils import genio, process, wait


# Full mirror of the kernel SMCA tables (one row per (HWID, McaType) tuple):
#   smca_hwid_mcatypes[]  -> hwid, mcatype
#   smca_names[]          -> sysfs (short) name
#   smca_long_names[]     -> longname (decoder). None where the kernel has no
#                            long name (decoder would print "(null)") or where
#                            the type is special (reserved); decode is skipped.
# Used as the default when no YAML data file is supplied.
_SMCA_BANKS = [
    {'hwid': 0x2E,  'mcatype': 0x0,  'sysfs': 'coherent_station', 'longname': 'Coherent Station'},
    {'hwid': 0x2E,  'mcatype': 0x2,  'sysfs': 'coherent_station', 'longname': 'Coherent Station'},
    {'hwid': 0x164, 'mcatype': 0x0,  'sysfs': 'dacc_be',          'longname': 'DACC Back-end Unit'},
    {'hwid': 0x157, 'mcatype': 0x0,  'sysfs': 'dacc_fe',          'longname': 'DACC Front-end Unit'},
    {'hwid': 0xB0,  'mcatype': 0x3,  'sysfs': 'decode_unit',      'longname': 'Decode Unit'},
    {'hwid': 0x1E0, 'mcatype': 0x0,  'sysfs': 'eddr5_cmn',        'longname': 'eDDR5 CMN Unit'},
    {'hwid': 0xB0,  'mcatype': 0x5,  'sysfs': 'execution_unit',   'longname': 'Execution Unit'},
    {'hwid': 0xB0,  'mcatype': 0x6,  'sysfs': 'floating_point',   'longname': 'Floating Point Unit'},
    {'hwid': 0x241, 'mcatype': 0x0,  'sysfs': 'gmi_pcs',          'longname': 'Global Memory Interconnect PCS Unit'},
    {'hwid': 0x269, 'mcatype': 0x0,  'sysfs': 'gmi_phy',          'longname': 'Global Memory Interconnect PHY Unit'},
    {'hwid': 0xB0,  'mcatype': 0x1,  'sysfs': 'insn_fetch',       'longname': 'Instruction Fetch Unit'},
    {'hwid': 0xB0,  'mcatype': 0x2,  'sysfs': 'l2_cache',         'longname': 'L2 Cache'},
    {'hwid': 0xB0,  'mcatype': 0x7,  'sysfs': 'l3_cache',         'longname': 'L3 Cache'},
    {'hwid': 0xB0,  'mcatype': 0x0,  'sysfs': 'load_store',       'longname': 'Load Store Unit'},
    {'hwid': 0xB0,  'mcatype': 0x10, 'sysfs': 'load_store',       'longname': 'Load Store Unit'},
    {'hwid': 0x2E,  'mcatype': 0x4,  'sysfs': 'ma_llc',           'longname': None},
    {'hwid': 0x01,  'mcatype': 0x2,  'sysfs': 'mp5',              'longname': 'Microprocessor 5 Unit'},
    {'hwid': 0xFF,  'mcatype': 0x2,  'sysfs': 'mpart',            'longname': 'MPART Unit'},
    {'hwid': 0xFD,  'mcatype': 0x0,  'sysfs': 'mpasp',            'longname': 'MPASP Unit'},
    {'hwid': 0xFD,  'mcatype': 0x1,  'sysfs': 'mpasp',            'longname': 'MPASP Unit'},
    {'hwid': 0xBE,  'mcatype': 0x0,  'sysfs': 'mpdacc',           'longname': 'MPDACC Unit'},
    {'hwid': 0x01,  'mcatype': 0x3,  'sysfs': 'mpdma',            'longname': 'MPDMA Unit'},
    {'hwid': 0xF9,  'mcatype': 0x0,  'sysfs': 'mpm',              'longname': 'MPM Unit'},
    {'hwid': 0x12,  'mcatype': 0x0,  'sysfs': 'mpras',            'longname': 'MPRAS Unit'},
    {'hwid': 0x6C,  'mcatype': 0x0,  'sysfs': 'nbif',             'longname': 'NBIF Unit'},
    {'hwid': 0x18,  'mcatype': 0x0,  'sysfs': 'nbio',             'longname': 'Northbridge IO Unit'},
    {'hwid': 0x05,  'mcatype': 0x0,  'sysfs': 'param_block',      'longname': 'Parameter Block'},
    {'hwid': 0x46,  'mcatype': 0x0,  'sysfs': 'pcie',             'longname': 'PCI Express Unit'},
    {'hwid': 0x46,  'mcatype': 0x1,  'sysfs': 'pcie',             'longname': 'PCI Express Unit'},
    {'hwid': 0x1E1, 'mcatype': 0x0,  'sysfs': 'pcie_pl',          'longname': 'PCIe Link Unit'},
    {'hwid': 0x2E,  'mcatype': 0x1,  'sysfs': 'pie',              'longname': 'Power, Interrupts, etc.'},
    {'hwid': 0xFF,  'mcatype': 0x0,  'sysfs': 'psp',              'longname': 'Platform Security Processor'},
    {'hwid': 0xFF,  'mcatype': 0x1,  'sysfs': 'psp',              'longname': 'Platform Security Processor'},
    {'hwid': 0x00,  'mcatype': 0x0,  'sysfs': 'reserved',         'longname': None},
    {'hwid': 0xA8,  'mcatype': 0x0,  'sysfs': 'sata',             'longname': 'SATA Unit'},
    {'hwid': 0x80,  'mcatype': 0x0,  'sysfs': 'shub',             'longname': 'System Hub Unit'},
    {'hwid': 0x01,  'mcatype': 0x0,  'sysfs': 'smu',              'longname': 'System Management Unit'},
    {'hwid': 0x01,  'mcatype': 0x1,  'sysfs': 'smu',              'longname': 'System Management Unit'},
    {'hwid': 0x5C,  'mcatype': 0x0,  'sysfs': 'ssbdci',           'longname': 'Die to Die Interconnect Unit'},
    {'hwid': 0x96,  'mcatype': 0x0,  'sysfs': 'umc',              'longname': 'Unified Memory Controller'},
    {'hwid': 0x96,  'mcatype': 0x1,  'sysfs': 'umc_v2',           'longname': 'Unified Memory Controller v2'},
    {'hwid': 0xAA,  'mcatype': 0x0,  'sysfs': 'usb',              'longname': 'USB Unit'},
    {'hwid': 0x180, 'mcatype': 0x0,  'sysfs': 'usr_cp',           'longname': None},
    {'hwid': 0x170, 'mcatype': 0x0,  'sysfs': 'usr_dp',           'longname': None},
    {'hwid': 0x267, 'mcatype': 0x0,  'sysfs': 'wafl_phy',         'longname': 'WAFL PHY Unit'},
    {'hwid': 0x50,  'mcatype': 0x0,  'sysfs': 'xgmi_pcs',         'longname': 'Ext Global Memory Interconnect PCS Unit'},
    {'hwid': 0x259, 'mcatype': 0x0,  'sysfs': 'xgmi_phy',         'longname': 'Ext Global Memory Interconnect PHY Unit'},
]

# arch/x86/include/asm/mce.h and asm/msr-index.h
MSR_IA32_MCG_CAP = 0x179
MSR_AMD64_SMCA_MC0_IPID = 0xC0002005
SMCA_MCx_STRIDE = 0x10

MACHINECHECK = '/sys/devices/system/machinecheck'
MCE_INJECT_DIR = '/sys/kernel/debug/mce-inject'


class SmcaBankTypes(Test):

    """
    :avocado: tags=ras,amd,mce,smca,x86_64,privileged
    """

    def setUp(self):
        cpuinfo = genio.read_file('/proc/cpuinfo')
        if 'AuthenticAMD' not in cpuinfo:
            self.cancel("Test is only applicable to AMD processors")
        # SMCA is exported as the "smca" flag on capable AMD parts.
        if ' smca ' not in ' %s ' % cpuinfo.replace('\n', ' '):
            self.cancel("SMCA (Scalable MCA) not supported on this system")

        # Full known-type reference table (built-in), used to recognise sysfs
        # directory names and to spot th_bank_<N> fallbacks.
        self.banks = _SMCA_BANKS

        # The single bank type under test for the per-bank methods, supplied by
        # the YAML mux (one variant per bank type). None when run without -m.
        self.bank = self._bank_from_params()

        # Which known bank types are exposed in the threshold sysfs directories.
        # The sysfs directory name IS the kernel-recognised type, so this needs
        # no privileges and works even when MSRs are not readable.
        self.sysfs_present = self._sysfs_present_banks()

        # MSR access is probed lazily (only when a test needs it) so the pure
        # sysfs tests never touch /dev/cpu. Cached on first use.
        self._msr_ok = None

    def _bank_from_params(self):
        """Return the single bank dict from the YAML mux variant, or None."""
        sysfs = self.params.get('sysfs', default=None)
        if sysfs is None:
            return None

        def _int(val):
            return val if isinstance(val, int) else int(str(val), 0)

        longname = self.params.get('longname', default=None)
        if longname in ('', 'null', 'None'):
            longname = None
        return {'hwid': _int(self.params.get('hwid')),
                'mcatype': _int(self.params.get('mcatype')),
                'sysfs': sysfs,
                'longname': longname}

    def _require_bank(self):
        """Per-bank precondition: a bank variant must be selected via -m."""
        if self.bank is None:
            self.cancel("No bank type selected; run with "
                        "-m ras/amd/mce_mca/smca_bank_types.py.data/smca_bank_types.yaml "
                        "to test each bank type individually")
        return self.bank

    # ---- low level helpers -------------------------------------------------

    @staticmethod
    def _read_msr(msr, cpu=0):
        """Read a 64-bit MSR from /dev/cpu/<cpu>/msr (kernel 'msr' driver,
        CONFIG_X86_MSR). The file position is the MSR number; one 8-byte read is
        the register value, little-endian. Requires root. Raises OSError on any
        failure so callers can uniformly skip: a #GP on an absent bank, an
        invalid/offline CPU, or a missing msr node."""
        with open('/dev/cpu/%d/msr' % cpu, 'rb') as fobj:
            fobj.seek(msr)
            data = fobj.read(8)
        if len(data) != 8:
            raise OSError("short MSR read for 0x%x on cpu%d" % (msr, cpu))
        return struct.unpack('<Q', data)[0]

    def _msr_available(self):
        """True if MSRs can be read from /dev/cpu/*/msr. Needs the kernel 'msr'
        driver (CONFIG_X86_MSR). Kept distinct from 'bank absent' so an access
        failure is never misreported as 'not present'."""
        process.system('modprobe msr', ignore_status=True)
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

    def _locate_bank(self, entry):
        """Return (cpu, bank_number) for entry's (hwid, mcatype) via MCA_IPID, or
        None if not found. Only the CPUs whose threshold sysfs exposes this
        bank's short name are scanned - those are exactly the CPUs that can host
        it, which avoids probing every (possibly offline/invalid) CPU."""
        key = (entry['hwid'], entry['mcatype'])
        cpus = sorted({cpu for (cpu, _d)
                       in self.sysfs_present.get(entry['sysfs'], [])})
        for cpu in cpus:
            try:
                nbanks = self._num_banks(cpu)
            except OSError:
                continue
            for bank in range(nbanks):
                try:
                    ipid = self._read_msr(MSR_AMD64_SMCA_MC0_IPID +
                                          SMCA_MCx_STRIDE * bank, cpu)
                except OSError:
                    continue
                if ipid and self._decode_ipid(ipid) == key:
                    return (cpu, bank)
        return None

    @staticmethod
    def _machinecheck_cpus():
        """CPU indices that have a machinecheck<cpu> sysfs dir (no root needed)."""
        if not os.path.isdir(MACHINECHECK):
            return []
        cpus = []
        for name in os.listdir(MACHINECHECK):
            match = re.match(r'machinecheck(\d+)$', name)
            if match:
                cpus.append(int(match.group(1)))
        return sorted(cpus)

    @staticmethod
    def _strip_instance(name):
        """'mpras_0' -> 'mpras'; 'dacc_fe' -> 'dacc_fe'; 'pcie_pl_1' -> 'pcie_pl'."""
        head, _, tail = name.rpartition('_')
        return head if (head and tail.isdigit()) else name

    def _num_banks(self, cpu):
        return self._read_msr(MSR_IA32_MCG_CAP, cpu) & 0xFF

    @staticmethod
    def _decode_ipid(ipid):
        # amd.c: hwid = high & MCI_IPID_HWID (0xFFF)
        #        mcatype = (high & MCI_IPID_MCATYPE (0xFFFF0000)) >> 16
        # where high is the upper 32 bits of the IPID.
        hwid = (ipid >> 32) & 0xFFF
        mcatype = (ipid >> 48) & 0xFFFF
        return hwid, mcatype

    @staticmethod
    def _bank_dirs(cpu):
        base = os.path.join(MACHINECHECK, 'machinecheck%d' % cpu)
        dirs = []
        if not os.path.isdir(base):
            return dirs
        for name in os.listdir(base):
            path = os.path.join(base, name)
            if name == 'power' or os.path.islink(path) or not os.path.isdir(path):
                continue
            dirs.append(name)
        return dirs

    def _sysfs_present_banks(self):
        """{sysfs_name: [(cpu, dirname), ...]} for known bank types found in the
        threshold sysfs directories. No root required."""
        wanted = {e['sysfs'] for e in self.banks}
        found = {}
        for cpu in self._machinecheck_cpus():
            for name in self._bank_dirs(cpu):
                base = self._strip_instance(name)
                if base in wanted:
                    found.setdefault(base, []).append((cpu, name))
        return found

    # ---- preconditions -----------------------------------------------------

    def _require_threshold_sysfs(self):
        """Shared precondition: CANCEL when the machinecheck/threshold sysfs
        interface is absent, so dependent tests report "not applicable" rather
        than passing vacuously."""
        if not os.path.isdir(MACHINECHECK):
            self.cancel("machinecheck sysfs interface absent (%s)"
                        % MACHINECHECK)
        if not any(self._bank_dirs(cpu) for cpu in self._machinecheck_cpus()):
            self.cancel("No threshold bank directories present; nothing to "
                        "validate.")

    # ---- tests -------------------------------------------------------------

    def test_machinecheck_sysfs_exists(self):
        """FAIL if the machinecheck sysfs base or any per-CPU machinecheck<cpu>
        dir is missing; CANCEL if no threshold bank dirs exist (not
        applicable)."""
        if not os.path.isdir(MACHINECHECK):
            self.fail("machinecheck sysfs base '%s' is missing" % MACHINECHECK)

        cpus = self._machinecheck_cpus()
        missing = [c for c in cpus
                   if not os.path.isdir(os.path.join(MACHINECHECK,
                                                     'machinecheck%d' % c))]
        if missing:
            self.fail("Missing machinecheck<cpu> sysfs dir(s) for CPU(s): %s"
                      % ', '.join(str(c) for c in missing))

        total = sum(len(self._bank_dirs(c)) for c in cpus)
        if not total:
            self.cancel("No threshold bank directories found under %s/"
                        "machinecheck*/ for the enabled MCA banks"
                        % MACHINECHECK)
        self.log.info("machinecheck sysfs present for %d CPU(s), %d threshold "
                      "bank dir(s) total", len(cpus), total)

    def test_no_unrecognized_banks(self):
        """FAIL if any populated MCA bank is exposed as a th_bank_<N> threshold
        directory (an SMCA type the kernel does not recognise)."""
        self._require_threshold_sysfs()
        bad = []
        for cpu in self._machinecheck_cpus():
            for name in self._bank_dirs(cpu):
                if self._strip_instance(name) == 'th_bank':
                    bad.append('machinecheck%d/%s' % (cpu, name))
        if bad:
            self.fail("Unrecognized SMCA bank(s) exposed as th_bank_<N>: %s"
                      % ', '.join(sorted(set(bad))))

    def test_sysfs_name(self):
        """Verify this bank type is exposed under its expected threshold sysfs
        short name (CANCEL if the hardware does not implement it), plus an
        authoritative MCA_IPID (HWID,McaType)->name cross-check where MSRs are
        readable."""
        self._require_threshold_sysfs()
        bank = self._require_bank()
        name = bank['sysfs']

        locs = self.sysfs_present.get(name)
        if not locs:
            self.cancel("Bank type '%s' (hwid 0x%x, mcatype 0x%x) is not present "
                        "on this system" % (name, bank['hwid'], bank['mcatype']))
        for (cpu, dirname) in locs:
            self.log.info("bank type '%s' present: machinecheck%d/%s",
                          name, cpu, dirname)

        if not self._get_msr_ok():
            self.log.warning("MSRs not readable (CONFIG_X86_MSR / msr driver); "
                             "verified sysfs presence/spelling only, skipped "
                             "authoritative (HWID,McaType)->name cross-check")
            return

        loc = self._locate_bank(bank)
        if loc is None:
            self.log.warning("Could not locate '%s' via MCA_IPID on the CPU(s) "
                             "exposing it; skipped cross-check", name)
            return
        cpu, num = loc
        found = [self._strip_instance(n) for n in self._bank_dirs(cpu)]
        if name not in found:
            self.fail("cpu%d bank%d IPID(hwid 0x%x,mcatype 0x%x) expected sysfs "
                      "'%s' (found: %s)" % (cpu, num, bank['hwid'],
                      bank['mcatype'], name, ', '.join(self._bank_dirs(cpu))))
        self.log.info("cpu%d bank%d IPID(hwid 0x%x,mcatype 0x%x) -> sysfs '%s' OK",
                      cpu, num, bank['hwid'], bank['mcatype'], name)

    def test_decode(self):
        """Software-inject a corrected error into this bank type and confirm the
        EDAC decoder prints its expected long name in the kernel log. Requires
        root. CANCEL for types with no kernel long name or absent from this
        hardware."""
        bank = self._require_bank()
        if not bank['longname']:
            self.cancel("Bank type '%s' has no kernel long name; decode not "
                        "applicable" % bank['sysfs'])
        if not self._get_msr_ok():
            self.cancel("MSRs not readable; enable CONFIG_X86_MSR (msr driver)")

        loc = self._locate_bank(bank)
        if loc is None:
            self.cancel("Bank type '%s' (hwid 0x%x, mcatype 0x%x) is not present "
                        "on this system (per IPID scan)"
                        % (bank['sysfs'], bank['hwid'], bank['mcatype']))
        cpu, num = loc

        if not os.path.isdir(MCE_INJECT_DIR):
            process.system('modprobe mce-inject', ignore_status=True)
        if not os.path.isdir(MCE_INJECT_DIR):
            self.cancel("mce-inject debugfs interface unavailable; enable "
                        "CONFIG_X86_MCE_INJECT and mount debugfs")

        expected = "%s Ext. Error Code:" % bank['longname']
        log = self._inject_sw_and_read(cpu, num, expected)
        if expected not in log:
            self.fail("cpu%d bank%d ('%s'): expected '%s' not found in log"
                      % (cpu, num, bank['sysfs'], expected))
        self.log.info("cpu%d bank%d: '%s' decoded as '%s' OK",
                      cpu, num, bank['sysfs'], bank['longname'])

    # ---- injection ---------------------------------------------------------

    @staticmethod
    def _dfs_write(path, value):
        """Write value + newline to a debugfs/kmsg file. The mce-inject 'flags'
        handler overwrites the last byte of the input (it expects a trailing
        newline), so a value written without one is truncated (e.g. 'sw' -> 's',
        'Invalid flags value'). The numeric attrs tolerate the newline too."""
        genio.write_file(path, '%s\n' % value)

    def _read_from_marker(self, marker):
        """Return the dmesg tail from our unique marker forward.

        dmesg can be very large, so reduce the volume before it reaches Python:
        grep from our unique marker forward (only a handful of decode lines)
        instead of scanning the whole buffer here. No match -> empty output.
        """
        return process.run("dmesg | grep -F -A 100 -- '%s'" % marker,
                           shell=True, ignore_status=True).stdout.decode(
                               'utf-8', 'replace')

    def _inject_sw_and_read(self, cpu, bank, expected, timeout=5):
        """Do a safe software-only injection and return the log tail once the
        expected decode line appears (or after timeout). Requires root (writes
        debugfs and /dev/kmsg directly).

        The 'sw' injection only logs the MCE; the EDAC mce_amd decoder that
        prints the "<name> Ext. Error Code:" line runs asynchronously off the
        MCE notifier chain from a workqueue (mce_gen_pool_process), so the line
        can lag the injecting 'bank' write by tens of milliseconds. Poll the log
        until it shows up rather than reading once and racing the decoder.
        """
        marker = "AVOCADO_SMCA_%d_c%db%d" % (os.getpid(), cpu, bank)
        self._dfs_write('/dev/kmsg', marker)

        # Order matters: writing 'bank' triggers the injection, so it goes last.
        # 'sw' only exercises the decode path and is documented as safe.
        #
        # Default status sets a non-zero XEC (bits [21:16]; here xec=1). This is
        # required for UMC banks: decode_smca_error() calls into amd64_edac's
        # decode_dram_ecc() only when xec == 0, and that DRAM-ECC path WARNs
        # ("Something is rotten in the state of Denmark") on a synthetic error
        # with no real DIMM/address. A non-zero xec keeps every bank on the
        # generic "<name> Ext. Error Code" decode path.
        status = self.params.get('status', default=0x10000)
        status = status if isinstance(status, int) else int(str(status), 0)
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'flags'), 'sw')
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'cpu'), str(cpu))
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'status'), '0x%x' % status)
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'synd'), '0x0')
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'addr'), '0x0')
        self._dfs_write(os.path.join(MCE_INJECT_DIR, 'bank'), str(bank))

        # The decoder output is deferred to a workqueue, so it may not be present
        # the instant the 'bank' write returns. Poll until the expected line
        # appears (or timeout), then return the final tail for the caller to
        # assert on. A genuine decode miss still returns an empty/short tail.
        wait.wait_for(lambda: expected in self._read_from_marker(marker),
                      timeout=timeout, step=0.1)
        return self._read_from_marker(marker)
