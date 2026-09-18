# AMD SMCA tests

This directory holds AMD Scalable MCA (SMCA) tests:

* `smca_bank_types.py` - bank-type recognition, sysfs naming and decode across
  every known bank type (see below).
* `smca_thr_interrupt.py` - SMCA Corrected Error Interrupt support
  (see "SMCA Corrected Error Interrupt test" at the end of this file).

# AMD SMCA bank types test

`smca_bank_types.py` validates the kernel's Scalable MCA (SMCA) bank-type
handling across **every known bank type** - the full `smca_hwid_mcatypes[]` /
`smca_names[]` tables (`arch/x86/kernel/cpu/mce/amd.c`) and `smca_long_names[]`
(`drivers/edac/mce_amd.c`). This supersedes the earlier new-bank-types-only test
and covers, among others, the types added by commit `b90d398138ab`
("x86/mce, EDAC/mce_amd: Add new SMCA bank types").

## What it checks

An SMCA bank is identified at boot by reading its `MCA_IPID` MSR and matching the
`(HWID, McaType)` tuple against `smca_hwid_mcatypes[]`. A recognised bank gets a
**short name** (its threshold sysfs directory) and a **long name** (printed by
the EDAC decoder). An unrecognised bank instead appears as `th_bank_<N>` and is
not decoded.

The suite is a collection of sub-tests:

* `test_machinecheck_sysfs_exists` - foundational check that runs first: the
  `/sys/devices/system/machinecheck/` base and per-CPU `machinecheck<cpu>` dirs
  must exist (FAIL if missing). The per-bank threshold directories depend on
  `CONFIG_X86_MCE_THRESHOLD`, so their absence is a CANCEL (not applicable).
* `test_no_unrecognized_banks` - fails if any populated MCA bank is exposed as a
  `th_bank_<N>` directory. Portable; runs on any SMCA system.
* `test_bank_sysfs_names` - detects every known bank type present from its
  threshold sysfs directory name and verifies the expected short name. Reports
  coverage (which known types were / were not seen). When MSRs are readable
  (root or passwordless sudo) it additionally performs the authoritative
  `(HWID,McaType) -> name` cross-check against each bank's `MCA_IPID`.
* `test_bank_decode` - software-injects a corrected error into each present known
  bank via `/sys/kernel/debug/mce-inject` and confirms the decoder prints the
  expected long name (e.g. `MPRAS Unit Ext. Error Code:`) in `dmesg`. Types with
  no kernel long name (`ma_llc`, `usr_cp`, `usr_dp`) and `reserved` are skipped.

Note on dependencies: Avocado runs each `test_*` method independently, with no
inter-method ordering or skip-on-failure. To avoid a dependent test passing
vacuously when the interface is absent, the sysfs-based tests share a
`_require_threshold_sysfs()` precondition that CANCELs when no threshold bank
directories exist - so an unsupported system reports CANCEL consistently rather
than a misleading PASS.

## Requirements

* AMD EPYC / Ryzen with `X86_FEATURE_SMCA` (`smca` in `/proc/cpuinfo` flags).
* The avocado process does **not** need to run as root: privileged operations
  (MSR reads via `dd` on `/dev/cpu/*/msr`, debugfs/`/dev/kmsg` writes via `tee`,
  `dmesg`) are performed through non-interactive `sudo -n`, which **never
  prompts**. The sysfs existence/naming checks invoke no sudo at all (MSR access
  is probed lazily). With **passwordless sudo** the MSR cross-check and decode
  test run; without it those steps degrade cleanly to a skip/CANCEL. Running the
  whole job as root also works.
* No extra userspace package is required: MSRs are read from `/dev/cpu/*/msr`
  with coreutils `dd`. Only the kernel `msr` driver is needed; it is loaded
  automatically via `sudo -n modprobe msr`.
* Kernel config: `CONFIG_X86_MSR` (MSR cross-check / decode), `CONFIG_X86_MCE_AMD`,
  `CONFIG_EDAC_DECODE_MCE` (mce_amd decoder), and `CONFIG_X86_MCE_INJECT` for the
  decode sub-test.
* `debugfs` mounted at `/sys/kernel/debug` (for the decode sub-test).

## Inputs (`smca_bank_types.py.data/smca_bank_types.yaml`)

* `smca_banks` - the full `(HWID, McaType) -> sysfs/long name` table, one row per
  tuple. `longname: null` marks types with no kernel decode long name (`ma_llc`,
  `usr_cp`, `usr_dp`) or the special `reserved` type; decode is skipped for them.
  Update this list as bank types are added/changed upstream. The `.py` carries an
  identical default, so the test runs without `-m`.
* `status` - `MCi_STATUS` value used for the decode-only injection (default `0x0`;
  the injector sets the `VAL` bit automatically).

## Coverage note

`decode_smca_error()` uses the boot-cached hardware bank type, not the injected
IPID, so a type's long name and the decode check are only exercised on hardware
that physically implements that bank. Bank types absent from the system under
test are reported (logged), not failed - a given part exercises the subset of
the full table that it implements.

## Running

```bash
# whole suite (sysfs checks unprivileged; MSR/decode use passwordless sudo):
avocado run --max-parallel-tasks=1 ras/amd/smca_bank_types.py \
    -m ras/amd/smca_bank_types.py.data/smca_bank_types.yaml

# a single sub-test:
avocado run "ras/amd/smca_bank_types.py:SmcaBankTypes.test_bank_sysfs_names"
```

## Note
SMCA bank-type coverage may vary on AMD EYPC server platforms due to bank availability differences across processor models.
Some bank-type tests may cancell because the corresponding SMCA banks are not present on the system. Since bank availability
is hardware-dependent, certain banks may exist on some AMD EPYC servers while being unavailable on others. As a result, tests
associated with unavailable banks are cancelled.

---

# SMCA Corrected Error Interrupt test

`smca_thr_interrupt.py` validates commit `4efaec6e16c2`
("x86/mce/amd: Support SMCA Corrected Error Interrupt").

On Scalable MCA systems the platform may manage the MCA thresholding limit and
send the MCA Thresholding interrupt to the OS. `smca_configure()` implements the
handshake with two `MCA_CONFIG` bits:

| Bit | Name | Direction | Meaning |
|-----|------|-----------|---------|
| 10 | `IntPresent` | platform -> OS | bank can send the interrupt without OS-initialized thresholding |
| 40 | `IntEn` | OS -> platform | the OS is ready to handle it |

The kernel sets `IntEn` (and adds the bank to `thr_intr_banks`) for every bank
advertising `IntPresent`, provided the threshold vector was installed in the
APIC LVT (`thr_intr_en`, from `smca_enable_interrupt_vectors()`).

## Sub-tests

* `test_config_int_enabled` - the primary, deterministic check, requiring no
  error injection: for every sampled CPU and bank, `IntPresent` set implies
  `IntEn` set. Reports how many banks advertise `IntPresent`; CANCELs if none do
  (the platform does not use platform-managed thresholding). Banks with `IntEn`
  set but `IntPresent` clear are logged as platform-preset, not failed - the
  kernel never creates that combination.
* `test_apic_lvt_vector_assigned` - corroborating boot evidence that the
  threshold vector (`THRESHOLD_APIC_VECTOR`, `0xf9`) was assigned an APIC LVT
  offset, logged by `reserve_eilvt_offset()` as
  `LVT offset <N> assigned for vector 0xf9`. Since the kernel only sets `IntEn`
  when that vector was installed, the message and the MSR state must agree:
  banks advertising `IntPresent` with no such message is a FAIL. If the kernel
  log no longer contains boot messages (ring buffer wrapped) the result is
  CANCEL (inconclusive) rather than a false failure.

## Requirements

* AMD with `smca` **and `succor`** in `/proc/cpuinfo` flags - `thr_intr_en` is
  never set without SUCCOR, so the feature would be inapplicable.
* `CONFIG_X86_MSR` (MSR reads), `CONFIG_X86_MCE_AMD`, `CONFIG_X86_MCE_THRESHOLD`.
* Passwordless sudo (or root). MSRs are read with `sudo -n dd` on
  `/dev/cpu/*/msr` - no `msr-tools` needed; `dmesg` also runs under `sudo -n`.

## Inputs (`smca_thr_interrupt.py.data/smca_thr_interrupt.yaml`)

* `int_present_bit` / `int_en_bit` - MCA_CONFIG bit positions (10 / 40).
* `threshold_vector` - `THRESHOLD_APIC_VECTOR` (`0xf9`), used to match the boot
  message.
* `max_cpus` - number of MCE-capable CPUs to sample for the per-CPU/per-bank MSR
  sweep (default 8; `0` = every CPU). A full sweep is one MSR read per bank per
  CPU, i.e. tens of thousands of reads on a 1000+ CPU system. Sampling is always
  reported in the log, never silent.

## Limitations

`thr_intr_banks` is kernel-internal and not exposed to userspace, so it cannot
be asserted directly. The platform actually *sending* the interrupt when its
threshold is reached cannot be forced from the OS either; validating that path
requires firmware-side stimulus.

## Running

```bash
avocado run --max-parallel-tasks=1 ras/amd/smca_thr_interrupt.py \
    -m ras/amd/smca_thr_interrupt.py.data/smca_thr_interrupt.yaml
```
