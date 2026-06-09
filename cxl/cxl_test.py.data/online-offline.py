#!/usr/bin/env python3
###
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Author: Ben Cheatham <Benjamin.Cheatham@amd.com>
# Module Name: online-offline.py
# History: Dec 12 2025 - Created
#
# Tests onlining and offlining CXL memory in system-ram mode and
# converting system-ram devices to devdax mode.
#
# Assumptions:
# - CXL device memory is managed by CXL driver
# - At least one DAX device is present for CXL memory
#
# Success case:
# All memory can be onlined and subsequently offlined in system-ram mode.
# All DAX devices can be converted to devdax mode and back.
#
# Testing Environment:
# - At least one CXL 2.0+ type 3 card is installed
# - Specific Purpose Memory (SPM) is enabled
# - "daxctl" and commands is installed
# - Test is run as root
###

from shutil import which
import subprocess as sp
import json
import uefi
from time import sleep


def get_daxdevs():
    try:
        dax = sp.run(["daxctl", "list"], capture_output=True).stdout.decode()
        return json.loads(dax)
    except Exception:
        return []


def dax_mem_online(dev):
    if "online_memblocks" in dev and dev["online_memblocks"] > 0:
        return True

    return False


def dax_mem_offline(dev):
    if "online_memblocks" not in dev or dev["online_memblocks"] == 0:
        return True

    if "state" in dev and dev["state"] == "disabled":
        return True

    return False


def dax_set_mode(devs, mode):
    if mode == "devdax":
        cmd = ["daxctl", "reconfigure-device", "--mode", "devdax"]
    elif mode == "system-ram":
        cmd = ["daxctl", "reconfigure-device", "--no-online", "--mode", "system-ram"]
    else:
        raise Exception(f"Invalid argument {mode}")

    if all(map(lambda dev: dev["mode"] == mode, devs)):
        return

    for dev in devs:
        if dax_mem_online(dev):
            raise Exception(f"{dev['chardev']} has onlined memory")

    for dev in devs:
        try:
            sp.run(cmd + [dev["chardev"]]).check_returncode()
        except Exception:
            raise Exception(f"failed to convert {dev['chardev']} to {mode} mode")


def dax_offline_mem(dev):
    if dax_mem_offline(dev):
        return

    try:
        sp.run(["daxctl", "offline-memory", dev["chardev"]]).check_returncode()
        sleep(0.5)
    except Exception:
        raise Exception(f"failed to offline memory for {dev['chardev']}")


def dax_online_mem(dev):
    if dax_mem_online(dev):
        return

    try:
        sp.run(["daxctl", "online-memory", dev["chardev"]]).check_returncode()
        sleep(0.5)
    except Exception:
        raise Exception(f"failed to online memory for {dev['chardev']}")

def dax_force_memory_state(devs, state="online"):
    if state == "online":
        func = dax_mem_online
    elif state == "offline":
        func = dax_mem_offline
    else:
        print(f"dax_force_memory_state: Invalid state: {state}")
        return

    for dev in devs:
        try:
            func(dev)
        except Exception:
            continue

def test_devdax_conversion():
    devs = get_daxdevs()

    for dev in devs:
        if dax_mem_online(dev):
            try:
                dax_offline_mem(dev)
            except Exception as e:
                print("FAIL: ", e)
                dax_force_memory_state(devs, "online")
                return False

    devs = get_daxdevs()
    try:
        dax_set_mode(devs, "devdax")
    except Exception as e:
        print("FAIL: ", e)
        return False

    return True


def test_sysram_mode():
    devs = get_daxdevs()
    for dev in devs:
        if dax_mem_online(dev):
            try:
                dax_offline_mem(dev)
            except Exception as e:
                print("FAIL: ", e)
                dax_force_memory_state(devs, "online")
                return False

    try:
        dax_set_mode(devs, "system-ram")
    except Exception as e:
        print("FAIL: ", e)
        return False

    failure = False
    for dev in get_daxdevs():
        try:
            dax_online_mem(dev)
        except Exception as e:
            failure = True
            print("FAIL: ", e)
            break

    devs = get_daxdevs()
    if not failure:
        for dev in devs:
            if dev["online_memblocks"] != dev["total_memblocks"]:
                print(f"FAIL: not all memory was onlined for {dev['chardev']}")
                failure = True
                break

    for dev in devs:
        try:
            dax_offline_mem(dev)
        except Exception as e:
            if not failure:
                print("FAIL: ", e)

            failure = True

    return not failure


def prereqs_met():
    if not which("daxctl"):
        print("CANCEL: daxctl utility not installed")
        return False

    if len(get_daxdevs()) == 0:
        print("CANCEL: No DAX devices found")
        return False

    spm = uefi.UefiSetting({"CXL Memory Attribute": "Enabled"})
    spm_set = spm.is_set()
    if spm_set is None:
        print("WARNING: Could not verify SPM is set")
    elif not spm_set:
        print("CANCEL: SPM not enabled")
        return False

    return True


if __name__ == "__main__":
    if not prereqs_met():
        exit(0)

    if test_devdax_conversion():
        print("PASS: devdax mode")
    else:
        exit(1)

    if test_sysram_mode():
        print("PASS: system-ram mode")
    else:
        exit(1)
