#!/usr/bin/env python3
###
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Author: Ben Cheatham <Benjamin.Cheatham@amd.com>
# Module Name: driver-basic.py
# History: Nov 10 2025 - Created
#
# Tests checking whether the CXL driver successfully loaded, enumerated,
# and set up present CXL type 3 devices.
#
# Assumptions:
# - CXL card memory is managed by CXL driver
# - CXL regions are pre-programmed by BIOS
#
# Success case:
# - All cxl_memdevs are present and part of a CXL region
#
# Testing Environment:
# - At least one CXL 2.0+ type 3 card is installed
# - "lspci" and "cxl" commands are installed
# - Test is run as root
# - BIOS settings:
#   + Physical addressing = System Address
#   + CXL Memory Attribute/Specific Purpose Memory = Enabled
###

from uefi import UefiSetting
import subprocess as sp
import json


def lspci_get_cxl_devs():
    out = sp.run(["lspci", "-d", "::0502"], capture_output=True).stdout.decode()
    return out.splitlines()

def bios_settings_set():
    addressing = UefiSetting({"CXL Physical Addressing": "System address"})
    spm = UefiSetting({"CXL Memory Attribute": "Enabled"})
    if addressing is None or spm is None:
        return None

    aset = addressing.is_set()
    sset = spm.is_set()
    if aset is None or sset is None:
        return None

    return aset and sset

### JSON UTILITY FUNCTIONS ###


def get_memdevs():
    try:
        list_out = sp.run(["cxl", "list", "-M"], capture_output=True).stdout
        return json.loads(list_out)
    except Exception:
        return {}


def get_regions():
    try:
        list_out = sp.run(["cxl", "list", "-R"], capture_output=True).stdout
        return json.loads(list_out)
    except Exception:
        return {}


def get_endpoints():
    try:
        list_out = sp.run(
            ["cxl", "list", "-P", "-p", "endpoint", "-D", "-d", "endpoint"],
            capture_output=True,
        ).stdout
        return json.loads(list_out)
    except Exception:
        return {}


### CXL MEMDEV UTILITY FUNCTIONS ###


def cxl_memdev_exists(memdevs, sbdf):
    try:
        for dev in memdevs:
            if dev["host"] == sbdf:
                return True

        return False
    except Exception:
        return False


### CXL MEMDEV TESTS ###


# Tests whether there's an associated cxl_memdev for each CXL device in "lspci"
# Returns the SBDF of the first CXL device that's missing a cxl_memdev
def each_cxldev_has_memdev(memdevs):
    for line in lspci_get_cxl_devs():
        sbdf = "0000:" + str(line).split()[0]
        if sbdf and not cxl_memdev_exists(memdevs, sbdf):
            print(f'FAIL: CXL device "{sbdf}" is missing a CXL memdev')
            return False

    return True


# Tests whether CXL.mem is enabled for a CXL memory device
def cxl_mem_enabled(memdev):
    if "host" not in memdev:
        return False

    lspci = sp.run(
        ["lspci", "-vv", "-s", memdev["host"]], capture_output=True
    ).stdout.decode()
    idx = lspci.find("CXLCap:")

    if idx == -1:
        return False

    cxl_cap = lspci[idx:].splitlines()[0]
    return "Mem+" in cxl_cap


def cxl_memdev_in_region(memdev):
    endpoints = get_endpoints()
    regions = get_regions()

    for ep in endpoints:
        if ep["host"] != memdev["memdev"]:
            continue

        name = ep["endpoint"]
        ep_decoders = ep[f"decoders:{name}"]
        for decoder in ep_decoders:
            if decoder["region"] not in [r["region"] for r in regions]:
                return False

    return True


if __name__ == "__main__":
    if len(lspci_get_cxl_devs()) == 0:
        print("CANCEL: No CXL devices present")
        exit(0)

    settings = bios_settings_set()
    if settings is None:
        print("WARNING: Couldn't verify required BIOS settings, may affect test outcome")
    elif not settings:
        print("CANCEL: Required BIOS settings not set")
        exit(0)

    memdevs = get_memdevs()
    if not each_cxldev_has_memdev(memdevs):
        exit(1)

    print("PASS: All CXL devices have an associated memdev")

    for dev in memdevs:
        if not cxl_mem_enabled(dev):
            print(f"CXL.mem not enabled for {dev['memdev']}")
            exit(1)

    print("PASS: CXL.mem enabled for all CXL devices")

    for dev in memdevs:
        if not cxl_memdev_in_region(dev):
            print(f"{dev['memdev']} not in a CXL region")
            exit(1)

    print("PASS: All CXL memdevs in a CXL region")
