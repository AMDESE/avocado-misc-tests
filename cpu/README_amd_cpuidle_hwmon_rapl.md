==== AMD EYPC CPU Idle States ====
AMD EPYC Server CPUs support multiple idle states, called C-states. The cpuidle framework in Linux manages idle states (C-states)
for CPUs when they have no runnable tasks.

Idle State Support on AMD EPYC
⦁	C0 - POLL state
 	* Active polling state
 	* CPU does not actually idle but spins waiting for work
 	* Provides lowest latency but no power savings
⦁	C1 - MWAIT state
 	* Shallow idle state
 	* Halts execution while allowing quick wake-up with minimal latency
⦁	C2 - IOPORT state
 	* Represents a deeper idle state
 	* Provides additional power savings compared to C1, with slightly higher exit latency.

Kernel Drivers
⦁	acpi_idle - Primary driver on EPYC, uses ACPI _CST tables to enumerate idle states.

cpuidle sysfs Entries
⦁ System global cpuidle related information and tunables are under
 	/sys/devices/system/cpu/cpuidle
⦁ Per logical CPU specific cpuidle information are under
 	/sys/devices/system/cpu/cpuX/cpuidle
   for each online cpu X

==== PM-QOS in CPUIdle ====
Power Management QoS is a Linux kernel framework that lets drivers or user-space apps request certain performance constraints from the kernel.
The CPUIdle framework decides which C-state (idle state) a CPU should enter when idle. The cpu_dma_latency is a runtime PM-QoS knob that restricts
which CPU idle states may be entered, based on their exit latency.

Sysfs entries:
⦁	/sys/devices/system/cpu/cpuX/cpuidle/stateN/latency

==== HWMON-Powercap ====
hwmon: Hardware monitoring framework in Linux. It exposes sensors like temperature, fan speed, and power etc. under /sys/class/hwmon/.
powercap: Kernel framework for exposing power capping and energy monitoring devices and often ties to HSMP (Host System Management Port).

On AMD EPYC, hwmon + powercap entries come from the HSMP driver bound to the ACPI device AMDI0097 or AMDI0097:0x.
EPYC Genoa (Zen 4): the AMDI0097 ACPI device is not exposed. So HSMP ACPI object sysfs entries won't be seen.
EPYC Turin / Turin+ (Zen 5 or later): the ACPI AMDI0097 object is present and kernel drivers will bind, so you’ll see the sysfs nodes automatically.

hwmon-powercap sysfs paths:
⦁	hwmon: /sys/devices/platform/AMDI0097:00/hwmon/hwmonX/
⦁	powercap: /sys/devices/platform/AMDI0097:00/hwmon/hwmonX/power1_cap*

How-To enable HSMP (Host System Management Port) from BIOS:
HSMP PCIe interface needs to be enabled in the BIOS. The CBS option can be found by navigating to the following path:
Advanced > AMD CBS > NBIO Common Options > SMU Common Options > HSMP Support -> Enabled

Reference to HSMP driver - https://github.com/amd/amd_hsmp

==== AMD RAPL - Running Average Power Limit ====
RAPL interface in AMD EYPC provide measurements of energy consumption and to implement power limits at core and package levels.
The users accesses and manage RAPL energy counters via the /sys/devices/power interface.


==== Testing ====
Pre-requisites tools:
	CPUIdle, HWMON/Powercap and Rapl test cases require Perf and cpupower tools to be installed for installed kernel on the system.
	Here are the steps to build/install Perf and cpupower tool from the linux source.
	HowTo build and install cpupower and perf for custom kernel.
	# Install pre-requisite packages
	# apt-get install -y libdw-dev llvm libdebuginfod-dev libslang2-dev libpfm4-dev libnuma-dev libtraceevent-dev libperl-dev libpci-dev gettext

	# cd linux   #where linux source resides
	# Build & Install cpupower
		# make -C tools/ cpupower_install

	# Build and Install perf
		# make -C tools/ DESTDIR=/usr perf_install

1. avocado-misc-tests/cpu/em_cpuidle.py
The test will checks for "cpuidle" sub-system and validate the number of cpuidle states(3 states: C0-POLL, C1 and C2) using cpupower tool and
validate the same against sysfs entries. Also, add the functionality to verify the flags of the CPUIdle C1 and C2 states if ACPI MWAIT or
ACPI IOPORT respectively.

2. avocado-misc-tests/cpu/cpuidle-usage.py
The cpuidle usage primarily checks for supported c-states on AMD EYPC platform. This test verifies that all the supported CPUIdle states are used
and the usage stats are updated in the sysfs files. The test case selectively enables just one cstate at a time and validates that the usage counter
for that cstate is increasing (assuming the system is mostly idle at that point). Similarly, the test will disable all the idle states for a particular
CPU-X and validate that enabling/disabling has a measurable effect on usage counts.

3. avocado-misc-tests/cpu/pmqos-cpu-latency.py
The test will set different values to latency and it validates the cpu_dma_latency value is honored by the cpuidle subsystem.
Any state which has higher target residency than PMQoS latency should not be entered. So the test writes a value "x" (in ms) to the cpu_dma_latency file
and ensures that no CState which has latency greater than "x" is entered. It also validates that at least one CState with latency less than or equal to
"x" is entered during the idle period.

4. avocado-misc-tests/cpu/hwmon-powercap.py
Add a testcase to validate that the package hwmon and powercap set via the HSMP hwmon interface is being correctly enforced.

The test loads a socket with 100% busy workload and increases the powercap limit from a minimum of 250W (currently hardcoded 250W). Iteratively increase
power1_cap in steps of 25W and validates that the socket power observed via the RAPL pkg-energy counters remains within the specified powercap.

When paths are missing the test case would cancel:
⦁	If /sys/devices/platform/AMDI0097:00/ isn’t present - BIOS probably hasn’t enabled HSMP ACPI object OR installed kernel on the system does not
        exposed the hwmon sysfs entry.
⦁	Kernel must have CONFIG_AMD_HSMP=m, CONFIG_AMD_HSMP_ACPI=m, CONFIG_AMD_HSMP_PLAT=m and CONFIG_HWMON enabled
Without these, hwmon and powercap entries won’t be exposed and test would get cancelled.

5. avocado-misc-tests/cpu/rapl-pkg-energy.py
The test loads the die-groups a package one at a time and ensures that the energy consumption of the package is increasing continuously. If the energy
consumption does not increase monotonically the test declares a failure.

6. avocado-misc-tests/cpu/rapl-core-energy.py
The test case picks 5 random cores from each socket and loads them one at a time. It measures the core-energy before and after adding the load and validates
that the energy after adding the load is greater than the energy prior to loading the core.
