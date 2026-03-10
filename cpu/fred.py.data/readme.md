# FRED Feature Validation Test

## Overview
This test verifies **FRED (Flexible Return and Event Delivery)** enablement on AMD platforms.
This test performs staged checks to ensure the environment supports FRED.

## Validation Workflow
The test runs in the following order:

1. **CPU Vendor**
   - Confirms the system reports `AuthenticAMD`.
   - If not AMD → test is skipped.

2. **CPUID Check**
   - Reads CPUID leaf `0x7`, subleaf `0x1`.
   - Ensures **EAX bit 17** is set.
   - If missing → test is canceled.

3. **CPU Flags**
   - Checks `/proc/cpuinfo` for the `fred` flag.
   - If missing → test is canceled.

4. **Kernel Config**
   - Verifies `CONFIG_X86_FRED=y` in booted kernel config.
   - If not set → test is canceled.

5. **Kernel Command Line**
   - Confirms `fred=on` is present in kernel boot parameters.
   - If missing → test is canceled.

6. **Logs and CPU Count**
   - This test checks if FRED is initialized and for all CPUs on the system. If not, test fails.

## Usage
Run with Avocado:
```bash
avocado run avocado-misc-tests/cpu/fred.py
```
