/* SPDX-License-Identifier: GPL-2.0-only
 * Copyright (C) 2025 Advanced Micro Devices, Inc.
 * Author: Ravi Bangoria <ravi.bangoria@amd.com>
 * File Name: bus_lock.c
 * Description: Bus lock trap test app to check if the system locks the bus while the CPU accesses the two cache lines.
 */

#include <stdio.h>

struct s {
        char b[62];
        int c;
} __attribute__ ((packed));

struct s s __attribute__((aligned(64)));

/*
 * Atomically add 10 *v using "lock addl" instruction.
 * Since *v crosses the cache line boundary, updating it atomically requires to take Bus Lock.
 */
static void atomic_add(int i, int *v)
{
        asm volatile("lock addl %1,%0"
                     : "+m" (*v)
                     : "ir" (i) : "memory");
}

int main()
{
        atomic_add(10, &s.c);
	/* printf("%d\n", s.c); */
        return s.c;
}
