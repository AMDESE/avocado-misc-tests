#!/usr/bin/env python3
###
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Author: Ben Cheatham <Benjamin.Cheatham@amd.com>
# Module Name: cxl-numa.py
# History: Nov 10 2025 - Created
#
# Tests NUMA node set up for CXL nodes
#
# Assumptions:
# - CXL memory doesn't share CPU NUMA node(s)
# - At least one initially memoryless NUMA node is created for the CXL memory
#
# Success Case:
# - CXL memory shows up in multiple tools and is "correctly" configured
#
# Tests:
# - CXL memory shows up in lsmem and numactl (online or offline)
#
# Testing environment:
# - At least one CXL 2.0+ type 3 card is installed
# - "numactl" installed
# - "lsmem" installed
# - Test is run as root
###

import subprocess as sp
from time import sleep
import json
import re


def lspci_get_cxl_devs():
    out = sp.run(["lspci", "-d", "::0502"], capture_output=True).stdout.decode()
    return out.splitlines()


def online_memory():
    try:
        devices = json.loads(sp.run(["daxctl", "list"], capture_output=True).stdout.decode())
        for dev in devices:
            if not ("online_memblocks" in dev and dev["total_memblocks"] == dev["online_memblocks"]):
                sp.run(["daxctl", "online-memory", dev["chardev"]]).check_returncode()

                # Onlining memory too quickly causes a warning
                sleep(0.5)

        return True
    except Exception:
        return False

def convert_unit(unit):
    if unit == "KB":
        pow = 1
    elif unit == "MB":
        pow = 2
    elif unit == "GB":
        pow = 3
    elif unit == "TB":
        pow = 4
    else:
        pow = 0

    return 1024**pow


class Node:
    def __init__(self, id):
        self.id = id
        self.ranges = []
        self.size = 0

    def get_mem(self, dmesg):
        for line in dmesg:
            if line.startswith(f"ACPI: SRAT: Node {self.id}"):
                mem = line.split()[7][:-1]
                start = int(mem.split("-")[0], 16)
                stop = int(mem.split("-")[1], 16)
                self.size += stop - start
                self.ranges.append(range(start, stop))


def get_dmesg():
    return (
        sp.run(["dmesg", "--notime"], capture_output=True).stdout.decode().splitlines()
    )


def build_memoryless_nodes(dmesg):
    nodes = [
        Node(int(line.split()[3]))
        for line in dmesg
        if line.startswith("Initmem") and "memoryless" in line
    ]

    for n in nodes:
        n.get_mem(dmesg)

    return nodes


def check_numactl(nodes):
    mem_online = online_memory()
    numactl = (
        sp.run(["numactl", "-H"], capture_output=True).stdout.decode().splitlines()
    )

    for node in nodes:
        for line in numactl:
            if line.startswith(f"node {node.id} cpus:") and line.split()[-1] != "cpus:":
                print("FAIL: CXL memory should have no cpus")
                return False

            if not mem_online:
                print("Memory not online, skipping numactl node size check")
                continue

            if line.startswith(f"node {node.id} size:"):
                parts = line.split()
                size = int(parts[-2]) * convert_unit(parts[-1])

                # Size of the free memory can be off by a bit in numactl
                if size < (node.size - 1024) or size > (node.size + 1024):
                    print(
                        f"FAIL: Numa node size is incorrect (numactl size: {size}, node {node.id} size: {node.size}"
                    )
                    return False

    return True


def range_contains(a, b):
    return a.start <= b.start and a.stop >= b.stop


def range_to_str(r):
    return "0x{:x}-0x{:x}".format(r.start, r.stop)


def check_lsmem(nodes):
    lsmem = (
        sp.run(["lsmem", "-o", "range"], capture_output=True)
        .stdout.decode()
        .splitlines()
    )

    ranges = [
        range(int(line.split("-")[0], 16), int(line.split("-")[1].rstrip(), 16))
        for line in lsmem if re.search("0x[0-9a-f]+-0x[0-9a-f]+", line)
    ]

    for node in nodes:
        for nr in node.ranges:
            if not any([range_contains(r, nr) for r in ranges]):
                print(f"FAIL: Node {node.id}: memory ({range_to_str(nr)}) not in lsmem")
                return False

    return True


if __name__ == "__main__":
    if len(lspci_get_cxl_devs()) == 0:
        print("CANCEL: No CXL devices present")
        exit(0)

    nodes = build_memoryless_nodes(get_dmesg())

    if not check_numactl(nodes):
        exit(1)

    print("PASS: CXL NUMA nodes correctly configured")

    if not check_lsmem(nodes):
        exit(1)

    print("PASS: CXL memory present in lsmem")
