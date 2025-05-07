# AMD Bus Lock Trap
AMD Bus Lock Trap feature allows OSes to trap after every buslock, which allows them to limit how many buslocks are occurring in a system.
The Bus Lock Trap is any atomic operation whose operand crosses two cache lines. Since the operand spans two cache lines and the operation
must be atomic, the system locks the bus while the CPU accesses the two cache lines.

# Hardware Support
Bus Lock Trap feature is supported from Turin+ (Breithorn-C0/C1 or Breithorn-Dense).

# Linux Upstream Kernel Support
The feature is supported from upstream kernel v6.14 or greater.

# How to run tests
Avocado framework is used to run buslock trap test.
   # cd avocado-misc-tests/buslock
   # avocado run --max-parallel-tasks=1 bus_lock_trap.py
