---- 5-Level Page Table Support on AMD EPYC hardware ----

** Address Space Extension with 5-level page table **
This feature increases the virtual address (VA) space from 48 bits (256 TB) to 57 bits (128 PB).

** 5-Level Page Table Support **
The 5-level page table feature is supported starting from AMD EPYC Genoa+ platforms, based on the ZEN4 microarchitecture.

** Platform and Kernel Requirements **

	- Hardware: Requires Genoa(ZEN4 based) or newer EPYC processors.

	- Kernel: Must be built with CONFIG_X86_5LEVEL=y to enable 5-level paging.

** Test Coverage **
The page_table.py test suite includes:

- Feature Detection Tests: cpuid and kernel config checking
- Functionality Tests: Covers validating page table behavior on Linux, covers for 5-level and 4-level.

** Expected Behavior on Systems Without 5-Level Page Table Support **

On platforms where 5-level page table support is unavailable, either due to:
	- Hardware limitations (i.e., only 4-level paging is supported), or

	- Kernel configuration does not enable CONFIG_X86_5LEVEL,

        the expected test behavior is as follows:

	- CPUID checks, 5-level detection tests, and kernel config validation tests marked as cancelled, since the 5-level paging feature
          is not supported or enabled.

	- Page table functionality tests will still execute normally using 4-level page tables, ensuring compatibility and test coverage on such systems.
