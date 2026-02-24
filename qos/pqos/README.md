# AMD Quality Of Server(QOS) or Platform Quality Of Service(PQOS)
AMD Quality of Service(PQoS or just QoS) is intended to provide the interface for the monitoring of the usage of
certain system resources by one or more processors and also provide the interface for allocation of limits on the
use of certain system resources. These technologies enable tracking and control of shared resources, such as the
Last Level Cache (LLC) and main memory (DRAM) bandwidth, in use by many applications, containers or VMs running on
the platform concurrently.

Quality of Service (QOS) features defined and implemented by the Cache Hierarchy to support the AMD64 Platform
Quality of Service Features. The QOS features provide mechanisms for the user to monitor shared resource utilization and,
separately, enforce limits on those shared resources. These QOS features operate in a QOS Domain of the Core Complex (CCX).
The shared resources monitored and controlled are L3 Cache Occupancy and L3 System Memory Bandwidth. The capabilities of
feature set are enumerated through CPUID identifiers so that software can easily support multiple instances of the feature.
The CPUID identifiers indicate the presence of MSR’s used to interact with the QOS features.

QoS ABMC - Assignable Bandwidth Monitoring Counters (ABMC), also referred as RMID Pinning
This enable users to explicitly assign hardware counters to RMID-event pairs, a practice also called QoS RMID pinning.
This practice guarantees that hardware continuously tracks the assigned RMID until it is explicitly unassigned.

Links:
https://www.kernel.org/doc/Documentation/x86/resctrl.rst
https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/programmer-references/40332.pdf
https://docs.amd.com/api/khub/documents/VuNrmUG_yfhPVgGYcFlkZg/content
https://docs.amd.com/v/u/en-US/40332-PUB_4.08

# Linux QoS Interfaces
QoS functionality can be achieved by following interfaces:
a. CPUID check for feature support
b. MSR interface
c. Sysfs interface
d. Intel CMT(Cache Monitoring Technology) and CAT(Cache Allocation Technology) interface i.e pqos tool/utility developed by Intel
	Reference: https://eci.intel.com/docs/3.0.1/development/intel-pqos.html

# Pre-requisites
1. Install pqos tool i.e 'intel-cmt-cat', follow below steps
   # apt-get install intel-cmt-cat(this will install distro specific intel-cmt-cat package)
   # Verify 'pqos' command works
            # pqos
2. Install msr-tools
   # apt-get install msr-tools(this will install distro specific msr-tools)

3. Ensure the booted kernel is built with config - "CONFIG_X86_CPU_RESCTRL=y".

# Notes
1. avocado run with --max-parallel-tasks=1 <.py>
   pqos avocado tests mandate to run with "--max-parallel-tasks=1" which runs the tests sequentially. This ensures pqos test case dependencies
   are handled.

2. pqos tests should be run with supervisor permission(ex: the root user).

3. Tests like sysfs-qos-llc-test.py, look for "resctrl" in the boot time dmesg log. If the boot time dmesg is cleared or has truncted log may cause
   failure in the test case, hence now a check has been added to look for "resctrl" in 'journalctl' log in addition to dmesg log.

# QoS feature testing coverage
a. Memory bandwidth monitoring
b. Memory bandwidth control
c. L3 cache occupancy monitoring
d. L3 cache allocation control
e. Assignable Bandwidth Monitoring Counters (ABMC) support also known as RMID Pinning

# PQOS tests
Avocado framework is used to run "pqos" tests. Setup avocado and install pqos tool, cpuid, msr-tools for tests to run successfully.
The following tests are covered as part of PQOS.
1. qos.py: CPUID feature check and MSR check tests
   # avocado run --max-parallel-tasks=1 qos.py
2. qos-llc-test.py: Detect L3 Cache Alloaction and check if able to set up allocation COS and test reset COS
   # avocado run --max-parallel-tasks=1 qos-llc-test.py
3. qos-mbm-test.py: Checks for Memory Bandwidth Allocation detection and control feature
   # avocado run --max-parallel-tasks=1 qos-mbm-test.py
4. sysfs-qos-llc-test.py: Check resource control support(Resctrl), mount, allocate half cache and validate the feature
   # avocado run --max-parallel-tasks=1 sysfs-qos-llc-test.py
5. sysfs-qos-mbm-test.py: Checks for resctrl support and detect for L3 resctrl
   # avocado run --max-parallel-tasks=1 sysfs-qos-mbm-test.py
6. sysfs-qos-rmid-pin-test.py: Detect ABMC feature (also called as RMID Pinning) support by checking for assignable monitoring support mode([mbm_event]),
	checks for total number of assignable counters and number of counters available for assignment. Also, tests for assign/unassign a MBM event
        across the domains.

# Known Issues
1. intel-cmt-cat tool issue
   Systems with over 300 CPUs may encounter pqos test failures due to an issue with the 'intel-cmt-cat' tool package (version 5.0.0) installed from
   the Linux distribution. The issue is resolved in the upstream version (6.0.0) of the 'intel-cmt-cat' tool. Installing the upstream version is
   recommended for successful pqos tests.
         Upstream intel-cmt-cat: https://github.com/intel/intel-cmt-cat/$

         Steps to build and install upstream 'intel-cmt-cat' tool on Ubuntu 24.04:
               # git clone https://github.com/intel/intel-cmt-cat.git$
               # cd intel-cmt-cat
               # make; make install

2. Issue with pqos lock file, /var/lock/libpqos
   Verify if the lock file "/var/lock/libpqos" exists and is owned by a non-root user. If it does, remove "/var/lock/libpqos" before running the
   pqos tests, as a lock file owned by a non-root user will cause the pqos tests to fail.
               # ls -l /var/lock/libpqos
                 -rw-r--r-- 1 amd amd 0 Mar  7 04:27 /var/lock/libpqos
               # rm /var/lock/libpqos
3. Expected Failure:
   In cache allocation tests (particularly test_pqos_mbm_monitor), reported total memory bandwidth may intermittently not align with the memory
   bandwidth limit set during the test, causing the test to fail. This is under investigation.
#EOF
