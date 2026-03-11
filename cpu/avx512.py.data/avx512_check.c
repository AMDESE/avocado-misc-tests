/*
 * avx512_check.c - AVX-512 CPUID detection and functional correctness dispatcher
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * Copyright (C) 2025 AMD Inc.
 *
 * Usage:
 *   ./avx512_check detect          - Detect AVX-512 subsets via CPUID
 *   ./avx512_check verify <flag>   - Functional correctness test for a subset
 *   ./avx512_check verify_all      - Run all applicable functional tests
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* ------------------------------------------------------------------ */
/* CPUID helpers                                                       */
/* ------------------------------------------------------------------ */

struct cpuid_regs {
	unsigned int eax;
	unsigned int ebx;
	unsigned int ecx;
	unsigned int edx;
};

static inline void native_cpuid(unsigned int *eax, unsigned int *ebx,
				unsigned int *ecx, unsigned int *edx)
{
	asm volatile("cpuid"
		: "=a" (*eax),
		  "=b" (*ebx),
		  "=c" (*ecx),
		  "=d" (*edx)
		: "0" (*eax), "2" (*ecx)
		: "memory");
}

static inline struct cpuid_regs cpuid_read(unsigned int leaf,
					   unsigned int subleaf)
{
	struct cpuid_regs regs;

	regs.eax = leaf;
	regs.ecx = subleaf;
	native_cpuid(&regs.eax, &regs.ebx, &regs.ecx, &regs.edx);
	return regs;
}

static inline int xgetbv_check(void)
{
	unsigned int eax, edx;

	asm volatile(".byte 0x0f,0x01,0xd0"
		: "=a" (eax), "=d" (edx)
		: "c" (0));
	/*
	 * Bits 2 (SSE state), 5 (opmask), 6 (ZMM_Hi256), 7 (Hi16_ZMM)
	 * must all be set for AVX-512 to be OS-enabled.
	 */
	return ((eax & 0xe6) == 0xe6) ? 1 : 0;
}

/* ------------------------------------------------------------------ */
/* CPUID leaf 7 bit definitions for AVX-512 subsets                   */
/* ------------------------------------------------------------------ */

struct avx512_flag {
	const char *name;
	unsigned int leaf;
	unsigned int subleaf;
	char reg;          /* 'b' = EBX, 'c' = ECX, 'd' = EDX, 'a' = EAX */
	unsigned int bit;
};

static const struct avx512_flag avx512_flags[] = {
	/* Leaf 7, subleaf 0, EBX */
	{ "avx512f",          0x7, 0x0, 'b', 16 },
	{ "avx512dq",         0x7, 0x0, 'b', 17 },
	{ "avx512ifma",       0x7, 0x0, 'b', 21 },
	{ "avx512cd",         0x7, 0x0, 'b', 28 },
	{ "avx512bw",         0x7, 0x0, 'b', 30 },
	{ "avx512vl",         0x7, 0x0, 'b', 31 },
	/* Leaf 7, subleaf 0, ECX */
	{ "avx512vbmi",       0x7, 0x0, 'c',  1 },
	{ "avx512_vbmi2",      0x7, 0x0, 'c',  6 },
	{ "avx512_vnni",       0x7, 0x0, 'c', 11 },
	{ "avx512_bitalg",     0x7, 0x0, 'c', 12 },
	{ "avx512_vpopcntdq", 0x7, 0x0, 'c', 14 },
};

#define NR_FLAGS (sizeof(avx512_flags) / sizeof(avx512_flags[0]))

static int flag_present(const struct avx512_flag *f)
{
	struct cpuid_regs regs = cpuid_read(f->leaf, f->subleaf);
	unsigned int val;

	switch (f->reg) {
	case 'a': val = regs.eax; break;
	case 'b': val = regs.ebx; break;
	case 'c': val = regs.ecx; break;
	case 'd': val = regs.edx; break;
	default:  return 0;
	}
	return (val >> f->bit) & 1;
}

/* ------------------------------------------------------------------ */
/* detect: print all AVX-512 flags detected via CPUID                 */
/* ------------------------------------------------------------------ */

static int cmd_detect(void)
{
	unsigned int i;
	int any = 0;

	struct cpuid_regs regs = cpuid_read(0x1, 0x0);
	int osxsave = (regs.ecx >> 27) & 1;

	if (!osxsave) {
		printf("OSXSAVE not enabled; OS has not enabled XSAVE\n");
		return 1;
	}

	if (!xgetbv_check()) {
		printf("OS has not enabled AVX-512 state in XCR0\n");
		return 1;
	}

	for (i = 0; i < NR_FLAGS; i++) {
		if (flag_present(&avx512_flags[i])) {
			printf("%s\n", avx512_flags[i].name);
			any = 1;
		}
	}

	if (!any) {
		printf("NONE\n");
		return 1;
	}
	return 0;
}

/* ------------------------------------------------------------------ */
/* External test-suite entry points (one per AVX-512 subset file)     */
/* ------------------------------------------------------------------ */

extern int test_avx512f_all(void);
extern int test_avx512bw_all(void);
extern int test_avx512dq_all(void);
extern int test_avx512cd_all(void);
extern int test_avx512vl_all(void);
extern int test_avx512ifma_all(void);
extern int test_avx512vbmi_all(void);
extern int test_avx512vbmi2_all(void);
extern int test_avx512vnni_all(void);
extern int test_avx512bitalg_all(void);
extern int test_avx512vpopcntdq_all(void);

/* ------------------------------------------------------------------ */
/* Dispatch table: maps flag name -> functional test suite             */
/* ------------------------------------------------------------------ */

struct func_test {
	const char *name;
	const char *prereq;
	int (*run)(void);
};

static const struct func_test func_tests[] = {
	{ "avx512f",            "avx512f",            test_avx512f_all },
	{ "avx512bw",           "avx512bw",           test_avx512bw_all },
	{ "avx512dq",           "avx512dq",           test_avx512dq_all },
	{ "avx512cd",           "avx512cd",           test_avx512cd_all },
	{ "avx512vl",           "avx512vl",           test_avx512vl_all },
	{ "avx512ifma",         "avx512ifma",         test_avx512ifma_all },
	{ "avx512vbmi",         "avx512vbmi",         test_avx512vbmi_all },
	{ "avx512_vbmi2",       "avx512_vbmi2",       test_avx512vbmi2_all },
	{ "avx512_vnni",        "avx512_vnni",        test_avx512vnni_all },
	{ "avx512_bitalg",      "avx512_bitalg",      test_avx512bitalg_all },
	{ "avx512_vpopcntdq",   "avx512_vpopcntdq",   test_avx512vpopcntdq_all },
};

#define NR_FUNC_TESTS (sizeof(func_tests) / sizeof(func_tests[0]))

static const struct avx512_flag *find_flag(const char *name)
{
	unsigned int i;

	for (i = 0; i < NR_FLAGS; i++) {
		if (strcmp(avx512_flags[i].name, name) == 0)
			return &avx512_flags[i];
	}
	return NULL;
}

static int cmd_verify(const char *name)
{
	unsigned int i;

	for (i = 0; i < NR_FUNC_TESTS; i++) {
		if (strcmp(func_tests[i].name, name) == 0) {
			const struct avx512_flag *f = find_flag(func_tests[i].prereq);
			if (!f || !flag_present(f)) {
				printf("SKIP %s: CPUID flag %s not present\n",
				       name, func_tests[i].prereq);
				return 2;
			}
			return func_tests[i].run();
		}
	}
	printf("ERROR: no functional test for '%s'\n", name);
	return 1;
}

static int cmd_verify_all(void)
{
	unsigned int i;
	int total = 0, passed = 0, failed = 0, skipped = 0;

	for (i = 0; i < NR_FUNC_TESTS; i++) {
		const struct avx512_flag *f = find_flag(func_tests[i].prereq);
		int rc;

		total++;
		if (!f || !flag_present(f)) {
			printf("SKIP %s: CPUID flag %s not present\n",
			       func_tests[i].name, func_tests[i].prereq);
			skipped++;
			continue;
		}
		rc = func_tests[i].run();
		if (rc == 0)
			passed++;
		else
			failed++;
	}

	printf("\n=== Summary: %d total, %d passed, %d failed, %d skipped ===\n",
	       total, passed, failed, skipped);
	return failed > 0 ? 1 : 0;
}

/* ------------------------------------------------------------------ */

static void print_usage(const char *prog)
{
	printf("Usage:\n");
	printf("  %s detect                 - List AVX-512 flags via CPUID\n", prog);
	printf("  %s verify <flag_name>     - Run functional test for one flag\n", prog);
	printf("  %s verify_all             - Run all applicable functional tests\n", prog);
}

int main(int argc, char *argv[])
{
	if (argc < 2) {
		print_usage(argv[0]);
		return 1;
	}

	if (strcmp(argv[1], "detect") == 0)
		return cmd_detect();

	if (strcmp(argv[1], "verify") == 0) {
		if (argc < 3) {
			printf("ERROR: 'verify' needs a flag name\n");
			print_usage(argv[0]);
			return 1;
		}
		return cmd_verify(argv[2]);
	}

	if (strcmp(argv[1], "verify_all") == 0)
		return cmd_verify_all();

	print_usage(argv[0]);
	return 1;
}
