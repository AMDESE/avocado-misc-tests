# CXL - Compress Express Link
Compute Express Link (CXL) is an open standard interconnect for high-speed, high capacity CPU-to-device and CPU-to-memory connections, designed for high
performance data center computers. CXL is built on the PCIe physical layer to add memory coherency and cache-based access for more efficient data sharing
between CPUs and accelerators, while PCIe is a general-purpose interface for a wide range of peripherals.

References:
- CXL 3.2 Specification: https://computeexpresslink.org/cxl-specification/
	- CXL 3.2 1.0-4 "Introduction"
	- CXL 3.2 2.3 "CXL Type 3 Device"
- Linux kernel documentation for the driver: https://docs.kernel.org/driver-api/cxl/index.html

# CXL Testing Overview
CXL testing is divided into two main categories:
1. Emulated CXL device tests – execute using the ndctl utility/tool and depend on kernel cxl selftest modules.
2. Physical CXL device tests – execute directly on systems equipped with a CXL card.

# Emulated CXL Device Testing
  The CXL test suite includes platform device tests where CXL devices are emulated, and these emulated device tests are executed using the ndctl utility.
  The test suite depends on the kernel CXL selftest modules (located under tools/testing/cxl in the kernel source) being built and set up to enable running
  the emulated CXL tests.

  # Prerequisites and Setup
  1. Clone the Linux source - v6.18.1 or later stable release

  2. Build the kernel with the following CXL-related configuration options enabled:
     CONFIG_CXL_BUS=m
     CONFIG_CXL_PCI=m
     CONFIG_CXL_ACPI=m
     CONFIG_LIBNVDIMM=m
     CONFIG_CXL_PMEM=m
     CONFIG_CXL_MEM=m
     CONFIG_CXL_PORT=m
     CONFIG_CXL_REGION=y
     CONFIG_CXL_REGION_INVALIDATION_TEST=y
     CONFIG_CXL_FEATURES=y
     CONFIG_DAX=m
     CONFIG_TRANSPARENT_HUGEPAGE=y
     CONFIG_DEV_DAX=m
     CONFIG_DEV_DAX_CXL=m
     CONFIG_MEMORY_HOTPLUG=y
     CONFIG_MEMORY_HOTREMOVE=y
     CONFIG_NVDIMM_SECURITY_TEST=y
     CONFIG_ENCRYPTED_KEYS=y
     CONFIG_NVDIMM_KEYS=y

     Recommendation: Use the reference host kernel configuration from the elves test project:
            https://github.com/AMDESE/elves/blob/master/reference_kconfig/host_kconfig

    After building and installing the kernel, ensure the above configurations are active in the running kernel.

  3. Build and load CXL modules
     Load the CXL modules required for running the test suites:
     # cd <linux_source>
     # make M=tools/testing/cxl/
     # make M=tools/testing/cxl modules_install
     # make modules_install
     # update-grub2
     # reboot

  4. Run the Avocado CXL test suite - Emulated CXL tests
     Use the avocado framework to run the emulated CXL tests:
     # avocado run cxl_test.py:cxl_test.test_ndctl_cxl

     # Example output: cxl_test.py:cxl_test.test_ndctl_cxl
	root@xxxx:~/elves/tests/avocado-misc-tests/cxl# avocado run cxl_test.py:cxl_test.test_ndctl_cxl
	JOB ID     : fd042bdfc16fd043ad31542edc372022d6e65cf2
	JOB LOG    : /root/elves/results/job-2025-11-25T04.11-fd042bd/job.log
	 (1/1) cxl_test.py:cxl_test.test_ndctl_cxl: STARTED
	 (1/1) cxl_test.py:cxl_test.test_ndctl_cxl: PASS (36.05 s)
	RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
	JOB HTML   : /root/elves/results/job-2025-11-25T04.11-fd042bd/results.html
	JOB TIME   : 39.88 s

     # Sample CXL emulated tests debug log
        1/12 ndctl:cxl / cxl-topology.sh               OK               3.28s
        2/12 ndctl:cxl / cxl-region-sysfs.sh           OK               2.50s
        3/12 ndctl:cxl / cxl-labels.sh                 OK               2.32s
        4/12 ndctl:cxl / cxl-create-region.sh          OK               4.85s
        5/12 ndctl:cxl / cxl-xor-region.sh             OK               2.64s
        6/12 ndctl:cxl / cxl-events.sh                 OK               2.09s
        7/12 ndctl:cxl / cxl-sanitize.sh               OK               5.01s
        8/12 ndctl:cxl / cxl-destroy-region.sh         OK               2.08s
        9/12 ndctl:cxl / cxl-qos-class.sh              OK               2.17s
        10/12 ndctl:cxl / cxl-security.sh              OK               1.02s
        11/12 ndctl:cxl / cxl-features.sh              OK               0.76s
        12/12 ndctl:cxl / cxl-poison.sh                OK               4.84s

        Ok:                 12
        Expected Fail:      0
        Fail:               0
        Unexpected Pass:    0
        Skipped:            0
        Timeout:            0

        Full log written to /<xxxx>/ndctl/build/meson-logs/testlog.txt

# Physical CXL Device Testing
  CXL device testing include tests that can be run on the physical CXL-2.0/3.0 card. These tests supported on ZEN 5 onwards EYPC platform.
  The system must have configured with CXL 2.0 card and required BIOS should be enabled.

  # Prerequisites and Setup
  1. BIOS settings on ZEN 5 (Turin):
     Advanced -> AMD CBS -> CXL Common Options:
		CXL Control -> Enabled
		CXL Physical Addressing -> System address
		CXL Memory Attribute -> Enabled
		CXL Memory Online/Offline -> Enabled

  2. Tests includes:
     cxl-numa.py: Tests NUMA node set up for CXL nodes.

     daxctl.py: Tests verifying DAX setup is correct.

     driver-basic.py: Tests checking whether the CXL driver successfully loaded, enumerated, and set up present CXL type 3 devices.

  3. Run the Avocado CXL tests - cxl_test.py
     # avocado run cxl_test.py
     # Example output for pass case:
	root@xxxx:~/elves/tests/avocado-misc-tests/cxl# avocado run cxl_test.py
	JOB ID     : 912602d071190e3186f79ed1ccaf78dad517e375
	JOB LOG    : /root/elves/results/job-2025-12-03T04.56-912602d/job.log
	 (1/4) cxl_test.py:cxl_test.test_cxl_numa: STARTED
	 (1/4) cxl_test.py:cxl_test.test_cxl_numa: PASS (3.28 s)
	 (2/4) cxl_test.py:cxl_test.test_daxctl: STARTED
	 (2/4) cxl_test.py:cxl_test.test_daxctl: PASS (3.14 s)
	 (3/4) cxl_test.py:cxl_test.test_driver_basic: STARTED
	 (3/4) cxl_test.py:cxl_test.test_driver_basic: PASS (3.54 s)
	 (4/4) cxl_test.py:cxl_test.test_ndctl_cxl: STARTED
	 (4/4) cxl_test.py:cxl_test.test_ndctl_cxl: PASS (37.43 s)
	RESULTS    : PASS 4 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
	JOB HTML   : /root/elves/results/job-2025-12-03T04.56-912602d/results.html
	JOB TIME   : 192.90 s

     If the tests are executed on a system without a CXL card, they will be cancelled. Sample cancelled tests:
     # Example output for a cancelled case in CXL device testing.
     # These tests were run on a system where no CXL card was present.
	root@xxxx:~/elves/tests/avocado-misc-tests/cxl# avocado run cxl_test.py
	JOB ID     : 5a3b29bf1eb67e4c504f49336d22b8d112fbd242
	JOB LOG    : /root/elves/results/job-2025-12-03T05.53-5a3b29b/job.log
	 (1/4) cxl_test.py:cxl_test.test_cxl_numa: STARTED
	 (1/4) cxl_test.py:cxl_test.test_cxl_numa: CANCEL:  No CXL devices present, check the debug log (30.02 s)
	 (2/4) cxl_test.py:cxl_test.test_daxctl: STARTED
	 (2/4) cxl_test.py:cxl_test.test_daxctl: CANCEL:  No CXL devices present, check the debug log (2.40 s)
	 (3/4) cxl_test.py:cxl_test.test_driver_basic: STARTED
	 (3/4) cxl_test.py:cxl_test.test_driver_basic: CANCEL:  No CXL devices present, check the debug log (2.43 s)
	 (4/4) cxl_test.py:cxl_test.test_ndctl_cxl: STARTED
	 (4/4) cxl_test.py:cxl_test.test_ndctl_cxl: PASS (36.30 s)
	RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 3
	JOB HTML   : /root/elves/results/job-2025-12-03T05.53-5a3b29b/results.html
	JOB TIME   : 82.56 s
#EOF
