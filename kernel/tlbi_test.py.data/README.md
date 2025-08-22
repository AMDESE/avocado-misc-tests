# TLBI - Translation Look-aside Buffer Invalidation
TLBI is a broadcast TLB invalidation feature introduced in AMD processors starting with EPYC Zen 3.
This feature allows the kernel to invalidate TLB entries on remote CPUs without sending IPIs and without waiting for remote CPUs to handle interrupts,
while still ensuring the operation is synchronized across all remote CPUs.

# Testing
- The TLBI test detects feature support by checking CPUID_80000008_EBX[3].
- If TLBI is not detected, the test will cancel.
- If the feature is detected, the test additionally verifies whether the kernel is built with CONFIG_BROADCAST_TLB_FLUSH to confirm TLBI is enabled
  at the kernel level.
