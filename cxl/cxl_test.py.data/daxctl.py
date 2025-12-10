#!/bin/python3
###
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Author: Ben Cheatham <Benjamin.Cheatham@amd.com>
# Module Name: daxctl.py
# History: Nov 10 2025 - Created
#
# Tests verifying DAX setup is correct
#
# Assumptions:
# - CXL device memory is managed by CXL driver
# - At least one DAX device per CXL region
#
# Success case:
# All CXL memory is enabled (not necessarily onlined) and available
# through a DAX mapping
#
# Testing Environment:
# - At least one CXL 2.0+ type 3 card is installed
# - "daxctl" and "lspci" commands are installed
# - Test is run as root
###

import subprocess as sp
import os.path as op
import json
import os


def lspci_get_cxl_devs():
    out = sp.run(["lspci", "-d", "::0502"], capture_output=True).stdout.decode()
    return out.splitlines()


def get_daxdevs():
    try:
        dax = sp.run(["daxctl", "list"], capture_output=True).stdout
        return json.loads(dax)
    except Exception:
        return {}


def matching_regions():
    bus_path = "/sys/bus/cxl/devices"
    cxl_regions = [r for r in os.listdir(bus_path) if r.startswith("region")]

    for cxl_region in [op.join(bus_path, r) for r in cxl_regions]:
        with open(op.join(cxl_region, "size")) as cxl_sf:
            cxl_size = int(cxl_sf.read().strip(), 16)

        dax_regions = [
            op.join(cxl_region, de + "/dax_region")
            for de in os.listdir(cxl_region)
            if de.startswith("dax_region")
        ]

        dax_size = 0
        for dr in dax_regions:
            with open(op.join(dr, "size")) as dax_sf:
                dax_size += int(dax_sf.read().strip())

        if dax_size != cxl_size:
            print(
                f"FAIL: DAX region size ({dax_size:x}) != CXL region size ({cxl_size:x})"
            )
            return False

    return True


def daxdev_disabled(dev):
    if "state" in dev and dev["state"] == "disabled":
        print(f"FAIL: DAX device {dev['chardev']} disabled")
        return True

    return False


if __name__ == "__main__":
    if len(lspci_get_cxl_devs()) == 0:
        print("CANCEL: No CXL devices present")
        exit(0)

    if not matching_regions():
        exit(1)
    else:
        print("PASS: CXL region sizes match DAX region sizes")

    for dev in get_daxdevs():
        if daxdev_disabled(dev):
            exit(1)

    print("PASS: All DAX devices enabled")
